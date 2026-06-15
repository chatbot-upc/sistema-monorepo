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
    ├── observability_stack.py  # CloudWatch dashboard + alarmas
    ├── frugal_stack.py         # arquitectura real: 1 EC2 con docker-compose
    └── cicd_stack.py           # CD: OIDC GitHub + rol de deploy (persistente)
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

## Variables de entorno (`.env`) — de dónde salen

El `.env` de **producción no se commitea ni pasa por GitHub**. La **fuente de verdad
es AWS SSM Parameter Store** (cifrado), en el parámetro `/chatbot-upc/frugal/env`.

```
TU PC (.env)  ──put-parameter (1 vez)──►  SSM /chatbot-upc/frugal/env  (fuente de verdad)
                                                  │ get-parameter
                                                  ▼
                                            EC2 → /opt/chatbot/.env  → docker compose
```

| Capa | Dónde vive | Quién lo lee |
|---|---|---|
| Local / dev | `.env` en la raíz (plantilla `.env.example`) | `docker-compose.yml` y las apps |
| Producción | SSM `/chatbot-upc/frugal/env` (SecureString) | user-data de la EC2 → `/opt/chatbot/.env` |
| CI / build | Secrets de GitHub Actions | los workflows |

**Subir / actualizar el `.env` (desde tu PC, cuando cambie una variable):**

```bash
aws ssm put-parameter \
  --name /chatbot-upc/frugal/env \
  --type SecureString \
  --value "$(cat .env)" \
  --region us-east-1 \
  --overwrite          # quitar la 1ª vez (solo al crearlo)
```

Tras esto, tu `.env` local ya no importa: en cada arranque/despliegue la EC2 baja la
copia de SSM. Editar una env = editar local + volver a correr `put-parameter` + un CD
o reinicio. Costo de SSM (parámetros standard): **$0**.

## CD — despliegue continuo

CI ya existe (`.github/workflows/`): `ci.yml` (lint+test) y `build-images.yml`
(publica imágenes ARM en ghcr.io). El CD lo cierra `deploy.yml` + el stack
`cicd_stack.py`: cuando `build-images` publica imágenes nuevas, avisa a la EC2 que
ya corre para que se actualice.

```
push a main → build-images (ghcr :latest) → deploy.yml
                                                 │ OIDC → rol IAM (ChatbotUpc-Cicd)
                                                 ▼ SSM Run Command (por tag)
                          EC2: git pull && docker compose pull && up -d && curl /health
```

- **Auth: GitHub OIDC → rol IAM** (sin access keys; el rol solo lo asume la rama `main`).
- **Target por tag** (`Project=chatbot-upc`, `Mode=frugal`), no por Instance ID → sobrevive
  al tear-down/re-deploy en ráfagas sin tocar nada.
- En cada deploy la EC2 re-baja el `.env` de SSM → las envs nuevas entran solas.
- **Health check**: tras `up -d` hace `curl http://localhost/health` (Caddy enruta
  `/health` → api); si la API no responde, el job de deploy queda **rojo**.
- GitHub Actions **nunca ve el contenido** del `.env`; solo dispara el comando, la EC2
  lo lee directo de SSM (rol de instancia con `ssm:GetParameter`).
- Único secret en GitHub: `AWS_DEPLOY_ROLE_ARN` (output `DeployRoleArn` de `ChatbotUpc-Cicd`).
- Si la EC2 está apagada (tear-down), no hay target → el deploy se **omite en verde**
  (esperado en el modelo de ráfagas).

### Puesta en marcha (1 vez)

```bash
cd infra/cdk
cdk deploy ChatbotUpc-Cicd          # persistente: NO se destruye en las ráfagas
# copiar el output DeployRoleArn y crearlo como secret de repo en GitHub:
#   Settings → Secrets and variables → Actions → New secret
#   name: AWS_DEPLOY_ROLE_ARN   value: <DeployRoleArn>
```

> **OIDC provider**: solo puede existir uno por cuenta. Si ya tienes uno de
> `token.actions.githubusercontent.com` (`aws iam list-open-id-connect-providers`),
> importa el existente en `cicd_stack.py` en vez de crear otro.

### Ciclo de vida (ráfagas)

`ChatbotUpc-Cicd` es persistente; la app sí se destruye para no quemar créditos.
**Nunca uses `--all`** para destruir (arrastraría el stack de CD):

```bash
cdk deploy  ChatbotUpc-Frugal       # levantar la app (empieza el gasto)
cdk destroy ChatbotUpc-Frugal       # tear-down de la ráfaga (NO --all)
```

## Notas

- **pgvector**: RDS Postgres 16; habilitar `CREATE EXTENSION vector;` (ver
  `infra/docker/postgres/init.sql`). Credenciales en Secrets Manager `chatbot-upc/<mode>/db`.
- **HTTPS**: el ALB usa puerto 80 con su DNS por defecto para la demo. En la
  arquitectura objetivo sería 443 con certificado ACM + Route 53 (dominio propio).
- El user-data de las EC2 solo instala Docker; el despliegue de los contenedores
  de las apps se hace aparte (CI/CD o compose). Aquí se modela la **infra**.
