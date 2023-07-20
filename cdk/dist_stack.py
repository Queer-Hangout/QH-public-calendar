from aws_cdk import (
    Stack,
    aws_s3 as s3,
    RemovalPolicy,
    aws_cloudfront as cf,
    aws_cloudfront_origins as origins,
    CfnOutput,
)
from constructs import Construct
from os import environ


class DistStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, certificate, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        distribution_id: str = f"{environ['PROJECT_NAME']}-events-distribution"
        bucket_id: str = f"{environ['PROJECT_NAME']}-events-bucket"
        response_headers_policy_id: str = f"{environ['PROJECT_NAME']}-events-distribution-rhp"

        self.bucket = s3.Bucket(
            scope=self,
            id=bucket_id,
            bucket_name=bucket_id,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        self.distribution = cf.Distribution(
            scope=self,
            id=distribution_id,
            default_behavior=cf.BehaviorOptions(
                allowed_methods=cf.AllowedMethods.ALLOW_GET_HEAD,
                cached_methods=cf.CachedMethods.CACHE_GET_HEAD,
                origin=origins.S3Origin(self.bucket),
                origin_request_policy=cf.OriginRequestPolicy.CORS_S3_ORIGIN,
                response_headers_policy=cf.ResponseHeadersPolicy(
                    scope=self,
                    id=response_headers_policy_id,
                    cors_behavior=cf.ResponseHeadersCorsBehavior(
                        access_control_allow_credentials=False,
                        access_control_allow_headers=['*'],
                        access_control_allow_methods=['GET'],
                        access_control_allow_origins=[
                            environ['CORS_ALLOWED_DOMAIN'],
                            environ['CORS_ALLOWED_SECONDARY_DOMAIN']
                        ] if eval(environ["ENABLE_CORS_ALLOWED_SECONDARY_DOMAIN"])
                        else [environ['CORS_ALLOWED_DOMAIN']],
                        origin_override=False
                    )
                )
            ),
            default_root_object="index.json",
            domain_names=[environ["DOMAIN_NAME"]],
            certificate=certificate,
        )

        CfnOutput(
            scope=self,
            id="distribution_domain_name",
            value=self.distribution.distribution_domain_name
        )
