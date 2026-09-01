from nicegui import ui
from Tools.header import base_layout


def bookmarks_page():
    base_layout()
    ui.label("Bookmarks").classes("text-xl text-accent")