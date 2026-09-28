from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.config import Settings, settings
from app.models.entities import CollectionRecord, PhotoRecord, SelfieRecord
from app.persistence.json_repository import JsonRepository
from app.schemas.collections import (
    CollectionStatusResponse,
    CreateCollectionResponse,
    FailedUploadResponse,
    FaceProcessingResponse,
    FailedImportResponse,
    GoogleDriveImportRequest,
    GoogleDriveImportResponse,
    MatchResponse,
    MatchResultResponse,
    PhotoResponse,
    SelfieResponse,
    UploadPhotosResponse,
)
from app.services.ingestion_service import IngestionError, IngestionService
from app.services.face_model import FaceError, SFaceModel
from app.services.face_service import FaceService
from app.services.matching_service import MatchingError, MatchingService, PhotoMatch
from app.integrations.google_drive.service import DriveIntegrationError, GoogleDriveClient, GoogleDriveImportService
from app.storage.local_storage import LocalStorage


router = APIRouter(prefix="/api/collections", tags=["collections"])
repository = JsonRepository(settings.storage_root)
storage = LocalStorage(settings.storage_root)
ingestion_service = IngestionService(settings, repository, storage)
face_service = FaceService(SFaceModel(settings.model_root, settings.cv_device), settings.storage_root, repository)
matching_service = MatchingService(settings, repository)
drive_import_service = GoogleDriveImportService(GoogleDriveClient(settings), ingestion_service)


def get_ingestion_service() -> IngestionService:
    return ingestion_service


def get_face_service() -> FaceService:
    return face_service


def get_matching_service() -> MatchingService:
    return matching_service


def _photo_response(photo: PhotoRecord) -> PhotoResponse:
    return PhotoResponse(photo_id=photo.id, collection_id=photo.collection_id, original_filename=photo.original_filename, storage_path=photo.storage_path, mime_type=photo.mime_type, file_size=photo.file_size, width=photo.width, height=photo.height, image_format=photo.image_format, created_at=photo.created_at, processing_status=photo.processing_status, face_count=photo.face_count, faces_embedded=photo.faces_embedded, face_processing_error=photo.face_processing_error, source=photo.source, drive_file_id=photo.drive_file_id, drive_folder_id=photo.drive_folder_id)


def _selfie_response(selfie: SelfieRecord) -> SelfieResponse:
    return SelfieResponse(selfie_id=selfie.id, collection_id=selfie.collection_id, original_filename=selfie.original_filename, storage_path=selfie.storage_path, mime_type=selfie.mime_type, file_size=selfie.file_size, width=selfie.width, height=selfie.height, image_format=selfie.image_format, created_at=selfie.created_at, processing_status=selfie.processing_status, face_count=selfie.face_count, faces_embedded=selfie.faces_embedded, face_processing_error=selfie.face_processing_error)


def _raise_ingestion_error(error: IngestionError, filename: str | None = None) -> None:
    code = 413 if error.code == "file_too_large" else 400
    raise HTTPException(status_code=code, detail={"code": error.code, "message": error.message, "filename": filename})


def _raise_face_error(error: FaceError) -> None:
    raise HTTPException(status_code=error.status, detail={"code": error.code, "message": error.message})


def _raise_matching_error(error: MatchingError) -> None:
    raise HTTPException(status_code=error.status, detail={"code": error.code, "message": error.message})


def _raise_drive_error(error: DriveIntegrationError) -> None:
    raise HTTPException(status_code=error.status, detail={"code": error.code, "message": error.message})


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


@router.post("/{collection_id}/import/google-drive", response_model=GoogleDriveImportResponse)
def import_google_drive(collection_id: str, request: GoogleDriveImportRequest):
    if not repository.get_collection(collection_id):
        _raise_drive_error(DriveIntegrationError("collection_not_found", "That photo collection could not be found.", 404))
    try:
        result = drive_import_service.import_folder(collection_id, request.folder_url)
    except DriveIntegrationError as error:
        _raise_drive_error(error)
    return GoogleDriveImportResponse(collection_id=result["collection_id"], source=result["source"], drive_folder_id=result["drive_folder_id"], discovered_count=result["discovered_count"], imported_count=result["imported_count"], duplicate_count=result["duplicate_count"], failed_count=result["failed_count"], failed_files=[FailedImportResponse(**failure) for failure in result["failed_files"]])


def _run_face_processing(collection_id: str) -> None:
    try:
        face_service.process_collection(collection_id)
    except (FaceError, OSError, ValueError) as error:
        face_service.mark_collection_failed(collection_id, getattr(error, "code", "processing_failed"))


