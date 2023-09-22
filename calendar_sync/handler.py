from model.calendar import Calendar, CalendarEvent
from datetime import datetime, timezone
import urllib.request as request
from os import environ
import boto3
import json
import math

s3_client = boto3.client('s3')
fetch_time = None


def fetch_ical_string() -> str:
    calendar_link = environ["CALENDAR_LINK"]
    print(f"Fetching ical at {calendar_link}")
    global fetch_time
    fetch_time = str(datetime.now(timezone.utc).isoformat())
    with request.urlopen(url=calendar_link, timeout=10) as response:
        body = response.read().decode('utf-8')
    return body


def get_paginated_recurring_events(calendar: Calendar) -> dict:
    per_page: int = int(environ['EVENTS_PER_PAGE'])
    if per_page < 0 or type(per_page) != int:
        raise ValueError("per_page must be a positive integer")

    result: dict = {}
    total_pages: int = math.ceil(len(calendar.recurring_events) / per_page)

    for page_number in range(total_pages):
        events_in_page = [event.to_dict() for event in calendar.recurring_events[
                                                       page_number * per_page: min((page_number + 1) * per_page,
                                                                                   len(calendar.recurring_events))
                                                       ]]
        result[page_number] = {
            "source-url": environ['CALENDAR_LINK'],
            "last-updated": fetch_time,
            "events-in-page": len(events_in_page),
            "total-events": len(calendar.recurring_events),
            "page": page_number,
            "total-pages": total_pages,
            "per-page": per_page,
            "has-more": page_number + 1 < total_pages,
            "events": events_in_page
        }
    return result


def get_file_from_s3(filename: str):
    return s3_client.get_object(
        Bucket=environ['BUCKET_NAME'],
        Key=filename,
    )['Body'].read().decode("utf-8")


def get_old_events() -> [CalendarEvent]:
    old_events_json = get_file_from_s3("events.json")
    old_events = json.loads(old_events_json)
    return [CalendarEvent.from_dict(event) for event in old_events]


def save_as_json(obj, filename: str):
    if type(obj) != list and type(obj) != dict:
        raise ValueError(f"Failed to save object as json. Object must be of type list or dict.")
    print(f"Writing file to S3: {filename}")
    return s3_client.put_object(
        Bucket=environ['BUCKET_NAME'],
        Key=filename,
        Body=bytes(json.dumps(obj, ensure_ascii=False), "utf-8"),
        ContentType="application/json"
    )


def notify_updates(old_events: [CalendarEvent], new_events: [CalendarEvent]):
    print("Changes in calendar detected. Notifying diff...")
    sns_client = boto3.client('sns')
    msg_body = {
        "old_events": [event.to_dict() for event in old_events],
        "new_events": [event.to_dict() for event in new_events]
    }
    sns_client.publish(
        TopicArn=environ["EVENTS_CHANGED_TOPIC_ARN"],
        Message=str(json.dumps(msg_body, ensure_ascii=False)),
        MessageGroupId="calendar_events_changed"
    )
    print("Message sent successfully")
    return


def check_for_updates(calendar: Calendar):
    try:
        old_events: [CalendarEvent] = get_old_events()
        new_events: [CalendarEvent] = calendar.events

        def notify():
            return notify_updates(old_events, new_events)

        return notify()

        if len(old_events) != len(new_events):
            return notify()

        for i in range(len(old_events)):
            if old_events[i] != new_events[i]:
                return notify()

    except s3_client.exceptions.NoSuchKey:
        print(f"events.json was not found. Skipping diff.")
        return False


def invalidate_cache():
    distribution_id: str = environ['DISTRIBUTION_ID']
    cf_client = boto3.client("cloudfront")

    print(f"Invalidating cache for distribution {distribution_id}")
    cf_client.create_invalidation(
        DistributionId=distribution_id,
        InvalidationBatch={
            "Paths": {
                "Quantity": 1,
                "Items": ["/*"]
            },
            "CallerReference": str(datetime.now())
        }
    )


def list_existing_pages() -> list:
    response = s3_client.list_objects_v2(
        Bucket=environ['BUCKET_NAME'],
        Prefix="pages/"
    )
    try:
        contents = response["Contents"]
    except KeyError:
        contents = []
    return contents


def get_expired_pages(total_pages: int, existing_pages: list) -> list:
    def file_is_expired(filename: str) -> bool:
        start_i = filename.rindex("/")
        end_i = filename.find(".")
        i = int(filename[start_i + 1:end_i])
        return i >= total_pages

    filenames = list(map(lambda file: file["Key"], list(existing_pages)))
    expired_files = list(map(lambda filename: {"Key": filename}, filter(file_is_expired, filenames)))
    return expired_files


def delete_objects(objects_to_delete: [str]) -> dict:
    total_deleted_pages: int = 0
    deleted_objects: list = []
    deletion_errors = []
    if len(objects_to_delete) > 0:
        print(f"Deleting {len(objects_to_delete)} files")
        res = s3_client.delete_objects(
            Bucket=environ['BUCKET_NAME'],
            Delete={
                "Objects": objects_to_delete
            }
        )
        total_deleted_pages = len(res["Deleted"])
        deleted_objects = res["Deleted"]

        try:
            deletion_errors = res["Errors"]
        except KeyError:
            deletion_errors = []
    return {
        "total-deleted-pages": total_deleted_pages,
        "deleted-objects": deleted_objects,
        "errors": deletion_errors
    }


def handler(event, context):
    ical_string: str = fetch_ical_string()
    calendar: Calendar = Calendar.from_ical(ical_string)

    check_for_updates(calendar)

    save_as_json(
        obj=[event.to_dict() for event in calendar.events],
        filename="events.json"
    )

    paginated: dict = get_paginated_recurring_events(calendar)
    total_updated_events: int = 0
    total_updated_pages: int = 0
    existing_pages: list = list_existing_pages()

    for page_number in paginated.keys():
        page_filename = f"pages/{page_number}.json"
        page = paginated[page_number]
        res = save_as_json(page, page_filename)
        if res["ResponseMetadata"]["HTTPStatusCode"] == 200:
            total_updated_pages += 1
            total_updated_events += len(page["events"])

    save_as_json({
        "source-url": environ["CALENDAR_LINK"],
        "last-updated": fetch_time,
        "total-events": total_updated_events,
        "total-pages": total_updated_pages,
        "per-page": environ["EVENTS_PER_PAGE"],
        "events": [event.to_dict() for event in calendar.recurring_events]
    }, "index.json")

    objects_to_delete: list = get_expired_pages(len(paginated.keys()), existing_pages)
    delete_result: dict = delete_objects(objects_to_delete)

    invalidate_cache()

    return {
        'statusCode': 200,
        'body': {
            'events_detected': len(calendar.recurring_events),
            'events_saved': total_updated_events,
            'pages_detected': len(paginated.keys()),
            'pages_updated': total_updated_pages,
            'previously_existing_pages': len(existing_pages),
            'pages_to_be_deleted': len(objects_to_delete),
            'deletion-result': delete_result
        }
    }
