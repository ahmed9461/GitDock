"""Ephemeral FSM states for Tier 0 public repository search."""

from aiogram.fsm.state import State, StatesGroup


class RepositorySearchFlow(StatesGroup):
    waiting_query = State()
    active = State()
    waiting_min_stars = State()
    waiting_owner = State()
    waiting_topic = State()
