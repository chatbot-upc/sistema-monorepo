"""NetworkStack — la VPC y todo el aislamiento de red.

Equivale a la "caja" VPC del diagrama: subnet publica (ALB), subnet privada
con egress (Next.js / FastAPI / Celery, que necesitan salir a OpenAI/Meta) y
subnet aislada (RDS / ElastiCache, sin salida a internet).

Tambien define los Security Groups (el firewall por recurso) con el principio de
minimo privilegio: cada capa solo acepta trafico de la capa anterior.
"""
from aws_cdk import Stack, CfnOutput
from aws_cdk import aws_ec2 as ec2
from constructs import Construct

from .config import InfraConfig


class NetworkStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, cfg: InfraConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- VPC: 1 linea crea VPC + subnets + IGW + NAT + route tables en N AZ ---
        self.vpc = ec2.Vpc(
            self,
            "Vpc",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=cfg.max_azs,
            nat_gateways=cfg.nat_gateways,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="app",  # privada con salida (NAT) para llamar a OpenAI/Meta
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="data",  # aislada: RDS y Redis NO salen a internet
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )

        # --- Security Groups (firewall por capa) ---
        self.alb_sg = ec2.SecurityGroup(
            self, "AlbSg", vpc=self.vpc,
            description="ALB - acepta HTTPS/HTTP desde internet", allow_all_outbound=True,
        )
        self.alb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443), "HTTPS publico")
        self.alb_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "HTTP publico (redirige a 443)")

        self.app_sg = ec2.SecurityGroup(
            self, "AppSg", vpc=self.vpc,
            description="Next.js / FastAPI / Celery", allow_all_outbound=True,
        )
        # Solo el ALB puede hablar con las apps
        self.app_sg.add_ingress_rule(self.alb_sg, ec2.Port.tcp(3000), "ALB -> Next.js")
        self.app_sg.add_ingress_rule(self.alb_sg, ec2.Port.tcp(8000), "ALB -> FastAPI")

        self.db_sg = ec2.SecurityGroup(
            self, "DbSg", vpc=self.vpc,
            description="RDS PostgreSQL", allow_all_outbound=False,
        )
        self.db_sg.add_ingress_rule(self.app_sg, ec2.Port.tcp(5432), "apps -> Postgres")

        self.redis_sg = ec2.SecurityGroup(
            self, "RedisSg", vpc=self.vpc,
            description="ElastiCache Redis", allow_all_outbound=False,
        )
        self.redis_sg.add_ingress_rule(self.app_sg, ec2.Port.tcp(6379), "apps -> Redis")

        CfnOutput(self, "VpcId", value=self.vpc.vpc_id)
