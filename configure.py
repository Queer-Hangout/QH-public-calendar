from os import environ
from dotenv import load_dotenv

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
    "TZ": "Europe/Oslo",
    "EVENTS_PER_PAGE": "10"
}


def configure_env():
    # Load .env file
    load_dotenv()

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

