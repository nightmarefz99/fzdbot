import logging

import discord
from discord import app_commands
from discord.ext import commands

from fzdbot.constants import SERVER_ICON_URL
from fzdbot.db import check_for_active_event, create_event, get_db_connection, get_event_schedule, get_event_types
from fzdbot.formatters import format_events_schedule
from fzdbot.settings import get_settings

logger = logging.getLogger(__name__)


class Events(commands.Cog):
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

    @app_commands.command(
        name="fzd_start_event", description="Choose FZD event to start, assuming no other event is ongoing"
    )
    async def startEvent(self, interaction: discord.Interaction, event: str):
        duration = 2
        opts = [event_option["name"] for event_option in self.recurring_events if "name" in event_option]
        try:
            event_name = [event_option["name"] for event_option in self.recurring_events if event_option["id"] == int(event)]
            if not event_name:
                raise IndexError("chosen event not part of list")

            async with get_db_connection() as db:
                for hour_to_check in range(0, duration + 1):
                    match_event = await check_for_active_event(db, hours_from_now=hour_to_check)
                    if match_event["name"] != "NULL":
                        message = f"another event is currently running -- {match_event['name']}"
                        if hour_to_check > 0:
                            message = f"another event will start within the next {duration} hours -- {match_event['name']}"
                        await interaction.response.send_message(
                            f"⚠️  Warning: Could not start event, {message}", ephemeral=True
                        )
                        return

                current_event = match_event
                current_event["name"] = event_name[0]
                current_event["id"] = int(event)
                await create_event(db, current_event, duration=duration)
                await interaction.response.send_message(f"✅ FZD event {event_name[0]} successfully started!")
                logger.info("User %s started event %s", interaction.user, event_name[0])
        except Exception as error:
            logger.warning("[startEvent] exception: %s", error)
            await interaction.response.send_message(
                f"❌ ERROR! Must choose from available event options -- {opts}", ephemeral=True
            )

    @app_commands.command(name="fzd_events_schedule", description="View upcoming FZD events schedule")
    async def viewSchedule(self, interaction: discord.Interaction):
        try:
            async with get_db_connection() as db:
                events = await get_event_schedule(db)
                formatted_lines = format_events_schedule(events)
                schedule = discord.Embed(title="Upcoming FZD Events Schedule", description="")
                schedule.set_thumbnail(url=SERVER_ICON_URL)
                schedule.add_field(name="", value=formatted_lines[0], inline=False)
                await interaction.response.send_message(embed=schedule)
        except Exception:
            await interaction.response.send_message(
                "❌ ERROR! Something went wrong, please contact FZD staff to address!", ephemeral=True
            )
            logger.exception("[viewSchedule] Exception occurred in fzd_events_schedule")

    async def cog_load(self):
        self.startEvent.autocomplete("event")(self.event_type_autocomplete)
        async with get_db_connection() as db:
            self.recurring_events = await get_event_types(db)


async def setup(bot: commands.Bot):
    settings = get_settings()
    guild_id = discord.Object(id=settings.server_id)
    await bot.add_cog(Events(bot), guild=guild_id)
