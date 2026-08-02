"""Secrets Stack — AWS Secrets Manager for API credentials.

Stores:
- MAX Exchange API Key + Secret (with auto-rotation support)
- Third-party API keys (CoinMarketCap, etc.)
"""

from constructs import Construct
import aws_cdk as cdk
from aws_cdk import (
    aws_secretsmanager as secretsmanager,
)


class SecretsStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # ─── MAX Exchange API Credentials ───────────────────────────────────
        self.max_api_secret = secretsmanager.Secret(
            self, "MaxApiSecret",
            secret_name="omniverse-wealth/max-api",
            description="MAX Exchange API credentials (Access Key + Secret Key)",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"access_key": "", "secret_key": "", "enable_trading": "0"}',
                generate_string_key="placeholder",
                exclude_punctuation=True,
            ),
        )

        # ─── Third-party API Keys ──────────────────────────────────────────
        self.third_party_secrets = secretsmanager.Secret(
            self, "ThirdPartySecrets",
            secret_name="omniverse-wealth/third-party",
            description="Third-party API keys (CoinMarketCap, Blockchain.com, etc.)",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"coinmarketcap_key": "", "blockchain_key": ""}',
                generate_string_key="placeholder",
                exclude_punctuation=True,
            ),
        )

        # ─── Outputs ───────────────────────────────────────────────────────
        cdk.CfnOutput(self, "MaxApiSecretArn",
            value=self.max_api_secret.secret_arn,
            description="ARN of MAX API credentials secret",
        )
