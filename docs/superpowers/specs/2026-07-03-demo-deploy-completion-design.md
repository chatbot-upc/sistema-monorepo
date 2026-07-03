# Completar despliegue de contenedores en el perfil `demo`

**Fecha:** 2026-07-03
**Estado:** Aprobado, pendiente de plan de implementación

## Contexto

El repo tiene dos perfiles de infraestructura en `infra/cdk` (`stacks/config.py`):

- **`frugal`** (default, `cdk deploy --all`): arquitectura real que la tesis corre
  de verdad. 1 EC2 con todo en `docker-compose.prod.yml` (Postgres/pgvector, Redis,
  Caddy, API, worker, web). El `user_data` de `frugal_stack.py` instala Docker,
  clona el repo, baja el `.env` de SSM y hace `docker compose up -d`. El CD
  (`.github/workflows/deploy.yml` + `cicd_stack.py`) ya la mantiene actualizada.

- **`demo`** (`-c mode=demo`): arquitectura objetivo de alta disponibilidad (VPC
  2 AZ, RDS Multi-AZ, ElastiCache con réplica, ALB + 3 Auto Scaling Groups —
  Next.js / FastAPI / Celery —, Cognito, CloudWatch). Este perfil **nunca se ha
  desplegado realmente**, solo `cdk synth`.

## Problema

El perfil `demo` aprovisiona toda la infraestructura pero **no despliega la
aplicación**: el `user_data` de `compute_stack.py` solo instala Docker; no hay
ningún paso que baje imágenes ni levante contenedores. El CD (`deploy.yml`) solo
resuelve una instancia por tag `Mode=frugal`, así que tampoco cubre las
instancias de los ASG de `demo`. Sin esto, `cdk deploy --all -c mode=demo` deja
las instancias sin nada corriendo, y no se puede escribir un manual de
despliegue honesto (paso a paso, reproducible) para este perfil.

## Objetivo

Que `demo` quede funcionalmente equivalente a `frugal` en cuanto a "levantar la
app de punta a punta", adaptado a que cada ASG corre **un solo servicio** contra
datos gestionados externos (RDS/ElastiCache), no contenedores locales.

## Diseño

### 1. Compose por servicio (perfiles)

Nuevo `docker-compose.demo.yml` en la raíz, con 3 servicios activables por
`profiles` (sin `postgres`/`redis`/`caddy` locales — van a RDS/ElastiCache/ALB):

```yaml
services:
  api:
    profiles: ["fastapi"]
    image: ghcr.io/chatbot-upc/chatbot-api:${IMAGE_TAG:-latest}
    env_file: .env
    restart: unless-stopped
    ports:
      - "8000:8000"

  worker:
    profiles: ["celery"]
    image: ghcr.io/chatbot-upc/chatbot-api:${IMAGE_TAG:-latest}
    command: celery -A chatbot_api.core.celery_app worker --pool=solo --loglevel=info
    env_file: .env
    restart: unless-stopped

  web:
    profiles: ["nextjs"]
    image: ghcr.io/chatbot-upc/chatbot-web:${IMAGE_TAG:-latest}
    env_file: .env
    restart: unless-stopped
    ports:
      - "3000:3000"
```

El puerto expuesto en cada host debe coincidir con el target group del ALB
(`ComputeStack`: 3000 para Next.js, 8000 para FastAPI).

### 2. Cada instancia sabe su rol por tag

`compute_stack.py`: etiquetar cada ASG con `Service=nextjs|fastapi|celery` vía
`cdk.Tags.of(asg).add("Service", "<valor>")` (se propaga a las instancias
lanzadas). El `user_data` compartido se reemplaza por uno equivalente al de
`frugal_stack.py`:

1. `dnf install -y docker git unzip` + habilitar Docker.
2. Instalar AWS CLI v2 (ARM) y Docker Compose v2 (plugin, ARM).
3. Clonar/actualizar `/opt/chatbot` desde `REPO_URL`.
4. Bajar `.env` desde SSM `/chatbot-upc/demo/env` (`aws ssm get-parameter`).
5. Resolver el propio rol: `aws ec2 describe-tags --filters
   "Name=resource-id,Values=$INSTANCE_ID" "Name=key,Values=Service"` (vía IMDSv2
   para el instance-id).
6. `docker compose -f docker-compose.demo.yml --env-file .env --profile "$SERVICE" up -d`.

IAM: el `app_role` de `ComputeStack` necesita además `ec2:DescribeTags` y
`ssm:GetParameter` sobre `/chatbot-upc/demo/env` (ya tiene `db_secret.grant_read`,
`docs_bucket.grant_read_write`, permisos de la cola).

### 3. Migraciones (una sola vez, no en cada boot)

