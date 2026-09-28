from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.config import Settings, settings
from app.models.entities import CollectionRecord, PhotoRecord, SelfieRecord
from app.persistence.json_repository import JsonRepository
from app.schemas.collections import (
    CollectionStatusResponse,
    CreateCollectionResponse,
    FailedUploadResponse,
    PhotoResponse,
    SelfieResponse,
    UploadPhotosResponse,
)
from app.services.ingestion_service import IngestionError, IngestionService
from app.storage.local_storage import LocalStorage


router = APIRouter(prefix="/api/collections", tags=["collections"])
repository = JsonRepository(settings.storage_root)
storage = LocalStorage(settings.storage_root)
ingestion_service = IngestionService(settings, repository, storage)


def get_ingestion_service() -> IngestionService:
    return ingestion_service


def _photo_response(photo: PhotoRecord) -> PhotoResponse:
    return PhotoResponse(photo_id=photo.id, collection_id=photo.collection_id, original_filename=photo.original_filename, storage_path=photo.storage_path, mime_type=photo.mime_type, file_size=photo.file_size, width=photo.width, height=photo.height, image_format=photo.image_format, created_at=photo.created_at, processing_status=photo.processing_status)


def _selfie_response(selfie: SelfieRecord) -> SelfieResponse:
    return SelfieResponse(selfie_id=selfie.id, collection_id=selfie.collection_id, original_filename=selfie.original_filename, storage_path=selfie.storage_path, mime_type=selfie.mime_type, file_size=selfie.file_size, width=selfie.width, height=selfie.height, image_format=selfie.image_format, created_at=selfie.created_at, processing_status=selfie.processing_status)


def _raise_ingestion_error(error: IngestionError, filename: str | None = None) -> None:
    code = 413 if error.code == "file_too_large" else 400
    raise HTTPException(status_code=code, detail={"code": error.code, "message": error.message, "filename": filename})


@router.post("", response_model=CreateCollectionResponse, status_code=status.HTTP_201_CREATED)
def create_collection(service: IngestionService = Depends(get_ingestion_service)):
    collection = service.create_collection()
    return CreateCollectionResponse(collection_id=collection.id, status=collection.status, created_at=collection.created_at)


@router.post("/{collection_id}/photos", response_model=UploadPhotosResponse)
def upload_photos(collection_id: str, files: list[UploadFile] = File(...), service: IngestionService = Depends(get_ingestion_service)):
    try:
        service.get_collection(collection_id)
    except IngestionError as error:
        _raise_ingestion_error(error)
    photos = []
    failures = []
    for upload in files:
        try:
            photos.append(_photo_response(service.ingest_photo(collection_id, upload.filename or "upload", upload.content_type, upload.file)))
        except IngestionError as error:
            failures.append(FailedUploadResponse(filename=upload.filename or "upload", code=error.code, message=error.message))
        finally:
            upload.file.close()
    if not photos and failures:
        raise HTTPException(status_code=400, detail={"code": "no_valid_photos", "message": "None of the selected files could be added.", "files": [failure.model_dump() for failure in failures]})
    return UploadPhotosResponse(collection_id=collection_id, photos=photos, failed_files=failures)


@router.post("/{collection_id}/selfie", response_model=SelfieResponse)
def upload_selfie(collection_id: str, file: UploadFile = File(...), service: IngestionService = Depends(get_ingestion_service)):
    try:
        selfie = service.ingest_selfie(collection_id, file.filename or "selfie", file.content_type, file.file)
    except IngestionError as error:
        _raise_ingestion_error(error, file.filename)
    finally:
        file.file.close()
    return _selfie_response(selfie)


@router.get("/{collection_id}", response_model=CollectionStatusResponse)
def collection_status(collection_id: str, service: IngestionService = Depends(get_ingestion_service)):
    try:
        collection: CollectionRecord = service.get_collection(collection_id)
    except IngestionError as error:
        _raise_ingestion_error(error)
    failed = collection.failed_photo_count
    selfie_status = collection.selfie.processing_status if collection.selfie else None
    return CollectionStatusResponse(collection_id=collection.id, status=collection.status, created_at=collection.created_at, photo_count=len(collection.photos), ingested_photo_count=len(collection.photos), failed_photo_count=failed, selfie_status=selfie_status)
