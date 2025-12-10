import discord
from discord.ext import tasks, commands
import asyncio
import json
import os
from datetime import timezone, datetime

from fzdbot.fzd_db import get_db_connection #connect_to_database
from fzdbot.fzd_db import get_event_scoreboard
from fzdbot.fzd_db import get_user_id
from fzdbot.formatters import format_discord_timestamp
from fzdbot.formatters import format_scoreboard_display_text
from fzdbot.formatters import format_scoreboard_for_discord_embed

thumbnail="https://media.discordapp.net/attachments/1399501477608951933/1400792457007861800/Supernova_Server_Icon.png?ex=689c6da3&is=689b1c23&hm=68b8d8790d30689fbad0dfb9341c78921ecf9afecc5919880c81680329c32644&=&format=webp&quality=lossless&width=1024&height=1024"
update_interval=30

class LiveScoreboardTask:
    def __init__(self, bot, event_id, thread_id, utc_start, utc_end, user_id):
        self.bot = bot
        self.event_id = event_id #1446594761916944546  # <-- Replace with your scoreboard channel
        self.thread_id = thread_id
        self.utc_start = utc_start
        self.utc_end = utc_end
        self.user_id = user_id
        
        self.scoreboard_message_id = None

        # Start the task
        self.update_scoreboard.start()

         # Start the loop
        #self.update_loop.start()

    async def build_scoreboard_embed(self) -> discord.Embed:
        """
        Generate a full Discord Embed for the scoreboard.
        """

        async with get_db_connection() as db: 
            eventinfo, eventscoreslist = await get_event_scoreboard(db, self.user_id, event_type=self.event_id)
        
        if eventinfo:
            eventdate = eventinfo['utc_start_dt'].replace(tzinfo=timezone.utc)
            scoreboard = discord.Embed(title=eventinfo['name']+"-- 🏁 Live Event Scoreboard", 
                                       description=f"*Played on {format_discord_timestamp(eventdate)}*", 
                                       color=discord.Color.blue())
            scoreboard.set_thumbnail(url=thumbnail)
            if not eventscoreslist:
                scoreboard.add_field(name="", value="NO RESULTS TO DISPLAY YET", inline=False)
            else:
                ranked_scoreboard = format_scoreboard_display_text(eventscoreslist)
                fields_display_text = format_scoreboard_for_discord_embed(ranked_scoreboard, max_num_lines=10)
                for i, block in enumerate(fields_display_text, start=1):
                    scoreboard.add_field(name="", value=block, inline=False)

            scoreboard.set_footer(text=f"Auto-updated every {update_interval} seconds")
            return scoreboard

    @tasks.loop(seconds=update_interval)
    async def update_scoreboard(self):
        """Background task that updates the scoreboard message."""
        await self.bot.wait_until_ready()

        # Check if event is active
        now = datetime.now(timezone.utc)
        if not (self.utc_start <= now <= self.utc_end):
            return  # Do nothing if outside event window

        # Get thread from id provided, ensure it exists
        print(self.thread_id)
        thread = await self.bot.fetch_channel(self.thread_id)
        if thread is None:
            print(f"[ERROR] Event {self.event_id}: thread not found")
            return

        # Create initial message if needed
        if self.scoreboard_message_id is None:
            embed = await self.build_scoreboard_embed()
            msg = await thread.send(embed=embed)
            self.scoreboard_message_id = msg.id
            return

        # Fetch existing message - create new one if not found
        try:
            msg = await thread.fetch_message(self.scoreboard_message_id)
        except discord.NotFound:
            embed = await self.build_scoreboard_embed()
            msg = await thread.send(embed=embed)
            self.scoreboard_message_id = msg.id
            return
        
        # Update the embed of the fetched message
        embed = await self.build_scoreboard_embed()
        await msg.edit(embed=embed)

    @update_scoreboard.before_loop
    async def before_update(self):
        await self.bot.wait_until_ready()

#async def setup(bot):
#    GUILD_ID=discord.Object(id=os.getenv('SERVER_ID'))
#    await bot.add_cog(LiveScoreboardCog(bot), guild=GUILD_ID)
