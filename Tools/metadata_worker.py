import threading
import time
import zipfile
import ffmpeg
import xml.etree.ElementTree as ET
from typing import Dict, Tuple, Any
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select
from PIL import Image as PILImage


from Tools.database import session_local, MetadataQueue, Media

MAX_WORKER_THREADS = 3


# ---- Media Specification ----
def extract_image_metadata(path: Path) -> Tuple[bool, Dict[str, Any]]:
    """ Extracts widthxheight """
    meta = {"dimensions": None}
    try:
        with PILImage.open(path) as img:
            w, h = img.size
            meta["dimensions"] = f"{w}x{h}"
        return True, meta
    except Exception as e:
        print(f"Metadata: Image Error | {path.name} | {e}")
        return False, {}


def extract_comic_metadata(path: Path) -> Tuple[bool, Dict[str, Any]]:
    """ Extracts the following metadata """
    meta = {
        "image_count": 0, "title": None, "writer": None,
        "publisher": None, "tags": None, "web_url": None, "year": None
    }
    try:
        with zipfile.ZipFile(path, 'r') as z:
            exts = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
            meta['image_count'] = sum(1 for name in z.namelist() if name.lower().endswith(exts))

            if 'ComicInfo.xml' in z.namelist():
                root = ET.fromstring(z.read('ComicInfo.xml'))
                tags_map = {
                    'title': 'Title', 'writer': 'Writer', 'publisher': 'Publisher',
                    'tags': 'Tags', 'web_url': 'Web', 'year': 'Year'
                }
                for k, xml_tag in tags_map.items():
                    el = root.find(xml_tag)
                    if el is not None and el.text:
                        meta[k] = el.text
        return True, meta

    except Exception as e:
        print(f"Metadata: Comic Error | {path.name} | {e}")
        return False, {}


def extract_video_metadata(path: Path) -> Tuple[bool, Dict[str, Any]]:
    """ Extracts resolution and duration """
    meta = {"duration": None, "resolution": None}
    try:
        path_str = str(path.absolute())
        probe = ffmpeg.probe(path_str)
        stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        if stream:
            w, h = stream.get('width'), stream.get('height')
            if w and h:
                meta['resolution'] = f"{w}x{h}"
            dur = stream.get('duration') or probe.get('format', {}).get('duration')
            if dur:
                meta['duration'] = int(float(dur))
        return True, meta
    except Exception as e:
        print(f"Metadata: Video Error | {path.name} | {e}")
        return False, {}


# ---- Workers ----
def process_metadata_task(task_id: int):
    """ Single Metadata task"""
    db = session_local()
    try:
        task = db.execute(select(MetadataQueue).filter(MetadataQueue.id == task_id)).scalar_one_or_none()
        if not task:
            return

        media_item = db.execute(select(Media).filter(Media.id == task.media_id)).scalar_one_or_none()
        if not media_item:
            task.status = "Failed"
            task.error_message = "Target item missing from database"
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        source_path = Path(media_item.file_path)
        if not source_path.exists():
            task.status = "Failed"
            task.error_message = f"Physical file missing from drive: {source_path}"
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        print(f"Metadata: Scraping {task.media_type} | {media_item.title}")

        success = False
        parsed_meta = {}

        # Routing generation by media_type
        if task.media_type == "image":
            success, parsed_meta = extract_image_metadata(source_path)
        elif task.media_type == "comic":
            success, parsed_meta = extract_comic_metadata(source_path)
        elif task.media_type == "video":
            success, parsed_meta = extract_video_metadata(source_path)
        else:
            task.status = "Failed"
            task.error_message = f"Metadata schema extraction unhandled for type: {task.media_type}"
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        # Transaction updates
        if success:
            if parsed_meta.get("title") and not media_item.title:
                media_item.title = parsed_meta.get("title")
            if parsed_meta.get("web_url"):
                media_item.source_url = parsed_meta.get("web_url")
            if parsed_meta.get("tags"):
                media_item.tags = parsed_meta.get("tags")

            current_metadata = dict(media_item.meta_data) if media_item.meta_data else {}
            current_metadata.update(parsed_meta)
            media_item.meta_data = current_metadata

            task.status = "Completed"
        else:
            task.status = "Failed"
            task.error_message = "Media routing failed to processing metadata"

        task.completed_at = datetime.now(timezone.utc)
        db.commit()


    except Exception as ex:
        db.rollback()

        try:
            task = db.execute(select(MetadataQueue).filter(MetadataQueue.id == task_id)).scalar_one()
            task.status = "Failed"
            task.error_message = str(ex)
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
        except Exception:
            pass

        print(f"Metadata: Error | {task_id} | {ex}")

    finally:
        db.close()


# ---- Scheduler ----
def start_metadata_workers(stop_event: threading.Event):
    """ Monitoring database task queue """
    print("Starting metadata workers")

    with ThreadPoolExecutor(max_workers=MAX_WORKER_THREADS) as executor:
        while not stop_event.is_set():
            db = session_local()

            pending_tasks = db.scalars(
                select(MetadataQueue)
                .filter(MetadataQueue.status == "pending")
                .order_by(MetadataQueue.created_at.asc())
                .limit(MAX_WORKER_THREADS)
            ).all()

            # Idle
            if not pending_tasks:
                db.close()
                for _ in range(20):
                    if stop_event.is_set():
                        break
                    time.sleep(0.1)
                continue

            # Lock the records to 'Processing' status
            task_ids = []
            for task in pending_tasks:
                task.status = "Processing"
                task_ids.append(task.id)

            db.commit()
            db.close()

            for t_id in task_ids:
                executor.submit(process_metadata_task, t_id)

    print("Thumbnail workers stopped.")