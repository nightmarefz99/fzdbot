# Scoring cog class which defines commands related to changing scores in the database:
#         /add_score, /edit_score, /delete_score

import os
import discord
from discord.ext import commands
from discord import app_commands

from fzdbot.fzd_db import connect_to_database
from fzdbot.fzd_db import get_user_id
from fzdbot.fzd_db import get_user_scores
from fzdbot.fzd_db import add_new_user
from fzdbot.fzd_db import check_for_active_event
from fzdbot.fzd_db import submit_score
from fzdbot.fzd_db import edit_score
from fzdbot.fzd_db import delete_score
from fzdbot.views.confirm_delete import ConfirmDeleteScore

class Scoring(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = connect_to_database()
        #self.recurring_events = get_event_types(self.db)

    # =============================================================================================================
    #   /add_score 
    # ============================================================================================================= 

    # Add a score to an event
    @app_commands.command(name="add_score", description="Add score to FZD scoreboard database") #, guild=GUILD_ID)
    @app_commands.describe(score="Enter an integer value for the score during an event")
    async def add_score(self, interaction: discord.Interaction, score: int):
        if score < 0:
            await interaction.response.send_message(f"⚠️  Please enter a positive integer! ")
        else:
            db_user_id = get_user_id(self.db, interaction.user.name)
            if db_user_id is None:
                add_new_user(self.db, interaction.user, display_name=interaction.user.nick[0:10])
                db_user_id = get_user_id(self.db, interaction.user.name)
            current_event = check_for_active_event(self.db)
            if (current_event['name'] != "NULL"):
                user_data = [current_event['id'], db_user_id, score] 
                submit_score(self.db, user_data)
                await interaction.response.send_message(
                      f"✅ User {interaction.user} has entered a score of {score} to {current_event['name']}"
                      )
            else: 
                await interaction.response.send_message(f"❌ ERROR! No event is active, score was not added!  ")

    # ------------------------------------------------------------------
    # Autocomplete handler for editScore and deleteScore (same for both)
    # ------------------------------------------------------------------
    async def user_scores_autocomplete(self, interaction: discord.Interaction, current: str):
        user_scores = get_user_scores(self.db, interaction.user.name)
  
        # Filter based on what the user is currently typing
        choices = [(opt['score'], opt['id']) for opt in user_scores if current.lower() in opt['score'].lower()]
        # Return up to 25 results (discord limit)
        return [app_commands.Choice(name=opt, value=f"{opt}|{idopt}") for opt, idopt in choices[:25]] 

    # =============================================================================================================
    #   /edit_score 
    # ============================================================================================================= 
    
    # This command queries the database for scores of a current event to edit for a user
    @app_commands.command(name="edit_score", description="Edit a submitted score, set it to new_score in FZD scoreboard database")
    async def editScore(self, interaction: discord.Interaction, old_score: str, new_score: str):
        #  old_score is returned packed as "<score>|<id>" when a proper option is selected
        valid_options = get_user_scores(self.db, interaction.user.name)
        opts = [s['score'] for s in valid_options if 'score' in s]
        try:
            score, idchoice = old_score.split("|")
            if score not in opts:
                raise ValueError("score {score} not one of the options {opts}")

            if score == "NO CURRENT EVENT":
                await interaction.response.send_message(
                      f"❌  No current event active, can't edit scores! If you need help, contact an FZD mod", 
                      ephemeral=True
                      )
            elif score == "NO USER SCORES FOUND":
                await interaction.response.send_message(
                      f"❌  No submitted scores found for user {interaction.user.name}! If you need help, contact an FZD mod", 
                      ephemeral=True
                      )
            else:    
                edit_score(self.db, (int(new_score), int(idchoice))) 
                await interaction.response.send_message(
                      f"✅ User {interaction.user.name} has modified submitted score from {score} to {new_score}"
                      )
        except Exception as e:
            print(f"Exception in editScore: {e}")
            await interaction.response.send_message(
                   "❌  ERROR! Both options 'old_score' and 'new_score'  must be entered as integers! \n" +
                  f"    And 'old_score' must be one of the available options for you: {opts} \n" +
                  f"    ---> You chose: '{old_score}'",
                  ephemeral=True 
                  )


    # =============================================================================================================
    #   /delete_score
    # ============================================================================================================= 
    
    # This command queries the database for scores of a current event to delete for a user
    @app_commands.command(name="delete_score", description="Delete a score you have submitted during an ongoing event")
    async def deleteScore(self, interaction: discord.Interaction, score_to_delete: str):
        #  score_to_delete is returned packed as "<score>|<id>" when a proper option is selected
        valid_options = get_user_scores(self.db, interaction.user.name)
        opts = [s['score'] for s in valid_options if 'score' in s]
        try:
            score, idchoice = score_to_delete.split("|")
            if score not in opts:
                raise ValueError("score {score} not one of the options {opts}")

            if score == "NO CURRENT EVENT":
                await interaction.response.send_message(
                      f"❌  No current event active, can't edit scores! If you need help, contact an FZD mod",
                      ephemeral=True
                      )
            elif score == "NO USER SCORES FOUND":
                await interaction.response.send_message(
                      f"❌  No submitted scores found for user {interaction.user.name}! If you need help, contact an FZD mod",
                      ephemeral=True
                      )
            else:        
                view = ConfirmDeleteScore(interaction)
                await interaction.response.send_message(f"⚠️  Are you sure you want to delete '{score}' from your scores?",
                                                        view=view,  ephemeral=True
                                                        )
                await view.wait() # Wait for user to make choice
                if view.confirmed:
                    delete_score(self.db, [idchoice])
                    await interaction.followup.send(
                          content=f"✅ User {interaction.user.name} has successfully deleted '{score}' from their submitted scores",
                          ephemeral=False
                          )
        except Exception as e:
            print(f"Exception in deleteScore: {e}")
            await interaction.response.send_message(
                  f"❌  ERROR! 'score_to_delete' must be one of the available options for you: {opts} \n" +
                  f"    ---> You chose: '{score_to_delete}'",
                  ephemeral=True 
                  )


    # Bind autocomplete handler to edit and delete commands in cog
    async def cog_load(self):
        self.editScore.autocomplete("old_score")(self.user_scores_autocomplete) 
        self.deleteScore.autocomplete("score_to_delete")(self.user_scores_autocomplete)

async def setup(bot: commands.Bot):
    GUILD_ID=discord.Object(id=os.getenv('SERVER_ID'))
    await bot.add_cog(Scoring(bot), guild=GUILD_ID)
