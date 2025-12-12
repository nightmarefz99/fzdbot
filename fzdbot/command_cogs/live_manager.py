import discord
from discord.ext import tasks, commands
import asyncio
import json
import os
from datetime import datetime,timezone

from fzdbot.fzd_db import get_db_connection #connect_to_database
from fzdbot.fzd_db import get_event_scoreboard
from fzdbot.fzd_db import get_user_id
from fzdbot.fzd_db import get_ggp7_events
from fzdbot.formatters import format_discord_timestamp
from fzdbot.formatters import format_scoreboard_display_text
from fzdbot.formatters import format_scoreboard_for_discord_embed
from fzdbot.command_cogs.live_scoreboard import  LiveScoreboardTask
import fzdbot.live_config as LC # Gets DIVISION_DICT 

class LiveScoreboardManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_tasks = {}  # event_id -> LiveScoreboardTask

        self.live_events = None
        # Automatically scan every 2 minutes
        self.scan_events.start()

    # -------------------------------------
    # PERIODIC EVENT SCAN
    # -------------------------------------
    @tasks.loop(minutes=2)
    async def scan_events(self):
        await self.bot.wait_until_ready()

        # Get list of events if we have not yet
        if self.live_events is None:
            async with get_db_connection() as db:
                self.live_events = await get_ggp7_events(db)
                print(self.live_events)

        now = datetime.now(timezone.utc)

        for ev in self.live_events:
            ev_id = ev["event_id"]
            start = ev["utc_start_dt"].replace(tzinfo=timezone.utc)
            end = ev["utc_end_dt"].replace(tzinfo=timezone.utc)
            
            # Extract thread ids and user ids from .env
            # for chosen event
            EVENT_STATIC_DATA = [d for d in LC.DIVISION_DICT if int(d.get("id")) == ev_id] # dict
            if EVENT_STATIC_DATA:
                thread_ids = EVENT_STATIC_DATA[0]["thread_ids"].split()
                user_ids = EVENT_STATIC_DATA[0]["user_ids"].split()

                print(f"{ev_id} ===> {EVENT_STATIC_DATA}")           
                # Event currently active
                for thread_id, user_id in zip(thread_ids, user_ids):
                    if start <= now <= end:
                        if thread_id not in self.active_tasks:
                            print(f"Starting task for event {ev_id}, {user_id}")
                            self.active_tasks[thread_id] = LiveScoreboardTask(
                                                       self.bot, ev_id, thread_id, 
                                                       start, end, user_id )
                    # Event already ended & task exists → stop it
                    elif thread_id in self.active_tasks:
                        print(f"Stopping task for event {ev_id}, {user_id}")
                        task = self.active_tasks.pop(thread_id)
                        task.update_scoreboard.cancel()

    @scan_events.before_loop
    async def before_scan(self):
        await self.bot.wait_until_ready()

async def setup(bot): 
    GUILD_ID=discord.Object(id=os.getenv('SERVER_ID'))
    await bot.add_cog(LiveScoreboardManager(bot), guild=GUILD_ID)
