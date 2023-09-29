from constructs import Construct
from os import environ
from aws_cdk import (
    Stack,
    aws_lambda,
    aws_sns as sns,
    aws_s3 as s3,
    aws_events as events,
    aws_events_targets as targets,
)
from build_utils import build


class DailyEventStack(Stack):
    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            events_bucket: s3.Bucket,
            **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        build.build_lambda("daily_event")

        daily_event_function_id: str = f"{environ['PROJECT_NAME']}-daily-event-lambda"
        rule_id: str = f"{environ['PROJECT_NAME']}-daily-event-lambda-trigger-rule"

        self.daily_event_topic = sns.Topic(
            self,
            "DailyEventTopic",
            topic_name="DailyEventTopic",
            content_based_deduplication=True,
            fifo=True,
        )

        self.daily_event_function = aws_lambda.Function(
            scope=self,
            id=daily_event_function_id,
            function_name=daily_event_function_id,
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            handler="handler.handler",
            code=aws_lambda.Code.from_asset("./daily_event/build.zip"),
            environment={
                "TZ": environ["TZ"],
                "BUCKET_NAME": events_bucket.bucket_name,
                "DAILY_EVENT_TOPIC_ARN": self.daily_event_topic.topic_arn
            }
        )
        events_bucket.grant_read(self.daily_event_function)
        self.daily_event_topic.grant_publish(self.daily_event_function)

        self.rule = events.Rule(
            scope=self,
            id=rule_id,
            rule_name=rule_id,
            schedule=events.Schedule.cron(
                hour="8",
                minute="0"
            ),
            targets=[targets.LambdaFunction(handler=self.daily_event_function)]
        )
