"""Configuracion parametrizada de la infra del chatbot UPC.

Dos perfiles, GENUINAMENTE distintos:

- ``frugal`` : ARQUITECTURA REAL (lo que la tesis corre de verdad).
               1 sola EC2 Graviton (t4g) en subnet publica con docker-compose
               (FastAPI + Celery + Next.js + Redis + Postgres/pgvector, todo en
               contenedores). SIN NAT, SIN ALB, SIN RDS, SIN ElastiCache.
               ~$24/mes (o menos). Con los $200 de credito sobra para toda la tesis.

- ``demo``   : ARQUITECTURA OBJETIVO (plan de continuidad / sustentacion).
               Alta disponibilidad: ALB + ASG multi-AZ + RDS Multi-AZ +
               ElastiCache con replica + SQS. ~$110/mes si corriera 24/7 -> se
               despliega en RAFAGAS para la demo y se destruye.

El perfil se elige con: ``cdk deploy --all -c mode=demo`` (default: frugal).

Optimizaciones aplicadas (ver conversacion de costos):
- Graviton (t4g) en todo: ~20% mas barato que t3, misma RAM.
- frugal sin NAT Gateway ($33/mes), sin ALB ($16), sin ElastiCache ($12),
  Postgres en contenedor en vez de RDS ($24).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class InfraConfig:
    mode: str
    single_node: bool          # True = frugal (1 EC2); False = demo (HA)
    instance_type: str         # tipo principal de computo
    # Red
    max_azs: int
    nat_gateways: int
    # Computo HA (solo demo)
    asg_min: int
    asg_max: int
    asg_desired: int
    # Datos gestionados (solo demo; en frugal van como contenedores)
    db_instance_type: str
    db_multi_az: bool
    db_allocated_storage: int
    db_backup_retention_days: int
    redis_node_type: str
    redis_replicas: int        # 0 = un nodo; >=1 = replication group HA
    # Costo estimado (informativo, USD/mes 24/7, us-east-1)
    est_monthly_usd: str


FRUGAL = InfraConfig(
    mode="frugal",
    single_node=True,
    instance_type="t4g.medium",   # 2 vCPU / 4 GB ARM — aguanta apps + SBERT + Redis + Postgres
    max_azs=1,
    nat_gateways=0,               # sin NAT: la VM esta en subnet publica
    # campos HA no usados en frugal (valores inocuos)
    asg_min=1, asg_max=1, asg_desired=1,
    db_instance_type="-", db_multi_az=False, db_allocated_storage=0, db_backup_retention_days=0,
    redis_node_type="-", redis_replicas=0,
    est_monthly_usd="~24 (1x t4g.medium con TODO adentro; ~12 con t4g.small o Postgres externo)",
)

DEMO = InfraConfig(
    mode="demo",
    single_node=False,
    instance_type="t4g.micro",    # Graviton en los ASG
    max_azs=2,
    nat_gateways=1,               # 1 NAT (no 2) para abaratar la rafaga
    asg_min=2,                    # 2 instancias en distintas AZ = sin punto unico de fallo
    asg_max=4,
    asg_desired=2,
    db_instance_type="t4g.micro",   # se envuelve en ec2.InstanceType -> sin prefijo "db."
    db_multi_az=True,             # standby automatico en otra AZ = failover (continuidad)
    db_allocated_storage=20,
    db_backup_retention_days=7,
    redis_node_type="cache.t4g.micro",
    redis_replicas=1,             # primario + 1 replica con failover automatico
    est_monthly_usd="~110 si 24/7 (ALB+NAT+ASG+RDS MultiAZ+ElastiCache) -> usar en rafagas",
)


def get_config(mode: str) -> InfraConfig:
    return {"frugal": FRUGAL, "demo": DEMO}.get(mode, FRUGAL)
