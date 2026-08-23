import time
import asyncio
import discord
from discord import app_commands, ui
from discord.ext import commands
from fzdbot.settings import get_settings
from fzdbot.fzd_db import (
    get_db_connection, 
    get_registration_events,
    get_stats_99_options_db
)
from fzdbot.utils.event_class import Event, UserRegistrations, UserStats
from fzdbot.utils.view_utils import NextStep, DivTeam
from fzdbot.utils.db_utils import refresh_event_list, registration_update_db, get_or_create_db_user
from fzdbot.views.register_views import (
    CancelView,
    LoadView,
    RegisterMenuView,
    DivTeamAddView,
    DivTeamEditView,
    ConfirmView,
    ConfirmWithdrawlView,
    ExitView
)
from fzdbot.views.stats_menu_views import (
        StatViewHistory99,
        StatViewHistoryClassic,
        BasicStatsView
)

#############################################
# Slash Commands
#############################################

class EventRegister(commands.Cog):
    def __init__(self, bot: commands.Bot, event_list: list[str]) -> None:
        self.bot: commands.Bot = bot
        self.event_list: list[str] | None = event_list

    #############################################
    # Functions for loading tasks
    #############################################

    @staticmethod
    async def loading_menu(interaction: discord.Interaction) -> None:
        """ Loading menu task to seek interaction from user while 
            database loading and view creation occur in the background.
        """
        load_view = LoadView()
        await interaction.response.send_message(view=load_view, ephemeral=True)
        await load_view.wait()

        return load_view.next_step


    @staticmethod
    async def get_event_information() -> list[Event]:
        """
        """
        events: list[Event] = []

        async with get_db_connection() as db:
            reg_event_dict_list = await get_registration_events(db)
            event_id_list = [event['scheduled_event_id'] for event in reg_event_dict_list if 'scheduled_event_id' in event]

        async with asyncio.TaskGroup() as eg:
            tasks = [eg.create_task(
                Event.load_event_from_database(scheduled_event_id=event_id)) for event_id in event_id_list]
        events = [task.result() for task in tasks]

        return events


    @staticmethod
    async def get_user_reg_information(interaction: discord.Interaction) -> UserRegistrations:
        """
        """
        user = UserRegistrations(interaction)
        await user.get_user_info(interaction)
        return user


    @staticmethod
    async def startup_tasks(interaction: discord.Interaction
            ) -> tuple[list[Event], UserRegistrations, ui.LayoutView]:
        """ Performs database retrievals and view creation while the user is 
            made to do the unthinkable: read text.
        """
        start = time.perf_counter()
        # Create task group for loading from the database
        async with asyncio.TaskGroup() as dlg:
            task1 = dlg.create_task(EventRegister.get_event_information())
            task2 = dlg.create_task(EventRegister.get_user_reg_information(interaction))

        events = task1.result()
        user = task2.result()

        database_load_time = time.perf_counter() - start
        print(f"Initial database calls complete: {database_load_time:.4f} seconds")

        return events, user


    @staticmethod
    async def get_stat_views(
        interaction: discord.Interaction, 
        selected_event: Event, 
        user_id: int) -> UserStats:
        """ Determines which stats view to present to the user. Currently hard-coded to 
            a "basic" view.
        """
        view_type = "basic"
        #match selected_event.mode:
        match view_type:
            case "99":
                async with get_db_connection() as db:
                    # machine_options = await get_machines(db)
                    ggp_options, recent_options, self_eval_options = await get_stats_99_options_db(db)
                    user_stats = await UserStats.load_user_stats(user_id, selected_event.scheduled_event_id)
                stats99_view = StatViewHistory99(ggp_options, recent_options, user_stats)
                await interaction.edit_original_response(view=stats99_view)
                timed_out = await stats99_view.wait()
                if await EventRegister.timeout_check(timed_out, interaction): return
                user_stats = stats99_view.user_stats
                next_view = stats99_view.next_step

            case "classic":
                async with get_db_connection() as db:
                    # machine_options = await get_machines(db)
                    ggp_options, recent_options, self_eval_options = await get_stats_99_options_db(db)
                    user_stats = await UserStats.load_user_stats(user_id, selected_event.scheduled_event_id)
                statsclassic_view = StatViewHistoryClassic(user_stats)
                await interaction.edit_original_response(view=statsclassic_view)
                timed_out = await statsclassic_view.wait()
                if await EventRegister.timeout_check(timed_out, interaction): return
                user_stats = statsclassic_view.user_stats
                next_view = statsclassic_view.next_step

            case "basic":
                async with get_db_connection() as db:
                    # machine_options = await get_machines(db)
                    ggp_options, recent_options, self_eval_options = await get_stats_99_options_db(db)
                    user_stats = await UserStats.load_user_stats(user_id, selected_event.scheduled_event_id)

                if user_stats.self_eval_id and user_stats.most_recent_id:
                    # Both already exist; no need to collect info
                    next_view = NextStep.NULL
                else:
                    statsbasic_view = BasicStatsView(recent_options, self_eval_options, user_stats)
                    await interaction.edit_original_response(view=statsbasic_view)
                    timed_out = await statsbasic_view.wait()
                    if await EventRegister.timeout_check(timed_out, interaction): return
                    user_stats = statsbasic_view.user_stats
                    next_view = statsbasic_view.next_step

        return user_stats, next_view
    

    """ Utility Methods """
    @staticmethod
    async def timeout_check(timed_out: bool, interaction: discord.Interaction):
        """ Checking asyncio wait for timeout after each message. Placed in separate method
            to preserve ease of reading in slack command.
        """
        # Check why we stopped waiting
        if timed_out:
            await interaction.followup.send("Selection timed out. Please try again.", ephemeral=True)
        return timed_out


    """ Commands """
    @app_commands.command(
        name="ggp_register", description="Register for an event"
    )
    async def event_register(self, interaction: discord.Interaction):
        """
        """
        # Method Variables
        selected_event: Event | None = None
        div_team_str: DivTeam | None = None
        div_team_id: int | None = None
        new_div_team_id: int | None = None
        async with get_db_connection() as db:
            user_id: int = await get_or_create_db_user(db, interaction.user)
        user_stats: UserStats | None = None
        next_view = NextStep.LOADING

        # View loop
        try: 
            async with asyncio.timeout(290):
                while next_view != NextStep.LEAVE:
                    match next_view:
                        case NextStep.LOADING:
                            # Set up concurrent tasks to load info and create views while user reading
                            # loading screen.
                            async with asyncio.TaskGroup() as tg:
                                task1 = tg.create_task(EventRegister.startup_tasks(interaction))
                                task2 = tg.create_task(EventRegister.loading_menu(interaction))

                            events, user = task1.result()
                            next_view = task2.result()

                        case NextStep.MENU:
                            div_team_str = None
                            selected_event = None
                            div_team_id = None
                            new_div_team_id = None
                            # Send register menu message
                            menu_view = RegisterMenuView(events, user)
                            await interaction.edit_original_response(view=menu_view)
                            timed_out = await menu_view.wait()
                            if await EventRegister.timeout_check(timed_out, interaction): return
                            next_view = menu_view.next_step
                            match next_view:
                                case NextStep.LEAVE:
                                    ...
                                case _:
                                    # Grab selected event
                                    selected_event = [event for event in events if event.scheduled_event_id == menu_view.choice][0]
                                    if selected_event.has_solo_division:
                                        match next_view:
                                            case NextStep.CONFIRM:
                                                user_stats, stats_next_view = await self.get_stat_views(interaction, selected_event, user_id)
                                                if stats_next_view == NextStep.MENU:
                                                    next_view = stats_next_view
                                                    selected_event = None
                                                    continue
                                                new_div_team_id = selected_event.divisions[0].id
                                            case NextStep.WITHDRAW_CONF:
                                                div_team_id = selected_event.divisions[0].id
                                            case _:
                                                print(f"Logic error: selecting a button of an event with a solo division should lead to 'confirm' or 'withdraw', not {next_view}")

                                    # String to identify if the event supports divisions or teams.
                                    div_team_str = selected_event.div_or_team()

                        case NextStep.ADD:
                            user_stats, stats_next_view = await self.get_stat_views(interaction, selected_event, user_id)
                            if stats_next_view == NextStep.MENU:
                                next_view = stats_next_view
                                selected_event = None
                                continue
                            div_team_view = DivTeamAddView(selected_event)
                            await interaction.edit_original_response(view=div_team_view)
                            timed_out = await div_team_view.wait()
                            if await EventRegister.timeout_check(timed_out, interaction): return

                            next_view = div_team_view.next_step
                            match next_view:
                                case NextStep.MENU:
                                    selected_event = None
                                    div_team_id = None
                                    new_div_team_id = None
                                case _:
                                    new_div_team_id = div_team_view.choice

                        case NextStep.EDIT:
                            user_stats, stats_next_view = await self.get_stat_views(interaction, selected_event, user_id)
                            if stats_next_view == NextStep.MENU:
                                next_view = stats_next_view
                                selected_event = None
                                continue
                            div_team_id = [user_reg["div_team_id"] for user_reg in user.registrations if user_reg["scheduled_event_id"] == selected_event.scheduled_event_id][0]
                            div_team_edit_view = DivTeamEditView(event=selected_event, 
                                                                    existing_div_team_id=div_team_id)
                            await interaction.edit_original_response(view=div_team_edit_view)
                            timed_out = await div_team_edit_view.wait()
                            if await EventRegister.timeout_check(timed_out, interaction): return

                            next_view = div_team_edit_view.next_step
                            match next_view:
                                case NextStep.MENU:
                                    selected_event = None
                                    div_team_id = None
                                    new_div_team_id = None
                                case _:
                                    new_div_team_id = div_team_edit_view.choice
                            

                        case NextStep.CONFIRM:
                            confirmation_view = ConfirmView(selected_event, new_div_team_id)
                            await interaction.edit_original_response(view=confirmation_view)
                            timed_out = await confirmation_view.wait()
                            if await EventRegister.timeout_check(timed_out, interaction): return

                            next_view = confirmation_view.next_step

                            # "choice" represents cancel (0) and confirm (1)
                            if confirmation_view.choice == 0:
                                # Confirmation canceled. Reset loop variables.
                                selected_event = None
                                div_team_id = None
                                new_div_team_id = None
                                user_stats = None

                            else:
                                # Update database to add/change user's division/team.
                                await registration_update_db(db_user_id=user.db_id, 
                                                        scheduled_event_id=selected_event.scheduled_event_id,
                                                        div_team_str=div_team_str,
                                                        add_div_team_id=new_div_team_id, 
                                                        rm_div_team_id=div_team_id)
                                print(f"{interaction.user.name} added to {selected_event.event_name}, {div_team_str} {div_team_id}")
                                await user_stats.save_user_stats()
                                print(f"User stats of {interaction.user.name} for {selected_event.event_name} have been saved to the database.")
                                user = await EventRegister.get_user_reg_information(interaction)

                                # Reset loop variables.
                                selected_event = None
                                div_team_id = None
                                new_div_team_id = None
                                user_stats = None

                        case NextStep.WITHDRAW_CONF:
                            withdraw_view = ConfirmWithdrawlView(selected_event, div_team_id)
                            await interaction.edit_original_response(view=withdraw_view)
                            timed_out = await withdraw_view.wait()
                            if await EventRegister.timeout_check(timed_out, interaction): return

                            next_view = withdraw_view.next_step

                            # "choice" represents cancel (0) and confirm (1)
                            if withdraw_view.choice == 0:
                                # Confirmation canceled. Reset loop variables.
                                selected_event = None
                                div_team_id = None
                                new_div_team_id = None
                                user_stats = None
                            else:
                                # Update database to remove user from division/team.
                                await registration_update_db(db_user_id=user.db_id, 
                                                        scheduled_event_id=selected_event.scheduled_event_id,
                                                        div_team_str=div_team_str,
                                                        rm_div_team_id=div_team_id)
                                print(f"{interaction.user.name} removed from {selected_event.event_name}, {div_team_str} {div_team_id}")
                                user = await EventRegister.get_user_reg_information(interaction)

                                # Reset loop variables.
                                selected_event = None
                                div_team_id = None
                                new_div_team_id = None
                                user_stats = None
        except TimeoutError:
            print("Async loop stopped by timeout.")
            await interaction.edit_original_response(view=ExitView())
        # For NextStep.LEAVE:
        await interaction.edit_original_response(view=ExitView())


async def setup(bot: commands.Bot):
    server_id = get_settings().server_id
    GUILD_ID = discord.Object(id=server_id)
    # Get initial event list. To be refreshed upon /event_create_update calls
    event_list = await refresh_event_list()
    await bot.add_cog(EventRegister(bot, event_list), guild=GUILD_ID)