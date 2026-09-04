"""FSM states for repository creation and administration flows."""

from aiogram.fsm.state import State, StatesGroup


class RepositoryCreateFlow(StatesGroup):
    name = State()
    description = State()


class RepositorySettingsFlow(StatesGroup):
    rename = State()
    description = State()
    default_branch = State()
    delete_name = State()
