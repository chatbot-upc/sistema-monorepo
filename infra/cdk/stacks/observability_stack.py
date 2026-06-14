"""ObservabilityStack — CloudWatch: dashboard + alarmas.

Coincide con el nodo CloudWatch del diagrama (Metrics/HTTPS). Vigila las senales
clave del plan de continuidad: errores 5xx del ALB, profundidad de la cola SQS
(mensajes atascados) y CPU/almacenamiento de RDS.
"""
from aws_cdk import Stack
from aws_cdk import aws_cloudwatch as cw
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_rds as rds
from aws_cdk import aws_sqs as sqs
from constructs import Construct

from .config import InfraConfig


class ObservabilityStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        cfg: InfraConfig,
        alb: elbv2.IApplicationLoadBalancer,
        db: rds.IDatabaseInstance,
        queue: sqs.IQueue,
        dlq: sqs.IQueue,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        dashboard = cw.Dashboard(self, "Dashboard", dashboard_name=f"chatbot-upc-{cfg.mode}")

        # Alarma: errores 5xx del ALB (apps caidas o fallando)
        alb_5xx = alb.metrics.http_code_elb(elbv2.HttpCodeElb.ELB_5XX_COUNT)
        alarm_5xx = alb_5xx.create_alarm(
            self, "Alb5xxAlarm",
            threshold=10, evaluation_periods=2,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        # Alarma: mensajes atascados en la cola (Celery no da abasto o esta caido)
        queue_depth = queue.metric_approximate_number_of_messages_visible()
        alarm_queue = queue_depth.create_alarm(
            self, "QueueDepthAlarm",
            threshold=100, evaluation_periods=3,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        # Alarma: mensajes que llegaron a la DLQ (fallaron 3 veces -> requieren atencion)
        dlq_alarm = dlq.metric_approximate_number_of_messages_visible().create_alarm(
            self, "DlqAlarm",
            threshold=1, evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        )

        # Alarma: CPU de RDS alta
        db_cpu = db.metric_cpu_utilization()
        alarm_db = db_cpu.create_alarm(
            self, "DbCpuAlarm",
            threshold=80, evaluation_periods=3,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )

        dashboard.add_widgets(
            cw.GraphWidget(title="ALB 5xx", left=[alb_5xx]),
            cw.GraphWidget(title="SQS pendientes", left=[queue_depth]),
            cw.GraphWidget(title="RDS CPU", left=[db_cpu]),
        )
        dashboard.add_widgets(
            cw.AlarmStatusWidget(alarms=[alarm_5xx, alarm_queue, dlq_alarm, alarm_db]),
        )
