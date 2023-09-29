from discord_webhook import DiscordWebhook
from os import environ
import json
from datetime import datetime
from html2text import HTML2Text


webhook_url: str = environ["DISCORD_WEBHOOK_URL"]
html_parser = HTML2Text()
html_parser.ignore_links = True


def build_time_string(start: str, end: str):
    start_dt: datetime = datetime.fromisoformat(start)
    end_dt: datetime = datetime.fromisoformat(end)

    if start_dt.date() != end_dt.date():
        return f"{start_dt.strftime('%d/%m/%Y %H:%M')} - {end_dt.strftime('%d/%m/%Y %H:%M')}"

    return f"{start_dt.strftime('%d/%m/%Y')}, {start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}"


def build_time_changed_string(old_event: dict, new_event: dict):
    if old_event['start'] == new_event['start'] and old_event['end'] == new_event['end']:
        return build_time_string(new_event['start'], new_event['end'])

    old_start_dt: datetime = datetime.fromisoformat(old_event['start'])
    old_end_dt: datetime = datetime.fromisoformat(old_event['end'])
    new_start_dt: datetime = datetime.fromisoformat(new_event['start'])
    new_end_dt: datetime = datetime.fromisoformat(new_event['end'])

    if old_start_dt.date() == old_end_dt.date() \
            and new_start_dt.date() == new_end_dt.date() \
            and old_start_dt.date() == new_start_dt.date():
        return f"{new_start_dt.strftime('%d/%m/%Y')}, " \
               f"~~{old_start_dt.strftime('%H:%M')} - {old_end_dt.strftime('%H:%M')}~~ " \
               f"{new_start_dt.strftime('%H:%M')} - {new_end_dt.strftime('%H:%M')}"

    return f"~~{build_time_string(old_event['start'], old_event['end'])}~~ " \
           f"{build_time_string(new_event['start'], new_event['end'])}"


def send_message_to_discord(message_text: str):
    print(f"Sending message to discord")
    webhook: DiscordWebhook = DiscordWebhook(
        url=webhook_url,
        content=message_text
    )
    return webhook.execute()


def truncate_content(content: str, max_length: int) -> str:
    if len(content) >= max_length:
        return f"{content[:max_length - 3]}..."
    return content


def process_new_event_message(message: dict):
    location_line: str = f"\n**Sted:** {message['event']['location']}" if message['event']['location'] != "" else ""
    rrule_line: str = f"\n**Gjentakelse:** {message['event']['rrule']}" if message['event']['rrule'] != "" else ""
    content: str = f":calendar_spiral: Et nytt arrangement har blitt opprettet :calendar_spiral:" \
                   f"\n" \
                   f"\n**{message['event']['summary']}**" \
                   f"\n" \
                   f"\n**Tid:** {build_time_string(message['event']['start'], message['event']['end'])}" \
                   f"{location_line}" \
                   f"{rrule_line}" \
                   f"\n" \
                   f"\n{html_parser.handle(message['event']['description'])}"

    content = truncate_content(content, 2000)
    return send_message_to_discord(content)


def process_deleted_event_message(message: dict):
    location_line: str = f"\n~~**Sted:** {message['event']['location']}~~" if message['event']['location'] != "" else ""
    rrule_line: str = f"~~\n**Gjentakelse:** {message['event']['rrule']}~~" if message['event']['rrule'] != "" else ""
    content: str = f":calendar_spiral: Et arrangement har blitt slettet :calendar_spiral:" \
                   f"\n" \
                   f"\n**{message['event']['summary']}**" \
                   f"\n" \
                   f"\n~~**Tid:** {build_time_string(message['event']['start'], message['event']['end'])}~~" \
                   f"{location_line}" \
                   f"{rrule_line}" \
                   f"\n" \
                   f"\n{html_parser.handle(message['event']['description'])}"

    content = truncate_content(content, 2000)
    return send_message_to_discord(content)


