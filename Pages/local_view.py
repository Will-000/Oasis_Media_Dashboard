import urllib.parse
from nicegui import ui, background_tasks
from sqlalchemy import select
from Tools.database import Media, Comic, session_local
from Tools.header import base_layout
from Tools.navigation_engine import get_adjacent_media_id


def local_view(media_id: int, view_container: ui.element=None, filters: dict = None):
    if filters is None:
        filters = {'sort': 'date_desc', 'media_type': '', 'search': '', 'page': 1}

    if 'origin_url' not in filters:
        filters['origin_url'] = '/home'

    try:
        filters['page'] = int(filters.get('page', 1))
    except (ValueError, TypeError):
        filters['page'] = 1

    current_client = ui.context.client

    # Query
    url_filters = {}
    for k, v in filters.items():
        if v and k != 'origin_url':
            if k == 'media_type' and isinstance(v, (list, tuple, set)):
                url_filters[k] = ",".join(str(item).strip().lower() for item in v)
            else:
                url_filters[k] = v

    query_str = urllib.parse.urlencode(url_filters)
    url_suffix = f"?{query_str}" if query_str else ""

    ui.run_javascript(f'window.history.pushState({{}}, "", "/view/local/{media_id}{url_suffix}");')

    # Data Fetch
    with session_local() as db:
        item = db.execute(select(Media).filter(Media.id == media_id)).scalar_one_or_none()

    if not item:
        ui.label("Media not found").classes("text-accent p-4")
        return

    # Overlay logic
    is_overlay = view_container is not None
    if is_overlay:
        view_container.clear()

        with current_client.layout:
            target_context = view_container.classes(
                'w-screen h-screen fixed inset-0 z-[3000] bg-[#121212]/95 flex flex-col justify-between overflow-hidden p-0 m-0',
                replace='w-screen h-screen fixed inset-0 z-[3000] bg-[#121212]/95 flex flex-col justify-between overflow-hidden p-0 m-0'
            )

    else:
        existing_context = next(
            (el for el in current_client.elements.values() if getattr(el, '_is_direct_view_root', False)), None)

        if existing_context:
            existing_context.clear()
            target_context = existing_context
        else:
            base_layout()
            with current_client.layout:
                target_context = ui.element('div').classes(
                    'w-screen h-screen fixed inset-0 z-[3000] bg-[#121212] flex flex-col justify-between overflow-hidden p-0 m-0'
                )
                target_context._is_direct_view_root = True

    # Return to previous page or home page
    def close():
        kp_listener.active = False
        destination = filters.get('origin_url', '/home')

        if isinstance(destination, str):
            if "%5B" in destination or "[" in destination:
                destination = destination.replace("[", "").replace("]", "").replace("'", "").replace('"', "").replace(" ", "")

        if is_overlay:
            ui.run_javascript(f'window.history.pushState({{}}, "", "{destination}");')
            view_container.clear()
            view_container.classes(
                remove='w-screen h-screen fixed inset-0 z-[3000] bg-[#121212]/95 flex flex-col justify-between overflow-hidden p-0 m-0')
        else:
            ui.navigate.to(destination)

    def navigate(delta: int):
        adj_id = get_adjacent_media_id(item.id, delta, filters)
        if adj_id:
            kp_listener.active = False
            filters['page'] = 1
            local_view(adj_id, view_container if is_overlay else target_context, filters)
        else:
            ui.notify("End of matching library records")

    with current_client.layout:
        kp_listener = ui.keyboard(active=True)

    def handle_keyboard(e):
        if not e.action.keyup:
            return
        if e.key.arrow_left:
            if item.media_type != "comic":
                navigate(-1)
        elif e.key.arrow_right:
            if item.media_type != "comic":
                navigate(1)
        elif e.key.escape:
            close()

    kp_listener.on_key(handle_keyboard)

    with target_context:
        with ui.column().classes('w-full h-full p-0 m-0 gap-0 no-wrap justify-between overflow-hidden'):
            # ---- Header ----
            with ui.row().classes('w-full justify-between items-center text-accent p-4'):
                ui.label(item.title or item.file_name).classes('text-lg font-semi-bold truncate grow max-w-[70%]')
                ui.label(item.file_type.upper()).classes('bg-secondary p-1 rounded text-xs opacity-70')

            # ---- Media Display ----
            with ui.element('div').classes('w-full grow h-0 flex items-center justify-center overflow-hidden relative'):
                # Images
                if item.media_type == "image":
                    with ui.element('div').classes('relative flex items-center justify-center').style('max-width: 100vw; max-height: calc(100vh - 140px); display: inline-flex;'):
                        ui.html(f'<img src="/api/media/{item.id}" style="max-width: 100%; max-height: calc(100vh - 140px); width: auto; height: auto; object-fit: contain; display: block;" />')

                        ui.element('div').classes('absolute left-0 top-0 w-1/2 h-full z-20 bg-transparent').on('click', lambda: navigate(-1))
                        ui.element('div').classes('absolute right-0 top-0 w-1/2 h-full z-20 bg-transparent').on('click', lambda: navigate(1))

                # Video
                elif item.media_type == "video":
                    with ui.element('div').classes('flex items-center justify-center').style('max-width: 100vw; max-height: 100%; display: inline-flex;'):
                        ui.html(f'''
                            <video id="page-video-{item.id}" controls autoplay playsinline style="max-width: 100%; max-height: 100%; width: auto; height: auto; object-fit: contain; display: block;">
                                <source src="/api/media/{item.id}" type="video/mp4">
                            </video>
                        ''')

                # Comic
                elif item.media_type == "comic":
                    comic_display(item, kp_listener, navigate, filters)

                # Audio/Book fallback
                else:
                    with ui.column().classes('items-center justify-center p-6 gap-2 text-accent'):
                        ui.icon('insert_drive_file', size='lg')
                        ui.label(f"Format: {item.file_type.upper()}").classes('italic')
                        ui.label(f"Path: {item.file_path}").classes('text-xs text-center opacity-60 break-all')

            # ---- Footer Controls ----
            with ui.row().classes('w-full grid grid-cols-3 items-center p-4 pointer-events-auto cursor-default shrink-0'):

                with ui.element('div').classes('justify-self-start'):
                    ui.button('Close', on_click=close).props('flat text-color=accent').classes('text-xs')

                with ui.row().classes('justify-self-center items-center gap-2 no-wrap'):
                    ui.button(icon='arrow_back', on_click=lambda: navigate(-1)).props('flat text-color=accent round').classes(
                        'shrink-0 z-30')

                    ui.button('Edit Info', on_click=lambda: print(f"Edit {item.title}")).props('flat text-color=white').classes('text-xs mx-8')

                    ui.button(icon='arrow_forward', on_click=lambda: navigate(1)).props('flat text-color=accent round').classes(
                        'shrink-0 z-30')

                with ui.element('div').classes('justify-self-end'):
                    pass


