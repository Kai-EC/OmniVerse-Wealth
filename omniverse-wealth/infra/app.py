#!/usr/bin/env python3
"""OmniVerse Wealth - AWS CDK Application Entry Point.

Deploys the complete serverless infrastructure:
- API Gateway (REST + WebSocket)
- Lambda functions (Multi-Agent controller)
- DynamoDB (Session state + Risk rules)
- Secrets Manager (MAX API credentials)
- Bedrock Knowledge Base + S3 (CSV RAG)
- CloudFront + S3 (Frontend static hosting)
"""

import aws_cdk as cdk

from stacks.api_gateway_stack import ApiGatewayStack
from stacks.compute_stack import ComputeStack
from stacks.database_stack import DatabaseStack
from stacks.secrets_stack import SecretsStack
from stacks.rag_stack import RagStack
from stacks.frontend_stack import FrontendStack

app = cdk.App()

env = cdk.Environment(
    account=app.node.try_get_context("account") or None,
    region=app.node.try_get_context("region") or "us-east-1",
)

# Stack deployment order respects dependencies
secrets_stack = SecretsStack(app, "OmniVerseSecrets", env=env)
database_stack = DatabaseStack(app, "OmniVerseDatabase", env=env)
rag_stack = RagStack(app, "OmniVerseRag", env=env)

compute_stack = ComputeStack(
    app, "OmniVerseCompute",
    env=env,
    secrets_stack=secrets_stack,
    database_stack=database_stack,
    rag_stack=rag_stack,
)

api_stack = ApiGatewayStack(
    app, "OmniVerseApi",
    env=env,
    compute_stack=compute_stack,
)

frontend_stack = FrontendStack(
    app, "OmniVerseFrontend",
    env=env,
    api_stack=api_stack,
)

# Tags
for stack in [secrets_stack, database_stack, rag_stack, compute_stack, api_stack, frontend_stack]:
    cdk.Tags.of(stack).add("Project", "OmniVerseWealth")
    cdk.Tags.of(stack).add("Environment", "production")
    cdk.Tags.of(stack).add("Hackathon", "2026-AWS-MaiCoin")

app.synth()
