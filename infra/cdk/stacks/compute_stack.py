"""ComputeStack — ALB + Auto Scaling Groups (Next.js / FastAPI / Celery) + IAM.

Es la capa de computo del diagrama. El ALB reparte:
- ``/*``      -> Next.js (panel admin)
- ``/api/*``  -> FastAPI (webhook WhatsApp + REST)
Celery corre como worker (sin ALB) y escala segun la profundidad de la cola SQS.

Plan de continuidad: cada ASG reparte instancias en 2 AZ y reemplaza solas las
que fallen; el ALB hace health checks y saca de rotacion las instancias enfermas.

Nota: el user-data deja Docker instalado como punto de arranque. El despliegue
real de los contenedores (imagenes de apps/web y apps/api) se hace via CI/CD o
docker compose; aqui se modela la INFRA, no el build de las apps.
"""
from aws_cdk import Stack, CfnOutput, Duration
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_autoscaling as autoscaling
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_sqs as sqs
from aws_cdk import aws_secretsmanager as secretsmanager
from constructs import Construct

from .config import InfraConfig


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

        # AMI ARM (Graviton) — debe coincidir con instancias t4g del config
        ami = ec2.MachineImage.latest_amazon_linux2023(
            cpu_type=ec2.AmazonLinuxCpuType.ARM_64
        )
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "dnf update -y",
            "dnf install -y docker",
            "systemctl enable --now docker",
            "usermod -aG docker ec2-user",
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
