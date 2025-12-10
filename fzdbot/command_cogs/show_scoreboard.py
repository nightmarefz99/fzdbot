# Cog class for displaying scoreboard results using bot (/show command)

import os
from datetime import timezone
import discord
from discord.ext import commands
from discord import app_commands

from fzdbot.fzd_db import get_db_connection #connect_to_database
from fzdbot.fzd_db import get_event_types
from fzdbot.fzd_db import get_event_scoreboard
from fzdbot.fzd_db import get_user_id
from fzdbot.fzd_db import get_ggp7_events
from fzdbot.formatters import format_discord_timestamp
from fzdbot.formatters import format_scoreboard_display_text
from fzdbot.formatters import format_scoreboard_for_discord_embed

thumbnail="https://media.discordapp.net/attachments/1399501477608951933/1400792457007861800/Supernova_Server_Icon.png?ex=689c6da3&is=689b1c23&hm=68b8d8790d30689fbad0dfb9341c78921ecf9afecc5919880c81680329c32644&=&format=webp&quality=lossless&width=1024&height=1024"

class Scoreboard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def event_type_autocomplete(self, interaction: discord.Interaction,
                                      current: str) -> list[app_commands.Choice[str]]:
        event_choices = [ app_commands.Choice(name=e['name'], value=str(e['id'])) 
                          for e in self.recurring_events 
                          if current.lower() in e['name'].lower() ]

        return event_choices[:25] # Discord only accepts max 25 autocomplete results
    
    @app_commands.command(name="fzd_show", description="Show most current FZD event scoreboard") #,  guild=GUILD_ID)
    async def showScoreboard(self, interaction: discord.Interaction, event_type: str = None):
        try:
            async with get_db_connection() as db:
                db_user_id = await get_user_id(db,interaction.user.name)
                eventinfo, eventscoreslist = await get_event_scoreboard(db, db_user_id, event_type=event_type)
                ggp7_events = await get_ggp7_events(db)
                print(ggp7_events)
            
            if not eventinfo: 
                if event_type:
                    event_name = [e['name'] for e in self.recurring_events if e['id'] == int(event_type)]
                    await interaction.response.send_message(
                          f"⚠️  No results found for event_type '{event_name[0]}'! If this is unexpected behavior contact a mod!",
                          ephemeral=True
                          )
                else:
                    await interaction.response.send_message(
                          f"❌ ERROR! Something unexpected went wrong, contact an FZD mod to help!",
                          ephemeral=True
                          )
                    print(f"[showScoreboard] Unknown issue encountered by {interaction.user}")
            else:
                eventdate = eventinfo['utc_start_dt'].replace(tzinfo=timezone.utc)
                title=eventinfo['name']
                if not eventscoreslist:
                    scoreboard = discord.Embed(title=title, description=f"*Played on {format_discord_timestamp(eventdate)}*")
                    scoreboard.add_field(name="", value="NO RESULTS TO DISPLAY YET", inline=False)
                else:
                    # Check for division name, put in title if so
                    has_divisions = any(d.get("division") is not None for d in eventscoreslist)
                    if has_divisions:
                        title=title+" - "+eventscoreslist[0]["division"]

                    scoreboard = discord.Embed(title=title, description=f"*Played on {format_discord_timestamp(eventdate)}*")
                    scoreboard.set_thumbnail(url=thumbnail)

                    ranked_scoreboard = format_scoreboard_display_text(eventscoreslist)
                    fields_display_text = format_scoreboard_for_discord_embed(ranked_scoreboard, max_num_lines=10)
                    for i, block in enumerate(fields_display_text, start=1):
                        scoreboard.add_field(name="", value=block, inline=False)

                await interaction.response.send_message(embed=scoreboard)
        except Exception as e:
            await interaction.response.send_message(
                          f"❌ ERROR! Something unexpected went wrong, contact an FZD mod to help!",
                          ephemeral=True
                          ) 
            print(f"[showScoreboard] Exception {repr(e)}")
    
    async def cog_load(self):
        # Bind autocomplete handler properly
        self.showScoreboard.autocomplete("event_type")(self.event_type_autocomplete)
        async with get_db_connection() as db:
            self.recurring_events = await get_event_types(db)

async def setup(bot: commands.Bot):
    GUILD_ID=discord.Object(id=os.getenv('SERVER_ID'))
    await bot.add_cog(Scoreboard(bot), guild=GUILD_ID)
