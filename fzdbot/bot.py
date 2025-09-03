# TODO: 
#    Add Special Event option to "/start_event" - needs new entry in "events" table of database
#    Add a "before_date" option to "/show" so users can show older results too?
#    And add pagination to "/show", mostly for large events with a big scoreboard (i.e. GGP)
#    Add logic to make sure a manual event created doesn't run into another event's start time
#         in its 2-h window
import os

# External required modules 
from dotenv import load_dotenv
import discord
from discord.ext import commands
from discord import app_commands



# LOAD INFO FROM .env FILE
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = discord.Object(id=os.getenv('SERVER_ID'))

# BOT SETUP
intents = discord.Intents.default()
intents.message_content = True  # Required to read message content

class FZDBot(commands.Bot):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def setup_hook(self):
        """Called automatically at startup, safe for async setup."""
        # Load all cogs from /command_cogs folder
        try:
            await self.load_extension("fzdbot.command_cogs.show_scoreboard")
            await self.load_extension("fzdbot.command_cogs.scoring")
            await self.load_extension("fzdbot.command_cogs.events_users_handling")
            print("✅ Loaded extensions")
        except Exception as e:
            print(f"Failed to load extensions: {e}")

        try:
            # Force sync so bot command changes will appear right away
            synced = await self.tree.sync(guild=GUILD_ID)
            print(f'Synced {len(synced)} commands to guild {GUILD_ID.id}')
        except Exception as e:
            print(f'Error syncing commands: {e}')

    async def on_ready(self) -> None:
        print(f'✅ {self.user} is now running!')


def main() -> None:
    # Define bot client according to FZDBot class above
    client = FZDBot(command_prefix="!",intents=intents)

    # Run the bot!
    client.run(token=TOKEN)

if __name__ == '__main__':
    main()
