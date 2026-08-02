"""Frontend Stack — S3 + CloudFront for static Next.js hosting.

Provides:
- S3 bucket for Next.js static export
- CloudFront distribution with OAC
- Custom error responses for SPA routing
"""

from constructs import Construct
import aws_cdk as cdk
from aws_cdk import (
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_s3_deployment as s3_deploy,
    RemovalPolicy,
)


class FrontendStack(cdk.Stack):
    def __init__(
        self, scope: Construct, id: str,
        api_stack,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # ─── S3 Bucket for Static Assets ───────────────────────────────────
        self.site_bucket = s3.Bucket(
            self, "SiteBucket",
            bucket_name=f"omniverse-wealth-frontend-{cdk.Aws.ACCOUNT_ID}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )

        # ─── CloudFront Distribution ──────────────────────────────────────
        self.distribution = cloudfront.Distribution(
            self, "SiteDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(
                    self.site_bucket,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
            ),
            default_root_object="index.html",
            error_responses=[
                # SPA fallback: return index.html for 403/404
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=cdk.Duration.seconds(0),
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=cdk.Duration.seconds(0),
                ),
            ],
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
        )

        # ─── S3 Deployment ─────────────────────────────────────────────────
        # Deploy the Next.js static export to S3
        s3_deploy.BucketDeployment(
            self, "DeploySite",
            sources=[s3_deploy.Source.asset("../frontend/out")],
            destination_bucket=self.site_bucket,
            distribution=self.distribution,
            distribution_paths=["/*"],
        )

        # ─── Outputs ───────────────────────────────────────────────────────
        cdk.CfnOutput(self, "CloudFrontUrl",
            value=f"https://{self.distribution.distribution_domain_name}",
            description="Frontend CloudFront URL",
        )
        cdk.CfnOutput(self, "SiteBucketName",
            value=self.site_bucket.bucket_name,
        )
