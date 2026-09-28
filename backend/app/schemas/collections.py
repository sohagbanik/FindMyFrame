from datetime import datetime
from pydantic import BaseModel, Field

from app.models.entities import CollectionStatus, PhotoStatus, SelfieStatus


class CreateCollectionResponse(BaseModel):
    collection_id: str
    status: CollectionStatus
    created_at: datetime


class PhotoResponse(BaseModel):
    photo_id: str
    collection_id: str
    original_filename: str
    storage_path: str
    mime_type: str
    file_size: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    image_format: str
    created_at: datetime
    processing_status: PhotoStatus
    face_count: int = 0
    faces_embedded: int = 0
    face_processing_error: str | None = None


class FailedUploadResponse(BaseModel):
    filename: str
    code: str
    message: str


class UploadPhotosResponse(BaseModel):
    collection_id: str
    photos: list[PhotoResponse]
    failed_files: list[FailedUploadResponse] = Field(default_factory=list)


class SelfieResponse(BaseModel):
    selfie_id: str
    collection_id: str
    original_filename: str
    storage_path: str
    mime_type: str
    file_size: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    image_format: str
    created_at: datetime
    processing_status: SelfieStatus
    face_count: int = 0
    faces_embedded: int = 0
    face_processing_error: str | None = None


class CollectionStatusResponse(BaseModel):
    collection_id: str
    status: CollectionStatus
    created_at: datetime
    photo_count: int
    ingested_photo_count: int
    failed_photo_count: int
    selfie_status: SelfieStatus | None = None
    processing_state: str = "ingestion_ready"
    face_processing_status: str = "not_started"
    faces_detected: int = 0
    faces_embedded: int = 0


class FaceProcessingResponse(BaseModel):
    collection_id: str
    status: str
    photos_processed: int
    photos_failed: int
    faces_detected: int
    faces_embedded: int
