import logging

import aiomysql
import discord
from discord import app_commands
from discord.ext import commands

from fzdbot.db import add_new_user, get_db_connection, get_user_id, modify_user_display_name
from fzdbot.settings import get_settings

logger = logging.getLogger(__name__)


class Users(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="fzd_register", description="Register your discord id to FZD scoreboard database")
    async def registerUser(self, interaction: discord.Interaction, display_name: str):
        warning = ""
        if display_name is None:
            display_name = interaction.user.nick[0:10]
        elif len(display_name) > 10:
            display_name = display_name[0:10]
            warning = "⚠️  Warning: display_name should be 10 characters or less (as in F-Zero 99 in game name) \n"

        try:
            async with get_db_connection() as db:
                db_user_id = await get_user_id(db, interaction.user.name)
                if db_user_id is None:
                    await add_new_user(db, interaction.user, display_name=display_name)
                    await interaction.response.send_message(
                        f"{warning}✅  User {interaction.user} is now registered in the FZD database with display name {display_name}",
                        ephemeral=True,
                    )
                    logger.info("User %s registered with display name %s", interaction.user, display_name)
                else:
                    await modify_user_display_name(db, db_user_id, display_name)
                    await interaction.response.send_message(
                        f"{warning}✅  User {interaction.user} successfully modified their display name to {display_name}",
                        ephemeral=True,
                    )
                    logger.info("User %s modified display name to %s", interaction.user, display_name)
        except aiomysql.IntegrityError as error:
            await interaction.response.send_message(
                f"{warning}❌ ERROR! The name '{display_name}' is already taken in the database, please use a different name!",
                ephemeral=True,
            )
            logger.warning("[registerUser] IntegrityError: %s", error)
        except Exception:
            await interaction.response.send_message(
                f"{warning}❌ ERROR! Something went wrong, please contact FZD staff to address!", ephemeral=True
            )
            logger.exception("[registerUser] Exception occurred in fzd_register")


async def setup(bot: commands.Bot):
    settings = get_settings()
    guild_id = discord.Object(id=settings.server_id)
    await bot.add_cog(Users(bot), guild=guild_id)
