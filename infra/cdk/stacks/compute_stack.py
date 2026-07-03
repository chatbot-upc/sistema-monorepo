"""ComputeStack — ALB + Auto Scaling Groups (Next.js / FastAPI / Celery) + IAM.

Es la capa de computo del diagrama. El ALB reparte:
- ``/*``      -> Next.js (panel admin)
- ``/api/*``  -> FastAPI (webhook WhatsApp + REST)
Celery corre como worker (sin ALB) y escala segun la profundidad de la cola SQS.

Plan de continuidad: cada ASG reparte instancias en 2 AZ y reemplaza solas las
que fallen; el ALB hace health checks y saca de rotacion las instancias enfermas.

Cada ASG se etiqueta con ``Service=nextjs|fastapi|celery`` (se propaga a las
instancias). El user-data es el mismo para los 3 ASG: instala Docker+Compose+AWS
CLI, clona el repo, baja el ``.env`` de SSM y resuelve en tiempo de arranque su
propio rol leyendo ese tag, para levantar solo el perfil de
``docker-compose.demo.yml`` que le corresponde (ver docs/superpowers/specs/
2026-07-03-demo-deploy-completion-design.md).
"""
from aws_cdk import Stack, CfnOutput, Duration, Tags
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_autoscaling as autoscaling
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_sqs as sqs
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct

from .config import InfraConfig

REPO_URL = "https://github.com/chatbot-upc/sistema-monorepo.git"
SSM_ENV_PARAM = "/chatbot-upc/demo/env"   # SecureString con el contenido del .env de demo


class ComputeStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        cfg: InfraConfig,
        vpc: ec2.IVpc,
        alb_sg: ec2.ISecurityGroup,
        app_sg: ec2.ISecurityGroup,
        queue: sqs.IQueue,
        docs_bucket: s3.IBucket,
        db_secret: secretsmanager.ISecret,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ---------------- IAM role compartido por las apps ----------------
        app_role = iam.Role(
            self,
            "AppInstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                # SSM Session Manager (acceso sin SSH / sin abrir puerto 22)
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchAgentServerPolicy"),
            ],
        )
        # Minimo privilegio sobre los recursos de datos
        queue.grant_consume_messages(app_role)
        queue.grant_send_messages(app_role)
        docs_bucket.grant_read_write(app_role)
        db_secret.grant_read(app_role)
        # Leer el .env de demo desde SSM
        app_role.add_to_policy(iam.PolicyStatement(
            actions=["ssm:GetParameter"],
            resources=[f"arn:aws:ssm:{self.region}:{self.account}:parameter{SSM_ENV_PARAM}"],
        ))
        # Resolver el propio rol (Service) leyendo el tag de la instancia en boot
        app_role.add_to_policy(iam.PolicyStatement(
            actions=["ec2:DescribeTags"],
            resources=["*"],  # DescribeTags no admite restriccion a nivel de recurso
        ))

        # AMI ARM (Graviton) — debe coincidir con instancias t4g del config
        ami = ec2.MachineImage.latest_amazon_linux2023(
            cpu_type=ec2.AmazonLinuxCpuType.ARM_64
        )
        # user-data comun a los 3 ASG: instala Docker+Compose+AWS CLI, clona el
        # repo, baja el .env de SSM y resuelve su propio Service (tag) en tiempo
        # de arranque para levantar solo ese perfil de docker-compose.demo.yml.
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "set -xe",
            "dnf update -y",
            "dnf install -y docker git unzip",
            "systemctl enable --now docker",
            "usermod -aG docker ec2-user",
            # AWS CLI v2 (ARM) para leer tags/SSM
            'curl -sSL "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o /tmp/awscliv2.zip',
            "unzip -q /tmp/awscliv2.zip -d /tmp && /tmp/aws/install",
            # Docker Compose v2 como plugin (binario aarch64)
            "mkdir -p /usr/local/lib/docker/cli-plugins",
            'curl -sSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-aarch64" '
            "-o /usr/local/lib/docker/cli-plugins/docker-compose",
            "chmod +x /usr/local/lib/docker/cli-plugins/docker-compose",
            # Codigo (repo publico) — idempotente: clona si no existe, si no actualiza
            "mkdir -p /opt/chatbot",
            f"if [ ! -d /opt/chatbot/.git ]; then git clone --depth 1 {REPO_URL} /opt/chatbot; "
            "else git -C /opt/chatbot pull --ff-only || true; fi",
            "cd /opt/chatbot",
            # Bajar el .env desde SSM (SecureString); el operador lo crea una vez
            f'aws ssm get-parameter --name "{SSM_ENV_PARAM}" --with-decryption '
            f'--region {self.region} --query Parameter.Value --output text > /opt/chatbot/.env || '
            'echo "WARN: falta el parametro SSM con el .env; crearlo y reiniciar docker compose"',
            # Resolver el propio rol (Service) via IMDSv2 + tag de la instancia
            'TOKEN=$(curl -sX PUT "http://169.254.169.254/latest/api/token" '
            '-H "X-aws-ec2-metadata-token-ttl-seconds: 21600")',
            'INSTANCE_ID=$(curl -sH "X-aws-ec2-metadata-token: $TOKEN" '
            'http://169.254.169.254/latest/meta-data/instance-id)',
            f'SERVICE=$(aws ec2 describe-tags --region {self.region} '
            '--filters "Name=resource-id,Values=$INSTANCE_ID" "Name=key,Values=Service" '
            '--query "Tags[0].Value" --output text)',
            # Levantar solo el perfil que le corresponde (imagenes ARM desde ghcr.io)
            "docker compose -f docker-compose.demo.yml --env-file .env pull || true",
            'docker compose -f docker-compose.demo.yml --env-file .env --profile "$SERVICE" up -d',
        )

        def make_asg(name: str, port: int) -> autoscaling.AutoScalingGroup:
            return autoscaling.AutoScalingGroup(
                self,
                name,
                vpc=vpc,
                vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                instance_type=ec2.InstanceType(cfg.instance_type),
                machine_image=ami,
                security_group=app_sg,
                role=app_role,
                user_data=user_data,
                min_capacity=cfg.asg_min,
                max_capacity=cfg.asg_max,
                desired_capacity=cfg.asg_desired,
                health_check=autoscaling.HealthCheck.elb(grace=Duration.minutes(3)),
            )

        self.nextjs_asg = make_asg("NextjsAsg", 3000)
        self.fastapi_asg = make_asg("FastApiAsg", 8000)
        # Celery: worker sin health check de ELB (no recibe trafico HTTP)
        self.celery_asg = autoscaling.AutoScalingGroup(
            self,
            "CeleryAsg",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            instance_type=ec2.InstanceType(cfg.instance_type),
            machine_image=ami,
            security_group=app_sg,
            role=app_role,
            user_data=user_data,
            min_capacity=cfg.asg_min,
            max_capacity=cfg.asg_max,
            desired_capacity=cfg.asg_desired,
        )

        # Tag Service (propagado a las instancias): el user-data lo lee en boot
        # para saber que perfil de docker-compose.demo.yml levantar.
        Tags.of(self.nextjs_asg).add("Service", "nextjs")
        Tags.of(self.fastapi_asg).add("Service", "fastapi")
        Tags.of(self.celery_asg).add("Service", "celery")
        # Celery escala segun cuantos mensajes esperan en la cola (continuidad de proceso)
        self.celery_asg.scale_on_metric(
            "ScaleOnQueueDepth",
            metric=queue.metric_approximate_number_of_messages_visible(),
            scaling_steps=[
                autoscaling.ScalingInterval(upper=10, change=0),
                autoscaling.ScalingInterval(lower=10, change=+1),
                autoscaling.ScalingInterval(lower=50, change=+2),
            ],
            adjustment_type=autoscaling.AdjustmentType.CHANGE_IN_CAPACITY,
        )

        # ---------------- Application Load Balancer ----------------
        self.alb = elbv2.ApplicationLoadBalancer(
            self,
            "Alb",
            vpc=vpc,
            internet_facing=True,
            security_group=alb_sg,
        )

        # En la arquitectura objetivo este listener seria 443 con cert ACM.
        # Para la demo usamos 80 (DNS del ALB) y dejamos HTTPS documentado.
        listener = self.alb.add_listener("Http", port=80, open=True)

        # Default -> Next.js
        listener.add_targets(
            "NextjsTarget",
            port=3000,
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[self.nextjs_asg],
            health_check=elbv2.HealthCheck(path="/", healthy_http_codes="200-399"),
        )
        # /api/* -> FastAPI
        listener.add_targets(
            "FastApiTarget",
            port=8000,
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[self.fastapi_asg],
            priority=10,
            conditions=[elbv2.ListenerCondition.path_patterns(["/api/*", "/health"])],
            health_check=elbv2.HealthCheck(path="/health", healthy_http_codes="200-399"),
        )

        # Escalado por CPU de las apps web
        for asg in (self.nextjs_asg, self.fastapi_asg):
            asg.scale_on_cpu_utilization("CpuScaling", target_utilization_percent=65)

        CfnOutput(self, "AlbDnsName", value=self.alb.load_balancer_dns_name)
