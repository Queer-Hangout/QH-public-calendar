import urllib.request as request
import pandas
from datetime import datetime, timezone
import recurring_ical_events
from dateutil.relativedelta import relativedelta
import icalendar
import boto3
from os import environ
import json


def fetch_ical_string() -> str:
    calendar_link = environ["CALENDAR_LINK"]
    with request.urlopen(url=calendar_link, timeout=10) as response:
        body = response.read().decode('utf-8')
    return body


def parse_event(event) -> [str]:
    start: datetime = event["DTSTART"].dt
    end: datetime = event["DTEND"].dt
    duration: pandas.Timedelta = pandas.Timedelta(end - start)
    try:
        description: str = event["DESCRIPTION"]
    except KeyError:
        description: str = ""
    try:
        location: str = event["LOCATION"]
    except KeyError:
        location: str = ""
    return [
        event["SUMMARY"],
        description,
        str(start.isoformat()),
        str(end.isoformat()),
        str(duration.isoformat()),
        location
    ]


def parse_events_to_dataframe(ical_string: str) -> pandas.DataFrame:
    cal_start = datetime.now()
    cal_end = cal_start + relativedelta(months=6)
    calendar = icalendar.Calendar.from_ical(ical_string)
    events_table = pandas.DataFrame(columns=["name", "description", "start", "end", "duration", "location"])
    events = recurring_ical_events.of(calendar).between(cal_start, cal_end)
    for event in events:
        events_table.loc[len(events_table)] = parse_event(event)
    events_table.sort_values(by='start', ascending=True, ignore_index=True, inplace=True)
    return events_table


def to_page_json(
        events_table_page: pandas.DataFrame,
        last_updated: str,
        total_events: int,
        page: int,
        total_pages: int
) -> str:
    events_per_page: int = int(environ['EVENTS_PER_PAGE'])
    source_url: str = environ['CALENDAR_LINK']
    return json.dumps({
        "source-url": source_url,
        "last-updated": last_updated,
        "events-in-page": len(events_table_page),
        "total-events": total_events,
        "page": page,
        "total-pages": total_pages,
        "per-page": events_per_page,
        "has-more": page + 1 < total_pages,
        "events": events_table_page.to_dict(orient="records")
    }, ensure_ascii=False)


def paginate_events_to_json(events_table: pandas.DataFrame, last_updated: str) -> [str]:
    events_per_page: int = int(environ['EVENTS_PER_PAGE'])
    total_pages = len(events_table) // events_per_page + 1

    if total_pages == 0:
        return [to_page_json(
            events_table_page=events_table,
            last_updated=last_updated,
            total_events=len(events_table),
            page=0,
            total_pages=1
        )]

    pages = [""] * total_pages
    for page in range(total_pages):
        start_index = page * events_per_page
        end_index = min(page * events_per_page + events_per_page, len(events_table))
        pages[page] = to_page_json(
            events_table_page=events_table[start_index:end_index],
            last_updated=last_updated,
            total_events=len(events_table),
            page=page,
            total_pages=total_pages
        )
    return pages


def invalidate_cache():
    distribution_id: str = environ['DISTRIBUTION_ID']
    client = boto3.client("cloudfront")
    client.create_invalidation(
        DistributionId=distribution_id,
        InvalidationBatch={
            "Paths": {
                "Quantity": 1,
                "Items": ["/*"]
            },
            "CallerReference": str(datetime.now())
        }
    )


def handler(event, context):
    bucket_name: str = environ['BUCKET_NAME']
    events_per_page: int = int(environ['EVENTS_PER_PAGE'])
    fetch_time: str = str(datetime.now(timezone.utc).isoformat())
    ical_string: str = fetch_ical_string()
    events_table: pandas.DataFrame = parse_events_to_dataframe(ical_string)
    pages: [str] = paginate_events_to_json(events_table, fetch_time)
    client = boto3.client('s3')
    total_updated_events: int = 0
    total_updated_pages: int = 0

    for page_number in range(len(pages)):
        res = client.put_object(
            Bucket=bucket_name,
            Key=f"pages/{page_number}.json",
            Body=bytes(pages[page_number], "utf-8"),
            ContentType="application/json"
        )
        if res["ResponseMetadata"]["HTTPStatusCode"] == 200:
            total_updated_pages += 1
            if page_number < len(pages) - 1:
                total_updated_events += events_per_page
            else:
                total_updated_events += len(events_table) - total_updated_events

    client.put_object(
        Bucket=bucket_name,
        Key="index.json",
        Body=bytes(json.dumps({
            "source-url": environ["CALENDAR_LINK"],
            "last-updated": fetch_time,
            "total-events": total_updated_events,
            "total-pages": total_updated_pages,
            "per-page": events_per_page,
            "events": events_table.to_dict(orient="records")
        }, ensure_ascii=False), "utf-8"),
        ContentType="application/json"
    )

    response = client.list_objects_v2(
        Bucket=bucket_name,
        Prefix="pages/"
    )

    def file_is_expired(filename: str) -> bool:
        start_i = filename.rindex("/")
        end_i = filename.find(".")
        i = int(filename[start_i + 1:end_i])
        return i >= len(pages)

    try:
        contents = response["Contents"]
    except KeyError:
        contents = []

    filenames = list(map(lambda file: file["Key"], list(contents)))
    objects_to_delete = list(map(lambda filename: {"Key": filename}, filter(file_is_expired, filenames)))

    total_deleted_pages: int = 0
    deletion_errors = []
    if len(objects_to_delete) > 0:
        res = client.delete_objects(
            Bucket=bucket_name,
            Delete={
                "Objects": objects_to_delete
            }
        )
        total_deleted_pages = len(res["Deleted"])

        try:
            deletion_errors = res["Errors"]
        except KeyError:
            deletion_errors = []

    invalidate_cache()

    return {
        'statusCode': 200,
        'body': {
            'events_detected': len(events_table),
            'events_saved': total_updated_events,
            'pages_detected': len(pages),
            'pages_updated': total_updated_pages,
            'previously_existing_pages': len(filenames),
            'pages_to_be_deleted': len(objects_to_delete),
            'deleted_pages': total_deleted_pages,
            'deletion_errors': deletion_errors,
        }
    }
