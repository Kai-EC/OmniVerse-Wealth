"""Compute Stack — Lambda functions for Multi-Agent orchestration.

Provides:
- Agent handler: Main LangGraph multi-agent query processing
- WebSocket handlers: Connect/disconnect/message for real-time streaming
- Health handler: Simple health check endpoint
"""

from constructs import Construct
import aws_cdk as cdk
from aws_cdk import (
    aws_lambda as _lambda,
    aws_iam as iam,
    Duration,
)


class ComputeStack(cdk.Stack):
    def __init__(
        self, scope: Construct, id: str,
        secrets_stack,
        database_stack,
        rag_stack,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # ─── Shared Lambda Layer (dependencies) ─────────────────────────────
        deps_layer = _lambda.LayerVersion(
            self, "DepsLayer",
            code=_lambda.Code.from_asset("lambda/layers/deps"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            description="Shared dependencies: langchain, langgraph, boto3, httpx",
        )

        # ─── IAM Role for Agent Lambda ──────────────────────────────────────
        agent_role = iam.Role(
            self, "AgentLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        # Bedrock invoke permission
        agent_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
            ],
            resources=["arn:aws:bedrock:*::foundation-model/*"],
        ))

        # Bedrock Knowledge Base retrieve permission
        agent_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=[
                "bedrock:Retrieve",
                "bedrock:RetrieveAndGenerate",
            ],
            resources=["*"],
        ))

        # DynamoDB access
        database_stack.session_table.grant_read_write_data(agent_role)
        database_stack.risk_rules_table.grant_read_data(agent_role)

        # Secrets Manager read
        secrets_stack.max_api_secret.grant_read(agent_role)

        # ─── Agent Handler Lambda ───────────────────────────────────────────
        self.agent_handler = _lambda.Function(
            self, "AgentHandler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.main",
            code=_lambda.Code.from_asset("lambda/agent"),
            role=agent_role,
            timeout=Duration.seconds(60),
            memory_size=1024,
            layers=[deps_layer],
            environment={
                "SESSION_TABLE_NAME": database_stack.session_table.table_name,
                "RISK_RULES_TABLE_NAME": database_stack.risk_rules_table.table_name,
                "MAX_SECRET_ARN": secrets_stack.max_api_secret.secret_arn,
                "BEDROCK_MODEL_ID": "anthropic.claude-3-5-sonnet-20241022-v2:0",
                "BEDROCK_KB_ID": rag_stack.knowledge_base_id,
                "POWERTOOLS_SERVICE_NAME": "omniverse-agent",
            },
        )

        # ─── Health Check Lambda ────────────────────────────────────────────
        self.health_handler = _lambda.Function(
            self, "HealthHandler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="handler.health",
            code=_lambda.Code.from_asset("lambda/agent"),
            timeout=Duration.seconds(5),
            memory_size=128,
        )

        # ─── WebSocket Handlers ─────────────────────────────────────────────
        ws_role = iam.Role(
            self, "WebSocketLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )
        database_stack.session_table.grant_read_write_data(ws_role)

        # Allow WebSocket management API calls
        ws_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["execute-api:ManageConnections"],
            resources=["*"],
        ))

        self.ws_connect_handler = _lambda.Function(
            self, "WsConnectHandler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="ws_handler.on_connect",
            code=_lambda.Code.from_asset("lambda/websocket"),
            role=ws_role,
            timeout=Duration.seconds(10),
            memory_size=256,
            environment={
                "SESSION_TABLE_NAME": database_stack.session_table.table_name,
            },
        )

        self.ws_disconnect_handler = _lambda.Function(
            self, "WsDisconnectHandler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="ws_handler.on_disconnect",
            code=_lambda.Code.from_asset("lambda/websocket"),
            role=ws_role,
            timeout=Duration.seconds(10),
            memory_size=256,
            environment={
                "SESSION_TABLE_NAME": database_stack.session_table.table_name,
            },
        )

        self.ws_message_handler = _lambda.Function(
            self, "WsMessageHandler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="ws_handler.on_message",
            code=_lambda.Code.from_asset("lambda/websocket"),
            role=agent_role,
            timeout=Duration.seconds(60),
            memory_size=1024,
            layers=[deps_layer],
            environment={
                "SESSION_TABLE_NAME": database_stack.session_table.table_name,
                "RISK_RULES_TABLE_NAME": database_stack.risk_rules_table.table_name,
                "MAX_SECRET_ARN": secrets_stack.max_api_secret.secret_arn,
                "BEDROCK_MODEL_ID": "anthropic.claude-3-5-sonnet-20241022-v2:0",
                "BEDROCK_KB_ID": rag_stack.knowledge_base_id,
            },
        )

        # ─── Ticker Broadcaster Lambda (EventBridge scheduled) ──────────────
        self.ticker_broadcaster = _lambda.Function(
            self, "TickerBroadcaster",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="ws_handler.broadcast_ticker",
            code=_lambda.Code.from_asset("lambda/websocket"),
            role=ws_role,
            timeout=Duration.seconds(15),
            memory_size=256,
            environment={
                "SESSION_TABLE_NAME": database_stack.session_table.table_name,
                "WS_API_ENDPOINT": "",  # Set after WebSocket API is created
            },
        )
