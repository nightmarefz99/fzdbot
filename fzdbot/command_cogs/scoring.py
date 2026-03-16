# Scoring cog class which defines commands related to changing scores in the database:
#         /add_score, /edit_score, /delete_score

import os
import discord
from discord.ext import commands
from discord import app_commands

from fzdbot.fzd_db import get_db_connection #connect_to_database
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

    # =============================================================================================================
    #   /add_score 
    # ============================================================================================================= 

    # Add a score to an event
    @app_commands.command(name="fzd_add_score", description="Add score to FZD scoreboard database") #, guild=GUILD_ID)
    @app_commands.describe(score="Enter an integer value for the score during an event")
    async def add_score(self, interaction: discord.Interaction, score: str):
        maxscore = 1000000 # arbitrarily set for now
        try:
            if int(score) < 0:
                raise ValueError(f"score can't be a negative integer {interaction.user}") 
            elif int(score) > maxscore:
                raise OverflowError(f"score entered too large! {interaction.user}")
    
            # Get user id first, or add user if not registered in database
            async with get_db_connection() as db:
                db_user_id = await get_user_id(db,interaction.user.name)
                if db_user_id is None:
                    await add_new_user(db, interaction.user, display_name=interaction.user.nick[0:10])
                    db_user_id = await get_user_id(db, interaction.user.name)
                    if db_user_id is None:
                        raise TypeError(f"Could not add new user {interaction.user}")
            
                # check an event is active before adding data
                current_event = await check_for_active_event(db)
                if (current_event['name'] == "NULL"):
                    await interaction.response.send_message(f"⚠️  Warning: No event is currently active, score was not added!  ", ephemeral=True)
                elif (current_event['scoring_method'] != "points"):
                    await interaction.response.send_message(f"⚠️  Warning: {current_event['name']} requires rank results, please use /fzd_add_rank ", ephemeral=True)
                else: 
                    user_data = [db_user_id, current_event['id'], int(score), current_event['scoring_method']] 
                    return_score = await submit_score(db, user_data) #interaction.user
                    await interaction.response.send_message(f"✅ User {interaction.user} has entered a score of {return_score} to {current_event['name']}") #, ephemeral=True)
                    print(f"✅ User {interaction.user.nick} has entered a score of {score} to {current_event['name']}")

        except ValueError as ve: # should catch negative numbers and any errors with int(score) if score is not a base 10 integer
            await interaction.response.send_message(f"❌ ERROR! 'score' must be entered as a positive integer!  ", ephemeral=True) 
        except OverflowError as oe:
            await interaction.response.send_message(f"❌ ERROR! 'score' should not be larger tnan {maxscore}. Please be nice to Nightmare's bot.", ephemeral=True) 
        except TypeError as te:
            await interaction.response.send_message(f"❌ ERROR! Could not add you to the database. Try the '/fzd_register' command, or contact FZD staff for help.", ephemeral=True) 
        except Exception as e:
            await interaction.response.send_message(f"❌ ERROR! Something went wrong, contact FZD staff for help! ", ephemeral=True)
            print(f"Exception in add_score encountered! {e}")


    # =============================================================================================================
    #   /add_rank 
    # ============================================================================================================= 

    # Add a score to an event
    @app_commands.command(name="fzd_add_rank", description="Add rank placement to FZD scoreboard (i.e. for Kingmaker events)") #, guild=GUILD_ID)
    @app_commands.describe(rank="Enter an integer value for the placement rank (1-99) during an event")
    async def add_rank(self, interaction: discord.Interaction, rank: str):
        maxrank = 99 
        try:
            if int(rank) < 1 or int(rank) > maxrank:
                raise ValueError(f"rank must be between 1 and 99 {interaction.user}")

            # Get user id first, or add user if not registered in database
            async with get_db_connection() as db:
                db_user_id = await get_user_id(db,interaction.user.name)
                if db_user_id is None:
                    await add_new_user(db, interaction.user, display_name=interaction.user.nick[0:10])
                    db_user_id = await get_user_id(db, interaction.user.name)
                    if db_user_id is None:
                        raise TypeError(f"Could not add new user {interaction.user}")

                # check an event is active before adding data
                current_event = await check_for_active_event(db)
                print(repr(current_event))
                if (current_event['name'] == "NULL"):
                    await interaction.response.send_message(f"⚠️  Warning: No event is currently active, rank was not added!  ", ephemeral=True)
                elif (current_event['scoring_method'] == "points"):
                    await interaction.response.send_message(f"⚠️  Warning: {current_event['name']} is normal scoring, please submit race/GP points using /fzd_add_score ", ephemeral=True)
                else:
                    user_data = [db_user_id, current_event['id'], int(rank), current_event['scoring_method']]
                    return_score = await submit_score(db, user_data) #interaction.user
                    await interaction.response.send_message(f"✅ User {interaction.user} has entered rank {rank} → {return_score} points have been added to {current_event['name']}") #, ephemeral=True)
                    print(f"✅ User {interaction.user.nick} has entered a score of {rank},  {return_score} to {current_event['name']}")

        except ValueError as ve: # should catch negative numbers and any errors with int(score) if score is not a base 10 integer
            await interaction.response.send_message(f"❌ ERROR! 'rank' must be between 1 and 99!  ", ephemeral=True)
        except TypeError as te:
            await interaction.response.send_message(f"❌ ERROR! Could not add you to the database. Try the '/fzd_register' command, or contact FZD staff for help.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ ERROR! Something went wrong, contact FZD staff for help! ", ephemeral=True)
            print(f"Exception in add_rank encountered! {e}")



    # ------------------------------------------------------------------
    # Autocomplete handler for editScore and deleteScore
    # ------------------------------------------------------------------
    async def user_scores_autocomplete(self, interaction: discord.Interaction, current: str):
        async with get_db_connection() as db:
            user_scores = await get_user_scores(db,interaction.user.name)
  
        # Filter based on what the user is currently typing
        choices = [(opt['score'], opt['id']) for opt in user_scores if current.lower() in opt['score'].lower()]
        # Return up to 25 results (discord limit)
        return [app_commands.Choice(name=opt, value=f"{opt}|{idopt}") for opt, idopt in choices[:25]] 
    
    async def user_scores_autocomplete_nokingmaker(self, interaction: discord.Interaction, current: str):
        async with get_db_connection() as db:
            user_scores = await get_user_scores(db,interaction.user.name,check_for_score_method=True)

        # Filter based on what the user is currently typing
        choices = [(opt['score'], opt['id']) for opt in user_scores if current.lower() in opt['score'].lower()]
        # Return up to 25 results (discord limit)
        return [app_commands.Choice(name=opt, value=f"{opt}|{idopt}") for opt, idopt in choices[:25]]    

    # =============================================================================================================
    #   /edit_score 
    # ============================================================================================================= 
    
    # This command queries the database for scores of a current event to edit for a user
    @app_commands.command(name="fzd_edit_score", description="Edit a submitted score, set it to new_score in FZD scoreboard database")
    async def editScore(self, interaction: discord.Interaction, old_score: str, new_score: str):
        #  old_score is returned packed as "<score>|<id>" when a proper option is selected
        try:
            async with get_db_connection() as db:
                valid_options = await get_user_scores(db, interaction.user.name, check_for_score_method=True)
                opts = [s['score'] for s in valid_options if 'score' in s]
                score, idchoice = old_score.split("|")
                if score not in opts:
                    raise ValueError("score {score} not one of the options {opts}")

                if score == "NO CURRENT EVENT":
                    await interaction.response.send_message(
                          f"⚠️   No current event active, can't edit scores! If you need help, contact an FZD mod", 
                          ephemeral=True
                          )
                elif score == "NO USER SCORES FOUND":
                    await interaction.response.send_message(
                          f"⚠️   No submitted scores found for user {interaction.user.name}! If you need help, contact an FZD mod", 
                          ephemeral=True
                          )
                elif (score == "DISABLED FOR THIS EVENT"):
                    await interaction.response.send_message(
                          "⚠️   The /fzd_edit_score command does not work with Rank-based Kingmaker-style events! \n" +
                          "        If you need to edit a score, you may instead: \n" +
                          "               (1) delete the score first with /fzd_delete_score, then \n" +
                          "               (2) resubmit your rank with /fzd_add_rank \n" +
                          "        Or contact an FZD mod for help!",
                          ephemeral=True
                          )

                else:    
                    await edit_score(db, (int(new_score), int(idchoice))) 
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
    @app_commands.command(name="fzd_delete_score", description="Delete a score you have submitted during an ongoing event")
    async def deleteScore(self, interaction: discord.Interaction, score_to_delete: str):
        #  score_to_delete is returned packed as "<score>|<id>" when a proper option is selected
        try:
            async with get_db_connection() as db:
                valid_options = await get_user_scores(db,interaction.user.name)
                opts = [s['score'] for s in valid_options if 'score' in s]
                
                score, idchoice = score_to_delete.split("|")
                if score not in opts:
                    raise ValueError("score {score} not one of the options {opts}")

                if score == "NO CURRENT EVENT":
                    await interaction.response.send_message(
                          f"⚠️   No current event active, can't edit scores! If you need help, contact an FZD mod",
                          ephemeral=True
                          )
                elif score == "NO USER SCORES FOUND":
                    await interaction.response.send_message(
                          f"⚠️   No submitted scores found for user {interaction.user.name}! If you need help, contact an FZD mod",
                          ephemeral=True
                          )
                else:        
                    view = ConfirmDeleteScore(interaction)
                    await interaction.response.send_message(f"⚠️  Are you sure you want to delete '{score}' from your scores?",
                                                        view=view,  ephemeral=True
                                                        )
                            
                    timed_out = await view.wait()
                    if timed_out or view.confirmed is None:
                        await interaction.followup.send("Timed out — no changes were made.", ephemeral=True)
                        return
                    if view.confirmed:
                        await delete_score(db,[idchoice])
                        await interaction.followup.send(
                              content=f"✅ User {interaction.user.name} has successfully deleted '{score}' from their submitted scores",
                              ephemeral=False
                              )
                    else:
                        await interaction.followup.send("Cancelled — no changes were made.", ephemeral=True)

        except Exception as e:
            print(f"Exception in deleteScore: {e}")
            await interaction.response.send_message(
                  f"❌  ERROR! 'score_to_delete' must be one of the available options for you: {opts} \n" +
                  f"    ---> You chose: '{score_to_delete}'",
                  ephemeral=True 
                  )


    # Bind autocomplete handler to edit and delete commands in cog
    async def cog_load(self):
        self.editScore.autocomplete("old_score")(self.user_scores_autocomplete_nokingmaker) 
        self.deleteScore.autocomplete("score_to_delete")(self.user_scores_autocomplete)

async def setup(bot: commands.Bot):
    GUILD_ID=discord.Object(id=os.getenv('SERVER_ID'))
    await bot.add_cog(Scoring(bot), guild=GUILD_ID)
