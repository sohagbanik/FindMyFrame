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
    source: str = "local_upload"
    drive_file_id: str | None = None
    drive_folder_id: str | None = None


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
    matching_status: str = "not_started"
    match_count: int = 0
    source: str = "local_upload"
    drive_folder_id: str | None = None


class FaceProcessingResponse(BaseModel):
    collection_id: str
    status: str
    photos_processed: int
    photos_failed: int
    faces_detected: int
    faces_embedded: int


class MatchResultResponse(BaseModel):
    photo_id: str
    collection_id: str
    similarity_score: float
    match_type: str
    image_url: str
    original_filename: str
    width: int
    height: int


class MatchResponse(BaseModel):
    collection_id: str
    status: str
    matches: list[MatchResultResponse] = Field(default_factory=list)
    match_count: int
    strong_match_count: int
    possible_match_count: int


class GoogleDriveImportRequest(BaseModel):
    folder_url: str


class FailedImportResponse(BaseModel):
    filename: str
    code: str
    message: str


class GoogleDriveImportResponse(BaseModel):
    collection_id: str
    source: str
    drive_folder_id: str
    discovered_count: int
    imported_count: int
    duplicate_count: int
    failed_count: int
    failed_files: list[FailedImportResponse] = Field(default_factory=list)
