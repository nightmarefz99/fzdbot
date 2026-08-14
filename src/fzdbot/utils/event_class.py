from typing import Literal, Self
from datetime import datetime
import asyncio
import discord
from fzdbot.utils.view_utils import discord_timestamp
from fzdbot.utils.db_utils import get_or_create_db_user
from fzdbot.fzd_db import (
    get_db_connection,
    get_registration_events,
    get_event_description,
    get_registration_period,
    get_event_divisions,
    get_event_teams,
    get_user_registrations,
    create_update_event,
    create_update_scheduled_event,
    create_update_divteam,
    create_update_registration_period
)

class Event():
    def __init__(self):
        self.event_id: int | None = None
        self.scheduled_event_id: int | None = None
        self.event_name: str | None = None
        self.description: str | None = None
        self.mode: Literal["99", "classic"] | None = None
        self.scoring: Literal["points", "placement"] | None = None
        self.machine_required: bool = False
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None
        self.divisions: list[Division] | None = []
        self.teams: list[Team] | None = []
        self.reg_period_id: int | None = None
        self.reg_open: datetime | None = None
        self.reg_close: datetime | None = None

    @property
    def duration(self) -> int | None:
        if self.start_time and self.end_time:
            return int(round((self.end_time - self.start_time).total_seconds() / 3600, 0))
        else:
            return None

    # reg_open and reg_close are optional values. if not present, assume event open,
    #   as users only presented with events that are in the future. 
    @property
    def reg_period_not_started(self) -> bool:
        if not self.reg_open:
            return False
        else:
            return self.reg_open > datetime.now()

    @property
    def reg_period_open(self) -> bool:
        if not self.reg_open or not self.reg_close:
            return True
        else:
            return (self.reg_open <= datetime.now()) and (self.reg_close > datetime.now())

    @property
    def reg_period_closed(self) -> bool:
        if not self.reg_close:
            return True
        else:
            return self.reg_close < datetime.now()

    @property
    def at_capacity(self) -> bool:
        if not self.divisions and not self.teams:
            raise AttributeError(f"Event object with id {self.scheduled_event_id} has no division or team defined.")
        if self.divisions:
            capacity_list = []
            for division in self.divisions:
                capacity_list.append(division.at_capacity)
            if all(capacity_list):
                return True
            else:
                return False
        if self.teams:
            capacity_list = []
            for team in self.teams:
                capacity_list.append(team.at_capacity)
            if all(capacity_list):
                return True
            else:
                return False

    @property
    def has_solo_division(self) -> bool:
        if self.divisions and self.teams:
            raise ValueError(f"An event can have teams or divisions, but not both.")
        if not self.divisions:
            return False
        elif len(self.divisions) == 1:
            return True
        else:
            return False


    def __repr__(self) -> str:
        return f"""Event(event_id='{self.event_id}'\n\
                scheduled_event_id='{self.scheduled_event_id}'\n\
                event_name='{self.event_name}'\n\
                description='{self.description}'\n\
                mode='{self.mode}'\n\
                scoring='{self.scoring}'\n\
                machine_required='{self.machine_required}'\n\
                start_time='{self.start_time}'\n\
                end_time='{self.end_time}'\n\
                divisions='{self.divisions}'\n\
                teams='{self.teams}'\n\
                reg_period_id='{self.reg_period_id}'\n\
                reg_open='{self.reg_open}'\n\
                reg_close='{self.reg_close}'\n\
                )"""

    # Make this a __format__ dunder method    
    def __format__(self, format_spec: str) -> Literal["detail"] | None:
        """Provides a detailed description of an event."""
        match format_spec:
            case "detail":
                if not self:
                    return None
                else:
                    event_string = ""
                    event_string += f"### {self.event_name}\n"
                    event_string += f"**Description:** {self.description if self.description is not None else "None"}\n"
                    event_string += f"**Mode:** {self.mode}   **Scoring:** {self.scoring}\n"
                    event_string += f"**Requires users to enter machine when scoring?:** {'Yes' if self.machine_required is self.machine_required else 'No'}\n"
                    event_string += f"**Event Start:** {discord_timestamp(self.start_time, 'long')}\n"
                    event_string += f"**Event End:** {discord_timestamp(self.end_time, 'long')}\n"
                    if self.teams:
                        event_string += f"**Teams:**\n"
                        for team in self.teams:
                            event_string += f"{team:detail}"
                    if self.divisions:
                        # Assume that if only division has same name as event that it is silent division
                        if (len(self.divisions) > 1) and (self.divisions[0].name != self.event_name):
                            event_string += f"**Divisions:**\n"
                            for division in self.divisions:
                                event_string += f"{division:detail}"
                    event_string += f"**Registration Window:**\n"
                    event_string += f"\t**Registration Opens:** {discord_timestamp(self.reg_open, 'long')}\n"
                    event_string += f"\t**Registration Closes:** {discord_timestamp(self.reg_close, 'long')}\n"

                    return event_string
            case _:
                raise ValueError("Unknown format specifier...")
                

    async def send_event_to_database(self):
        """ As method name suggests...
            Database calls allow for either updating or creating new database rows, 
            depending on if a row id is or is not None.  
        """
        # Save event and get id
        async with get_db_connection() as db:
            self.event_id = await create_update_event(db=db,
                            id=self.event_id, 
                            name=self.event_name,
                            description=self.description, 
                            duration=self.duration,
                            mode=self.mode, 
                            scoring=self.scoring
                            )
            self.scheduled_event_id = await create_update_scheduled_event(db=db,
                            id=self.scheduled_event_id, 
                            event_id=self.event_id,
                            name=self.event_name, 
                            start_time=self.start_time, 
                            end_time=self.end_time,
                            mode=self.mode, 
                            scoring=self.scoring, 
                            machine_required=self.machine_required
                            )
            self.reg_period_id = await create_update_registration_period(db=db,
                            id=self.reg_period_id,
                            scheduled_event_id=self.scheduled_event_id,
                            reg_open=self.reg_open,
                            reg_close=self.reg_close
                            )
            
            if self.divisions:
                for division in self.divisions:
                    await division.send_division_to_database(self.scheduled_event_id)
            if self.teams:
                for team in self.teams:
                    await team.send_team_to_database(self.scheduled_event_id)


    @staticmethod
    async def _get_event_description(event_id):
        """ Get description from events table
        """
        async with get_db_connection() as db:
            return await get_event_description(db, event_id)


    @staticmethod
    async def _get_registration_period(scheduled_event_id):
        """ Get information about the registration period
        """
        async with get_db_connection() as db:
            reg_period = await get_registration_period(db, scheduled_event_id)
            if reg_period:
                id = reg_period["reg_period_id"]
                open = reg_period["reg_open"]
                close = reg_period["reg_close"]
                return id, open, close
            else:
                return None, None, None


    @staticmethod
    async def _get_event_divisions(scheduled_event_id):
        """ Get division information
        """
        async with get_db_connection() as db:
            division_dict_list = await get_event_divisions(db, scheduled_event_id)
        if division_dict_list:
            div_list = []
            for division_dict in division_dict_list:
                division = Division()
                division.id = int(division_dict["id"])
                division.name = division_dict["name"]
                division.alt_name = division_dict["alt_name"]
                division.capacity = division_dict["capacity"]
                division.num_registered = division_dict["num_registered"]
                division.emote = division_dict["emote"]
                div_list.append(division)
            divisions = div_list
        else:
            divisions = None
        return divisions


    @staticmethod
    async def _get_event_teams(scheduled_event_id):
        """ Get teams information
        """
        async with get_db_connection() as db:
            team_dict_list = await get_event_teams(db, scheduled_event_id)
        if team_dict_list:
            team_list = []
            for team_dict in team_dict_list:
                team = Team()
                team.id = int(team_dict["id"])
                team.name = team_dict["name"]
                team.alt_name = team_dict["alt_name"]
                team.capacity = team_dict["capacity"]
                team.num_registered = team_dict["num_registered"]
                team.emote = team_dict["emote"]
                team_list.append(team)
            teams = team_list
        else:
            teams = None
        return teams


    @classmethod
    async def load_event_from_database(
        self, scheduled_event_name: str = None, scheduled_event_id: int = None) -> Self:
        """ As method name suggests...
        """
        # Accept only one input parameter
        if (scheduled_event_name is None) == (scheduled_event_id is None):
            raise ValueError(
                "Method accepts exactly one argument: either 'scheduled_event_name' or 'scheduled_event_id'.")
        
        # Create object
        self = Event()

        # Get scheduled_event (that have not ended) from list of registration events
        async with get_db_connection() as db:
            reg_event_dict_list = await get_registration_events(db)
        
        # Get event information based on input parameter: either id or name
        if scheduled_event_id is not None:
            reg_event_dict = next(
                (item for item in reg_event_dict_list if item["scheduled_event_id"] == scheduled_event_id), None)
        else:
            reg_event_dict = next(
                (item for item in reg_event_dict_list if item["event_name"] == scheduled_event_name), None)
        
        # Begin populating Event object instance
        self.event_id: int | None = int(reg_event_dict["event_id"])
        self.scheduled_event_id: int | None = int(reg_event_dict["scheduled_event_id"])
        self.event_name: str | None = reg_event_dict["event_name"]
        self.mode: Literal["99", "classic"] | None = reg_event_dict["mode"]
        self.scoring: Literal["points", "placement"] | None = reg_event_dict["scoring"]
        if reg_event_dict["scoring"] == 1:
            self.machine_required: bool = True
        else:
            self.machine_required: bool = False
        self.start_time: datetime | None = reg_event_dict["start_time"]
        self.end_time: datetime | None = reg_event_dict["end_time"]

        async with asyncio.TaskGroup() as evg:
            task_desc = evg.create_task(Event._get_event_description(self.event_id))
            task_sched = evg.create_task(Event._get_registration_period(self.scheduled_event_id))
            task_div = evg.create_task(Event._get_event_divisions(self.scheduled_event_id))
            task_team = evg.create_task(Event._get_event_teams(self.scheduled_event_id))

        self.description = task_desc.result()
        self.reg_period_id, self.reg_open, self.reg_close = task_sched.result()
        self.divisions = task_div.result()
        self.teams = task_team.result()

        return self


    def div_or_team(self) -> str:
        """ Returns string "division" or "team" depending on the whether the event has 
            divisions or teams.
        """
        if self.divisions:
            div_team_str = "division"
        elif self.teams:
            div_team_str = "team"
        else:
            raise ValueError(f"Event must have either divisions or teams, not neither.")

        return div_team_str

    
    def check_event(self):
        """Checks event instance for event readiness from a database/programmatic perspective."""

        # Check 1: Does the event have a scheduled event
        ...

