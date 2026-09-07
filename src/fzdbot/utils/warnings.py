from typing import Literal
import discord

# =============================================================================
# Custom exception classes
# =============================================================================

class UserError(Exception):
    """ Base exception class """
    def __init__(self, message: str = "User error", name: str = "UserError"):
        self.message = message
        self.name = name
        super().__init__(self.message, self.name)

class NoUserInDatabaseError(UserError):
    """ No user in database, and cannot create """
    def __init__(self, message: str = "No user in database", name: str = "NoUserInDatabaseError"):
        self.message = message
        self.name = name
        super().__init__(self.message, self.name)


class ScoreEntryError(Exception):
    """ Base exception class """
    def __init__(self, message: str = "User input error", name: str = "ScoreEntryError"):
        self.message = message
        self.name = name
        super().__init__(self.message, self.name)

class NoActiveEventError(ScoreEntryError):
    """ When there is no active event """
    def __init__(self, message: str = "No active event", name: str = "NoActiveEventError"):
        self.message = message
        self.name = name
        super().__init__(self.message, self.name)

class WrongEventTypeError(ScoreEntryError):
    """ When the the user runs a slash command not relevant to the event """
    def __init__(self, message: str = "Wrong event type", name: str = "WrongEventTypeError"):
        self.message = message
        self.name = name
        super().__init__(self.message, self.name)

class OutOfBoundsError(ScoreEntryError):
    """ When the the user enters a numeric value not within required bounds """
    def __init__(self, message: str = "Entry out of bounds", name: str = "OutOfBoundsError"):
        self.message = message
        self.name = name
        super().__init__(self.message, self.name)

class InvalidMachineError(ScoreEntryError):
    """" When the the user makes an invald entry into the machine field """
    def __init__(self, message: str = "Invalid machine", name: str = "InvalidMachineError"):
        self.message = message
        self.name = name
        super().__init__(self.message, self.name)

class InvalidLineupError(ScoreEntryError):
    """" When the the user makes an invald entry into the lineup field """
    def __init__(self, message: str = "Invalid lineup", name: str = "InvalidLineupError"):
        self.message = message
        self.name = name
        super().__init__(self.message, self.name)

class OptionRequiredError(ScoreEntryError):
    """" When an optional slash command is required for the specific event """
    def __init__(self, message: str = "Option required", name: str = "OptionRequiredError"):
        self.message = message
        self.name = name
        super().__init__(self.message, self.name)

class NoResultsToModifyError(ScoreEntryError):
    """ When a database lookup determines the user hasn't entered any results to edit or delete """
    def __init__(self, message: str = "No results to modify", name: str = "NoResultsToModifyError"):
        self.message = message
        self.name = name
        super().__init__(self.message, self.name)

class WrongSelectionError(ScoreEntryError):
    """ When the user makes a selection that doesn't exist (often by ignoring the autocomplete) """
    def __init__(self, message: str = "Selection chosen does not exist", name: str = "WrongSelectionError"):
        self.message = message
        self.name = name
        super().__init__(self.message, self.name)


# =============================================================================
# User warning class
# =============================================================================