Con `asg_min=2`, correr `alembic upgrade head` en el `user_data` de cada
instancia FastAPI arriesgaría una carrera entre dos migraciones concurrentes en
el primer boot. En vez de eso, la migración **no** vive en el user-data: se
ejecuta como paso explícito y único —`ssm send-command` dirigido a **una sola**
instancia con `Service=fastapi`— disparado desde el propio flujo de despliegue
(manual la primera vez, luego desde el CD extendido). Es idempotente (alembic
no reaplica lo ya migrado), así que puede repetirse en cada deploy sin riesgo.

### 4. Config/secretos (`.env` de demo)

Nuevo parámetro SSM `/chatbot-upc/demo/env` (paralelo a
`/chatbot-upc/frugal/env`). A diferencia de frugal (`.env` 100% manual), en
demo `DATABASE_URL` y `REDIS_URL` dependen de outputs del `DataStack`
(`DbEndpoint`, `DbSecretArn`, `RedisEndpoint`) que solo se conocen **después**
de desplegar `ChatbotUpc-Data`. Orden documentado en el manual:

```
cdk deploy (Network, Data, Auth, Compute, Observability)
  → leer outputs (DbEndpoint, DbSecretArn, RedisEndpoint, DocsBucketName, QueueUrl,
                  UserPoolId, UserPoolClientId, AlbDnsName)
  → armar .env.demo (DATABASE_URL construido con el secret de Secrets Manager,
                     REDIS_URL, AWS_S3_BUCKET, SQS_QUEUE_URL, COGNITO_*, OPENAI_*, META_*)
  → aws ssm put-parameter --name /chatbot-upc/demo/env --type SecureString ...
  → reiniciar instancias del ASG (o esperar el próximo ciclo de CD)
```

### 5. Extender el CD para `demo`

`.github/workflows/deploy.yml` hoy asume una única instancia (`Mode=frugal`).
Se extiende para soportar ambos modos sin cambiar el comportamiento de frugal:

1. Resolver instancias `running` con tag `Project=chatbot-upc` (ambos modos).
2. Si hay instancias `Mode=frugal`: comportamiento actual, sin cambios.
3. Si hay instancias `Mode=demo`: agrupar por tag `Service`.
   - Enviar el comando de migración una sola vez a la primera instancia
     `Service=fastapi`.
   - Enviar `git pull && docker compose -f docker-compose.demo.yml --env-file .env
     pull && ... up -d --profile <service>` a **cada** instancia de cada grupo
     (loop sobre instance-ids), leyendo su `.env` fresco desde SSM
     `/chatbot-upc/demo/env` en cada una.
4. Mismo mecanismo de espera/verificación por `ssm get-command-invocation` ya
   existente, aplicado a cada `command_id`.

`cicd_stack.py`: el rol de deploy ya envía `ssm:SendCommand` a cualquier
instancia con tag `Project=chatbot-upc` (no filtra por `Mode`), así que no
necesita cambios de permisos para cubrir `demo`.

## Alcance explícito (fuera de esta iteración)

- **Sin TLS en el ALB** — ya documentado como pendiente en el código actual
  (`compute_stack.py` usa el listener HTTP:80); no se agrega ACM/Route 53 aquí.
- **Sin blue/green ni rolling update** — el redeploy reinicia contenedores
  in-place en cada instancia existente del ASG; aceptable para una ráfaga de
  demo/tesis, no para producción con tráfico real 24/7.
- **Sin lock distribuido para migraciones** — se resuelve por diseño (una sola
  instancia objetivo), no con `pg_advisory_lock` u otro mecanismo a nivel app.
- **No se corre `cdk deploy --all -c mode=demo` como parte de esta iteración**
  de código: se prueba con `cdk synth` (ya existente) y revisión manual de los
  templates generados. El despliegue real (que sí genera gasto en AWS) queda
  para cuando se redacte y valide el manual de despliegue.

## Relación con el manual de despliegue (anexo de tesis)

Este es un sub-proyecto previo al manual. Una vez implementado y validado
(`cdk synth` limpio, revisión de los templates y del `user_data` generado), se
retoma el diseño del **Manual de Despliegue** (anexo de tesis, `.docx`,
alcance = perfil `demo` completo, paso a paso reproducible, con diagrama de
arquitectura, sin capturas de pantalla) como spec independiente, documentando
ya el flujo real descrito arriba.

## Testing

- `cdk synth --all -c mode=demo` sin errores, y diff manual de
  `ChatbotUpc-Compute.template.json` (tags `Service` presentes, IAM con
  `ec2:DescribeTags` y el nuevo `ssm:GetParameter`).
- Lint/sintaxis de `docker-compose.demo.yml` (`docker compose -f
  docker-compose.demo.yml config`) para validar que los profiles y las envs
  referenciadas existen.
- Revisión manual del `user_data` renderizado (`cdk synth` incluye el script en
  el template) para confirmar que el flujo de bootstrap es equivalente al de
  `frugal_stack.py`.
- `deploy.yml`: no hay entorno de CI que lance EC2 reales, así que se valida
  con `act`/lectura manual del YAML + un dry-run comentado en el PR; la
  verificación end-to-end real ocurre en la ráfaga de despliegue real (fuera
  de esta iteración, ver Alcance).
