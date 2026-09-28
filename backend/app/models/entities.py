from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class CollectionStatus(StrEnum):
    CREATED = "created"
    UPLOADING = "uploading"
    READY = "ready"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


class PhotoStatus(StrEnum):
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    READY = "ready"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


class SelfieStatus(StrEnum):
    UPLOADED = "uploaded"
    READY = "ready"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class PhotoRecord:
    id: str
    collection_id: str
    original_filename: str
    storage_path: str
    mime_type: str
    file_size: int
    width: int
    height: int
    image_format: str
    created_at: datetime
    processing_status: PhotoStatus = PhotoStatus.READY


@dataclass
class SelfieRecord:
    id: str
    collection_id: str
    storage_path: str
    original_filename: str
    mime_type: str
    file_size: int
    width: int
    height: int
    image_format: str
    created_at: datetime
    processing_status: SelfieStatus = SelfieStatus.READY


@dataclass
class CollectionRecord:
    id: str
    created_at: datetime
    status: CollectionStatus = CollectionStatus.CREATED
    photos: list[PhotoRecord] = field(default_factory=list)
    selfie: SelfieRecord | None = None
    failed_photo_count: int = 0
