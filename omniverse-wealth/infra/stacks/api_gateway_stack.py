"""API Gateway Stack — REST + WebSocket endpoints.

Provides:
- REST API for synchronous agent queries
- WebSocket API for real-time streaming (CoT + trade confirmations)
"""

from constructs import Construct
import aws_cdk as cdk
from aws_cdk import (
    aws_apigateway as apigw,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as integrations,
    aws_iam as iam,
)


class ApiGatewayStack(cdk.Stack):
    def __init__(
        self, scope: Construct, id: str,
        compute_stack,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # ─── REST API ───────────────────────────────────────────────────────
        self.rest_api = apigw.RestApi(
            self, "OmniVerseRestApi",
            rest_api_name="OmniVerse Wealth API",
            description="Multi-Agent AI Investment Assistant REST API",
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization"],
            ),
            deploy_options=apigw.StageOptions(
                stage_name="prod",
                throttling_rate=100,
                throttling_burst=200,
            ),
        )

        # POST /query — Main agent query endpoint
        query_resource = self.rest_api.root.add_resource("query")
        query_resource.add_method(
            "POST",
            apigw.LambdaIntegration(
                compute_stack.agent_handler,
                proxy=True,
            ),
        )

        # GET /health — Health check
        health_resource = self.rest_api.root.add_resource("health")
        health_resource.add_method(
            "GET",
            apigw.LambdaIntegration(compute_stack.health_handler),
        )

        # GET /portfolio — Portfolio summary
        portfolio_resource = self.rest_api.root.add_resource("portfolio")
        portfolio_resource.add_method(
            "GET",
            apigw.LambdaIntegration(compute_stack.agent_handler),
        )

        # ─── WebSocket API ──────────────────────────────────────────────────
        self.websocket_api = apigwv2.WebSocketApi(
            self, "OmniVerseWebSocketApi",
            api_name="OmniVerse Wealth WebSocket",
            description="Real-time streaming for Agent CoT and trade updates",
            connect_route_options=apigwv2.WebSocketRouteOptions(
                integration=integrations.WebSocketLambdaIntegration(
                    "ConnectIntegration",
                    handler=compute_stack.ws_connect_handler,
                ),
            ),
            disconnect_route_options=apigwv2.WebSocketRouteOptions(
                integration=integrations.WebSocketLambdaIntegration(
                    "DisconnectIntegration",
                    handler=compute_stack.ws_disconnect_handler,
                ),
            ),
            default_route_options=apigwv2.WebSocketRouteOptions(
                integration=integrations.WebSocketLambdaIntegration(
                    "DefaultIntegration",
                    handler=compute_stack.ws_message_handler,
                ),
            ),
        )

        self.websocket_stage = apigwv2.WebSocketStage(
            self, "OmniVerseWebSocketStage",
            web_socket_api=self.websocket_api,
            stage_name="prod",
            auto_deploy=True,
        )

        # ─── Outputs ───────────────────────────────────────────────────────
        cdk.CfnOutput(self, "RestApiUrl",
            value=self.rest_api.url,
            description="REST API endpoint URL",
        )
        cdk.CfnOutput(self, "WebSocketUrl",
            value=self.websocket_stage.url,
            description="WebSocket API endpoint URL",
        )
