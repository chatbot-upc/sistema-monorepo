# Infraestructura como Código — Chatbot UPC (AWS CDK · Python)

IaC de la **arquitectura objetivo** del chatbot de matrícula UPC, usada como
**plan de continuidad** de la tesis. Compila a CloudFormation con `cdk synth`.

## Estructura

```
infra/cdk/
├── app.py                      # entrada CDK: orquesta los 5 stacks
├── cdk.json                    # "app": "uv run python app.py"
├── pyproject.toml              # deps gestionadas con uv
├── deploy_runbook.ipynb        # notebook: construir → outputs → destruir + doc
└── stacks/
    ├── config.py               # perfiles demo (HA) vs frugal (económico)
    ├── network_stack.py        # VPC 2 AZ, subnets, NAT, security groups
    ├── data_stack.py           # RDS Multi-AZ pgvector, ElastiCache, S3, SQS
    ├── auth_stack.py           # Cognito User Pool + client
    ├── compute_stack.py        # ALB + 3 ASG (Next/FastAPI/Celery) + IAM
    └── observability_stack.py  # CloudWatch dashboard + alarmas
```

## Perfiles (`-c mode=`)

| | `demo` (default) | `frugal` |
|---|---|---|
| Objetivo | Arquitectura objetivo / continuidad | Correr barato |
| ASG | 2–4 instancias/servicio, multi-AZ | 1 instancia/servicio |
| RDS | Multi-AZ (failover) | Single-AZ |
| Redis | Replication group + réplica | 1 nodo |
| Costo ~24/7 | ~$100–130/mes | ~$45–60/mes |

## Uso rápido

```bash
cd infra/cdk
uv sync                              # instala aws-cdk-lib en .venv
cdk synth --all                      # genera CloudFormation (entregable)
cdk diff  --all                      # previsualiza cambios
cdk bootstrap                        # solo la 1ª vez por cuenta/región
cdk deploy --all                     # ⚠️ empieza el gasto de créditos
# ... demo / capturas ...
cdk destroy --all                    # 🗑️ tear-down, detiene el gasto
```

Perfil económico: añade `-c mode=frugal` a cualquier comando.

> **Cuenta AWS**: post-15-jul-2025 → $200 en créditos (6 meses), no horas gratis.
> Desplegar en **ráfagas** y destruir al terminar. Ojo con el **NAT Gateway** (~$32/mes),
> el costo fijo más alto aunque no haya tráfico.

## Notas

- **pgvector**: RDS Postgres 16; habilitar `CREATE EXTENSION vector;` (ver
  `infra/docker/postgres/init.sql`). Credenciales en Secrets Manager `chatbot-upc/<mode>/db`.
- **HTTPS**: el ALB usa puerto 80 con su DNS por defecto para la demo. En la
  arquitectura objetivo sería 443 con certificado ACM + Route 53 (dominio propio).
- El user-data de las EC2 solo instala Docker; el despliegue de los contenedores
  de las apps se hace aparte (CI/CD o compose). Aquí se modela la **infra**.
