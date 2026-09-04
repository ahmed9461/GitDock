"""Transient FSM states for P4.1 file browsing and input collection."""

from aiogram.fsm.state import State, StatesGroup


class FileBrowserFlow(StatesGroup):
    active = State()
    ref_input = State()
    create_name = State()
    create_content = State()
    upload_document = State()
    edit_content = State()
    replace_document = State()
