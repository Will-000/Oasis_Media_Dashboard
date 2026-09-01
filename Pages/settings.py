import asyncio
import threading
from pathlib import Path
from nicegui import ui, app, run
from Tools.header import base_layout
from Tools.scanner import scan_directory
from Tools.thumb_worker import start_thumbnail_workers
from Tools.metadata_worker import start_metadata_workers

thumbnail_thread = None
thumbnail_stop_signal = threading.Event()

metadata_thread = None
metadata_stop_signal = threading.Event()


def settings_page():
    base_layout()

    if "directories" not in app.storage.general:
        app.storage.general["directories"] = []

    with ui.column():

        # ---- Scanner ----
        with ui.column():
            ui.label("Scanner").classes('text-xl text-accent text-bold')

            @ui.refreshable
            def render_directory_list():
                current_dirs = app.storage.general["directories"]

                with ui.column().classes('bg-secondary w-full p-2'):
                    for index, directory in enumerate(current_dirs):
                        with ui.row().classes("bg-primary p-2 gap-2 items-center justify-between w-full"):
                            ui.label(directory).classes('text-accent text-md')

                            def remove_path(idx=index):
                                dirs = app.storage.general["directories"]
                                dirs.pop(idx)
                                app.storage.general["directories"] = dirs
                                render_directory_list.refresh()
                                ui.notify("Path removed.")

                            ui.icon("remove", color="red").classes("cursor-pointer").on('click', remove_path)

                    with ui.row().classes("bg-primary items-center justify-between p-2 gap-2 w-full"):
                        new_input = ui.input(placeholder="Enter folder path").classes('text-md').props("borderless input-class='text-white'")

                        def add_path():
                            path_str = new_input.value.strip()
                            if not path_str:
                                return

                            if not Path(path_str).exists():
                                ui.notify("Path does not exist.", type="negative")
                                return

                            dirs = app.storage.general["directories"]
                            if path_str not in dirs:
                                dirs.append(path_str)
                                app.storage.general["directories"] = dirs
                                render_directory_list.refresh()
                                ui.notify("Path added.")
                            else:
                                ui.notify("Path already saved.", type="info")

                        ui.icon("add", color="green").classes("cursor-pointer").on('click', add_path)

            render_directory_list()

            async def trigger_scan():
                target_paths = [Path(p) for p in app.storage.general["directories"]]
                if not target_paths:
                    ui.notify("Add at least one directory.", type="negative")
                    return

                ui.notify("Scanning process started.", type="info")
                await run.cpu_bound(scan_directory, target_paths)
                ui.notify("Library scan completed.", type="positive")

            ui.button("Scan Directories", on_click=trigger_scan).classes("bg-secondary text-accent").props("flat")

        # ---- Thumbnail ----
        with ui.column():
            ui.label("Thumbnail Workers").classes('text-xl text-accent text-bold')

            @ui.refreshable
            def render_engine_toggle_button():
                global thumbnail_thread, thumbnail_stop_signal

                # Check generator status
                is_running = thumbnail_thread is not None and thumbnail_thread.is_alive()

                async def toggle_engine():
                    global thumbnail_thread, thumbnail_stop_signal

                    if thumbnail_thread is not None and thumbnail_thread.is_alive():
                        # Engine active -> Signal shut down
                        thumbnail_stop_signal.set()

                        while thumbnail_thread.is_alive():
                            await asyncio.sleep(0.1)

                        thumbnail_thread = None
                        ui.notify("Thumbnail workers stopped.", type="positive")

                    else:
                        # Engine idle -> Initialize
                        ui.notify("Starting thumbnail workers.", type="info")
                        thumbnail_stop_signal.clear()

                        thumbnail_thread = threading.Thread(
                            target=start_thumbnail_workers,
                            args=(thumbnail_stop_signal,),
                            daemon=True
                        )
                        thumbnail_thread.start()
                        ui.notify("Thumbnail worker engine is running.", type="positive")

                    render_engine_toggle_button.refresh()

                # UI
                if is_running:
                    ui.label("Status: Active").classes("text-positive text-sm italic")
                    ui.button("Stop Thumbnail Workers", on_click=toggle_engine).classes("bg-negative text-accent w-full").props("flat")
                else:
                    ui.label("Status: Inactive").classes("text-negative text-sm italic")
                    ui.button("Start Thumbnail Workers", on_click=toggle_engine).classes("bg-positive text-accent w-full").props("flat")

            # Initialize rendering loop
            render_engine_toggle_button()

        # ---- Metadata ----
        with ui.column():
            ui.label("Metadata Workers").classes('text-xl text-accent text-bold')

            @ui.refreshable
            def render_engine_toggle_button():
                global metadata_thread, metadata_stop_signal

                # Check generator status
                is_running = metadata_thread is not None and metadata_thread.is_alive()

                async def toggle_engine():
                    global metadata_thread, metadata_stop_signal

                    if metadata_thread is not None and metadata_thread.is_alive():
                        # Engine active -> Signal shut down
                        metadata_stop_signal.set()

                        while metadata_thread.is_alive():
                            await asyncio.sleep(0.1)

                        metadata_thread = None
                        ui.notify("Metadata workers stopped.", type="positive")

                    else:
                        # Engine idle -> Initialize
                        ui.notify("Starting Metadata workers.", type="info")
                        metadata_stop_signal.clear()

                        metadata_thread = threading.Thread(
                            target=start_metadata_workers,
                            args=(metadata_stop_signal,),
                            daemon=True
                        )
                        metadata_thread.start()
                        ui.notify("Metadata worker engine is running.", type="positive")

                    render_engine_toggle_button.refresh()

                # UI
                if is_running:
                    ui.label("Status: Active").classes("text-positive text-sm italic")
                    ui.button("Stop Metadata Workers", on_click=toggle_engine).classes("bg-negative text-accent w-full").props("flat")
                else:
                    ui.label("Status: Inactive").classes("text-negative text-sm italic")
                    ui.button("Start Metadata Workers", on_click=toggle_engine).classes("bg-positive text-accent w-full").props("flat")

            # Initialize rendering loop
            render_engine_toggle_button()