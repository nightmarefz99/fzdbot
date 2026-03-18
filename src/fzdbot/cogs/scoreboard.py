import logging
from datetime import timezone

import discord
from discord import app_commands
from discord.ext import commands

from fzdbot.constants import SERVER_ICON_URL
from fzdbot.db import get_db_connection, get_event_scoreboard, get_event_types, get_user_id
from fzdbot.formatters import (
    format_discord_timestamp,
    format_scoreboard_display_text,
    format_scoreboard_for_discord_embed,
)
from fzdbot.settings import get_settings

logger = logging.getLogger(__name__)


class Scoreboard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def event_type_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        event_choices = [
            app_commands.Choice(name=event["name"], value=str(event["id"]))
            for event in self.recurring_events
            if current.lower() in event["name"].lower()
        ]
        return event_choices[:25]

    @app_commands.command(name="fzd_show", description="Show most current FZD event scoreboard")
    async def showScoreboard(self, interaction: discord.Interaction, event_type: str = None):
        try:
            await interaction.response.defer()
            async with get_db_connection() as db:
                db_user_id = await get_user_id(db, interaction.user.name)
                eventinfo, eventscoreslist = await get_event_scoreboard(db, db_user_id, event_type=event_type)

            if not eventinfo:
                if event_type:
                    event_name = [event["name"] for event in self.recurring_events if event["id"] == int(event_type)]
                    await interaction.followup.send(
                        f"⚠️  No results found for event_type '{event_name[0]}'! If this is unexpected behavior contact a mod!",
                        ephemeral=True,
                    )
                else:
                    await interaction.followup.send(
                        "❌ ERROR! Something unexpected went wrong, contact an FZD mod to help!",
                        ephemeral=True,
                    )
                    logger.warning("[showScoreboard] Unknown issue encountered by %s", interaction.user)
                return

            eventdate = eventinfo["utc_start_dt"].replace(tzinfo=timezone.utc)
            title = eventinfo["name"]
            if not eventscoreslist:
                scoreboard = discord.Embed(title=title, description=f"*Played on {format_discord_timestamp(eventdate)}*")
                scoreboard.add_field(name="", value="NO RESULTS TO DISPLAY YET", inline=False)
            else:
                has_divisions = any(entry.get("division") is not None for entry in eventscoreslist)
                if has_divisions:
                    title = title + " - " + eventscoreslist[0]["division"]

                scoreboard = discord.Embed(title=title, description=f"*Played on {format_discord_timestamp(eventdate)}*")
                scoreboard.set_thumbnail(url=SERVER_ICON_URL)

                ranked_scoreboard = format_scoreboard_display_text(eventscoreslist)
                fields_display_text = format_scoreboard_for_discord_embed(ranked_scoreboard, max_num_lines=10)
                for block in fields_display_text:
                    scoreboard.add_field(name="", value=block, inline=False)

            await interaction.followup.send(embed=scoreboard)
        except Exception:
            logger.exception("[showScoreboard] Exception user=%r event_type=%r", interaction.user, event_type)
            if interaction.response.is_done():
                await interaction.followup.send(
                    "❌ ERROR! Something unexpected went wrong, contact an FZD mod to help!",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "❌ ERROR! Something unexpected went wrong, contact an FZD mod to help!",
                    ephemeral=True,
                )

    async def cog_load(self):
        self.showScoreboard.autocomplete("event_type")(self.event_type_autocomplete)
        async with get_db_connection() as db:
            self.recurring_events = await get_event_types(db)


async def setup(bot: commands.Bot):
    settings = get_settings()
    guild_id = discord.Object(id=settings.server_id)
    await bot.add_cog(Scoreboard(bot), guild=guild_id)
