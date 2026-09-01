from nicegui import ui
from Tools.header import base_layout


def scraper_page():
    base_layout()
    ui.label("Scraper").classes("text-xl text-accent")