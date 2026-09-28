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


class CollectionStatusResponse(BaseModel):
    collection_id: str
    status: CollectionStatus
    created_at: datetime
    photo_count: int
    ingested_photo_count: int
    failed_photo_count: int
    selfie_status: SelfieStatus | None = None
    processing_state: str = "ingestion_ready"
