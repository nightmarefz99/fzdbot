import traceback
from typing import Literal
from datetime import datetime, timedelta
import discord
from discord import ui
from discord.ui import Modal, TextInput, Button
from fzdbot.utils.view_utils import (
    NextStep
)

#################################
# Button classes
#################################
class GenericButton(ui.Button):
    def __init__(self, parent_view: ui.LayoutView,
                 selection_id: int | None,
                 button_label: str, 
                 button_color: discord.ButtonStyle, 
                 button_disabled: bool,
                 next_step: NextStep):
        self.parent_view = parent_view
        self.selection_id = selection_id
        self.next_step = next_step
        super().__init__(label=button_label, style=button_color, disabled=button_disabled)

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.choice = self.selection_id
        self.parent_view.next_step = self.next_step

        self.disabled = True
        await interaction.response.defer()
        self.parent_view.stop()

    async def on_error(self, error: Exception, item: discord.ui.Item, interaction: discord.Interaction) -> None:
        # Print the traceback to your console for debugging
        traceback.print_exception(type(error), error, error.__traceback__)
        
        # Inform the user safely via interaction response or followup
        message = "An unexpected error occurred while processing your click."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)