def comic_display(item: Comic, kp_listener: ui.keyboard, navigate, filters: dict):
    """ Helper for CBR/CBZ """
    total_pages = item.image_count or 1
    initial_page = filters.get('page', 1)
    if not (1 <= initial_page <= total_pages):
        initial_page = 1

    state = {'current_page': 1}

    def handle_comic_keyboard(e):
        if not e.action.keyup:
            return
        if e.key.arrow_left:
            change_page(-1)
        elif e.key.arrow_right:
            change_page(1)

    kp_listener.on_key(handle_comic_keyboard)

    # ---- Display ----
    with ui.element('div').classes('relative overflow-y-auto overflow-x-hidden w-full max-w-full min-h-0').style(
            'max-height: calc(100vh - 140px); display: block;') as scroll_container:
        scroll_container.props(f'id="{scroll_container.id}"')
        comic_frame = ui.element('img').props(f'src="/api/media/{item.id}/page/{initial_page}"').style(
            'max-width: 100%; max-height: none; width: auto; height: auto; display: block; margin: 0 auto;')

        ui.element('div').classes('absolute left-0 top-0 w-1/2 h-full z-20 bg-transparent').on('click', lambda: change_page(-1))
        ui.element('div').classes('absolute right-0 top-0 w-1/2 h-full z-20 bg-transparent').on('click', lambda: change_page(1))

    page_indicator = ui.label(f"Page {initial_page} of {total_pages}").classes(
        'fixed bottom-20 left-1/2 -translate-x-1/2 font-medium text-sm min-w-[100px] text-center text-accent bg-black/20 px-3 py-1 rounded-full z-30')


    def change_page(delta: int):
        new_p = state['current_page'] + delta
        if 1 <= new_p <= total_pages:
            state['current_page'] = new_p
            comic_frame.props(f'src="/api/media/{item.id}/page/{new_p}"')
            page_indicator.text = f"Page {new_p} of {total_pages}"

            ui.run_javascript(f'''
                setTimeout(() => {{
                    const container = document.getElementById("{scroll_container.id}");
                    if (container) container.scrollTop = 0;
                }}, 0);
            ''')

            filters['page'] = new_p
            query_str = urllib.parse.urlencode({k: v for k, v in filters.items() if v})
            url_suffix = f"?{query_str}" if query_str else ""
            ui.run_javascript(f'window.history.pushState({{}}, "", "/view/local/{item.id}{url_suffix}");')
        else:
            navigate(delta)