"""CicdStack — identidad para el despliegue continuo (CD) desde GitHub Actions.

Ciclo de vida PROPIO, separado de la app:
- Se despliega UNA vez (`cdk deploy ChatbotUpc-Cicd`) y NO se destruye en las
  rafagas de tear-down (las rafagas solo tocan `ChatbotUpc-Frugal`). Asi el rol y
  su ARN son estables y el secret de GitHub se configura una sola vez.

Que hace:
- Crea el OIDC provider de GitHub (token.actions.githubusercontent.com).
- Crea un rol que SOLO puede asumir la rama `main` de este repo (sin llaves
  estaticas) y que SOLO puede mandar un SSM Run Command a la EC2 del proyecto.

El workflow `.github/workflows/deploy.yml` asume este rol via OIDC y dispara el
redeploy en la instancia (git pull + docker compose pull/up + health check).
"""
from aws_cdk import Stack, CfnOutput
from aws_cdk import aws_iam as iam
from constructs import Construct

# Repo que puede asumir el rol (debe coincidir con el remote real).
GITHUB_REPO = "chatbot-upc/sistema-monorepo"
GITHUB_OIDC_URL = "https://token.actions.githubusercontent.com"


class CicdStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- OIDC provider de GitHub (solo puede existir UNO por cuenta) ---
        # Si ya existe uno en la cuenta, importarlo con
        # iam.OpenIdConnectProvider.from_open_id_connect_provider_arn(...) en vez
        # de crearlo (ver README / Verificacion del plan).
        provider = iam.OpenIdConnectProvider(
            self,
            "GithubOidc",
            url=GITHUB_OIDC_URL,
            client_ids=["sts.amazonaws.com"],
        )

        # --- Rol de deploy: confianza acotada a main de este repo ---
        deploy_role = iam.Role(
            self,
            "GithubDeployRole",
            role_name="chatbot-upc-github-deploy",
            assumed_by=iam.WebIdentityPrincipal(
                provider.open_id_connect_provider_arn,
                conditions={
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                    },
                    "StringLike": {
                        "token.actions.githubusercontent.com:sub":
                            f"repo:{GITHUB_REPO}:ref:refs/heads/main",
                    },
                },
            ),
            description="GitHub Actions (main) -> SSM Run Command para redeploy de la EC2",
        )

        # Permiso 1a: usar el documento gestionado AWS-RunShellScript. Es público
        # de AWS y NO tiene el tag Project, así que va SIN condición (la condición
        # de tag aquí lo denegaría, que era el bug del deploy).
        deploy_role.add_to_policy(iam.PolicyStatement(
            actions=["ssm:SendCommand"],
            resources=[f"arn:aws:ssm:{self.region}::document/AWS-RunShellScript"],
        ))
        # Permiso 1b: enviar el comando SOLO a instancias del proyecto (tag).
        deploy_role.add_to_policy(iam.PolicyStatement(
            actions=["ssm:SendCommand"],
            resources=[f"arn:aws:ec2:{self.region}:{self.account}:instance/*"],
            conditions={
                "StringEquals": {"aws:ResourceTag/Project": "chatbot-upc"},
            },
        ))

        # Permiso 2: leer el resultado del comando (polling desde el workflow).
        deploy_role.add_to_policy(iam.PolicyStatement(
            actions=[
                "ssm:GetCommandInvocation",
                "ssm:ListCommandInvocations",
            ],
            resources=["*"],
        ))

        # Permiso 3: resolver el instance-id por tag antes de enviar el comando.
        deploy_role.add_to_policy(iam.PolicyStatement(
            actions=["ec2:DescribeInstances"],
            resources=["*"],
        ))

        CfnOutput(self, "DeployRoleArn", value=deploy_role.role_arn)
