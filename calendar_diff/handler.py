import json
import boto3
from os import environ

client = boto3.client('sns')


def events_list_to_dict(events_list: [dict]) -> dict:
    result: dict = {}
    for event in events_list:
        result[event["uid"]] = event
    return result


def notify_new_event(calendar_event):
    print(f"Notifying new event: {calendar_event['uid']}")
    return client.publish(
        TopicArn=environ["NEW_EVENT_TOPIC_ARN"],
        Message=str(json.dumps({
            "event": calendar_event
        }, ensure_ascii=False)),
        MessageGroupId="new_calendar_event"
    )


def notify_deleted_event(calendar_event):
    print(f"Notifying deleted event: {calendar_event['uid']}")
    return client.publish(
        TopicArn=environ["DELETED_EVENT_TOPIC_ARN"],
        Message=str(json.dumps({
            "event": calendar_event
        }, ensure_ascii=False)),
        MessageGroupId="deleted_calendar_event"
    )


def notify_updated_event(old_event, new_event):
    print(f"Notifying updated event: {old_event['uid']}")
    return client.publish(
        TopicArn=environ["UPDATED_EVENT_TOPIC_ARN"],
        Message=str(json.dumps({
            "old_event": old_event,
            "new_event": new_event
        }, ensure_ascii=False)),
        MessageGroupId="updated_calendar_event"
    )


def is_equal(old_event: dict, new_event: dict) -> bool:
    for key in ["start", "end", "summary", "description", "location", "rrule"]:
        if old_event[key] != new_event[key]:
            return False
    return True


def handler(event, _):
    event_body: dict = json.loads(event['Records'][0]['body'])
    message: dict = json.loads(event_body['Message'])
    old_events: dict = events_list_to_dict(message['old_events'])
    new_events: dict = events_list_to_dict(message['new_events'])

    response = {
        "new_events": [],
        "updated_events": [],
        "deleted_events": [],
        "errors": []
    }

    for event_uid in new_events.keys():
        try:
            if event_uid not in old_events:
                notify_new_event(new_events[event_uid])
                response["new_events"] = response["new_events"] + [event_uid]
            elif not is_equal(old_events[event_uid], new_events[event_uid]):
                notify_updated_event(old_events[event_uid], new_events[event_uid])
                response["updated_events"] = response["updated_events"] + [event_uid]
        except Exception as error:
            response['errors'] = response['errors'] + [error]

    for event_uid in old_events.keys():
        if event_uid not in new_events:
            try:
                notify_deleted_event(old_events[event_uid])
                response["deleted_events"] = response["deleted_events"] + [event_uid]
            except Exception as error:
                response['errors'] = response['errors'] + [error]

    print(response)

    if len(response['errors']) > 0:
        raise Exception("\n".join(response['errors']))

    return response