class InputWarnings():
    """
    """
    def __init__(interaction: discord.Interaction) -> None:
        ...

    @staticmethod
    async def user_not_found(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "❌ ERROR! Could not add you to the database. Try the '/fzd_set_name' command, or contact FZD staff for help.",
            ephemeral=True,
        )
        raise NoUserInDatabaseError(f"User {interaction.user.name} cannot be added to the database.")


    @staticmethod
    async def no_event(interaction: discord.Interaction, 
                       command: Literal["points","placement","edit","delete", "time"]) -> None:
        match command:
            case "points" | "placement" | "time":
                await interaction.response.send_message(
                    f"⚠️  Warning: No event is currently active, {command} was not added!  ", 
                    ephemeral=True
                )
            case "edit" | "delete":
                await interaction.response.send_message(
                    f"⚠️  Warning: No event is currently active, can't {command} scores! If you need help, contact an FZD mod",
                    ephemeral=True,
                )
        raise NoActiveEventError(f"User {interaction.user.name} tried to submit a race result with no active event.")


    @staticmethod
    async def wrong_scoring_method(interaction: discord.Interaction, 
            event_name: str, method: Literal["points","placement","time"]) -> None:
        match method:
            case "points":
                await interaction.response.send_message(
                    f"⚠️  Warning: {event_name} is normal scoring, please submit race/GP points using /fzd_add_score ",
                    ephemeral=True,
                )
            case "placement":
                await interaction.response.send_message(
                    f"⚠️  Warning: {event_name} requires rank results, please use /fzd_add_rank ",
                    ephemeral=True,
                )
            case "time":
                await interaction.response.send_message(
                    f"⚠️  Warning: {event_name} requires time submissions, please use /fzd_add_time ",
                    ephemeral=True,
                )
        raise WrongEventTypeError(f"User {interaction.user.name} used the wrong command during {event_name}")


    @staticmethod
    async def no_existing_score(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            f"⚠️   No submitted scores found for user {interaction.user.name}! If you need help, contact an FZD mod",
            ephemeral=True,
        )
        raise NoResultsToModifyError(f"User {interaction.user.name} attempted to edit/delete score but has none.")


    @staticmethod
    async def edit_disabled(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "⚠️   The /fzd_edit_score command does not work with Time-based or Rank-based Kingmaker-style events! \n"
            + "        If you need to edit a score, you may instead: \n"
            + "               (1) delete the score first with /fzd_delete_score, then \n"
            + "               (2) resubmit your rank with /fzd_add_rank or /fzd_add_time\n"
            + "        Or contact an FZD mod for help!",
            ephemeral=True,
        )
        raise WrongEventTypeError(f"User {interaction.user.name} attempted to use \\fzd_edit_score outside a points-based event.")

    @staticmethod
    async def machine_not_found(interaction: discord.Interaction, 
        machine: str, machine_list: list[str]) -> None:
        """ """
        machine_names = [machine["name"] for machine in machine_list]
        await interaction.response.send_message(
            f"⚠️  Warning: Machine {machine} not one of the options {machine_names}. Result not added.",
            ephemeral=True,
        )
        raise InvalidMachineError(f"User {interaction.user.name} entered Machine {machine} when only the following were allowed: {machine_names}")


    @staticmethod
    async def lineup_not_found(interaction: discord.Interaction, lineup: str) -> None:
        await interaction.response.send_message(
                    f"⚠️  Warning: Lineup '{lineup}' not one of the available options. Result not added.",
                    ephemeral=True,
                )
        raise InvalidLineupError(f"User {interaction.user.name} entered Lineup id {lineup}, which was not one of the options.")


    @staticmethod
    async def machine_needed(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            f"⚠️  Warning: Machine option required for this event. Result not added.",
            ephemeral=True,
        )
        raise OptionRequiredError(f"User {interaction.user.name} did not provide a machine when it was required for an event.")
    

    @staticmethod
    async def lineup_needed(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            f"⚠️  Warning: Lineup option required for this event. Result not added.",
            ephemeral=True,
        )
        raise OptionRequiredError(f"User {interaction.user.name} did not provide a lineup when it was required for an event.")


    @staticmethod
    async def machine_and_lineup_needed(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            f"⚠️  Warning: Both machine and lineup options are required for this event. Result not added.",
            ephemeral=True,
        )
        raise OptionRequiredError(f"User {interaction.user.name} did not provide either a machine or lineup when both were required for an event.")


    @staticmethod
    async def not_integer(interaction: discord.Interaction, 
        field: str, method: Literal["score","placement","time"]) -> None:
        """ Warns user of failure to enter an integer.
        """
        await interaction.response.send_message(
            f"⚠️  Warning: {field.capitalize()} must be a positive integer. {method.capitalize()} not added.",
            ephemeral=True,
        )
        raise ValueError(f"User {interaction.user.name} entered a {field} that was not a (positive) integer.")


    @staticmethod
    async def out_of_bounds(interaction: discord.Interaction, 
        field: str, min_val: int | float, max_val: int | float) -> None:
        """ Warns user of value they entered in a field that is out of logic bounds.
        """
        await interaction.response.send_message(
            f"⚠️  Warning: Result must be between {min_val} and {max_val}, not {field}. Result not added.",
            ephemeral=True,
        )
        raise OutOfBoundsError(f"User {interaction.user.name} entered a result of {field}.")


    @staticmethod
    async def result_not_found(interaction: discord.Interaction) -> None:
        """
        """
        await interaction.response.send_message(
            f"⚠️  Warning: Result not one of the available options. Scores remain unchanged.",
            ephemeral=True,
        )
        raise WrongSelectionError(f"User {interaction.user.name} attempted to choose an option that doesn't exist.")