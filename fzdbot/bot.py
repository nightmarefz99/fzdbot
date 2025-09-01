# TODO: 
#    Add Special Event option to "/start_event" - needs new entry in "events" table of database
#    Add a "before_date" option to "/show" so users can show older results too?
#    And add pagination to "/show", mostly for large events with a big scoreboard (i.e. GGP)

import os
from datetime import timezone

# External required modules 
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands

# Local functions 
from fzdbot.fzd_db import connect_to_database
from fzdbot.fzd_db import create_event
from fzdbot.fzd_db import get_event_types
from fzdbot.fzd_db import get_user_id
from fzdbot.fzd_db import get_user_scores
from fzdbot.fzd_db import submit_score
from fzdbot.fzd_db import edit_score
from fzdbot.fzd_db import delete_score
from fzdbot.fzd_db import check_for_active_event
from fzdbot.fzd_db import add_new_user
from fzdbot.fzd_db import modify_user_display_name
from fzdbot.fzd_db import get_event_scoreboard
# formatters.py
from fzdbot.formatters import format_discord_timestamp
from fzdbot.formatters import format_scoreboard_display_text
from fzdbot.formatters import format_scoreboard_for_discord_embed

# LOAD INFO FROM .env FILE
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = discord.Object(id=os.getenv('SERVER_ID'))

# BOT SETUP
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content

class Client(commands.Bot):
    async def on_ready(self) -> None:
        print(f'{self.user} is now running!')
        try:
            # Force sync so bot command changes will appear right away
            synced = await self.tree.sync(guild=GUILD_ID)
            print(f'Synced {len(synced)} commands to guild {GUILD_ID.id}')
        except Exception as e:
            print(f'Wrror syncing commands: {e}')