change_descriptions = {
    "summary": "navn",
    "description": "beskrivelse",
    "location": "sted",
    "rrule": "gjentakelse",
    "status": "status"
}


def process_updated_event_message(message: dict):
    old_event: dict = message['old_event']
    new_event: dict = message['new_event']

    updated_keys: [str] = list(filter(lambda key: old_event[key] != new_event[key], change_descriptions.keys()))
    updated_description_keys: [str] = [change_descriptions[key] for key in updated_keys]

    time_is_updated: bool = old_event['start'] != new_event['start'] or old_event['end'] != new_event['end']
    if time_is_updated:
        updated_description_keys = updated_description_keys + ['tid']

    message_title: str = f":calendar_spiral: Et arrangement har blitt endret :calendar_spiral:"
    change_description_line: str = f"\nEndret: {', '.join(updated_description_keys)}"

    summary_line: str = f"**{new_event['summary']}**"
    if old_event['summary'] != new_event['summary']:
        summary_line = f"~~{old_event['summary']}~~ {summary_line}"
    summary_line = f"\n{summary_line}"

    time_line: str = f"\n**Tid:** {build_time_changed_string(old_event, new_event)}"

    location_line: str = new_event['location']
    if old_event['location'] != "" and old_event['location'] != new_event['location']:
        location_line = f"~~{old_event['location']}~~ {location_line}"
    if old_event['location'] != "" or new_event['location'] != "":
        location_line = f"\n**Sted:** {location_line}"

    rrule_line: str = new_event['rrule']
    if old_event['rrule'] != "" and old_event['rrule'] != new_event['rrule']:
        rrule_line = f"~~{old_event['rrule']}~~ {rrule_line}"
    if old_event['rrule'] != "" or new_event['rrule'] != "":
        rrule_line = f"\n**Gjentakelse:** {rrule_line}"

    description_line: str = f"\n{html_parser.handle(new_event['description'])}"

    content: str = f"{message_title}" \
                   f"\n" \
                   f"{change_description_line}" \
                   f"\n" \
                   f"{summary_line}" \
                   f"\n" \
                   f"{time_line}" \
                   f"{location_line}" \
                   f"{rrule_line}" \
                   f"\n" \
                   f"{description_line}"

    content = truncate_content(content, 2000)
    return send_message_to_discord(content)


def process_event_is_tomorrow_message(message: dict):
    location_line: str = f"\n**Sted:** {message['event']['location']}" if message['event']['location'] != "" else ""
    rrule_line: str = f"\n**Gjentakelse:** {message['event']['rrule']}" if message['event']['rrule'] != "" else ""
    content: str = f"@here" \
                   f"\n:calendar_spiral: Påminnelse: Arrangement i morgen :calendar_spiral:" \
                   f"\n" \
                   f"\n**{message['event']['summary']}**" \
                   f"\n" \
                   f"\n**Tid:** {build_time_string(message['event']['start'], message['event']['end'])}" \
                   f"{location_line}" \
                   f"{rrule_line}" \
                   f"\n" \
                   f"\n{html_parser.handle(message['event']['description'])}"
    content = truncate_content(content, 2000)
    return send_message_to_discord(content)


message_handlers = {
    "new_calendar_event": process_new_event_message,
    "updated_calendar_event": process_updated_event_message,
    "deleted_calendar_event": process_deleted_event_message,
    "event_is_tomorrow": process_event_is_tomorrow_message
}


def process_record(record: dict):
    record_body = json.loads(record['body'])
    message_group_id = record['attributes']['MessageGroupId']

    if message_group_id not in message_handlers.keys():
        raise Exception(f"No message handler found for MessageGroupId {message_group_id}")

    record_message = json.loads(record_body['Message'])
    return message_handlers[message_group_id](record_message)


def handler(event, context):
    print(f"Processing event: {event}")
    for record in event['Records']:
        process_record(record)
