from constructs import Construct
from os import environ
from aws_cdk import (
    Stack,
    aws_lambda,
    aws_lambda_event_sources as event_sources,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subscriptions,
    aws_sqs as sqs
)
from build_utils import build


class DiscordNotifyStack(Stack):
    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            sns_topics: [sns.Topic],
            **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        build.build_lambda("discord_notify")

        discord_notify_function_id: str = f"{environ['PROJECT_NAME']}-discord-notify-lambda"

        # SQS Queue
        self.discord_notify_queue = sqs.Queue(
            self,
            "DiscordNotifyQueue",
            queue_name="DiscordNotifyQueue.fifo",
            fifo=True,
            content_based_deduplication=False,
            deduplication_scope=sqs.DeduplicationScope.MESSAGE_GROUP,
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=2,
                queue=sqs.Queue(
                    self, "DiscordNotifyDLQ",
                    queue_name="DiscordNotifyDLQ.fifo",
                    content_based_deduplication=False,
                    deduplication_scope=sqs.DeduplicationScope.MESSAGE_GROUP,
                    fifo=True
                )
            )
        )

        for sns_topic in sns_topics:
            sns_topic.add_subscription(sns_subscriptions.SqsSubscription(self.discord_notify_queue))

        self.discord_notify_function = aws_lambda.Function(
            scope=self,
            id=discord_notify_function_id,
            function_name=discord_notify_function_id,
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            handler="handler.handler",
            code=aws_lambda.Code.from_asset("./discord_notify/build.zip"),
            environment={
                "TZ": environ["TZ"],
                "DISCORD_WEBHOOK_URL": environ["DISCORD_WEBHOOK_URL"]
            }
        )

        self.discord_notify_function.add_event_source(
            event_sources.SqsEventSource(
                self.discord_notify_queue,
                batch_size=1
            )
        )
