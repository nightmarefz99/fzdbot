from datetime import datetime, timedelta, timezone

from fzdbot.db.connection import execute_query


async def get_event_types(db):
    """Get event types and ids of recurring events from the events table."""
    sql_gettypes = "SELECT id, name FROM events"
    return await execute_query(db, sql_gettypes, fetch="all")


async def create_event(db, event, duration: int = 2) -> None:
    """Insert new event into the events_scheduled database."""
    now = datetime.now(timezone.utc)
    endtime = now + timedelta(hours=duration)
    tformat = "%Y-%m-%d %H:%M:%S"
    sql_addevent = "INSERT INTO events_scheduled (event_id, utc_start_dt, utc_end_dt) VALUES (%s, %s, %s);"
    await execute_query(
        db,
        sql_addevent,
        params=(event["id"], now.strftime(tformat), endtime.strftime(tformat)),
        fetch=None,
    )


async def check_for_active_event(db, hours_from_now: int = 0):
    """Check event times to see if an event is active right now."""
    active_event = {"name": "NULL", "id": 0}
    sql_getevent = """SELECT es.id, e.name, es.utc_start_dt, es.utc_end_dt, es.scoring_method
                    FROM events_scheduled es
                    JOIN events e ON e.id = es.event_id
                    WHERE DATE_ADD(UTC_TIMESTAMP(), INTERVAL %s HOUR)
                          BETWEEN utc_start_dt AND utc_end_dt;"""
    eventmatch = await execute_query(db, sql_getevent, params=(hours_from_now,), fetch="one")
    if eventmatch:
        active_event["name"] = eventmatch["name"]
        active_event["id"] = eventmatch["id"]
        active_event["scoring_method"] = eventmatch["scoring_method"]
    return active_event


async def get_latest_event(db, event_id=None):
    """Get the most recent event."""
    sql_getevent = """SELECT es.id, e.name, es.utc_start_dt, es.utc_end_dt, es.event_id
                    FROM events_scheduled es
                    JOIN events e ON e.id = es.event_id
                    WHERE utc_start_dt =
                        (SELECT MAX(utc_start_dt) FROM events_scheduled
                         WHERE utc_start_dt < UTC_TIMESTAMP())"""
    params = None
    if event_id is not None:
        sql_getevent = sql_getevent.replace("())", "() AND event_id = %s)")
        params = (event_id,)
    return await execute_query(db, sql_getevent, params=params, fetch="one")


async def get_event_schedule(db):
    """Get scheduled events in the future."""
    sql_events = "SELECT event, utc_start, utc_end FROM vw_list_scheduled_events"
    return await execute_query(db, sql_events, params=None, fetch="all")
