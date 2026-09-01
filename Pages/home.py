from nicegui import ui, app
from Pages.local_view import local_view
from Tools.cards import bookmark_card, local_card, missing_card
from Tools.database import session_local, Media, Bookmark
from Tools.header import base_layout
from Tools.web_stack import setup_history_listener


def home_page():
    base_layout()

    # Data fetch
    with session_local() as db:
        if "home_row_limit" not in app.storage.general:
            app.storage.general["home_row_limit"] = 10

        home_row_limit = app.storage.general["home_row_limit"]

        b_q  = db.query(Bookmark).order_by(Bookmark.date_added.desc())
        m_q = db.query(Media).order_by(Media.date_added.desc())

        filter = {
            'sort': 'date_desc'
        }

        all_media = [
            {'label': 'Bookmarks', 'type': 'bookmark', 'data': b_q.limit(home_row_limit).all()},
            {'label': 'All', 'type': 'all', 'data': m_q.limit(home_row_limit).all()},
            {'label': 'Images', 'type': 'image', 'data': m_q.filter(Media.media_type == "image").limit(home_row_limit).all()},
            {'label': 'Comics', 'type': 'comic', 'data': m_q.filter(Media.media_type == "comic").limit(home_row_limit).all()},
            {'label': 'Videos', 'type': 'video', 'data': m_q.filter(Media.media_type == "video").limit(home_row_limit).all()},
            {'label': 'Audio', 'type': 'audio', 'data': m_q.filter(Media.media_type == "audio").limit(home_row_limit).all()},
            {'label': 'Books', 'type': 'book', 'data': m_q.filter(Media.media_type == "book").limit(home_row_limit).all()}
        ]


    # UI
    with ui.column().classes("gap-4 w-full"):
        # ---- Rows ----
        for media in all_media:
            ui.label(media['label']).classes("text-xl text-accent cursor-pointer").on("click", lambda media_type=media['type']: ui.navigate.to(f"/view/local?media_type={media_type}"))
            with ui.scroll_area().classes("w-full h-72"):
                with ui.row().classes("w-full h-full flex-nowrap"):
                    if media['data']:
                        for item in media['data']:
                            with ui.row().classes('w-48 h-full'):
                                temp_filters = filter | {
                                    'media_type': media['type']
                                }
                                if media['type'] == 'bookmark':
                                    bookmark_card(item)
                                else:
                                    local_card(item, on_click=lambda target_id=item.id, filters=temp_filters: local_view(target_id, overlay_container, filters=filters))
                    else:
                        with ui.row().classes('w-48 h-full'):
                            missing_card(f"No {media['label']}")


    overlay_container = ui.element('div').classes('z-[3000]')
    setup_history_listener(overlay_container)
