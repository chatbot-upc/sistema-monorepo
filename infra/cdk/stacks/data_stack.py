"""DataStack — capa de datos: RDS pgvector, ElastiCache Redis, S3, SQS.

Es el corazon del plan de continuidad:
- RDS Multi-AZ  -> failover automatico de base de datos.
- ElastiCache con replica -> failover de cache/contexto conversacional.
- SQS -> cola durable (los mensajes de WhatsApp no se pierden si Celery cae).
- S3  -> almacenamiento durable de documentos (11 nueves de durabilidad).
"""
from aws_cdk import Stack, CfnOutput, Duration, RemovalPolicy
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_rds as rds
from aws_cdk import aws_elasticache as elasticache
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_sqs as sqs
from constructs import Construct

from .config import InfraConfig


class DataStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        cfg: InfraConfig,
        vpc: ec2.IVpc,
        db_sg: ec2.ISecurityGroup,
        redis_sg: ec2.ISecurityGroup,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ---------------- RDS PostgreSQL + pgvector ----------------
        # pgvector se habilita con `CREATE EXTENSION vector;` (ver infra/docker/postgres/init.sql).
        # Postgres 16 soporta pgvector de forma nativa en RDS.
        self.db = rds.DatabaseInstance(
            self,
            "Postgres",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16
            ),
            instance_type=ec2.InstanceType(cfg.db_instance_type),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[db_sg],
            multi_az=cfg.db_multi_az,                      # <- failover automatico (continuidad)
            allocated_storage=cfg.db_allocated_storage,
            max_allocated_storage=cfg.db_allocated_storage * 2,
            backup_retention=Duration.days(cfg.db_backup_retention_days),
            # Credenciales auto-generadas y guardadas en Secrets Manager
            credentials=rds.Credentials.from_generated_secret(
                "chatbot_admin", secret_name=f"chatbot-upc/{cfg.mode}/db"
            ),
            database_name="chatbot",
            deletion_protection=False,                     # False -> permite tear-down (no quemar creditos)
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ---------------- ElastiCache Redis ----------------
        subnet_group = elasticache.CfnSubnetGroup(
            self,
            "RedisSubnetGroup",
            description="Subnets aisladas para Redis",
            subnet_ids=vpc.select_subnets(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ).subnet_ids,
        )

        if cfg.redis_replicas > 0:
            # Modo HA: replication group con failover automatico (continuidad)
            self.redis = elasticache.CfnReplicationGroup(
                self,
                "Redis",
                replication_group_description="Redis HA chatbot UPC",
                engine="redis",
                cache_node_type=cfg.redis_node_type,
                num_node_groups=1,
                replicas_per_node_group=cfg.redis_replicas,
                automatic_failover_enabled=True,
                multi_az_enabled=True,
                cache_subnet_group_name=subnet_group.ref,
                security_group_ids=[redis_sg.security_group_id],
            )
            self.redis_endpoint = self.redis.attr_primary_end_point_address
        else:
            # Modo frugal: un solo nodo
            self.redis = elasticache.CfnCacheCluster(
                self,
                "Redis",
                engine="redis",
                cache_node_type=cfg.redis_node_type,
                num_cache_nodes=1,
                cache_subnet_group_name=subnet_group.ref,
                vpc_security_group_ids=[redis_sg.security_group_id],
            )
            self.redis_endpoint = self.redis.attr_redis_endpoint_address

        self.redis.add_dependency(subnet_group)

        # ---------------- S3 (documentos para RAG) ----------------
        self.docs_bucket = s3.Bucket(
            self,
            "DocsBucket",
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            removal_policy=RemovalPolicy.DESTROY,          # tear-down limpio
            auto_delete_objects=True,
        )

        # ---------------- SQS (cola de mensajes WhatsApp) ----------------
        self.dlq = sqs.Queue(
            self,
            "DeadLetterQueue",
            retention_period=Duration.days(14),
        )
        self.queue = sqs.Queue(
            self,
            "MessagesQueue",
            visibility_timeout=Duration.seconds(120),       # > tiempo de proceso de Celery
            retention_period=Duration.days(4),
            dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=3, queue=self.dlq),
        )

        CfnOutput(self, "DbEndpoint", value=self.db.db_instance_endpoint_address)
        CfnOutput(self, "DbSecretArn", value=self.db.secret.secret_arn)
        CfnOutput(self, "RedisEndpoint", value=self.redis_endpoint)
        CfnOutput(self, "DocsBucketName", value=self.docs_bucket.bucket_name)
        CfnOutput(self, "QueueUrl", value=self.queue.queue_url)
