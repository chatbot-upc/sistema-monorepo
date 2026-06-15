#!/usr/bin/env python3
"""Punto de entrada CDK — chatbot UPC.

Dos arquitecturas segun el contexto `mode`:

    cdk deploy --all                  # FRUGAL (real, 1 EC2, ~$24/mes)  [default]
    cdk deploy --all -c mode=demo     # DEMO (objetivo HA, ~$110/mes, en rafagas)

FRUGAL despliega un solo stack (1 EC2 con docker-compose).
DEMO despliega los 5 stacks de alta disponibilidad.
"""
import os
import aws_cdk as cdk

from stacks.config import get_config

app = cdk.App()

mode = app.node.try_get_context("mode") or "frugal"
cfg = get_config(mode)

env = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT"),
    region=os.getenv("CDK_DEFAULT_REGION", "us-east-1"),
)
prefix = "ChatbotUpc"
tags = {"Project": "chatbot-upc", "Mode": mode, "ManagedBy": "cdk"}
stacks = []

# ---------- CD: identidad para GitHub Actions (ciclo de vida propio) ----------
# Independiente del modo. Se despliega 1 vez y NO se destruye en las rafagas:
#   cdk deploy ChatbotUpc-Cicd      # persistente
#   cdk destroy ChatbotUpc-Frugal   # tear-down de rafaga (NO --all)
from stacks.cicd_stack import CicdStack

stacks.append(CicdStack(app, f"{prefix}-Cicd", env=env))

if cfg.single_node:
    # ---------- ARQUITECTURA REAL (frugal): 1 EC2 con todo ----------
    from stacks.frugal_stack import FrugalStack

    stacks.append(FrugalStack(app, f"{prefix}-Frugal", cfg=cfg, env=env))
else:
    # ---------- ARQUITECTURA OBJETIVO (demo): alta disponibilidad ----------
    from stacks.network_stack import NetworkStack
    from stacks.data_stack import DataStack
    from stacks.auth_stack import AuthStack
    from stacks.compute_stack import ComputeStack
    from stacks.observability_stack import ObservabilityStack

    network = NetworkStack(app, f"{prefix}-Network", cfg=cfg, env=env)
    data = DataStack(
        app, f"{prefix}-Data", cfg=cfg,
        vpc=network.vpc, db_sg=network.db_sg, redis_sg=network.redis_sg, env=env,
    )
    auth = AuthStack(app, f"{prefix}-Auth", cfg=cfg, env=env)
    compute = ComputeStack(
        app, f"{prefix}-Compute", cfg=cfg,
        vpc=network.vpc, alb_sg=network.alb_sg, app_sg=network.app_sg,
        queue=data.queue, docs_bucket=data.docs_bucket, db_secret=data.db.secret, env=env,
    )
    observability = ObservabilityStack(
        app, f"{prefix}-Observability", cfg=cfg,
        alb=compute.alb, db=data.db, queue=data.queue, dlq=data.dlq, env=env,
    )
    stacks.extend([network, data, auth, compute, observability])

# Etiquetas en todos los recursos (rastreo de costos en Cost Explorer)
for stack in stacks:
    for k, v in tags.items():
        cdk.Tags.of(stack).add(k, v)

app.synth()
