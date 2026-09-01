from pathlib import Path
from nicegui import ui


def bookmark_card(item):
    with ui.card().classes("bg-secondary w-full aspect-[3/4] flex flex-col justify-center items-center p-4"):
        ui.label(f"{item}").classes("text-accent")


def local_card(item, on_click=None):
    card = ui.card()

    if on_click:
        card.on('click', on_click)
    else:
        card.on('click', lambda: ui.navigate.to(f'/view/local/{item.id}'))

    with card.tight().classes('bg-secondary w-full aspect-[3/4] overflow-hidden hover:scale-105 transition-transform duration-200 cursor-pointer flex flex-col no-wrap'):

        with ui.element('div').classes('w-full h-[75%] shrink-0 overflow-hidden flex items-center justify-center relative'):
            if item.thumb_path:
                ui.image(Path(item.thumb_path)).classes('w-full h-full').props('fit=cover no-spinner')
            else:
                ui.icon("broken_image", color="accent").classes('w-full h-full flex items-center justify-center').props('size=4rem')

        with ui.element('div').classes('w-full h-[25%] grow px-3 py-1 flex items-center overflow-hidden'):
            ui.label(item.title).classes('text-accent text-sm font-medium line-clamp-2 leading-tight w-full')

def missing_card(text: str):
    with ui.card().tight().classes('bg-secondary w-full aspect-[3/4] overflow-hidden hover:scale-105 transition-transform duration-200 flex flex-col no-wrap'):
        with ui.element('div').classes('w-full h-[75%] shrink-0 overflow-hidden flex items-center justify-center bg-black/10'):
            ui.icon("broken_image", color="accent").classes('w-full h-full flex items-center justify-center').props('size=4rem')

        with ui.element('div').classes('w-full h-[25%] grow px-3 py-1 flex items-center overflow-hidden'):
            ui.label(str(text)).classes('text-accent text-sm font-medium line-clamp-2 leading-tight w-full text-center')
