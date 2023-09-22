#!/usr/bin/env python3
import aws_cdk as cdk
from os import environ
from cdk.cert_stack import CertStack
from cdk.dist_stack import DistStack
from cdk.calendar_sync_stack import CalendarSyncStack
from cdk.calendar_diff_stack import CalendarDiffStack
from cdk.discord_notify_stack import DiscordNotifyStack
from configure import configure_env

configure_env()

account = environ["AWS_ACCOUNT_ID"]
default_region = environ["AWS_DEFAULT_REGION"]

app = cdk.App()

# Runs when the source calendar has changes. Processes old and new events and sends notifications upon updates
calendar_diff_stack = CalendarDiffStack(
    app, "CalendarDiffStack",
    env=cdk.Environment(account=account, region=default_region)
)

# Subscribes to any event changes from calendar_diff, and posts them to a Discord channel
discord_notify_stack = DiscordNotifyStack(
    app, "DiscordNotifyStack",
    sns_topics=[
        calendar_diff_stack.new_event_topic,
        calendar_diff_stack.updated_event_topic,
        calendar_diff_stack.deleted_event_topic
    ],
    env=cdk.Environment(account=account, region=default_region)
)
discord_notify_stack.add_dependency(calendar_diff_stack)

# Certificate for CloudFront distribution
cert_stack = CertStack(app, "CertStack", env=cdk.Environment(account=account, region="us-east-1"),
                       cross_region_references=True)

# CloudFront distribution for distributing processed event files
dist_stack = DistStack(app, "DistStack", cross_region_references=True,
                       env=cdk.Environment(account=account, region=default_region),
                       certificate=cert_stack.certificate)
dist_stack.add_dependency(cert_stack)

# Pulls the source calendar and processes the data into json format, distributing it to CloudFront.
# Notifies about any changes to the calendar, so that the changes may be processed by calendar_diff
calendar_sync_stack = CalendarSyncStack(
    app, "CalendarSyncStack",
    env=cdk.Environment(account=account, region=default_region),
    bucket=dist_stack.bucket, distribution=dist_stack.distribution,
    events_changed_topic=calendar_diff_stack.events_changed_topic
)
calendar_sync_stack.add_dependency(dist_stack)
calendar_sync_stack.add_dependency(calendar_diff_stack)

app.synth()
