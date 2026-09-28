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
    face_count: int = 0
    faces_embedded: int = 0
    face_processing_error: str | None = None
    source: str = "local_upload"
    drive_file_id: str | None = None
    drive_folder_id: str | None = None
    drive_modified_time: str | None = None


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
    face_count: int = 0
    faces_embedded: int = 0
    face_processing_error: str | None = None


@dataclass
class CollectionRecord:
    id: str
    created_at: datetime
    status: CollectionStatus = CollectionStatus.CREATED
    photos: list[PhotoRecord] = field(default_factory=list)
    selfie: SelfieRecord | None = None
    failed_photo_count: int = 0
    face_records: list[object] = field(default_factory=list)
    face_processing_status: str = "not_started"
    face_processing_error_count: int = 0
    matching_status: str = "not_started"
    match_count: int = 0
    source: str = "local_upload"
    drive_folder_id: str | None = None
