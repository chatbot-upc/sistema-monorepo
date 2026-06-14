"""FrugalStack — ARQUITECTURA REAL: 1 sola EC2 con todo en docker-compose.

Es lo que la tesis corre de verdad. Una unica instancia Graviton (t4g) en una
subnet PUBLICA (sin NAT) que levanta, via docker-compose, todos los servicios
como contenedores: FastAPI + Celery + Next.js + Redis + Postgres/pgvector + Caddy.

Costo ~$24/mes (1x t4g.medium). Sin NAT, ALB, RDS ni ElastiCache.

Reparto de responsabilidades:
- CDK (este stack): red minima, EC2 + IP fija, IAM, y un user-data que instala
  Docker + Compose v2 (ARM), clona el repo publico y hace `docker compose up`.
- CI (GitHub Actions): construye y publica las imagenes ARM en ghcr.io.
- Operador (1 vez): sube el contenido del .env como SecureString en SSM
  (`/chatbot-upc/frugal/env`); el user-data lo baja al arrancar.
"""
from aws_cdk import Stack, CfnOutput, RemovalPolicy
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3 as s3
from constructs import Construct

from .config import InfraConfig

REPO_URL = "https://github.com/chatbot-upc/sistema-monorepo.git"
SSM_ENV_PARAM = "/chatbot-upc/frugal/env"   # SecureString con el contenido del .env


class FrugalStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, cfg: InfraConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- Red minima: 1 subnet publica, SIN NAT (ahorra ~$33/mes) ---
        vpc = ec2.Vpc(
            self,
            "Vpc",
            ip_addresses=ec2.IpAddresses.cidr("10.1.0.0/16"),
            max_azs=1,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(name="public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24),
            ],
        )

        sg = ec2.SecurityGroup(
            self, "Sg", vpc=vpc,
            description="Chatbot UPC frugal - web publica", allow_all_outbound=True,
        )
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "HTTP")
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443), "HTTPS")
        # SSH no se abre: el acceso administrativo es por SSM Session Manager.

        # --- S3 para documentos (RAG) ---
        docs_bucket = s3.Bucket(
            self, "DocsBucket",
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # --- IAM: SSM Session Manager + leer el .env + S3 ---
        role = iam.Role(
            self, "InstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
            ],
        )
        docs_bucket.grant_read_write(role)
        role.add_to_policy(iam.PolicyStatement(
            actions=["ssm:GetParameter"],
            resources=[f"arn:aws:ssm:{self.region}:{self.account}:parameter{SSM_ENV_PARAM}"],
        ))

        # --- user-data: Docker + Compose v2 (ARM) + clonar repo + up ---
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(
            "set -xe",
            "dnf update -y",
            "dnf install -y docker git unzip",
            "systemctl enable --now docker",
            "usermod -aG docker ec2-user",
            # AWS CLI v2 (ARM) para leer el secreto desde SSM
            'curl -sSL "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o /tmp/awscliv2.zip',
            "unzip -q /tmp/awscliv2.zip -d /tmp && /tmp/aws/install",
            # Docker Compose v2 como plugin (binario aarch64) — NO el docker-compose v1 (deprecado)
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
            # Levantar todo (imagenes ARM desde ghcr.io)
            "docker compose -f docker-compose.prod.yml --env-file .env pull || true",
            "docker compose -f docker-compose.prod.yml --env-file .env up -d",
        )

        instance = ec2.Instance(
            self, "App",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            instance_type=ec2.InstanceType(cfg.instance_type),
            machine_image=ec2.MachineImage.latest_amazon_linux2023(
                cpu_type=ec2.AmazonLinuxCpuType.ARM_64
            ),
            security_group=sg,
            role=role,
            user_data=user_data,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvda",
                    volume=ec2.BlockDeviceVolume.ebs(30, volume_type=ec2.EbsDeviceVolumeType.GP3),
                ),
            ],
        )

        # IP fija (Elastic IP) para que la URL no cambie al reiniciar
        eip = ec2.CfnEIP(self, "Eip", domain="vpc")
        ec2.CfnEIPAssociation(
            self, "EipAssoc",
            allocation_id=eip.attr_allocation_id,
            instance_id=instance.instance_id,
        )

        CfnOutput(self, "PublicIp", value=eip.ref)
        CfnOutput(self, "DocsBucketName", value=docs_bucket.bucket_name)
        CfnOutput(self, "SsmEnvParam", value=SSM_ENV_PARAM)
        CfnOutput(self, "InstanceId", value=instance.instance_id)
