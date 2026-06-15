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

## Runbook: levantar la MV frugal de cero

Orden importante: **las imágenes deben existir en ghcr.io ANTES del `cdk deploy`**
(la EC2 hace `docker compose pull` al arrancar), y **el `.env` debe estar en SSM
ANTES del deploy** (el user-data lo baja en el primer boot).

**Fase 0 — Prerrequisitos (una vez)**
1. Credenciales AWS locales (`aws sts get-caller-identity` responde).
2. Cognito **ya existe** (frugal NO lo crea): ten tu User Pool + un usuario, y anota
   `USER_POOL_ID` y `CLIENT_ID`.
3. Bootstrap CDK: `cd infra/cdk && uv sync && uv run cdk bootstrap`.

**Fase 1 — Construir imágenes**
4. Merge `development` → `main` → `build-images.yml` publica
   `ghcr.io/chatbot-upc/chatbot-{api,web}:latest`. **Espera a que termine en verde.**
   (`deploy.yml` se dispara pero se omite: aún no hay EC2.)

**Fase 2 — Config a SSM**
5. Arma tu `.env.prod` (local, gitignoreado). Mínimo:
   ```bash
   AWS_S3_BUCKET=chatbot-upc-docs-<account_id>   # output DocsBucketName del FrugalStack
   COGNITO_USER_POOL_ID=...  COGNITO_CLIENT_ID=...  COGNITO_REGION=us-east-1
   ADMIN_EMAIL=tu-email@...  ADMIN_NAME=Tu Nombre
   PUBLIC_BASE_URL=https://remiai.tech
   DOMAIN=                                         # vacío al inicio (acceso por IP)
   # + DATABASE_URL/REDIS_URL (contenedores), OPENAI_*, META_*, etc.
   ```
6. Súbelo a SSM:
   ```bash
   aws ssm put-parameter --name /chatbot-upc/frugal/env --type SecureString \
     --value "$(cat .env.prod)" --region us-east-1 --overwrite
   ```

**Fase 3 — Levantar**
7. `cd infra/cdk && uv run cdk deploy ChatbotUpc-Frugal`. Anota el output `PublicIp`.
   ⚠️ Aquí empieza el gasto.

**Fase 4 — Verificar**
8. ~2-3 min (user-data instala Docker + `compose up`; el servicio `migrate` crea el
   esquema y siembra tu admin desde `ADMIN_EMAIL`).
9. `http://<PublicIp>/health` responde → entra al CRM y loguéate con Cognito.
10. Re-ingesta los PDFs al bucket nuevo (está vacío): `scripts/bulk_ingest.py`.

**Fase 5 — Dominio + HTTPS**
11. Registro `A`: `remiai.tech` → `PublicIp`. Verifica con `dig +short remiai.tech`.
12. Edita `.env.prod` → `DOMAIN=remiai.tech`, re-sube a SSM (`--overwrite`) y reinicia
    compose (o dispara el CD). Caddy saca el certificado solo.

> Cuando termines la ráfaga: `cdk destroy ChatbotUpc-Frugal` (NO `--all`).

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
