from typing import Literal
import discord


class InputWarnings():
    """
    """
    def __init__(interaction: discord.Interaction):
        ...


    @staticmethod
    async def no_event(interaction: discord.Interaction, 
                       command: Literal["points","rank","edit","delete", "time"] ):
        match command:
            case "points" | "rank" | "time":
                await interaction.response.send_message(
                    f"⚠️  Warning: No event is currently active, {command} was not added!  ", 
                    ephemeral=True
                )
            case "edit" | "delete":
                await interaction.response.send_message(
                    f"⚠️  Warning: No event is currently active, can't {command} scores! If you need help, contact an FZD mod",
                    ephemeral=True,
                )


    @staticmethod
    async def wrong_scoring_method(interaction: discord.Interaction, 
                                   event_name: str, method: Literal["points","rank","time"]):
        match method:
            case "points":
                await interaction.response.send_message(
                    f"⚠️  Warning: {event_name} is normal scoring, please submit race/GP points using /fzd_add_score ",
                    ephemeral=True,
                )
            case "rank":
                await interaction.response.send_message(
                    f"⚠️  Warning: {event_name} requires rank results, please use /fzd_add_rank ",
                    ephemeral=True,
                )
            case "time":
                await interaction.response.send_message(
                    f"⚠️  Warning: {event_name} requires time submissions, please use /fzd_add_time ",
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
        machine_names = [machine["name"] for machine in machine_list]
        await interaction.response.send_message(
            f"⚠️  Warning: {machine} not one of the options {machine_names}. Score not added.",
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


    @staticmethod
    async def not_integer(interaction: discord.Interaction, 
        field: str, method: Literal["score","rank","time"]):
        """ Warns user of failure to enter an integer.
        """
        await interaction.response.send_message(
            f"⚠️  Warning: {field.capitalize()} must be a positive integer. {method.capitalize()} not added.",
            ephemeral=True,
        )


    @staticmethod
    async def out_of_bounds(interaction: discord.Interaction, 
        field: str, min_val: int | float, max_val: int | float, 
        method: Literal["score","rank","time"]):
        """ Warns user of value they entered in a field that is out of logic bounds.
        """
        await interaction.response.send_message(
            f"⚠️  Warning: Out of bounds. {field.capitalize()} must be between {min_val} and {max_val}. {method.capitalize()} not added.",
            ephemeral=True,
        )