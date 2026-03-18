from datetime import timezone

from fzdbot.formatters.discord import format_discord_timestamp


def format_events_schedule(events):
    """Format the upcoming event schedule for a Discord embed."""
    utc_start = [event["utc_start"].replace(tzinfo=timezone.utc) for event in events if "utc_start" in event]
    events_start_discord_timestamps = [format_discord_timestamp(start) for start in utc_start]
    events_names = [event["event"] for event in events if "event" in event]

    formatted_fields = []
    curstr = ""
    for event, start in zip(events_names, events_start_discord_timestamps):
        curstr += event + ": " + start + " \n "
    formatted_fields.append(curstr)
    return formatted_fields
