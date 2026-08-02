"""Database Stack — DynamoDB tables for session state and risk rules.

Tables:
- SessionTable: Stores user conversation sessions and agent intermediate states
- RiskRulesTable: Stores per-user risk control configuration
"""

from constructs import Construct
import aws_cdk as cdk
from aws_cdk import (
    aws_dynamodb as dynamodb,
    RemovalPolicy,
)


class DatabaseStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # ─── Session Table ──────────────────────────────────────────────────
        # Stores: user sessions, conversation history, agent intermediate states
        self.session_table = dynamodb.Table(
            self, "SessionTable",
            table_name="OmniVerseWealth-Sessions",
            partition_key=dynamodb.Attribute(
                name="session_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp", type=dynamodb.AttributeType.NUMBER
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl",
        )

        # GSI: Query sessions by user
        self.session_table.add_global_secondary_index(
            index_name="UserIndex",
            partition_key=dynamodb.Attribute(
                name="user_id", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp", type=dynamodb.AttributeType.NUMBER
            ),
        )

        # GSI: Query active WebSocket connections
        self.session_table.add_global_secondary_index(
            index_name="ConnectionIndex",
            partition_key=dynamodb.Attribute(
                name="connection_id", type=dynamodb.AttributeType.STRING
            ),
        )

        # ─── Risk Rules Table ───────────────────────────────────────────────
        # Stores: per-user risk parameters, global default rules
        self.risk_rules_table = dynamodb.Table(
            self, "RiskRulesTable",
            table_name="OmniVerseWealth-RiskRules",
            partition_key=dynamodb.Attribute(
                name="rule_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ─── Outputs ───────────────────────────────────────────────────────
        cdk.CfnOutput(self, "SessionTableName",
            value=self.session_table.table_name,
        )
        cdk.CfnOutput(self, "RiskRulesTableName",
            value=self.risk_rules_table.table_name,
        )
