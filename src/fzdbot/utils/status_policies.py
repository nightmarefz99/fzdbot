import discord
from fzdbot.utils.event_class import Event, UserRegistrations
from fzdbot.utils.view_utils import NextStep, discord_timestamp


def user_event_status(event: Event, user: UserRegistrations) -> dict:
    """
        Structure of user_dict:
            scheduled_event_id: int,
            type: Literal["division","team"],
            id: int (either division_id or team_id)

        Structure of output:
            label:
                - already registered (user in user_divisions or user_teams)
                - waitlist (user in log but not in user_divisions or user_teams)
                - registration open (user not in log and 
                    now > reg_open and num_registered < sum(capacity))
                - registration not yet open (now > reg_open)
                - registration closed (now > reg_close and user not in log)
                - event full (user not in log and num_registered >= capacity)
            button_label: str {"register", "edit"}
            button_disabled: bool [True, False]
            button_color: str [green, yellow]
            next_step: NextStep [enum]
    """
    status: dict | None = None
    # Case: user is registered
    #   Note: Present logic allows user to edit a registration after the 
    #       registration period closes
    if user.is_registered(event.scheduled_event_id):
        if event.has_solo_division:
            status = {
                "label": "Registered",
                "button_label": "Withdraw",
                "button_color": discord.ButtonStyle.red,
                "button_disabled": False,
                "next_step": NextStep.WITHDRAW_CONF
            }
        else:
            status = {
                "label": "Registered",
                "button_label": "Edit",
                "button_color": discord.ButtonStyle.blurple,
                "button_disabled": False,
                "next_step": NextStep.EDIT
            }
        return status

    # Case: user not registered, but registration is open
    if ((user.is_registered(event.scheduled_event_id) == False) and 
        (event.reg_period_open == True) and 
        (event.at_capacity == False)
    ):
        if event.has_solo_division:
            status = {
                        "label": "Registration Open!",
                        "button_label": "Register",
                        "button_color": discord.ButtonStyle.green,
                        "button_disabled": False,
                        "next_step": NextStep.CONFIRM
                    }
        else:
            status = {
                        "label": "Registration Open!",
                        "button_label": "Register",
                        "button_color": discord.ButtonStyle.green,
                        "button_disabled": False,
                        "next_step": NextStep.ADD
                    }
        return status
    
    # Case: user not registered, but registration not yet open
    if ((user.is_registered(event.scheduled_event_id) == False) and 
        (event.reg_period_not_started == True)
    ):
        status = {
                    "label": f"Registration opens {discord_timestamp(event.reg_open, "long")}",
                    "button_label": "Register",
                    "button_color": discord.ButtonStyle.green,
                    "button_disabled": True,
                    "next_step": NextStep.NULL
                }
        return status

    # Case: user not registered, but registration has closed
    if ((user.is_registered(event.scheduled_event_id) == False) and 
        (event.reg_period_closed == True)
    ):
        status = {
                    "label": f"Registration period has ended",
                    "button_label": "-----",
                    "button_color": discord.ButtonStyle.gray,
                    "button_disabled": True,
                    "next_step": NextStep.NULL
                }
        return status

    # Case: user not registered, and registration period has not closed, but event is full
    #   Note: to be modified if waitlist implemented
    if ((user.is_registered(event.scheduled_event_id) == False) and 
        (event.reg_period_closed == False) and 
        (event.at_capacity == True)
    ):
        status = {
                    "label": f"Event Full!",
                    "button_label": "-----",
                    "button_color": discord.ButtonStyle.gray,
                    "button_disabled": True,
                    "next_step": NextStep.NULL
                }
        return status