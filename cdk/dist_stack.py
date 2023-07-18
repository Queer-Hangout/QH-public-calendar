from aws_cdk import (
    Stack,
    aws_s3 as s3,
    RemovalPolicy,
    aws_cloudfront as cf,
    aws_cloudfront_origins as origins,
    CfnOutput
)
from constructs import Construct
from os import environ


class DistStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, certificate, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        distribution_id: str = f"{environ['PROJECT_NAME']}-events-distribution"
        bucket_id: str = f"{environ['PROJECT_NAME']}-events-bucket"

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
                origin=origins.S3Origin(self.bucket)
            ),
            default_root_object="index.json",
            domain_names=[environ["DOMAIN_NAME"]],
            certificate=certificate
        )

        CfnOutput(
            scope=self,
            id="distribution_domain_name",
            value=self.distribution.distribution_domain_name
        )