class Division():
    def __init__(self):
        self.id: int | None = None
        self.scheduled_event_id = int | None
        self.name: str | None = None
        self.alt_name: str | None = None
        self.capacity: int | None = None
        self.num_registered: int | None = None
        self.emote: str | None = None


    @property
    def at_capacity(self) -> bool:
        if not self.capacity:
            return False
        else:
            return self.num_registered >= self.capacity
        

    def __repr__(self) -> str:
        return f"""Division(id='{self.id}'\n\
                scheduled_event_id='{self.scheduled_event_id}'\n\
                name='{self.name}'\n\
                alt_name='{self.alt_name}'\n\
                capacity='{self.capacity}'\n\
                emote='{self.emote}'\n\
                )"""
                
    
    def __format__(self, format_spec: str) -> Literal["detail"] | None:
        """Provides a detailed description of a division."""
        match format_spec:
            case "detail":
                if not self:
                    return None
                else:
                    division_string = ""
                    division_string += f"\t**Name:** {self.name}\n"
                    division_string += f"\t\t**Alternate Name:** {self.alt_name}\n"
                    division_string += f"\t\t**Emote:** {self.emote}\n"
                    division_string += f"\t\t**Capacity:** {self.capacity}\n"
                    return division_string
            case _:
                raise ValueError("Unknown format specifier...")
            
        
    async def send_division_to_database(self, scheduled_event_id: int):
        """ As the name suggests...
        """
        async with get_db_connection() as db:
            self.id = await create_update_divteam(db=db, 
                    id=self.id,
                    scheduled_event_id=scheduled_event_id, 
                    div_team="divisions",
                    name=self.name,
                    alt_name=self.alt_name,
                    emote=self.emote,
                    capacity=self.capacity
                    )


