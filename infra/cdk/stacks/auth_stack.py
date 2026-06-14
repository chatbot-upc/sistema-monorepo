"""AuthStack — Cognito User Pool para el login del administrador del CRM.

Coincide con el diagrama: Administradores -> Route 53 -> Cognito (OAuth2/OIDC).
Como solo hay UN admin (proyecto de tesis), el auto-registro esta deshabilitado:
los usuarios se crean a mano desde la consola/CLI.
"""
from aws_cdk import Stack, CfnOutput, RemovalPolicy, Duration
from aws_cdk import aws_cognito as cognito
from constructs import Construct

from .config import InfraConfig


class AuthStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, cfg: InfraConfig, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.user_pool = cognito.UserPool(
            self,
            "AdminUserPool",
            user_pool_name=f"chatbot-upc-admins-{cfg.mode}",
            self_sign_up_enabled=False,            # solo el admin, creado manualmente
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=10,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=False,
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.DESTROY,  # tear-down limpio
        )

        # App client para el frontend Next.js (Auth.js v5 CredentialsProvider / OIDC)
        self.user_pool_client = self.user_pool.add_client(
            "WebClient",
            auth_flows=cognito.AuthFlow(user_password=True, user_srp=True),
            access_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30),
            prevent_user_existence_errors=True,
        )

        CfnOutput(self, "UserPoolId", value=self.user_pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=self.user_pool_client.user_pool_client_id)
