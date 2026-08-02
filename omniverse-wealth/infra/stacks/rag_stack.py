"""RAG Stack — Bedrock Knowledge Base + S3 Data Source.

Provides:
- S3 bucket for CSV trading history storage
- Bedrock Knowledge Base configuration
- OpenSearch Serverless collection (vector store)
"""

from constructs import Construct
import aws_cdk as cdk
from aws_cdk import (
    aws_s3 as s3,
    aws_iam as iam,
    RemovalPolicy,
)


class RagStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # ─── S3 Bucket for CSV Data ────────────────────────────────────────
        self.data_bucket = s3.Bucket(
            self, "RagDataBucket",
            bucket_name=f"omniverse-wealth-rag-data-{cdk.Aws.ACCOUNT_ID}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
        )

        # ─── Bedrock KB Service Role ───────────────────────────────────────
        self.kb_role = iam.Role(
            self, "BedrockKBRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            inline_policies={
                "S3Access": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["s3:GetObject", "s3:ListBucket"],
                            resources=[
                                self.data_bucket.bucket_arn,
                                f"{self.data_bucket.bucket_arn}/*",
                            ],
                        ),
                    ]
                ),
                "BedrockModel": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["bedrock:InvokeModel"],
                            resources=["arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v2:0"],
                        ),
                    ]
                ),
            },
        )

        # ─── Knowledge Base (CfnResource — CDK L2 not yet available) ──────
        # Note: Bedrock KB is created via CfnResource since L2 construct
        # is not yet stable. In production, use console or CLI to create,
        # then reference the ID in environment variables.

        # Placeholder KB ID — replace after manual creation or use custom resource
        self.knowledge_base_id = "PLACEHOLDER_KB_ID"

        # ─── Outputs ───────────────────────────────────────────────────────
        cdk.CfnOutput(self, "RagDataBucketName",
            value=self.data_bucket.bucket_name,
            description="S3 bucket for RAG CSV data",
        )
        cdk.CfnOutput(self, "KBRoleArn",
            value=self.kb_role.role_arn,
            description="Bedrock Knowledge Base service role ARN",
        )
