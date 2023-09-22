from constructs import Construct
from os import environ
from aws_cdk import (
    Stack,
    aws_certificatemanager as cm
)


class CertStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        certificate_id: str = f"{environ['PROJECT_NAME']}-calendar-sync-events-distribution-cert"
        self.certificate = cm.Certificate(
            scope=self,
            id=certificate_id,
            certificate_name=certificate_id,
            domain_name=environ["DOMAIN_NAME"]
        )
