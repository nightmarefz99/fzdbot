# Miscellaneous bot commands for registering users in the database (/register)
# or modifying events (/start_event only for now) 
import os
from datetime import timezone
import discord
from discord.ext import commands
from discord import app_commands
import mysql.connector

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
    @app_commands.command(name="fzd_start_event", description="Choose FZD event to start, assuming no other event is ongoing")
    async def startEvent(self, interaction: discord.Interaction, event: str):
        duration = 2 # duration of event (hours), set constant for now
        opts = [s['name'] for s in self.recurring_events if 'name' in s] # list of event names (all valid options)
        try:
            event_name = [e['name'] for e in self.recurring_events if e['id'] == int(event)] #chosen event name
            if not event_name: # in the rare case user inputs an integer 'event', and above line returns empty list
                raise IndexError("chosen event not part of list")

            # Check every hour in the proposed new event for possible overlap with database events
            for hour_to_check in range(0,duration+1):
                match_event = check_for_active_event(self.db, hours_from_now=hour_to_check)
                if (match_event['name'] != "NULL"):
                    message=f"another event is currently running -- {match_event['name']}"
                    if hour_to_check > 0:
                        message=f"another event will start within the next {duration} hours -- {match_event['name']}" 
                    await interaction.response.send_message(f"⚠️  Warning: Could not start event, {message}", ephemeral=True)
                    return
  
            # Event is created here
            current_event = match_event
            current_event['name'] = event_name[0]
            current_event['id'] = int(event)
            create_event(self.db, current_event, duration=duration)  # default duration is 2 hours
            await interaction.response.send_message(f"✅ FZD event {event_name[0]} successfully started!")
            print(f'User {interaction.user} just started the event {event_name[0]}')

        except Exception as e:
            print(f"{e=}")
            await interaction.response.send_message(f"❌ ERROR! Must choose from available event options -- {opts}", ephemeral=True)
   
    async def cog_load(self):
        # Bind autocomplete handler properly
        self.startEvent.autocomplete("event")(self.event_type_autocomplete)


    # This command registers a user into the database
    @app_commands.command(name="fzd_register", description="Register your discord id to FZD scoreboard database")
    async def registerUser(self, interaction: discord.Interaction, display_name: str):
        warning=""
        if display_name is None:
            display_name = interaction.user.nick[0:10]
        elif len(display_name) > 10:
            display_name = display_name[0:10]
            warning="⚠️  Warning: display_name should be 10 characters or less (as in F-Zero 99 in game name) \n"
        
        try:
            db_user_id = get_user_id(self.db,interaction.user.name)
            if db_user_id is None:
                add_new_user(self.db, interaction.user, display_name=display_name)
                await interaction.response.send_message(f"{warning}✅  User {interaction.user} is now registered in the FZD database with display name {display_name}", ephemeral=True)
                print(f"{warning}✅  User {interaction.user} is now registered in the FZD database with display name {display_name}")
            else:
                modify_user_display_name(self.db, db_user_id, display_name)
                await interaction.response.send_message(f"{warning}✅  User {interaction.user} successfully modified their display name to {display_name}", ephemeral=True)
                print(f"{warning}✅  User {interaction.user} successfully modified their display name to {display_name}")

        except mysql.connector.errors.IntegrityError as ie: # The error you get when you try to enter a duplicate row value to a UNIQUE column
            await interaction.response.send_message(f"{warning}❌ ERROR! The name '{display_name}' is already taken in the database, please use a different name!", ephemeral=True)
            print(f"IntegrityError: {ie}") 

        except Exception as e:
            await interaction.response.send_message(f"{warning}❌ ERROR! Something went wrong, please contact FZD staff to address!", ephemeral=True)
            print(f"Exception occurred in fzd_register: {e}")
    
async def setup(bot: commands.Bot):
    GUILD_ID=discord.Object(id=os.getenv('SERVER_ID'))
    await bot.add_cog(Modify_Events_Users(bot), guild=GUILD_ID)
