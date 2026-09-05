from typing import Literal
import discord


class InputWarnings():
    """
    """
    def __init__(interaction: discord.Interaction):
        ...


    @staticmethod
    async def no_event(interaction: discord.Interaction, 
                       command: Literal["points","rank","edit","delete"] ):
        match command:
            case "points":
                await interaction.response.send_message(
                    "⚠️  Warning: No event is currently active, score was not added!  ", 
                    ephemeral=True
                )
            case "rank":
                await interaction.response.send_message(
                    "⚠️  Warning: No event is currently active, rank was not added!  ", 
                    ephemeral=True
                )
            case "edit":
                await interaction.response.send_message(
                    "⚠️   No current event active, can't edit scores! If you need help, contact an FZD mod",
                    ephemeral=True,
                )
            case "delete":
                await interaction.response.send_message(
                    "⚠️   No current event active, can't delete scores! If you need help, contact an FZD mod",
                    ephemeral=True,
                )


    @staticmethod
    async def wrong_scoring_method(interaction: discord.Interaction, 
                                   event_name: str, method: Literal["points","rank"]):
        match method:
            case "points":
                await interaction.response.send_message(
                    f"⚠️  Warning: {event_name} is normal scoring, please submit race/GP points using /fzd_add_score ",
                    ephemeral=True,
                )
            case "rank":
                await interaction.response.send_message(
                    f"⚠️  Warning: {method} requires rank results, please use /fzd_add_rank ",
                    ephemeral=True,
                )


    @staticmethod
    async def no_existing_score(interaction: discord.Interaction, name: str):
        await interaction.response.send_message(
            f"⚠️   No submitted scores found for user {name}! If you need help, contact an FZD mod",
            ephemeral=True,
        )


    @staticmethod
    async def edit_disabled(interaction: discord.Interaction):
        await interaction.response.send_message(
            "⚠️   The /fzd_edit_score command does not work with Rank-based Kingmaker-style events! \n"
            + "        If you need to edit a score, you may instead: \n"
            + "               (1) delete the score first with /fzd_delete_score, then \n"
            + "               (2) resubmit your rank with /fzd_add_rank \n"
            + "        Or contact an FZD mod for help!",
            ephemeral=True,
        )


    @staticmethod
    async def machine_not_found(interaction: discord.Interaction, 
                                machine: str, machine_list: list[str]):
        await interaction.response.send_message(
            f"⚠️  Warning: {machine} not one of the options {machine_list}. Score not added.",
            ephemeral=True,
        )

    @staticmethod
    async def lineup_not_found(interaction: discord.Interaction):
        await interaction.response.send_message(
                    f"⚠️  Warning: Lineup provided not one of the available options. Score not added.",
                    ephemeral=True,
                )

    @staticmethod
    async def machine_needed(interaction: discord.Interaction):
        await interaction.response.send_message(
            "⚠️  Warning: Machine option required for this event. Score not added.",
            ephemeral=True,
        )
    
    @staticmethod
    async def lineup_needed(interaction: discord.Interaction):
        await interaction.response.send_message(
            "⚠️  Warning: Lineup option required for this event. Score not added.",
            ephemeral=True,
        )