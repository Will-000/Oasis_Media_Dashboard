import random
import urllib.parse
from nicegui import ui, app
from sqlalchemy import or_, select, and_, func
from Pages.local_view import local_view
from Tools.cards import local_card, missing_card
from Tools.database import session_local, Media
from Tools.header import base_layout
from Tools.navigation_engine import build_base_media_query
from Tools.web_stack import setup_history_listener


def local_page(filters: dict):
    base_layout()

    page_limits = [10, 25, 50, 100, 250, 500]
    if "items_per_page" not in app.storage.general:
        app.storage.general["items_per_page"] = 50
    items_per_page = app.storage.general["items_per_page"]

    if items_per_page not in page_limits:
        items_per_page = min(page_limits, key=lambda x: abs(x - items_per_page))
        app.storage.general["items_per_page"] = items_per_page

    if "card_columns_scale" not in app.storage.general:
        app.storage.general["card_columns_scale"] = 4
    initial_slider_value  = app.storage.general["card_columns_scale"]

    def calculate_columns(slider_val: int) -> int:
        return 10 - slider_val
    initial_columns = calculate_columns(initial_slider_value)

    # Filter parse
    base_stmt, search_str, active_types = build_base_media_query(filters)

    page_num = filters.get('page_num', 1)
    sort_by = filters.get('sort', 'date_desc')

    try:
        seed_val = float(filters.get('seed', 0.5))
    except (ValueError, TypeError):
        seed_val = 0.5

    # Data Fetch
    with session_local() as db:
        # Pagination
        total_items = db.execute(select(func.count()).select_from(base_stmt.subquery())).scalar() or 0
        total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
        if page_num > total_pages:
            page_num = total_pages

        # Sorting Logic
        if sort_by == 'date_desc':
            order_clause = [Media.date_added.desc(), Media.id.desc()]
        elif sort_by == 'date_asc':
            order_clause = [Media.date_added.asc(), Media.id.asc()]
        elif sort_by == 'title_asc':
            order_clause = [Media.title.asc(), Media.id.asc()]
        elif sort_by == 'title_desc':
            order_clause = [Media.title.desc(), Media.id.desc()]
        elif sort_by == 'random':
            seed_factor = int(abs(seed_val) * 1000000) or 7
            order_clause = [func.hex((Media.id * seed_factor) % 999983)]
        else:
            order_clause = [Media.date_added.desc(), Media.id.desc()]

        # Fetching
        offset_val = (page_num - 1) * items_per_page
        paginated_stmt = base_stmt.order_by(*order_clause).offset(offset_val).limit(items_per_page)
        items = db.execute(paginated_stmt).scalars().all()


    def apply_filters(updated_changes: dict):
        """ Re-compiles parameters and trigger a redirect """
        new_filters = {**filters, **updated_changes}
        if new_filters.get('sort') == 'random':
            if 'seed' not in new_filters or updated_changes.get('sort') == 'random':
                new_filters['seed'] = random.random()
        else:
            new_filters.pop('seed', None)

        query_params = {k: v for k, v in new_filters.items() if v and v != 'all'}
        query_str = urllib.parse.urlencode(query_params)
        suffix = f"?{query_str}" if query_str else ""
        ui.navigate.to(f"/view/local{suffix}")

    def pagination_controls():
        if total_pages > 1:
            with ui.row().classes("w-full items-center justify-between"):
                ui.button(icon='chevron_left', on_click=lambda: apply_filters({'page_num': page_num - 1})).props(
                    'flat text-color=accent')

                ui.label(f"Page {page_num} of {total_pages}").classes('text-accent')

                ui.button(icon='chevron_right', on_click=lambda: apply_filters({'page_num': page_num + 1})).props(
                    'flat text-color=accent')

    def update_grid_columns(slider_val: int):
        app.storage.general["card_columns_scale"] = slider_val
        actual_cols = calculate_columns(slider_val)
        grid_container.style(f'grid-template-columns: repeat({actual_cols}, minmax(0, 1fr));')

    def change_items_per_page(new_limit: int):
        app.storage.general["items_per_page"] = new_limit
        apply_filters({'page_num': 1})

    # UI
    with ui.column().classes('w-full'):
        # Header
        with ui.row().classes('w-full justify-between items-center text-accent'):
            ui.label("Library View").classes("text-2xl font-bold")
            ui.label(f"{total_items} Items").classes("text-md opacity-60")

        # Search Controls
        with ui.row().classes('w-full gap-4 items-center justify-evenly text-accent'):

            # Search Field
            with ui.row().classes("bg-secondary rounded-sm items-center min-w-[150px] min-h-[40px] px-2"):
                search_input = ui.input(placeholder='Search...', value=search_str).props('borderless dense color=accent input-class="text-accent"')
                search_input.on('keydown.enter', lambda: apply_filters({'search': search_input.value, 'page_num': 1}))
                search_input.on('clear', lambda: apply_filters({'search': '', 'page_num': 1}))

            # Sort Dropdown
            with ui.row().classes("bg-secondary rounded-sm items-center min-w-[150px] min-h-[40px] px-2"):
                sort_options = {
                    'date_desc': 'Newest First',
                    'date_asc': 'Oldest First',
                    'title_asc': 'Alphabetical',
                    'random': 'Random'
                }

                ui.add_css('''
                    .custom-select .q-field__native, 
                    .custom-select .q-field__native span {
                        color: var(--q-accent) !important;
                    }
                ''')

                ui.select(
                    options=sort_options,
                    value=sort_by,
                    on_change=lambda e: apply_filters({'sort': e.value, 'page_num': 1})
                ).props('''dense options-dense popup-content-style="background-color: var(--q-primary); color: var(--q-accent); border: 1px solid var(--q-secondary);"'''
                ).classes('custom-select rounded')

            # Category Chips
            with ui.row().classes("items-center min-w-[150px] min-h-[40px]"):
                ui.label("Categories:").classes("text-sm opacity-80")
                categories = ['all', 'image', 'comic', 'video', 'audio', 'book']

                for cat in categories:
                    is_active = cat in active_types or (cat == 'all' and ('all' in active_types or not active_types))
                    color_class = 'bg-secondary font-bold' if is_active else 'opacity-60'

                    def toggle_category(target_cat=cat):
                        if target_cat == 'all':
                            apply_filters({'media_type': 'all', 'page_num': 1})
                        else:
                            # Logic to add/remove from stackable selections list
                            current_stack = [t for t in active_types if t != 'all']
                            if target_cat in current_stack:
                                current_stack.remove(target_cat)
                            else:
                                current_stack.append(target_cat)

                            joined_str = ",".join(current_stack) if current_stack else 'all'
                            apply_filters({'media_type': joined_str, 'page_num': 1})

                    ui.button(cat.upper(), on_click=toggle_category).classes(f'text-xs px-3 py-1 rounded-full text-accent {color_class}').props('flat dense')

            # Card Sizer
            with ui.row().classes('bg-secondary rounded-sm px-2 items-center justify-evenly min-w-[150px] min-h-[40px] no-wrap'):
                ui.icon('zoom_in', size='xs').classes('text-accent')
                ui.label("Card:").classes("text-sm text-accent")

                size_slider = ui.slider(min=2, max=8, step=1, value=initial_slider_value, on_change=lambda e: update_grid_columns(e.value))
                size_slider.props('dense color=accent label input-style="color: var(--q-accent)"')

            # Item Count Sizer
            with ui.row().classes("bg-secondary rounded-sm px-2 items-center justify-evenly min-w-[150px] min-h-[40px] no-wrap"):
                ui.icon('article', size='xs').classes('text-accent mr-1')
                ui.label("Items:").classes("text-sm text-accent")

                per_page_options = {10: '10', 25: '25', 50: '50', 100: '100', 250: '250', 500: '500'}

                ui.select(
                    options=per_page_options,
                    value=items_per_page,
                    on_change=lambda e: change_items_per_page(int(e.value))
                ).props(
                    '''dense options-dense borderless popup-content-style="background-color: var(--q-primary); color: var(--q-accent); border: 1px solid var(--q-secondary);"'''
                    ).classes('custom-select rounded text-xs text-accent').style('width: 110px;')

        # ---- Cards ----
        pagination_controls()
        with ui.column().classes("w-full"):
            with ui.element('div').classes('w-full grid gap-4 p-2').style(f'grid-template-columns: repeat({initial_columns}, minmax(0, 1fr));') as grid_container:
                if items:
                    current_gallery_url = f"/view/local?page_num={page_num}&media_type={active_types}&sort={sort_by}&search={search_str}"
                    if sort_by == 'random': current_gallery_url += f"&seed={seed_val}"
                    for item in items:
                        item_filter = {
                            'sort': sort_by,
                            'media_type': ','.join(active_types),
                            'search': search_str,
                            'origin_url': current_gallery_url
                        }
                        if sort_by == 'random': item_filter['seed'] = seed_val
                        local_card(item, on_click=lambda target_id=item.id: local_view(target_id, overlay_container, filters=item_filter))
                else:
                    missing_card("No Images")
        pagination_controls()

    overlay_container = ui.element('div').classes('z-[3000]')
    setup_history_listener(overlay_container)
