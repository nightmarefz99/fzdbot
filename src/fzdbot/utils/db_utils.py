import discord
from fzdbot.fzd_db import (
    get_db_connection,
    get_user_id,
    add_new_user,
    get_registration_events,
    get_user_registrations,
    add_user_to_division_sql,
    add_user_to_team_sql,
    remove_user_from_division_sql,
    remove_user_from_team_sql,
    reg_log_entry
)
from fzdbot.utils.view_utils import DivTeam

#########################################################
# Syncronous Utility Functions
#########################################################



#########################################################
# Asyncronous Utility Functions
#########################################################

async def get_or_create_db_user(db, discord_user):
    """ Gets the user id from the database given a discord user. If the user is not in the database, creates a new user and returns the id.
    """
    db_user_id = await get_user_id(db, discord_user.name)
    if db_user_id is None:
        await add_new_user(db, discord_user, display_name=discord_user.nick[0:10])
        db_user_id = await get_user_id(db, discord_user.name)
        if db_user_id is None:
            raise TypeError(f"Could not add new user {discord_user}")
    return db_user_id


async def refresh_event_list() -> list[str]:
    async with get_db_connection() as db:
        reg_event_dict = await get_registration_events(db)
    return [event['event_name'] for event in reg_event_dict if 'event_name' in event]


async def get_registration_events_from_db(interaction: discord.Interaction):
    """ Calls database for 
            the user_id in the database, 
            events open to registration, 
            and events the user has already registered for.
    """
    async with get_db_connection() as db:
        # get user info from database
        db_user_id = await get_or_create_db_user(interaction.user.name)
        
        # get registration info
        reg_event_dict = await get_registration_events(db)
        user_event_dict = await get_user_registrations(db, db_user_id)
        
    return db_user_id, reg_event_dict, user_event_dict


async def registration_update_db(db_user_id: int,
                                 scheduled_event_id: int, 
                                 div_team_str: str, 
                                 add_div_team_id: int = None, 
                                 rm_div_team_id: int = None):
    """ Adds, removes, or edits a division/team regisration depending on whether
        an addition id, a remove id, or both.
    """
    # Must have at least one optional argument
    if not any([add_div_team_id, rm_div_team_id]):
        raise ValueError("You must provide 'add_div_team_id', 'rm_div_team_id', or both.")
    
    async with get_db_connection() as db:
        match div_team_str:
            case DivTeam.DIVISION:
                if rm_div_team_id:
                    await remove_user_from_division_sql(db, db_user_id, rm_div_team_id)
                    await reg_log_entry(
                        db, db_user_id, scheduled_event_id, DivTeam.DIVISION, rm_div_team_id, "withdraw")
                if add_div_team_id:
                    await add_user_to_division_sql(db, db_user_id, add_div_team_id)
                    await reg_log_entry(
                        db, db_user_id, scheduled_event_id, DivTeam.DIVISION, add_div_team_id, "join")
            case DivTeam.TEAM:
                if rm_div_team_id:
                    await remove_user_from_team_sql(db, db_user_id, rm_div_team_id)
                    await reg_log_entry(
                        db, db_user_id, scheduled_event_id, DivTeam.TEAM, rm_div_team_id, "withdraw")
                if add_div_team_id:
                    await add_user_to_team_sql(db, db_user_id, add_div_team_id)
                    await reg_log_entry(
                        db, db_user_id, scheduled_event_id, DivTeam.TEAM, add_div_team_id, "join")
            case _:
                raise ValueError(f"Event must have either divisions or teams, not neither.")