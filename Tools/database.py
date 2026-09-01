from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, event, Integer, String, ForeignKey, DateTime, JSON, Float, Boolean
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Mapped, mapped_column, relationship
from pathlib import Path


database_url = f"sqlite:///{Path(__file__).resolve().parent.parent}/database.db"
engine = create_engine(
    database_url,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
)
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()

session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---- Helper ----
def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# ---- Folders ----
class Folder(Base):
    """ Physical directory for local data """
    __tablename__ = "folders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("folders.id", ondelete="CASCADE"))

    subfolders: Mapped[List["Folder"]] = relationship("Folder", back_populates="parent_folder", cascade="all, delete-orphan")
    parent_folder: Mapped[Optional["Folder"]] = relationship("Folder", back_populates="subfolders", remote_side=[id])

    media: Mapped[List["Media"]] = relationship("Media", back_populates="folder", cascade="all, delete-orphan")


class OrganizationalFolder(Base):
    """ Virtual directory for organizational purposes """
    __tablename__ = 'organizational_folders'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizational_folders.id", ondelete="CASCADE"))
    date_added: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now)
    date_created: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now)

    url: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    tags: Mapped[Optional[str]] = mapped_column(String)
    meta_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    views: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)

    thumb_path: Mapped[str] = mapped_column(String)
    thumb_url: Mapped[str] = mapped_column(String)

    subfolders: Mapped[List["OrganizationalFolder"]] = relationship("OrganizationalFolder", back_populates="parent_folder", cascade="all, delete-orphan")
    parent_folder: Mapped[Optional["OrganizationalFolder"]] = relationship("OrganizationalFolder", back_populates="subfolders", remote_side=[id])

    bookmarks: Mapped[List["Bookmark"]] = relationship("Bookmark", back_populates="folder", cascade="all, delete-orphan")
    media: Mapped[List["Media"]] = relationship("Media", back_populates="curated_folder")

# ---- Bookmarks ----
class Bookmark(Base):
    """ User added urls """
    __tablename__ = 'bookmarks'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String)
    date_added: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now)

    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    date_created: Mapped[Optional[datetime]] = mapped_column(DateTime)
    tags: Mapped[Optional[str]] = mapped_column(String)
    meta_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    views: Mapped[int] = mapped_column(Integer)
    rating: Mapped[float] = mapped_column(Float)
    favorite: Mapped[bool] = mapped_column(Boolean)

    thumb_path: Mapped[str] = mapped_column(String)
    thumb_url: Mapped[str] = mapped_column(String)

    folder_id: Mapped[int] = mapped_column(ForeignKey("organizational_folders.id", ondelete="CASCADE"), nullable=False)
    folder: Mapped["OrganizationalFolder"] = relationship("OrganizationalFolder", back_populates="bookmarks")


# ---- Local Media ----
class Media(Base):
    """ Locally saved data """
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_path: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    file_name: Mapped[str] = mapped_column(String)
    file_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String)
    date_added: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now)
    date_created: Mapped[Optional[datetime]] = mapped_column(DateTime)

    source_url: Mapped[Optional[str]] = mapped_column(String)
    source_domain: Mapped[Optional[str]] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(String)
    tags: Mapped[Optional[Optional[str]]] = mapped_column(String)
    meta_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    views: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    progress: Mapped[int] = mapped_column(Integer, default=0)

    thumb_path: Mapped[Optional[str]] = mapped_column(String)

    folder_id: Mapped[int] = mapped_column(ForeignKey("folders.id", ondelete="CASCADE"), nullable=False)
    folder: Mapped["Folder"] = relationship("Folder", back_populates="media")

    organizational_folder_id: Mapped[Optional[int]] = mapped_column(ForeignKey("organizational_folders.id", ondelete="SET NULL"))
    curated_folder: Mapped[Optional["OrganizationalFolder"]] = relationship("OrganizationalFolder", back_populates="media")

    media_type: Mapped[str] = mapped_column(String, nullable=False)

    __mapper_args__ = {
        "polymorphic_on": "media_type",
        "polymorphic_identity": "generic_media"
    }


class Image(Media):
    __mapper_args__ = {"polymorphic_identity": "image"}

    @property
    def dimensions(self) -> Optional[str]:
        return self.meta_data.get("dimensions")

    @dimensions.setter
    def dimensions(self, val: str):
        self.meta_data["dimensions"] = val


class Comic(Media):
    __mapper_args__ = {"polymorphic_identity": "comic"}

    @property
    def image_count(self) -> int:
        return self.meta_data.get("image_count", 0)

    @image_count.setter
    def image_count(self, val: int):
        self.meta_data["image_count"] = val


class Video(Media):
    __mapper_args__ = {"polymorphic_identity": "video"}

    @property
    def duration(self) -> Optional[int]:
        return self.meta_data.get("duration")

    @duration.setter
    def duration(self, val: int):
        self.meta_data["duration"] = val

    @property
    def resolution(self) -> Optional[str]:
        return self.meta_data.get("resolution")

    @resolution.setter
    def resolution(self, val: str):
        self.meta_data["resolution"] = val


class Audio(Media):
    __mapper_args__ = {"polymorphic_identity": "audio"}

    @property
    def duration(self) -> Optional[int]:
        return self.meta_data.get("duration")

    @duration.setter
    def duration(self, val: int):
        self.meta_data["duration"] = val


class Book(Media):
    __mapper_args__ = {"polymorphic_identity": "book"}

    @property
    def words(self) -> Optional[int]:
        return self.meta_data.get("words")

    @words.setter
    def words(self, val: int):
        self.meta_data["words"] = val

# ---- Queues ----
class Queue(Base):
    """ Background queue for async workers """
    __tablename__ = "queues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=get_utc_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    media_type: Mapped[str] = mapped_column(String)
    target_url: Mapped[Optional[str]] = mapped_column(String)
    meta_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    media_id: Mapped[Optional[int]] = mapped_column(ForeignKey("media.id", ondelete="CASCADE"))
    bookmark_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bookmarks.id", ondelete="CASCADE"))
    media_item: Mapped[Optional["Media"]] = relationship("Media")
    bookmark_item: Mapped[Optional["Bookmark"]] = relationship("Bookmark")

    queue_type: Mapped[str] = mapped_column(String, nullable=False)

    __mapper_args__ = {
        "polymorphic_on": "queue_type",
        "polymorphic_identity": "generic_queue"
    }


class MetadataQueue(Queue):
    __mapper_args__ = {"polymorphic_identity": "metadata_queue"}

    @property
    def overwrite_existing(self) -> bool:
        return self.meta_data.get("overwrite_existing", False)

    @overwrite_existing.setter
    def overwrite_existing(self, val: bool):
        self.meta_data["overwrite_existing"] = val


class ThumbnailQueue(Queue):
    __mapper_args__ = {"polymorphic_identity": "thumbnail_queue"}

    @property
    def force_aspect_ratio(self) -> Optional[str]:
        return self.meta_data.get("force_aspect_ratio")

    @force_aspect_ratio.setter
    def force_aspect_ratio(self, val: str):
        self.meta_data["force_aspect_ratio"] = val


class ScraperQueue(Queue):
    __mapper_args__ = {"polymorphic_identity": "scraper_queue"}


# ---- Helper ----
def init_db():
    Base.metadata.create_all(bind=engine)
    print(f"Database initialized: {database_url}")


if __name__ == "__main__":
    init_db()