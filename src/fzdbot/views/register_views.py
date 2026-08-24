import traceback
import discord
from discord import ui
from fzdbot.utils.event_class import Event, Division, Team, UserRegistrations
from fzdbot.utils.view_utils import NextStep, DivTeam, discord_timestamp
from fzdbot.utils.status_policies import user_event_status
from fzdbot.views.common import GenericButton


#################################
# LayoutView classes
#################################

class CancelView(ui.LayoutView):
    def __init__(self, message: str):
        super().__init__(timeout=300)
        container = ui.Container()

        container.add_item(ui.TextDisplay(content=message))
        self.add_item(container)


class LoadView(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=300)
        self.next_step: NextStep = NextStep.NULL

        loading_screen_text = """Welcome to your portal to sign up for FZD events! If we have a pending event ready for your signup, you'll find it here.

For events with divisions or teams, we will endeavor to place you in your requested division or team, but we may need to make changes to account for capacity and balance.

In addition to server RULES, Event RULES are designed to foster a fun and competitive environment for all participants. Each event has its own set of rules and instructions. If you have a question, please ask. We only ask that you agree to read and follow the rules for the events you register for. 

Please confirm that you will read and follow the rules for each event you register for."""

        container = ui.Container()
        container.add_item(ui.TextDisplay(content="# Register for an Event"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay(content=loading_screen_text))

        self.affirm_button = GenericButton(parent_view=self, 
                                        selection_id=None, 
                                        button_label="Continue", 
                                        button_color=discord.ButtonStyle.green, 
                                        button_disabled=False, 
                                        next_step=NextStep.MENU
                                            )
        self.cancel_button = GenericButton(parent_view=self, 
                                        selection_id=None, 
                                        button_label="Leave", 
                                        button_color=discord.ButtonStyle.red, 
                                        button_disabled=False, 
                                        next_step=NextStep.LEAVE
                                            )
        
        container.add_item(ui.ActionRow(self.affirm_button, self.cancel_button))
        self.add_item(container)


class RegisterMenuView(ui.LayoutView):
    def __init__(self, events: list[Event], user: UserRegistrations):
        super().__init__(timeout=300)
        self.choice: int | None = None
        self.next_step: NextStep = NextStep.NULL
        self.message: str = ""

        container = ui.Container()
        container.add_item(ui.TextDisplay(content="# Register for an Event"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # Build sections for each event in events
        section_text: list[ui.TextDisplay] = []
        section_button: list[GenericButton] = []
        section: list[ui.Section] = []

        # Select button for each status.next_step
        for i, event in enumerate(events):
            status = user_event_status(event, user)
            section_text.append(ui.TextDisplay(
                content=f"### {event.event_name}\n\t{discord_timestamp(event.start_time, "long")}\n\t{status["label"]}"))
            section_button.append(GenericButton(parent_view=self, 
                                        selection_id=event.scheduled_event_id, 
                                        button_label=status["button_label"], 
                                        button_color=status["button_color"], 
                                        button_disabled=status["button_disabled"], 
                                        next_step=status["next_step"]
                                          ))
            section.append(ui.Section(section_text[i], accessory=section_button[i]))
            container.add_item(section[i])

        # Build the Cancel button section
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.ActionRow(
            GenericButton(parent_view=self, 
                            selection_id=None, 
                            button_label="Leave", 
                            button_color=discord.ButtonStyle.red, 
                            button_disabled=False, 
                            next_step=NextStep.LEAVE
                            )
        ))

        self.add_item(container)


class DivTeamAddView(ui.LayoutView):
    def __init__(self, event: Event):
        super().__init__(timeout=300)
        self.next_step: NextStep = NextStep.NULL
        self.choice: int | None = None
        self.event: Event = event
        self.div_team_string: DivTeam | None = None

        if self.event.divisions:
            self.div_team_string = DivTeam.DIVISION
            div_team_list = self.event.divisions
        elif self.event.teams:
            self.div_team_string = DivTeam.TEAM
            div_team_list = self.event.teams
        else:
            raise ValueError("To create a DivTeamView there need to be divisions (plural) or teams.")

        container = ui.Container()
        container.add_item(ui.TextDisplay(
            f"# Chooose a {self.div_team_string.capitalize()}"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # Build dropdown
        container.add_item(ui.ActionRow(self.div_team_selection(self, div_team_list)))
        self.status_text = ui.TextDisplay(content="-")
        container.add_item(self.status_text)

        # Build the Continue button section
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.continue_button = GenericButton(parent_view=self, 
                                        selection_id=self.choice, 
                                        button_label="Continue", 
                                        button_color=discord.ButtonStyle.green, 
                                        button_disabled=True, 
                                        next_step=NextStep.CONFIRM
                                          )
        self.back_button = GenericButton(parent_view=self, 
                                        selection_id=0, 
                                        button_label="Back", 
                                        button_color=discord.ButtonStyle.blurple, 
                                        button_disabled=False, 
                                        next_step=NextStep.MENU
                                            )
        container.add_item(ui.ActionRow(self.back_button, self.continue_button))

        self.add_item(container)

        self.set_status()

    #################################
    # Drowdown subclass
    #################################
    class div_team_selection(ui.Select):
        def __init__(self, parent_view: ui.LayoutView, div_team_list: list[Division] | list[Team]):
            self.parent_view = parent_view

            options = []
            for div_team in div_team_list:
                options.append(discord.SelectOption(label=div_team.name, 
                                        description=None, 
                                        value=div_team.id
                ))
            super().__init__(options=options)

        async def callback(self, interaction: discord.Interaction):
            # Assign output to class variable
            self.parent_view.choice = int(self.values[0])

            # Set default dropdown option to user's selection
            for option in self.options:
                option.default = (int(option.value) == int(self.values[0]))

            self.parent_view.set_status()
            await interaction.response.edit_message(view=self.parent_view)


    ###########################
    # Class methods
    ###########################

    def set_status(self) -> None:
        """ Enable/disable Continue button and set status textbox.
        """
        # Find div_team with dropdown choice id
        if not self.choice:
            self.continue_button.disabled = True
            self.status_text.content = "-"
            return

        # Get div_team object selected
        match self.div_team_string:
            case DivTeam.DIVISION:
                div_team = [dt for dt in self.event.divisions if dt.id == self.choice][0]
            case DivTeam.TEAM:
                div_team = [dt for dt in self.event.teams if dt.id == self.choice][0]
            case _:
                raise ValueError(f"Self.div_team must be 'division' or 'team', not {div_team}")

        # Set statuses
        if div_team.at_capacity:
            self.continue_button.disabled = True
            print(f"{self.div_team_string.capitalize()} {div_team.name} full!")
            self.status_text.content = f"{self.div_team_string.capitalize()} {div_team.name} full!"
        else:
            self.continue_button.disabled = False
            self.status_text.content = f"{div_team.capacity - div_team.num_registered} spots available!"
            self.continue_button.selection_id = self.choice


class DivTeamEditView(ui.LayoutView):
    def __init__(self, event: Event, existing_div_team_id: int):
        super().__init__(timeout=300)
        self.choice: int | None = existing_div_team_id
        self.event: Event = event
        self.existing_div_team_id: int = existing_div_team_id
        self.div_team_string: DivTeam | None = None
        self.next_step: NextStep = NextStep.NULL
        
        if self.event.divisions:
            self.div_team_string = DivTeam.DIVISION
            div_team_list = self.event.divisions
        elif self.event.teams:
            self.div_team_string = DivTeam.TEAM
            div_team_list = self.event.teams
        else:
            raise ValueError("To create a DivTeamView there need to be divisions (plural) or teams.")

        container = ui.Container()
        container.add_item(ui.TextDisplay(
            f"# Edit Your Registration"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))

        # Build dropdown part of container
        container.add_item(ui.ActionRow(self.div_team_selection(self, div_team_list)))
        self.status_text = ui.TextDisplay(content="-")
        container.add_item(self.status_text)

        # Build the button ActionRow
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        self.edit_button = GenericButton(parent_view=self, 
                                            selection_id=self.choice, 
                                            button_label="Change", 
                                            button_color=discord.ButtonStyle.blurple, 
                                            button_disabled=True, 
                                            next_step=NextStep.CONFIRM
                                                )
        self.withdraw_button = GenericButton(parent_view=self, 
                                            selection_id=self.choice, 
                                            button_label="Withdraw from Event", 
                                            button_color=discord.ButtonStyle.red, 
                                            button_disabled=False, 
                                            next_step=NextStep.WITHDRAW_CONF
                                                )
        self.back_button = GenericButton(parent_view=self, 
                                            selection_id=0, 
                                            button_label="Back", 
                                            button_color=discord.ButtonStyle.gray, 
                                            button_disabled=False, 
                                            next_step=NextStep.MENU
                                                )
        container.add_item(ui.ActionRow(
            self.back_button,
            self.edit_button, 
            self.withdraw_button)
            )

        self.add_item(container)

        self.set_status()


    #################################
    # Drowdown subclass
    #################################
    class div_team_selection(ui.Select):
        def __init__(self, parent_view: ui.LayoutView, div_team_list: list[Division] | list[Team]):
            self.parent_view = parent_view

            options = []
            for div_team in div_team_list:
                if div_team.id == self.parent_view.existing_div_team_id:
                    label = f"{div_team.name} (current)"
                else:
                    label = f"{div_team.name}"
                options.append(discord.SelectOption(label=label, 
                                        description=None, 
                                        value=div_team.id
                ))
            super().__init__(options=options)

        async def callback(self, interaction: discord.Interaction):
            # Assign output to class variable
            self.parent_view.choice = int(self.values[0])

            # Set default dropdown option to user's selection
            for option in self.options:
                option.default = (int(option.value) == int(self.values[0]))

            self.parent_view.set_status()
            await interaction.response.edit_message(view=self.parent_view)


    ###########################
    # Class methods
    ###########################

    def set_status(self) -> None:
        """ Enable/disable Continue button and set status textbox.
        """
        # Find div_team with dropdown choice id
        if not self.choice:
            self.edit_button.disabled = True
            self.status_text.content = "-"
            return

        # Get div_team object selected
        match self.div_team_string:
            case DivTeam.DIVISION:
                div_team = [d for d in self.event.divisions if d.id == self.choice][0]
            case DivTeam.TEAM:
                div_team = [t for t in self.event.teams if t.id == self.choice][0]
            case _:
                raise ValueError(f"Self.div_team must be 'division' or 'team', not {div_team}")

        # Set statuses
        if div_team.at_capacity:
            self.edit_button.disabled = True
            print(f"{self.div_team_string.capitalize()} {div_team.name} full!")
            self.status_text.content = f"{self.div_team_string.capitalize()} {div_team.name} full!"
        else:
            self.edit_button.disabled = False
            self.status_text.content = f"{div_team.capacity - div_team.num_registered} spots available!"
            self.edit_button.selection_id = self.choice

        if self.choice == self.existing_div_team_id:
            self.edit_button.disabled = True


class ConfirmView(ui.LayoutView):
    def __init__(self, event: Event, div_team_id: int):
        super().__init__(timeout=300)
        self.selection_id: int = 0
        self.next_step: NextStep = NextStep.NULL

        div_team_str = event.div_or_team()

        # get division/team name
        match div_team_str:
            case DivTeam.DIVISION:
                if len(event.divisions) == 1:
                    div_team_str = DivTeam.NEITHER
                    div_team_name = ""
                else:
                    div_team_name = [d.name for d in event.divisions if d.id == div_team_id][0]
            case DivTeam.TEAM:
                div_team_name = [t.name for t in event.teams if t.id == div_team_id][0]
            case _:
                raise ValueError(f"Self.div_team must be 'division' or 'team', not {div_team_str}")

        choice_text = f"### {event.event_name}\n\t{discord_timestamp(event.start_time, "long")}\n"
        if div_team_str != DivTeam.NEITHER:
            choice_text += f"**{div_team_str.capitalize()}**\n\t{div_team_name}"
        confirm_text = f"### Are you ready! Confirm below."

        container = ui.Container()
        container.add_item(ui.TextDisplay(content="# Confirm Your Choice"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay(content=f"{choice_text}\n\n\n\n{confirm_text}"))

        self.affirm_button = GenericButton(parent_view=self, 
                                selection_id=1, 
                                button_label="Let's Go!", 
                                button_color=discord.ButtonStyle.green, 
                                button_disabled=False, 
                                next_step=NextStep.MENU
                                    )
        self.cancel_button = GenericButton(parent_view=self, 
                                selection_id=0, 
                                button_label="Nevermind", 
                                button_color=discord.ButtonStyle.red, 
                                button_disabled=False, 
                                next_step=NextStep.MENU
                                            )

        container.add_item(ui.ActionRow(self.affirm_button, self.cancel_button))
        self.add_item(container)


class ConfirmWithdrawlView(ui.LayoutView):
    def __init__(self, event: Event, div_team_id: int):
        super().__init__(timeout=300)
        self.selection_id: int = 0
        self.next_step: NextStep = NextStep.NULL

        div_team_str = event.div_or_team()

        # get division/team name
        match div_team_str:
            case DivTeam.DIVISION:
                if len(event.divisions) == 1:
                    div_team_str = DivTeam.NEITHER
                    div_team_name = ""
                else:
                    div_team_name = [d.name for d in event.divisions if d.id == div_team_id][0]
            case DivTeam.TEAM:
                div_team_name = [t.name for t in event.teams if t.id == div_team_id][0]
            case _:
                raise ValueError(f"Self.div_team must be 'division' or 'team', not {div_team_str}")

        choice_text = f"### {event.event_name}\n\t{discord_timestamp(event.start_time, "long")}\n"
        if div_team_str != DivTeam.NEITHER:
            choice_text += f"**{div_team_str.capitalize()}**\n\t{div_team_name}"
        confirm_text = f"### Are you sure you want to withdraw your registration?"

        container = ui.Container()
        container.add_item(ui.TextDisplay(content="# Withdraw Your Registration?"))
        container.add_item(ui.Separator(spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay(content=f"{choice_text}\n\n\n\n{confirm_text}"))

        self.affirm_button = GenericButton(parent_view=self, 
                                        selection_id=1, 
                                        button_label="Withdraw", 
                                        button_color=discord.ButtonStyle.red, 
                                        button_disabled=False, 
                                        next_step=NextStep.MENU
                                            )
        self.cancel_button = GenericButton(parent_view=self, 
                                        selection_id=0, 
                                        button_label="Nevermind", 
                                        button_color=discord.ButtonStyle.gray, 
                                        button_disabled=False, 
                                        next_step=NextStep.MENU
                                            )
        container.add_item(ui.ActionRow(
            self.affirm_button,
            self.cancel_button)
            )
        self.add_item(container)

class ExitView(ui.LayoutView):
    def __init__(self):
        super().__init__(timeout=300)

        self.add_item(ui.Container(ui.TextDisplay("Thank you!")))