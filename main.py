import mimetypes
import zipfile
import urllib.parse
from functools import lru_cache
from fastapi import HTTPException, Response, Request
from fastapi.responses import FileResponse
from nicegui import app, ui
from pathlib import Path

# Tools
from Tools.database import init_db, session_local, Media, Comic

# Pages
from Pages.home import home_page
from Pages.bookmarks import bookmarks_page
from Pages.local import local_page
from Pages.local_view import local_view
from Pages.scraper import scraper_page
from Pages.settings import settings_page
from Tools.header import base_layout

mimetypes.init()
mimetypes.add_type('application/javascript', '.mjs')
mimetypes.add_type('application/javascript', '.js')

DOMAIN_NAME = ''   # Add Tailscale domain

# Colors
ui.add_css('''
    .q-dialog__backdrop {
        background-color: rgba(0, 0, 0, 0.85) !important;
    }
''', shared=True)
ui.add_head_html('''
    <style>
        html, body { background-color: #263238 !important; }
    </style>
''', shared=True)
app.colors(
    primary='#263238',    # blue-grey-10
    secondary='#37474F',  # blue-grey-8
    accent='#FFFFFF',     # white
    dark='#212121',       # grey-10
    positive='#8BC34A',   # light-green-5
    negative='#FF5722',   # deep-orange-5
    info='#673AB7',       # deep-purple-5
    warning='#FFC107'     # amber-5
)


@ui.page('/')
def main_page():
    base_layout()

    if not Path(f"{Path(__file__).resolve().parent}/database.db").is_file():
        ui.label("No database found...").classes("text-accent text-xl")
        ui.button("Create database", on_click=lambda: (init_db(), ui.run_javascript("location.reload();"))).classes("bg-secondary text-accent").props("flat")
    else:
        ui.navigate.to("/home")


@ui.page("/home")
def route_home():
    home_page()


@ui.page("/view/bookmarks")
def route_bookmarks():
    bookmarks_page()


@ui.page("/view/local")
def route_local(request: Request):
    filters = {
        'page_num': int(request.query_params.get('page_num', 1)),
        'sort': request.query_params.get('sort', 'date_desc'),
        'media_type': request.query_params.get('media_type', 'all'),
        'search': request.query_params.get('search', '')
    }

    local_page(filters)


@ui.page("/view/local/{media_id}")
def view_media_page(media_id: int, request: Request):
    filters = {
        'sort': request.query_params.get('sort', 'date_desc'),
        'media_type': request.query_params.get('media_type', ''),
        'search': request.query_params.get('search', ''),
        'page': request.query_params.get('page', 1)
    }

    referrer = request.headers.get("referer")
    if referrer:
        parsed_ref = urllib.parse.urlparse(referrer)
        filters['origin_url'] = parsed_ref.path + (f"?{parsed_ref.query}" if parsed_ref.query else "")
    else:
        filters['origin_url'] = '/view/local'

    local_view(media_id, view_container=None, filters=filters)


@ui.page("/scraper")
def route_scraper():
    scraper_page()


@ui.page("/settings")
def route_settings():
    settings_page()


@app.get("/api/media/{media_id}")
def stream_media_file(media_id: int):
    db = session_local()
    item = db.query(Media).filter(Media.id == media_id).first()
    db.close()

    if not item:
        raise HTTPException(status_code=404, detail="Media asset not found")

    if item.media_type == "comic":
        return stream_comic_page(media_id=media_id, page_num=1)

    file_path = Path(item.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Physical file missing from drive")

    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "application/octet-stream"

    return FileResponse(file_path, media_type=mime_type)


@lru_cache(maxsize=128)
def get_cached_comic_pages(file_path_str: str) -> list:
    """ Opens zip archive once and holds its sorted file structure checklist in RAM """
    valid_exts = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
    with zipfile.ZipFile(file_path_str, 'r') as z:
        return sorted([name for name in z.namelist() if name.lower().endswith(valid_exts)])


@app.get('/api/media/{media_id}/page/{page_num}')
def stream_comic_page(media_id: int, page_num: int):
    with session_local() as db:
        item = db.query(Comic).filter(Comic.id == media_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Comic not found")

    comic_path = Path(item.file_path)
    if not comic_path.exists():
        raise HTTPException(status_code=404, detail="File missing")

    try:
        pages = get_cached_comic_pages(str(comic_path))

        target_index = page_num - 1
        if target_index < 0 or target_index >= len(pages):
            raise HTTPException(status_code=400, detail="Requested page out of bounds")

        with zipfile.ZipFile(comic_path, 'r') as z:
            image_bytes = z.read(pages[target_index])
            inner_file_name = pages[target_index]

        mime_type, _ = mimetypes.guess_type(inner_file_name)
        if not mime_type:
            mime_type = "image/jpeg"

        headers = {
            "Cache-Control": "public, max-age=3600, immutable",
        }

        return Response(content=image_bytes, media_type=mime_type, headers=headers)

    except zipfile.BadZipFile:
        raise HTTPException(status_code=500, detail="Corrupted or invalid cbz format")


ui.run(
    host='0.0.0.0',
    port=7070,
    title="Oasis",
    favicon='favicon.png',
    storage_secret='Super Secret',              # Add a random string here
    ssl_certfile=f"./certs/{DOMAIN_NAME}.crt",  # Remove if not using Tailscale
    ssl_keyfile=f"./certs/{DOMAIN_NAME}.key",   # Remove if not using Tailscale
    show=False,
    reload=False
)