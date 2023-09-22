from constructs import Construct
from os import environ
from aws_cdk import (
    Stack,
    aws_sqs as sqs,
    aws_lambda,
    aws_logs as logs,
    Duration,
    aws_lambda_event_sources as event_sources,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subscriptions,
    CfnOutput,
)
from build_utils import build


class CalendarDiffStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        build.build_lambda("calendar_diff")

        cal_diff_function_id: str = f"{environ['PROJECT_NAME']}-calendar-diff-lambda"

        # SQS Queue
        self.calendar_diff_queue = sqs.Queue(
            self,
            "CalendarDiffQueue",
            queue_name="CalendarDiffQueue.fifo",
            fifo=True,
            content_based_deduplication=False,
            deduplication_scope=sqs.DeduplicationScope.MESSAGE_GROUP,
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=2,
                queue=sqs.Queue(
                    self, "CalendarDiffDLQ",
                    queue_name="CalendarDiffDLQ.fifo",
                    content_based_deduplication=False,
                    deduplication_scope=sqs.DeduplicationScope.MESSAGE_GROUP,
                    fifo=True
                )
            )
        )
        CfnOutput(
            scope=self,
            id="calendar_diff_queue_url",
            value=self.calendar_diff_queue.queue_url
        )

        # SNS topics
        self.events_changed_topic = sns.Topic(
            self, "EventsChangedTopic",
            topic_name="EventsChangedTopic",
            content_based_deduplication=True,
            fifo=True
        )
        self.events_changed_topic.add_subscription(sns_subscriptions.SqsSubscription(self.calendar_diff_queue))

        self.new_event_topic = sns.Topic(
            self,
            "NewEventTopic",
            topic_name="NewEventTopic",
            content_based_deduplication=True,
            fifo=True,
        )
        self.updated_event_topic = sns.Topic(
            self,
            "UpdatedEventTopic",
            topic_name="UpdatedEventTopic",
            content_based_deduplication=True,
            fifo=True
        )
        self.deleted_event_topic = sns.Topic(
            self,
            "DeletedEventTopic",
            topic_name="DeletedEventTopic",
            content_based_deduplication=True,
            fifo=True
        )
        self.topics = [self.new_event_topic, self.updated_event_topic, self.deleted_event_topic]

        # Lambda function
        self.calendar_diff_function = aws_lambda.Function(
            scope=self,
            id=cal_diff_function_id,
            function_name=cal_diff_function_id,
            runtime=aws_lambda.Runtime.PYTHON_3_9,
            handler="handler.handler",
            code=aws_lambda.Code.from_asset("./calendar_diff/build.zip"),
            log_retention=logs.RetentionDays.ONE_MONTH,
            timeout=Duration.seconds(10),
            environment={
                "TZ": environ["TZ"],
                "NEW_EVENT_TOPIC_ARN": self.new_event_topic.topic_arn,
                "UPDATED_EVENT_TOPIC_ARN": self.updated_event_topic.topic_arn,
                "DELETED_EVENT_TOPIC_ARN": self.deleted_event_topic.topic_arn,
            }
        )
        self.calendar_diff_function.add_event_source(
            event_sources.SqsEventSource(
                self.calendar_diff_queue,
                batch_size=1
            )
        )
        for topic in self.topics:
            topic.grant_publish(self.calendar_diff_function)