class Team():
    def __init__(self):
        self.id: int | None = None
        self.scheduled_event_id = int | None
        self.name: str | None = None
        self.alt_name: str | None = None
        self.capacity: int | None = None
        self.num_registered: int | None = None
        self.emote: str | None = None


    @property
    def at_capacity(self) -> bool:
        if not self.capacity:
            return False
        else:
            return self.num_registered >= self.capacity
    

    def __repr__(self) -> str:
        return f"""Team(id='{self.id}'\n\
                scheduled_event_id='{self.scheduled_event_id}'\n\
                name='{self.name}'\n\
                alt_name='{self.alt_name}'\n\
                capacity='{self.capacity}'\n\
                emote='{self.emote}'\n\
                )"""


    def __format__(self, format_spec: str) -> Literal["detail"] | None:
        """Provides a detailed description of a team."""
        match format_spec:
            case "detail":
                if not self:
                    return None
                else:
                    team_string = ""
                    team_string += f"\t**Name:** {self.name}\n"
                    team_string += f"\t\t**Alternate Name:** {self.alt_name}\n"
                    team_string += f"\t\t**Emote:** {self.emote}\n"
                    team_string += f"\t\t**Capacity:** {self.capacity}\n"
                    return team_string
            case _:
                raise ValueError("Unknown format specifier...")
            

    async def send_team_to_database(self, scheduled_event_id: int):
        """ As the name suggests...
        """
        async with get_db_connection() as db:
            self.id = await create_update_divteam(db=db, 
                    id=self.id,
                    scheduled_event_id=scheduled_event_id, 
                    div_team="teams",
                    name=self.name,
                    alt_name=self.alt_name,
                    emote=self.emote,
                    capacity=self.capacity
                    )
        

