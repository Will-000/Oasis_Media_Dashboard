import io
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import ffmpeg
from PIL import Image, ImageFile
from sqlalchemy import select
from Tools.database import session_local, Media, ThumbnailQueue

ImageFile.LOAD_TRUNCATED_IMAGES = True

THUMBNAIL_ROOT = Path(__file__).resolve().parent.parent / "thumbnails"
MAX_WORKER_PROCESSES = 3
THUMB_SIZE = (384, 384)

# ---- Media Specification ----
def extract_image_thumb(image_path: Path, output_path: Path) -> bool:
    """ Shrinks image """
    try:
        with Image.open(image_path) as image:
            image.thumbnail(THUMB_SIZE)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            image.convert('RGB').save(output_path, 'JPEG', quality=80, optimize=True)
            return True

    except Exception as e:
        print(f"Thumbnail: Image Error | {image_path.name} | {e}")
        return False


def extract_comic_thumb(comic_path: Path, output_path: Path) -> bool:
    """ Extracts the first image page out of .cbz/.cbr """
    try:
        with zipfile.ZipFile(comic_path, 'r') as z:
            valid_exts = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
            pages = sorted([name for name in z.namelist() if name.lower().endswith(valid_exts)])
            if not pages:
                return False

            image_data = z.read(pages[0])
            with Image.open(io.BytesIO(image_data)) as image:
                image.thumbnail(THUMB_SIZE)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                image.convert('RGB').save(output_path, 'JPEG', quality=80, optimize=True)
                return True

    except Exception as e:
        print(f"Thumbnail: Comic Error | {comic_path.name} | {e}")
        return False


def extract_video_thumb(video_path: Path, output_path: Path, duration_secs: int = 0) -> bool:
    """ Grabs frame at 5 seconds """
    try:
        # Determine the target frame
        time_offset = min(5, duration_secs // 10) if duration_secs else 2
        video_path_str = str(video_path.absolute())
        output_path_str = str(output_path.absolute())

        (
            ffmpeg
            .input(video_path_str, ss=time_offset)
            .filter('scale', THUMB_SIZE[0], THUMB_SIZE[1], force_original_aspect_ratio='decrease')
            .output(output_path_str, vframes=1, loglevel="error")
            .overwrite_output()
            .run()
        )
        return True

    except Exception as e:
        print(f"Thumbnail: Video Error | {video_path.name} | {e}")
        return False


# ---- Workers ----
def process_thumbnail_task(task_id: int):
    """ Single thumbnail task """
    db = session_local()
    try:
        task = db.execute(select(ThumbnailQueue).filter(ThumbnailQueue.id == task_id)).scalar_one_or_none()

        if not task:
            return

        media_item = db.execute(select(Media).filter(Media.id == task.media_id)).scalar_one_or_none()

        if not media_item:
            task.status = "Failed"
            task.error_message = "Target item missing from database"
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        output_path = THUMBNAIL_ROOT / task.media_type / f"{media_item.id}.jpg"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Thumbnail: Generating {task.media_type} | {media_item.title}")

        success = False
        source_path = Path(media_item.file_path)

        # Routing generation by media_type
        if task.media_type == "image":
            success = extract_image_thumb(source_path, output_path)
        elif task.media_type == "comic":
            success = extract_comic_thumb(source_path, output_path)
        elif task.media_type == "video":
            # fetch the metadata duration if it exists inside the JSON column
            duration = media_item.meta_data.get("duration", 0) if media_item.meta_data else 0
            success = extract_video_thumb(source_path, output_path, duration)
        else:
            # Fallback for unhandled formats
            task.status = "Failed"
            task.error_message = f"Thumbnail generation not supported for type: {task.media_type}"
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        # Transaction updates
        if success:
            task.status = "Completed"
            media_item.thumb_path = str(output_path)
        else:
            task.status = "Failed"
            task.error_message = "Media routing failed to processing thumbnail"

        task.completed_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as ex:
        db.rollback()

        try:
            task = db.execute(select(ThumbnailQueue).filter(ThumbnailQueue.id == task_id)).scalar_one()
            task.status = "Failed"
            task.error_message = str(ex)
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
        except Exception:
            pass
        print(f"Thumbnail: Error | {task_id} | {ex}")

    finally:
        db.close()


# ---- Schedular ----
def start_thumbnail_workers(stop_event: threading.Event):
    """ Monitoring database task queue """
    print("Starting thumbnail workers")

    with ThreadPoolExecutor(max_workers=MAX_WORKER_PROCESSES) as executor:
        while not stop_event.is_set():
            db = session_local()

            pending_tasks = db.scalars(
                select(ThumbnailQueue)
                .filter(ThumbnailQueue.status == "pending")
                .order_by(ThumbnailQueue.created_at.asc())
                .limit(MAX_WORKER_PROCESSES)
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
                executor.submit(process_thumbnail_task, t_id)

    print("Thumbnail workers stopped.")