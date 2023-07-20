#!/usr/bin/env python3
import aws_cdk as cdk
from os import environ
from dotenv import load_dotenv
from cdk.cert_stack import CertStack
from cdk.dist_stack import DistStack
from cdk.func_stack import FuncStack

load_dotenv()

required_env_vars = [
    "AWS_ACCOUNT_ID",
    "AWS_DEFAULT_REGION",
    "CALENDAR_LINK",
    "PROJECT_NAME",
    "DOMAIN_NAME",
    "CORS_ALLOWED_DOMAIN"
]

default_optional_env_vars = {
    "ENABLE_CORS_ALLOWED_SECONDARY_DOMAIN": str(False),
    "CORS_ALLOWED_SECONDARY_DOMAIN": "http://localhost:8000",
    "EVENTS_PER_PAGE": "10"
}

# Make sure all required environment variables are present
for env_var in required_env_vars:
    if environ.get(env_var) is None:
        raise Exception(
            f"\n\nMissing environment variable: {env_var}"
            f"\nMake sure that you have created a .env file and added all the required environment variables."
            f"\nSee README.md for a list for required environment variables."
        )

# Set the default value for optional environment variables
for env_var in default_optional_env_vars.keys():
    environ.setdefault(env_var, default_optional_env_vars[env_var])


account = environ["AWS_ACCOUNT_ID"]
default_region = environ["AWS_DEFAULT_REGION"]

app = cdk.App()

cert_stack = CertStack(app, "CertStack", env=cdk.Environment(account=account, region="us-east-1"),
                       cross_region_references=True)

dist_stack = DistStack(app, "DistStack", cross_region_references=True,
                       env=cdk.Environment(account=account, region=default_region),
                       certificate=cert_stack.certificate)
dist_stack.add_dependency(cert_stack)

func_stack = FuncStack(
    app, "FuncStack",
    env=cdk.Environment(account=account, region=default_region),
    bucket=dist_stack.bucket, distribution=dist_stack.distribution
)
func_stack.add_dependency(dist_stack)

app.synth()
