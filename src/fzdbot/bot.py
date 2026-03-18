import logging

import discord
from discord.ext import commands

from fzdbot.db import init_db_pool
from fzdbot.settings import configure_logging, get_settings

logger = logging.getLogger(__name__)


class FZDBot(commands.Bot):
    async def setup_hook(self):
        try:
            self.db_pool = await init_db_pool()
            await self.load_extension("fzdbot.cogs.scoreboard")
            await self.load_extension("fzdbot.cogs.scoring")
            await self.load_extension("fzdbot.cogs.events")
            await self.load_extension("fzdbot.cogs.users")
            logger.info("Loaded extensions")
        except Exception:
            logger.exception("Failed to load extensions")

        try:
            settings = get_settings()
            guild_id = discord.Object(id=settings.server_id)
            synced = await self.tree.sync(guild=guild_id)
            logger.info("Synced %s commands to guild %s", len(synced), guild_id.id)
        except Exception:
            logger.exception("Error syncing commands")

    async def on_ready(self) -> None:
        logger.info("%s is now running", self.user)


def main() -> None:
    settings = get_settings()
    configure_logging()
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.messages = True

    client = FZDBot(command_prefix="!", intents=intents)
    client.run(token=settings.discord_token)


if __name__ == "__main__":
    main()