def main() -> None:
    # Define bot client according to Client class above
    client = Client(command_prefix="!",intents=intents)

    # Establish database connection
    db_connect = connect_to_database()
    if not db_connect:
        print("Bot cannot start without database connection.")
        exit(1)
    
    # Get all event types from 'events' table
    recurring_events = get_event_types(db_connect)
    print(recurring_events)
    print(repr(recurring_events))
    
    # Define event choices for dropdown menus (used in /start_event and /show commands)
    event_choices=[ app_commands.Choice(name=e['name'], value=e['id']) for e in recurring_events ]

    
    # =============================================================================================================
    #   /start_event
    # ============================================================================================================= 
    
    # Manually start an event
    @client.tree.command(name="start_event", description="Choose FZD event to start", guild=GUILD_ID)
    @app_commands.choices(event=event_choices)
    async def startEvent(interaction: discord.Interaction, event: app_commands.Choice[int]):
        current_event = check_for_active_event(db_connect)
        if (current_event['name'] != "NULL"):
            await interaction.response.send_message(f"❌ ERROR! Another event is currently running!")
            print(f"USER ERROR: User {interaction.user} tried to start {event.name},"
                  f"but there is another event currently running: {current_event['name']}")
        else:
            current_event['name'] = event.name
            current_event['id'] = int(event.value)
            create_event(db_connect, current_event)
            await interaction.response.send_message(f"✅ FZD event {event.name} successfully started!")
            print(f'User {interaction.user} just started the event {event.name}')
 

    # =============================================================================================================
    #   /add_score 
    # ============================================================================================================= 
    
    # Add a score to an event
    @client.tree.command(name="add_score", description="Add score to FZD scoreboard database", guild=GUILD_ID)
    async def addScore(interaction: discord.Interaction, score: int):
        if score < 0:
            await interaction.response.send_message(f"⚠️  Please enter a positive integer! ")
        else:
            db_user_id = get_user_id(db_connect, interaction.user.name)
            if db_user_id is None:
                add_new_user(db_connect, interaction.user, display_name=interaction.user.nick[0:10])
            current_event = check_for_active_event(db_connect)
            if (current_event['name'] != "NULL"):
                #print(f"current event active: {current_event}")
                #print(f"{interaction.user}, with id {db_user_id}, entered data")
                user_data = [current_event['id'], db_user_id, score] 
                submit_score(db_connect, user_data)
                await interaction.response.send_message(f"✅ User {interaction.user} has entered a score of {score} to {current_event['name']}")
            else: 
                await interaction.response.send_message(f"❌ ERROR! No event is active, score was not added!  ")


    # =============================================================================================================
    #   /register
    # ============================================================================================================= 

    # This command registers a user into the database
    @client.tree.command(name="register", description="Register your discord id to FZD scoreboard database", guild=GUILD_ID)
    async def registerUser(interaction: discord.Interaction, display_name: str = None):
        warning=""
        if display_name is None:
            display_name = interaction.user.nick[0:10]
        elif len(display_name) > 10:
            display_name = display_name[0:10]
            warning="⚠️  Warning: display_name should be 10 characters or less (as in F-Zero 99 in game name) \n"
        
        db_user_id = get_user_id(db_connect,interaction.user.name)
        if db_user_id is None:
            add_new_user(db_connect, interaction.user, display_name=display_name)
            await interaction.response.send_message(f"{warning}✅  User {interaction.user} is now registered in the FZD database with display name {display_name}")
        else:
            modify_user_display_name(db_connect, db_user_id, display_name)
            await interaction.response.send_message(f"{warning}✅  User {interaction.user} successfully modified their display name to {display_name}")

    
    # =============================================================================================================
    #   /edit_score (Its autocomplete handler for old_score is defined in the /delete_score section)
    # ============================================================================================================= 
    
    # This command queries the database for scores of a current event to edit for a user
    @client.tree.command(name="edit_score", description="Edit a submitted score, set it to new_score in FZD scoreboard database", guild=GUILD_ID)
    async def editScore(interaction: discord.Interaction, old_score: str, new_score: str):
        valid_options = get_user_scores(db_connect, interaction.user.name)
        score, idchoice = old_score.split("|")
        score_in_opts = any(d.get('score') == score for d in valid_options)
        if not score_in_opts:
            await interaction.response.send_message(f"❌ '{score}' is not a valid choice for you. Please select one of the options shown: {valid_options}", ephemeral=True) 
        elif score == "NO CURRENT EVENT":
            await interaction.response.send_message(f"❌  No current event active, can't edit scores! If you need help, contact an FZD mod", ephemeral=True)
        elif score == "NO USER SCORES FOUND":
            await interaction.response.send_message(f"❌  No submitted scores found for user {interaction.user.name}! If you need help, contact an FZD mod", ephemeral=True)
        else:
            try:
               edit_score(db_connect, (int(new_score), idchoice)) 
               await interaction.response.send_message(f"✅ User {interaction.user.name} has modified submitted score from {score} to {new_score}") 
            except ValueError: # Catching integers this way because autocomplete works with strings only
               await interaction.response.send_message(f"❌  ERROR! Please enter an integer value!", ephemeral=True) 


    # =============================================================================================================
    #   /delete_score
    # ============================================================================================================= 
    
    # Define the confirmation view for delete_score command below
    class ConfirmDeleteScore(discord.ui.View):
        def __init__(self, original_interaction):
            super().__init__(timeout=20) # Set a timeout for the view
            self.original_interaction = original_interaction
            self.confirmed = False
            
        @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
        async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.confirmed = True
            self.stop() # Stop listening for further interactions
            # Execute the action here
            delete_score(db_connect, [self.idchoice])
            await interaction.response.edit_message(content=f"Score deleted.", view=None) # Remove buttons
            await interaction.followup.send(content=f"✅ User {interaction.user.name} has successfully deleted '{self.score}' from their submitted scores", ephemeral=False)
 
        @discord.ui.button(label="No", style=discord.ButtonStyle.red)
        async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.confirmed = False
            self.stop() # Stop listening for further interactions
            await interaction.response.edit_message(content="Action canceled.", view=None) # Remove buttons

        async def on_timeout(self):
            # Handle timeout if no button is pressed
            if not self.confirmed:
                await self.original_interaction.edit_original_response(content="Confirmation timed out.", view=None)
  
    # This command queries the database for scores of a current event to delete for a user
    @client.tree.command(name="delete_score", description="Delete a score you have submitted during an ongoing event", guild=GUILD_ID)
    async def deleteScore(interaction: discord.Interaction, score_to_delete: str):
        valid_options = get_user_scores(db_connect, interaction.user.name)
        score, idchoice = score_to_delete.split("|")
        score_in_opts = any(d.get('score') == score for d in valid_options)
        if not score_in_opts:
            await interaction.response.send_message(f"❌ '{score}' is not a valid choice for you. Please select one of the options shown: {valid_options}", ephemeral=True)
        elif score == "NO CURRENT EVENT":
            await interaction.response.send_message(f"❌  No current event active, can't edit scores! If you need help, contact an FZD mod", ephemeral=True)
        elif score == "NO USER SCORES FOUND":
            await interaction.response.send_message(f"❌  No submitted scores found for user {interaction.user.name}! If you need help, contact an FZD mod", ephemeral=True)
        else:
            view = ConfirmDeleteScore(interaction)
            view.score = score # Send score to the ConfirmDeleteScore class
            view.idchoice = idchoice # Send id of the score to ConfirmDeleteScore class
            await interaction.response.send_message(f"⚠️  Are you sure you want to delete '{score}' from your scores?",
                        view=view,  ephemeral=True) 
            await view.wait() # Wait for user to make choice

    # Autocomplete handler for editScore and deleteScore (same for both)
    @editScore.autocomplete("old_score")
    @deleteScore.autocomplete("score_to_delete")
    async def option_autocomplete(interaction: discord.Interaction, current: str):
        user_scores = get_user_scores(db_connect, interaction.user.name)
  
        # Filter based on what the user is currently typing
        choices = [(opt['score'], opt['id']) for opt in user_scores if current.lower() in opt['score'].lower()]
        # Return up to 25 results (discord limit)
        return [app_commands.Choice(name=opt, value=f"{opt}|{idopt}") for opt, idopt in choices[:25]] 
 

    # =============================================================================================================
    #   /show = Show results of FZD event in discord embed
    # ============================================================================================================= 

    @client.tree.command(name="show", description="Show most current FZD event scoreboard", guild=GUILD_ID)
    @app_commands.choices(event_type=event_choices)
    async def showScoreboard(interaction: discord.Interaction, event_type: int = None):
        eventinfo, eventscoreslist = get_event_scoreboard(db_connect, event_type=event_type)
        if eventinfo and eventscoreslist:
            ranked_scoreboard = format_scoreboard_display_text(eventscoreslist)
            eventdate = eventinfo['utc_start_dt'].replace(tzinfo=timezone.utc)

            scoreboard = discord.Embed(title=eventinfo['name'], description=f"*Played on {format_discord_timestamp(eventdate)}*")
            scoreboard.set_thumbnail(url="https://media.discordapp.net/attachments/1399501477608951933/1400792457007861800/Supernova_Server_Icon.png?ex=689c6da3&is=689b1c23&hm=68b8d8790d30689fbad0dfb9341c78921ecf9afecc5919880c81680329c32644&=&format=webp&quality=lossless&width=1024&height=1024") 
        
            fields_display_text = format_scoreboard_for_discord_embed(ranked_scoreboard, max_num_lines=10)
            #for lin in fields_display_text:
            #    print(lin)
            #print(len(fields_display_text))
            for i, block in enumerate(fields_display_text, start=1):
                scoreboard.add_field(name="", value=block, inline=False)
            await interaction.response.send_message(embed=scoreboard)   
        else:
            event_name = [e['name'] for e in recurring_events if e['id'] == event_type]
            await interaction.response.send_message(
                  f"⚠️  No results found for event_type '{event_name[0]}'! If this is unexpected behavior contact a mod!",
                  ephemeral=True
                  )

    # =============================================================================================================
    #   Run the bot!
    # =============================================================================================================     
    
    client.run(token=TOKEN)

if __name__ == '__main__':
    main()
