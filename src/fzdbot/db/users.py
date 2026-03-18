from fzdbot.db.connection import execute_query


async def get_user_id(db, discord_id: str):
    """Given a discord user id (discord_id), returns the database id of that user."""
    sql_getuser = "SELECT id from users WHERE discord_user_id = %s"
    user = await execute_query(db, sql_getuser, params=(discord_id,), fetch="one")
    if user:
        return user["id"]
    return None


async def add_new_user(db, discord_username, display_name=None) -> None:
    """Adds new user to the database."""
    sql_newuser = "INSERT INTO users (tag, discord_user_id) VALUES (%s, %s);"

    if display_name is None:
        display_name = discord_username.nick[0:10]
    await execute_query(db, sql_newuser, params=(display_name, discord_username.name), fetch=None)


async def modify_user_display_name(db, db_user_id, display_name) -> None:
    """Modifies an existing user's display name in the database."""
    sql_modifyuser = "UPDATE users SET tag = %s WHERE id = %s;"
    await execute_query(db, sql_modifyuser, params=(display_name, db_user_id), fetch=None)
