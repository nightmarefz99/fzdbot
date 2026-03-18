def format_discord_timestamp(dt, inline=False) -> str:
    """Build a Discord timestamp string."""
    particle = "on " if inline else ""
    return "{0}<t:{1}:f>".format(particle, int(dt.timestamp()))
