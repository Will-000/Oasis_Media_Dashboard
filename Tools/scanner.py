import os
from datetime import datetime
from pathlib import Path
from typing import List
from sqlalchemy import select
from Tools.database import session_local, Folder, Media, Comic, Video, Image, Audio, Book, ThumbnailQueue, MetadataQueue


def scan_directory(root_paths: List[Path]):
    db = session_local()

    stack = []
    for path in root_paths:
        p = Path(path)
        if p.exists():
            stack.append((p, None))
        else:
            print(f"Path does not exist: {p}")

    print(f"Scanning {root_paths}")
    commit_interval = 250
    pending_changes = 0
    total_scans = 0

    while stack:
        current_path, parent_id = stack.pop()

        try:
            items = list(current_path.iterdir())
        except PermissionError:
            print(f"Permission denied accessing: {current_path}")
            continue

        folder_path_str = str(current_path.absolute())
        folder_record = db.execute(select(Folder).filter(Folder.path == folder_path_str)).scalar_one_or_none()

        if not folder_record:
            folder_record = Folder(name=current_path.name, path=folder_path_str, parent_id=parent_id)
            db.add(folder_record)
            db.flush()

        current_folder_id = folder_record.id

        existing_images = set(db.scalars(select(Media.file_path).filter(Media.folder_id == current_folder_id, Media.media_type == "image")).all())
        existing_comics = set(db.scalars(select(Media.file_path).filter(Media.folder_id == current_folder_id, Media.media_type == "comic")).all())
        existing_videos = set(db.scalars(select(Media.file_path).filter(Media.folder_id == current_folder_id, Media.media_type == "video")).all())
        existing_audios = set(db.scalars(select(Media.file_path).filter(Media.folder_id == current_folder_id, Media.media_type == "audio")).all())
        existing_books = set(db.scalars(select(Media.file_path).filter(Media.folder_id == current_folder_id, Media.media_type == "book")).all())

        for item in items:
            item_path_str = str(item.absolute())
            ext = item.suffix.lower()

            if item.is_dir():
                stack.append((item, current_folder_id))

            elif item.is_file():
                # ---- Images ----
                if ext in ('.jpg', '.jpeg', '.png', '.webp'):
                    if item_path_str not in existing_images:
                        image = Image(
                            file_path=item_path_str,
                            file_name=item.name,
                            file_type=ext,
                            title=item.stem,
                            date_added=datetime.now(),
                            date_created=datetime.fromtimestamp(os.path.getctime(Path(item_path_str))),
                            folder_id = current_folder_id,
                            organizational_folder_id=None
                        )
                        db.add(image)
                        db.flush()

                        db.add(ThumbnailQueue(media_id=image.id, media_type="image"))
                        db.add(MetadataQueue(media_id=image.id, media_type="image"))
                        pending_changes += 1

                # ---- Comics ----
                elif ext in ('.cbz', '.cbr'):
                    if item_path_str not in existing_comics:
                        comic = Comic(
                            file_path=item_path_str,
                            file_name=item.name,
                            file_type=ext,
                            title=item.stem,
                            date_added=datetime.now(),
                            date_created=datetime.fromtimestamp(os.path.getctime(Path(item_path_str))),
                            folder_id = current_folder_id,
                            organizational_folder_id=None
                        )
                        db.add(comic)
                        db.flush()

                        db.add(ThumbnailQueue(media_id=comic.id, media_type="comic"))
                        db.add(MetadataQueue(media_id=comic.id, media_type="comic"))
                        pending_changes += 1

                # ---- Videos ----
                elif ext in ('.mp4', '.mkv', '.avi', '.mov'):
                    if item_path_str not in existing_videos:
                        video = Video(
                            file_path=item_path_str,
                            file_name=item.name,
                            file_type=ext,
                            title=item.stem,
                            date_added=datetime.now(),
                            date_created=datetime.fromtimestamp(os.path.getctime(Path(item_path_str))),
                            folder_id = current_folder_id,
                            organizational_folder_id=None
                        )
                        db.add(video)
                        db.flush()

                        db.add(ThumbnailQueue(media_id=video.id, media_type="video"))
                        db.add(MetadataQueue(media_id=video.id, media_type="video"))
                        pending_changes += 1

                # ---- Audios ----
                elif ext in ('.mp3', '.wav'):
                    if item_path_str not in existing_audios:
                        audio = Audio(
                            file_path=item_path_str,
                            file_name=item.name,
                            file_type=ext,
                            title=item.stem,
                            date_added=datetime.now(),
                            date_created=datetime.fromtimestamp(os.path.getctime(Path(item_path_str))),
                            folder_id = current_folder_id,
                            organizational_folder_id=None
                        )
                        db.add(audio)
                        db.flush()

                        db.add(ThumbnailQueue(media_id=audio.id, media_type="audio"))
                        db.add(MetadataQueue(media_id=audio.id, media_type="audio"))
                        pending_changes += 1

                # ---- Books ----
                elif ext in ('.epub'):
                    if item_path_str not in existing_books:
                        book = Book(
                            file_path=item_path_str,
                            file_name=item.name,
                            file_type=ext,
                            title=item.stem,
                            date_added=datetime.now(),
                            date_created=datetime.fromtimestamp(os.path.getctime(Path(item_path_str))),
                            folder_id = current_folder_id,
                            organizational_folder_id=None
                        )
                        db.add(book)
                        db.flush()

                        db.add(ThumbnailQueue(media_id=book.id, media_type="book"))
                        db.add(MetadataQueue(media_id=book.id, media_type="book"))
                        pending_changes += 1

            if pending_changes >= commit_interval:
                print(f'Committing {pending_changes} indexes')
                db.commit()
                total_scans += pending_changes
                pending_changes = 0

    if pending_changes > 0:
        total_scans += pending_changes
        print(f'Committing final {pending_changes} indexes')
        db.commit()

    db.close()
    print(f"Total scans {total_scans}")
