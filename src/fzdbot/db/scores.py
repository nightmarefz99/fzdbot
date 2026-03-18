from fzdbot.db.connection import execute_query
from fzdbot.db.events import check_for_active_event, get_latest_event
from fzdbot.db.users import get_user_id


async def submit_score(db, dataentry) -> int:
    """Insert a score and return the stored score value."""
    sql_newrow = "sp_insert_score"
    dataentry.append("NULL")
    score = await execute_query(db, sql_newrow, params=dataentry, fetch="one", is_proc=True)
    return int(score["@sp_output_score"])


async def edit_score(db, dataentry) -> None:
    """Modify an existing score."""
    sql_updaterow = "UPDATE event_result_points SET score = %s WHERE id = %s;"
    await execute_query(db, sql_updaterow, params=dataentry, fetch=None)


async def delete_score(db, dataentry) -> None:
    """Delete an existing score."""
    sql_deleterow = "DELETE FROM event_result_points WHERE id = %s;"
    await execute_query(db, sql_deleterow, params=dataentry, fetch=None)


async def get_user_scores(db, user_name, check_for_score_method=False) -> list[dict[str, str]]:
    """Query the active event scores for a given user."""
    active_event = await check_for_active_event(db)
    if active_event["name"] == "NULL":
        return [{"score": "NO CURRENT EVENT", "id": "-999"}]
    if check_for_score_method and active_event["scoring_method"] == "placement":
        return [{"score": "DISABLED FOR THIS EVENT", "id": "-888"}]

    db_user_id = await get_user_id(db, user_name)
    sql_getscores = """SELECT CAST(score AS CHAR) AS score,
                              CAST(id AS CHAR) AS id
                       FROM event_result_points
                       WHERE user_id = %s AND scheduled_event_id = %s
                       ORDER BY id ASC;"""
    scoresdict = await execute_query(db, sql_getscores, params=(db_user_id, active_event["id"]), fetch="all")
    if not scoresdict:
        return [{"score": "NO USER SCORES FOUND", "id": "-999"}]
    return scoresdict


async def get_event_scoreboard(db, db_user_id: int, event_type=None):
    """Query all scores for a given event scoreboard."""
    sql_getscoreboard = "sp_show_scoreboard"

    if event_type is None:
        eventinfo = await get_latest_event(db)
    else:
        eventinfo = await get_latest_event(db, event_id=int(event_type))

    if not eventinfo:
        return None, None

    allscores = await execute_query(db, sql_getscoreboard, params=(eventinfo["id"], db_user_id), is_proc=True)

    valid_qual_events = [8, 9, 10, 11, 12, 13]
    if eventinfo["event_id"] not in valid_qual_events:
        for score in allscores:
            score.pop("is_qualified", None)

    return eventinfo, allscores
