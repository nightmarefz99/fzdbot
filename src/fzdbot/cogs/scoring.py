# Scoring cog class which defines commands related to changing scores in the database:
#         /add_score, /edit_score, /delete_score

import logging

import time
import asyncio
import discord
from discord import app_commands
from discord.ext import commands

from fzdbot.error_alerts import send_error_alert
from fzdbot.utils.db_utils import get_or_create_db_user
from fzdbot.fzd_db import (
    check_for_active_event,
    get_user_id,
    delete_score,
    edit_score,
    get_db_connection,  # connect_to_database
    get_machines,
    get_machine_config_db,
    get_event_config_flags,
    get_user_scores,
    get_event_lineups_and_scores,
    get_prix_options,
    submit_score,
    submit_score_sql
)
from fzdbot.settings import get_settings
from fzdbot.views.confirm_delete import ConfirmDeleteScore
from fzdbot.utils.warnings import InputWarnings

logger = logging.getLogger(__name__)


class Scoring(commands.Cog):

    # ==========================================================================================
    #   Class Cache Variables
    # ==========================================================================================
    # Set the autocomplete cache and cache expiration
    _OPTIONS_CACHE = {
        "lineup_option_list": [], # list of dict[lineup_id, combined string]
        "machine_option_list": [], # list of dict[db_id, name]
        "last_updated": 0
    }
    _EVENT_CONFIG_CACHE = {
        "is_lineup_input_required": False,
        "is_machine_input_required": False,
        "is_registration_event": False,
        "last_updated": 0
    }
    _ACTIVE_TTL_SECONDS: int = 10
    _MAXSCORE = 1000000  # arbitrarily set for now

    def __init__(self, bot: commands.Bot, machine_dict: list[dict[str, str]]):
        self.bot = bot
        self.machine_dict = machine_dict


    # ==========================================================================================
    #   Class and Static Methods
    # ==========================================================================================

    @classmethod
    async def grab_machines(cls) -> list[dict[str, str]]:
        """Fetch machine dictionaries used to initialize the cog."""
        async with get_db_connection() as db:
            return await get_machines(db)

    @classmethod
    async def get_event_config_from_db(self, discord_name: str) -> tuple[dict, int]:
        """ Gets config information to support autocomplete and slash commands.
            Triggered upon autocomplete when cache expired.
        """
        all_prix_shortnames = ["knight", "queen", "king", "ace", "mknight",
                                "mqueen", "mking", "mace", "MP", "cMP", "99",
                                "classic", "TB", "MP", "cMP", "WT", "mWT"]
        # Load config information from the database
        async with get_db_connection() as db:
            active_event = await check_for_active_event(db)
            user_id = await get_user_id(db, discord_name)

            if active_event and user_id:
                lineup_dict_list = await get_event_lineups_and_scores(db, active_event["id"], user_id)
                if not lineup_dict_list:
                    # This is an error in that it has the wrong id (needs to be lineup.id)
                    #   MUST FIX
                    default_lineup_list = get_prix_options(db, "all")
                
                machine_dict_list = await get_machine_config_db(db, active_event["id"])
                if not machine_dict_list:
                    machine_dict_list = await get_machines(db)

                event_config_flag_dict = await get_event_config_flags(db, active_event["id"])

        # Set event flags
        if not event_config_flag_dict:
            self_EVENT_CONFIG_CACHE["is_lineup_input_required"] = False
            self_EVENT_CONFIG_CACHE["is_machine_input_required"] = False
            self_EVENT_CONFIG_CACHE["is_registration_event"] = False
        else:
            self_EVENT_CONFIG_CACHE["is_lineup_input_required"] = event_config_flag_dict["is_lineup_input_required"]
            self_EVENT_CONFIG_CACHE["is_machine_input_required"] = event_config_flag_dict["is_machine_input_required"]
            self_EVENT_CONFIG_CACHE["is_registration_event"] = event_config_flag_dict["is_registration_event"]
        
        # Get the lineup list in format easy to create app_commands.Choice entries with.
        self._OPTIONS_CACHE["lineup_option_list"] = []
        if lineup_dict_list:
            # Display text gathered from multiple fields
            for lineup_dict in lineup_dict_list:
                lineup_string = f"{lineup_dict["lineup_num"]}: {lineup_dict["lineup_name"]}"
                if lineup_dict["score"]:
                    lineup_string += f" - score {lineup_dict["score"]}"
                self._OPTIONS_CACHE["lineup_option_list"].append(
                    {"name": lineup_string, "value": str(lineup_dict["event_lineup_id"]}))
        else:
            for lineup_dict in default_lineup_list:
                self._OPTIONS_CACHE["lineup_option_list"].append(
                    {"name": lineup_dict["name"], "value": str(lineup_dict["event_lineup_id"]}))

        # Get the machine list in format easy to create app_commands.Choice entries with.
        for machine_dict in machine_dict_list:
            self._OPTIONS_CACHE["machine_option_list"].append(
                {"name": machine_dict["name"], "value": str(machine_dict["id"]}))
        
        self._OPTIONS_CACHE["last_updated"] = time.monotonic()

        return active_event, user_id


    # ------------------------------------------------------------------
    # Autocomplete handlers
    # ------------------------------------------------------------------
    async def user_scores_autocomplete(self, interaction: discord.Interaction, current: str):
        async with get_db_connection() as db:
            user_scores = await get_user_scores(db, interaction.user.name)

        # Filter based on what the user is currently typing
        choices = [(opt["score"], opt["id"]) for opt in user_scores if current.casefold() in opt["score"].casefold()]
        # Return up to 25 results (discord limit)
        return [app_commands.Choice(name=opt, value=f"{opt}|{idopt}") for opt, idopt in choices[:25]]


    async def user_scores_autocomplete_nokingmaker(self, interaction: discord.Interaction, current: str):
        async with get_db_connection() as db:
            user_scores = await get_user_scores(db, interaction.user.name, check_for_score_method=True)

        # Filter based on what the user is currently typing
        choices = [(opt["score"], opt["id"]) for opt in user_scores if current.casefold() in opt["score"].casefold()]
        # Return up to 25 results (discord limit)
        return [app_commands.Choice(name=opt, value=f"{opt}|{idopt}") for opt, idopt in choices[:25]]


    async def machine_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        """ Autocomplete to present machine options.
        """
        clock = time.monotonic()

        if self._OPTIONS_CACHE["machine_option_list"] is not None and clock - self._OPTIONS_CACHE["last_updated"] < self._ACTIVE_TTL_SECONDS:
            # Use existing cache values
            options = self._OPTIONS_CACHE["machine_option_list"]
            # Assume no need to check whether the event is active, given the short
            #   cache window.
            return [app_commands.Choice(name=option["name"], value=option["value"]) for option in options[:4]]
        else:
            active_event, user_id = await self.get_event_config_from_db(interaction.user.name)
            if not active_event:
                return [app_commands.Choice(name="No active event", value="-1")]
            if not user_id:
                return [app_commands.Choice(name="No user id. Use command `/fzd_set_name` to add yourself.", value="-2")]
        
        options = [opt for opt in self._OPTIONS_CACHE["machine_option_list"] if current.casefold() in opt["name"].casefold()]
        return [app_commands.Choice(name=option["name"], value=option["id"]) for option in options[:4]]


    async def lineup_score_autocomplete(self, 
            interaction: discord.Interaction, 
            current: str) -> list[app_commands.Choice[str]]:
        """ Autocomplete to present lineup options.
        """
        clock = time.monotonic()

        if self._OPTIONS_CACHE["lineup_option_list"] is not None and clock - self._OPTIONS_CACHE["last_updated"] < self._ACTIVE_TTL_SECONDS:
            # Use existing cache values
            options = self._OPTIONS_CACHE["lineup_option_list"]
            # Assume no need to check whether the event is active, given the short
            #   cache window.
            return [app_commands.Choice(name=option["name"], value=option["value"]) for option in options[:25]]
        else:
            # Refresh lineup information from database and get info to confirm
            #   that there is an active event and user is in the database.
            active_event, user_id = await self.get_event_config_from_db(interaction.user.name)

            if not active_event:
                return [app_commands.Choice(name="No active event", value="-1")]
            if not user_id:
                return [app_commands.Choice(name="No user id. Use command `/fzd_set_name` to add yourself.", value="-2")]
            if not self._OPTIONS_CACHE["lineup_option_list"]:
                # Note: this condition should not trigger, as all possible 
                #   options are fetched if there are no event-specific lineups.
                return [app_commands.Choice(name="No lineups are available for this event.", value="-3")]
                    
            options = [opt for opt in self._OPTIONS_CACHE["lineup_option_list"] if current.casefold() in opt["name"].casefold()]
            # Note discord limit is 25 options; only first 25 options provided if exceeded.
            return [app_commands.Choice(name=option["name"], value=str(option["value"])) for option in options[:25]]
            

    # ==========================================================================================
    #   Begin slash commands
    # ==========================================================================================

    # =============================================================================================================
    #   /add_score
    # =============================================================================================================

    # Add a score to an event
    @app_commands.command(
        name="fzd_add_score", description="Add score to FZD scoreboard database"
    )  # , guild=GUILD_ID)
    @app_commands.describe(score="Enter an integer value for the score during an event")
    @app_commands.describe(machine="Select the machine used")
    async def add_score(self, interaction: discord.Interaction, score: str, machine: str = None, lineup: str = None):
        try:
            if int(score) < 0:
                raise ValueError(f"score can't be a negative integer {interaction.user}")
            elif int(score) > self._MAXSCORE:
                raise OverflowError(f"score entered too large! {interaction.user}")

            current_event, db_user_id = await self.get_event_config_from_db(interaction.user.name)
            if not db_user_id:
                # Ensure db_user_id created in database
                async with get_db_connection() as db:
                    db_user_id = await get_or_create_db_user(db, interaction.user)

            # Warnings
            if current_event["name"] == "NULL":
                await InputWarnings.no_event(interaction, "points")
                return
            if current_event["scoring_method"] != "points":
                await InputWarnings.wrong_scoring_method(interaction, current_event["name"], "points")
                return
            if not any(int(option.get("value")) == int(machine) for option in self._OPTIONS_CACHE["machine_option_list"]) and machine is not None:
                await InputWarnings.machine_not_found(interaction, machine, self._OPTIONS_CACHE["machine_option_list"])
                return
            if not any(int(option.get("value")) == int(lineup) for option in self._OPTIONS_CACHE["lineup_option_list"]) and lineup is not None:
                await InputWarnings.lineup_not_found(interaction)
                return
            if _EVENT_CONFIG_CACHE["is_machine_input_required"] is True and machine is None:
                await InputWarnings.machine_needed(interaction)
                return
            if _EVENT_CONFIG_CACHE["is_lineup_input_required"] is True and lineup is None:
                await InputWarnings.lineup_needed(interaction)
                return

            # Process machine info
            if machine is not None:
                machine_name = next(
                    (item["name"] for item in self._OPTIONS_CACHE["machine_option_list"] if item.get("id") == int(machine)), None)
            else:
                machine_name = None

            user_data = [
                db_user_id,
                current_event["id"],
                int(score),
                current_event["scoring_method"],
                int(machine),
                int(lineup),
            ]

            # Add score to database
            async with get_db_connection() as db:
                return_score = await submit_score_sql(db, user_data)  # interaction.user
            await interaction.response.send_message(
                f"✅ User {interaction.user} has entered a score of {return_score} to {current_event['name']} using machine {machine_name}"
            )  # , ephemeral=True)
            logger.info(
                "User %s entered score=%s for event=%s machine=%s",
                interaction.user,
                score,
                current_event["name"],
                machine_name,
            )

        except (
            ValueError
        ):  # should catch negative numbers and any errors with int(score) if score is not a base 10 integer
            await interaction.response.send_message(
                "❌ ERROR! 'score' must be entered as a positive integer!  ", ephemeral=True
            )
        except OverflowError:
            await interaction.response.send_message(
                f"❌ ERROR! 'score' should not be larger than {maxscore}. Please be nice to Nightmare's bot.",
                ephemeral=True,
            )
        except TypeError:
            await interaction.response.send_message(
                "❌ ERROR! Could not add you to the database. Try the '/fzd_set_name' command, or contact FZD staff for help.",
                ephemeral=True,
            )
        except Exception as error:
            await interaction.response.send_message(
                "❌ ERROR! Something went wrong, contact FZD staff for help! ", ephemeral=True
            )
            logger.exception("Exception in add_score for user=%s", interaction.user)
            await send_error_alert(
                self.bot,
                where="fzd_add_score",
                error=error,
                interaction=interaction,
            )

    # =============================================================================================================
    #   /add_rank
    # =============================================================================================================

    # Add a rank to an event
    @app_commands.command(
        name="fzd_add_rank", description="Add rank placement to FZD scoreboard (i.e. for Kingmaker events)"
    )  # , guild=GUILD_ID)
    @app_commands.describe(rank="Enter an integer value for the placement rank (1-99) during an event")
    @app_commands.describe(machine="Select the machine used")
    async def add_rank(self, interaction: discord.Interaction, rank: str, machine: str = None):
        maxrank = 99
        try:
            if int(rank) < 1 or int(rank) > maxrank:
                raise ValueError(f"rank must be between 1 and 99 {interaction.user}")

            # Get user id first, or add user if not registered in database
            async with get_db_connection() as db:
                db_user_id = await get_or_create_db_user(db, interaction.user)
                machine_list = [s["name"] for s in self.machine_dict if "name" in s]

                # check an event is active before adding data
                current_event = await check_for_active_event(db)

            logger.debug("add_rank current_event=%r", current_event)
            if current_event["name"] == "NULL":
                await InputWarnings.no_event(interaction, "rank")
                return
            if current_event["scoring_method"] == "points":
                await InputWarnings.wrong_scoring_method(interaction, current_event["name"], "points")
                return
            if machine not in machine_list and machine is not None:
                await InputWarnings.machine_not_found(interaction, machine, machine_list)
                return
            if current_event.get("is_machine_input_required") is True and machine is None:
                await InputWarnings.machine_needed(interaction)
                return

            if machine is not None:
                machine_choice = next(
                    (item for item in self.machine_dict if item.get("name") == machine), None
                )
                machine_choice_id = machine_choice["id"] if machine_choice else None
                machine_choice_name = machine_choice["name"] if machine_choice else None
            else:
                machine_choice_id = None
                machine_choice_name = None

            user_data = [
                db_user_id,
                current_event["id"],
                int(rank),
                current_event["scoring_method"],
                machine_choice_id,
            ]

            # Add rank to database
            async with get_db_connection() as db:
                return_score = await submit_score(db, user_data)  # interaction.user

            await interaction.response.send_message(
                f"✅ User {interaction.user} has entered rank {rank} → {return_score} points have been added to {current_event['name']} using machine {machine_choice_name}"
            )  # , ephemeral=True)
            logger.info(
                "User %s entered rank=%s (%s points) for event=%s machine=%s",
                interaction.user,
                rank,
                return_score,
                current_event["name"],
                machine_choice_name,
            )

        except (
            ValueError
        ):  # should catch negative numbers and any errors with int(score) if score is not a base 10 integer
            await interaction.response.send_message(
                "❌ ERROR! 'rank' must be between 1 and 99!  ", ephemeral=True
            )
        except TypeError:
            await interaction.response.send_message(
                "❌ ERROR! Could not add you to the database. Try the '/fzd_set_name' command, or contact FZD staff for help.",
                ephemeral=True,
            )
        except Exception as error:
            await interaction.response.send_message(
                "❌ ERROR! Something went wrong, contact FZD staff for help! ", ephemeral=True
            )
            logger.exception("Exception in add_rank for user=%s", interaction.user)
            await send_error_alert(
                self.bot,
                where="fzd_add_rank",
                error=error,
                interaction=interaction,
            )


    # =============================================================================================================
    #   /edit_score
    # =============================================================================================================

    # This command queries the database for scores of a current event to edit for a user
    @app_commands.command(
        name="fzd_edit_score",
        description="Edit a submitted score, set it to new_score in FZD scoreboard database",
    )
    async def editScore(self, interaction: discord.Interaction, old_score: str, new_score: str):
        #  old_score is returned packed as "<score>|<id>" when a proper option is selected
        opts = []
        try:
            async with get_db_connection() as db:
                valid_options = await get_user_scores(db, interaction.user.name, check_for_score_method=True)
                opts = [s["score"] for s in valid_options if "score" in s]
                score, idchoice = old_score.split("|")
                if score not in opts:
                    raise ValueError("score {score} not one of the options {opts}")

            # Warnings
            if score == "NO CURRENT EVENT":
                await InputWarnings.no_event(interaction, "edit")
                return
            elif score == "NO USER SCORES FOUND":
                await InputWarnings.no_existing_score(interaction, interaction.user.name)
                return
            elif score == "DISABLED FOR THIS EVENT":
                await InputWarnings.edit_disabled(interaction)
                return

            # Edit score in database
            async with get_db_connection() as db:
                await edit_score(db, (int(new_score), int(idchoice)))
            await interaction.response.send_message(
                f"✅ User {interaction.user.name} has modified submitted score from {score} to {new_score}"
            )

        except (ValueError, TypeError) as e:
            logger.warning("Exception in editScore for user=%s: %s", interaction.user, e)
            await interaction.response.send_message(
                "❌  ERROR! Both options 'old_score' and 'new_score'  must be entered as integers! \n"
                + f"    And 'old_score' must be one of the available options for you: {opts} \n"
                + f"    ---> You chose: '{old_score}'",
                ephemeral=True,
            )
        except Exception as error:
            logger.exception("Unexpected exception in editScore for user=%s", interaction.user)
            await send_error_alert(
                self.bot,
                where="fzd_edit_score",
                error=error,
                interaction=interaction,
                details={"old_score": old_score, "new_score": new_score},
            )
            await interaction.response.send_message(
                "❌ ERROR! Something went wrong, contact FZD staff for help!",
                ephemeral=True,
            )

    # =============================================================================================================
    #   /delete_score
    # =============================================================================================================

    # This command queries the database for scores of a current event to delete for a user
    @app_commands.command(
        name="fzd_delete_score", description="Delete a score you have submitted during an ongoing event"
    )
    async def deleteScore(self, interaction: discord.Interaction, score_to_delete: str):
        #  score_to_delete is returned packed as "<score>|<id>" when a proper option is selected
        opts = []
        try:
            async with get_db_connection() as db:
                valid_options = await get_user_scores(db, interaction.user.name)

            opts = [s["score"] for s in valid_options if "score" in s]
            score, idchoice = score_to_delete.split("|")
            
            if score not in opts:
                raise ValueError("score {score} not one of the options {opts}")

            # Warnings
            if score == "NO CURRENT EVENT":
                await InputWarnings.no_event(interaction, "delete")
                return
            elif score == "NO USER SCORES FOUND":
                await InputWarnings.no_existing_score(interaction, interaction.user.name)
                return

            view = ConfirmDeleteScore(interaction)
            await interaction.response.send_message(
                f"⚠️  Are you sure you want to delete '{score}' from your scores?",
                view=view,
                ephemeral=True,
            )

            timed_out = await view.wait()
            if timed_out or view.confirmed is None:
                await interaction.followup.send("Timed out — no changes were made.", ephemeral=True)
                return

            if view.confirmed:
                async with get_db_connection() as db:
                    await delete_score(db, [idchoice])
                await interaction.followup.send(
                    content=f"✅ User {interaction.user.name} has successfully deleted '{score}' from their submitted scores",
                    ephemeral=False,
                )
            else:
                await interaction.followup.send("Cancelled — no changes were made.", ephemeral=True)

        except (ValueError, TypeError) as e:
            logger.warning("Exception in deleteScore for user=%s: %s", interaction.user, e)
            await interaction.response.send_message(
                f"❌  ERROR! 'score_to_delete' must be one of the available options for you: {opts} \n"
                + f"    ---> You chose: '{score_to_delete}'",
                ephemeral=True,
            )
        except Exception as error:
            logger.exception("Unexpected exception in deleteScore for user=%s", interaction.user)
            await send_error_alert(
                self.bot,
                where="fzd_delete_score",
                error=error,
                interaction=interaction,
                details={"score_to_delete": score_to_delete},
            )
            if interaction.response.is_done():
                await interaction.followup.send(
                    "❌ ERROR! Something went wrong, contact FZD staff for help!",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "❌ ERROR! Something went wrong, contact FZD staff for help!",
                    ephemeral=True,
                )

    # Bind autocomplete handler to edit and delete commands in cog
    async def cog_load(self):
        self.editScore.autocomplete("old_score")(self.user_scores_autocomplete_nokingmaker)
        self.deleteScore.autocomplete("score_to_delete")(self.user_scores_autocomplete)
        self.add_score.autocomplete("machine")(self.machine_autocomplete)
        self.add_score.autocomplete("lineup")(self.lineup_score_autocomplete)
        self.add_rank.autocomplete("machine")(self.machine_autocomplete)


async def setup(bot: commands.Bot):
    settings = get_settings()
    GUILD_ID = discord.Object(id=settings.server_id)
    machine_dict = await Scoring.grab_machines()
    await bot.add_cog(Scoring(bot, machine_dict), guild=GUILD_ID)
