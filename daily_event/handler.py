import json
import boto3
from os import environ
from datetime import datetime, timedelta

sns_client = boto3.client('sns')
s3_client = boto3.client('s3')


def notify_event_is_tomorrow(calendar_event: dict):
    print(f"Notifying event tomorrow: {calendar_event['uid']}")
    return sns_client.publish(
        TopicArn=environ["DAILY_EVENT_TOPIC_ARN"],
        Message=str(json.dumps({
            "event": calendar_event
        }, ensure_ascii=False)),
        MessageGroupId="event_is_tomorrow"
    )


def get_file_from_s3(filename: str):
    return s3_client.get_object(
        Bucket=environ['BUCKET_NAME'],
        Key=filename,
    )['Body'].read().decode("utf-8")


def get_all_recurring_events() -> [dict]:
    index_json: str = get_file_from_s3("index.json")
    index_dict: dict = json.loads(index_json)
    return index_dict["events"]


def datetime_is_tomorrow(datetime_str: str) -> bool:
    tomorrow: datetime = datetime.now() + timedelta(days=1)
    return datetime.fromisoformat(datetime_str).date() == tomorrow.date()


def handler(event, _):
    try:
        recurring_events: [dict] = get_all_recurring_events()
        for calendar_event in recurring_events:
            if datetime_is_tomorrow(calendar_event["start"]):
                notify_event_is_tomorrow(calendar_event)
    except s3_client.exceptions.NoSuchKey:
        print(f"index.json was not found. Skipping daily events check")
        return False

