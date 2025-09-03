# Miscellaneous bot commands for registering users in the database (/register)
# or modifying events (/start_event only for now) 
import os
from datetime import timezone
import discord
from discord.ext import commands
from discord import app_commands


from fzdbot.fzd_db import connect_to_database
from fzdbot.fzd_db import get_event_types
from fzdbot.fzd_db import add_new_user
from fzdbot.fzd_db import get_user_id
from fzdbot.fzd_db import modify_user_display_name
from fzdbot.fzd_db import check_for_active_event
from fzdbot.fzd_db import create_event

class Modify_Events_Users(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = connect_to_database()
        self.recurring_events = get_event_types(self.db)

    async def event_type_autocomplete(self, interaction: discord.Interaction,
                                      current: str) -> list[app_commands.Choice[str]]:
        event_choices = [ app_commands.Choice(name=e['name'], value=str(e['id']))
                          for e in self.recurring_events
                          if current.lower() in e['name'].lower() ]

        return event_choices[:25] # Discord only accepts max 25 autocomplete results

    # Manually start an event
    @app_commands.command(name="start_event", description="Choose FZD event to start, assuming no other event is ongoing")
    async def startEvent(self, interaction: discord.Interaction, event: str):
        current_event = check_for_active_event(self.db)
        event_name = [e['name'] for e in self.recurring_events if e['id'] == int(event)]
        if (current_event['name'] != "NULL"):
            await interaction.response.send_message(f"❌ ERROR! Another event is currently running -- {current_event['name']}")
            print(f"USER ERROR: User {interaction.user} ({interaction.user.nick}) tried to start {event_name[0]}, "
                  f"but there is another event currently running: {current_event['name']}")
        else:
            current_event['name'] = event_name[0]
            current_event['id'] = int(event)
            create_event(self.db, current_event)
            await interaction.response.send_message(f"✅ FZD event {event_name[0]} successfully started!")
            print(f'User {interaction.user} just started the event {event_name[0]}')

    async def cog_load(self):
        # Bind autocomplete handler properly
        self.startEvent.autocomplete("event")(self.event_type_autocomplete)


    # This command registers a user into the database
    @app_commands.command(name="register", description="Register your discord id to FZD scoreboard database")
    async def registerUser(self, interaction: discord.Interaction, display_name: str = None):
        warning=""
        if display_name is None:
            display_name = interaction.user.nick[0:10]
        elif len(display_name) > 10:
            display_name = display_name[0:10]
            warning="⚠️  Warning: display_name should be 10 characters or less (as in F-Zero 99 in game name) \n"
        
        db_user_id = get_user_id(self.db,interaction.user.name)
        if db_user_id is None:
            add_new_user(self.db, interaction.user, display_name=display_name)
            await interaction.response.send_message(f"{warning}✅  User {interaction.user} is now registered in the FZD database with display name {display_name}")
        else:
            modify_user_display_name(self.db, db_user_id, display_name)
            await interaction.response.send_message(f"{warning}✅  User {interaction.user} successfully modified their display name to {display_name}")

async def setup(bot: commands.Bot):
    GUILD_ID=discord.Object(id=os.getenv('SERVER_ID'))
    await bot.add_cog(Modify_Events_Users(bot), guild=GUILD_ID)
