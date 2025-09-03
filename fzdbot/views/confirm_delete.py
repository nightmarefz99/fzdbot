import discord

# Define the confirmation view for delete_score command below
class ConfirmDeleteScore(discord.ui.View):
    def __init__(self, original_interaction):
        super().__init__(timeout=20) # Set a timeout for the view
        self.original_interaction = original_interaction
        self.confirmed = False

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        self.stop() # Stop listening for further interactions
        await interaction.response.edit_message(content=f"Score deleted.", view=None) # Remove buttons
        #await interaction.followup.send(content=f"✅ User {interaction.user.name} has successfully deleted '{self.score}' from their submitted scores", ephemeral=False)

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        self.stop() # Stop listening for further interactions
        await interaction.response.edit_message(content="Action canceled.", view=None) # Remove buttons

    async def on_timeout(self):
        # Handle timeout if no button is pressed
        if not self.confirmed:
            await self.original_interaction.edit_original_response(content="Confirmation timed out.", view=None)