def group_list(group: list[Division] | list[Team]):
        string = ""
        for i, item in enumerate(group):
            string += f"{item.emote if item.emote is not None else ''} {item.name}"
            if (i+1) < len(group):
                string += "\n"
        return string


class UserRegistrations():
    def __init__(self, interaction: discord.Interaction):
        self.discord_user_id: str = interaction.user.name
        self.db_id: int | None = None
        self.registrations: list[dict] | None = None
        """ self.registrations dictionary format:
                {scheduled_event_id: int,
                type: Literal["division", "team],
                div_team_id: int}
            Note that waitlist status in div_team_id not currently implemented
        """

    def __format__(self, format_spec: str) -> Literal["detail"] | None:
            """Provides a detailed description of an event."""
            match format_spec:
                case "detail":
                    if not self:
                        return None
                    else:
                        out_string = "UserRegistrations(\n"
                        out_string += f"\tdiscord_user_id: {self.discord_user_id}\n"
                        out_string += f"\tdb_id: {self.db_id}\n"
                        out_string += "\tregistrations:\n"
                        if not self.registrations:
                            out_string += "\t\tNone\n"
                        else:
                            for i, registration in enumerate(self.registrations):
                                out_string += f"\t\tRegistration {i}\n"
                                out_string += f"\t\t\tscheduled_event_id: {registration['scheduled_event_id']}\n"
                                out_string += f"\t\t\ttype: {registration['type']}\n"
                                out_string += f"\t\t\tdiv_team_id: {registration['div_team_id']}\n"
                        return out_string
    

    def is_registered(self, scheduled_event_id):
        if self.registrations:
            if any(r.get("scheduled_event_id") == scheduled_event_id for r in self.registrations):
                return True
            else:
                return False
        else:
            return False
        

    async def get_user_info(self, interaction: discord.Interaction):
        if not self.discord_user_id:
            self.discord_user_id = interaction.user.name
        async with get_db_connection() as db:
            self.db_id = await get_or_create_db_user(db, interaction.user)
            self.registrations = await get_user_registrations(db, self.db_id)


# Dummy event for testing
from fzdbot.utils.view_utils import time_string_to_datetime
def test_event() -> Event:
    
    masters_division = Division()
    masters_division.id = None
    masters_division.name = "Masters"
    masters_division.alt_name = "masters"
    masters_division.emote = ":poop:"
    masters_division.capacity = 80
    expert_division = Division()
    expert_division.id = None
    expert_division.name = "Expert"
    expert_division.alt_name = "expert"
    expert_division.emote = ":smile:"
    expert_division.capacity = 80
    dummy_divisions = [
        masters_division,
        expert_division
    ]
    
    dummy_event = Event()
    dummy_event.event_id = None
    dummy_event.scheduled_event_id = None
    dummy_event.event_name = "Biggo Bigg Event"
    dummy_event.description = "A really big shew....."
    dummy_event.mode= "classic"
    dummy_event.scoring = "points"
    dummy_event.machine_required = False
    dummy_event.start_time = time_string_to_datetime("2026-09-01 01:00")
    dummy_event.end_time = time_string_to_datetime("2026-09-01 03:00")
    dummy_event.divisions = dummy_divisions
    dummy_event.teams = None
    dummy_event.reg_period_id = None
    dummy_event.reg_open = time_string_to_datetime("2026-07-30 05:00")
    dummy_event.reg_close = time_string_to_datetime("2026-08-31 14:00")

    return dummy_event