@router.post("/{collection_id}/process-faces", response_model=FaceProcessingResponse, status_code=status.HTTP_202_ACCEPTED)
def process_faces(collection_id: str, background_tasks: BackgroundTasks, service: FaceService = Depends(get_face_service)):
    collection = repository.get_collection(collection_id)
    if not collection:
        _raise_face_error(FaceError("collection_not_found", "That photo collection could not be found.", 404))
    if not collection.photos:
        _raise_face_error(FaceError("no_photos", "Add at least one event photograph before processing.", 400))
    if collection.face_processing_status == "processing":
        return FaceProcessingResponse(collection_id=collection_id, status="processing", photos_processed=0, photos_failed=0, faces_detected=0, faces_embedded=0)
    background_tasks.add_task(_run_face_processing, collection_id)
    collection.face_processing_status = "processing"
    repository.save_collection(collection)
    return FaceProcessingResponse(collection_id=collection_id, status="processing", photos_processed=0, photos_failed=0, faces_detected=0, faces_embedded=0)


@router.post("/{collection_id}/process-selfie", response_model=SelfieResponse)
def process_selfie(collection_id: str, service: FaceService = Depends(get_face_service)):
    try:
        selfie = service.process_selfie_for_collection(collection_id)
    except FaceError as error:
        _raise_face_error(error)
    return _selfie_response(repository.get_collection(collection_id).selfie)


def _match_response(collection_id: str, matches: list[PhotoMatch], status_value: str) -> MatchResponse:
    response_matches = [MatchResultResponse(photo_id=match.photo.id, collection_id=collection_id, similarity_score=round(match.score, 6), match_type=match.match_type, image_url=f"/api/collections/{collection_id}/photos/{match.photo.id}", original_filename=match.photo.original_filename, width=match.photo.width, height=match.photo.height) for match in matches]
    return MatchResponse(collection_id=collection_id, status=status_value, matches=response_matches, match_count=len(response_matches), strong_match_count=sum(match.match_type == "strong" for match in response_matches), possible_match_count=sum(match.match_type == "possible" for match in response_matches))


@router.post("/{collection_id}/match", response_model=MatchResponse)
def match_collection(collection_id: str, service: MatchingService = Depends(get_matching_service)):
    service.set_matching_status(collection_id, "matching")
    try:
        matches = service.match_selfie_to_collection(collection_id)
    except MatchingError as error:
        service.set_matching_status(collection_id, "matching_failed")
        _raise_matching_error(error)
    result_status = "matched" if matches else "no_matches"
    service.set_matching_status(collection_id, result_status, len(matches))
    return _match_response(collection_id, matches, result_status)


@router.get("/{collection_id}", response_model=CollectionStatusResponse)
def collection_status(collection_id: str, service: IngestionService = Depends(get_ingestion_service)):
    try:
        collection: CollectionRecord = service.get_collection(collection_id)
    except IngestionError as error:
        _raise_ingestion_error(error)
    failed = collection.failed_photo_count
    selfie_status = collection.selfie.processing_status if collection.selfie else None
    photo_faces = sum(photo.face_count for photo in collection.photos)
    embedded_faces = sum(photo.faces_embedded for photo in collection.photos)
    return CollectionStatusResponse(collection_id=collection.id, status=collection.status, created_at=collection.created_at, photo_count=len(collection.photos), ingested_photo_count=len(collection.photos), failed_photo_count=failed, selfie_status=selfie_status, processing_state=collection.face_processing_status, face_processing_status=collection.face_processing_status, faces_detected=photo_faces, faces_embedded=embedded_faces, matching_status=collection.matching_status, match_count=collection.match_count, source=collection.source, drive_folder_id=collection.drive_folder_id)


@router.get("/{collection_id}/photos/{photo_id}")
def get_collection_photo(collection_id: str, photo_id: str):
    collection = repository.get_collection(collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail={"code": "collection_not_found", "message": "That photo collection could not be found."})
    photo = next((photo for photo in collection.photos if photo.id == photo_id), None)
    if not photo:
        raise HTTPException(status_code=404, detail={"code": "photo_not_found", "message": "That photograph could not be found."})
    root = settings.storage_root.resolve()
    path = (settings.storage_root / photo.storage_path).resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail={"code": "photo_unavailable", "message": "That photograph is no longer available."})
    return FileResponse(path, media_type=photo.mime_type, filename=Path(photo.original_filename).name)
