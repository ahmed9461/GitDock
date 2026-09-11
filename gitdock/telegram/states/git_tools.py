"""FSM states for P4.2 branch/commit interactions."""

from aiogram.fsm.state import State, StatesGroup


class GitToolsStates(StatesGroup):
    branch_name = State()
    branch_base = State()
    branch_search = State()
    commit_ref = State()
    compare_base = State()
    compare_head = State()
