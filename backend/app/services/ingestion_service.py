from datetime import datetime, timezone
from pathlib import Path
import uuid
from typing import BinaryIO

from app.config import Settings
from app.models.entities import CollectionRecord, CollectionStatus, PhotoRecord, SelfieRecord
from app.persistence.json_repository import JsonRepository
from app.storage.local_storage import LocalStorage
from app.utils.image_validation import ImageValidationError, validate_image_file


class IngestionError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class IngestionService:
    def __init__(self, settings: Settings, repository: JsonRepository, storage: LocalStorage):
        self.settings = settings
        self.repository = repository
        self.storage = storage

    def create_collection(self) -> CollectionRecord:
        record = CollectionRecord(id=uuid.uuid4().hex, created_at=datetime.now(timezone.utc))
        return self.repository.create_collection(record)

    def _collection_or_raise(self, collection_id: str) -> CollectionRecord:
        collection = self.repository.get_collection(collection_id)
        if not collection:
            raise IngestionError("collection_not_found", "That photo collection could not be found.")
        return collection

    def _save_and_validate(self, collection_id: str, kind: str, filename: str, content_type: str | None, source: BinaryIO) -> tuple[str, Path, int, object]:
        try:
            relative_path, absolute_path, file_size = self.storage.save_upload(collection_id, kind, filename, source, self.settings.max_image_size_bytes)
        except ValueError as error:
            if str(error) == "file_too_large":
                raise IngestionError("file_too_large", f"{filename} is larger than the {self.settings.max_image_size_bytes // (1024 * 1024)} MB upload limit.") from None
            raise IngestionError("storage_error", "The image could not be stored safely.") from error
        try:
            metadata = validate_image_file(absolute_path, content_type)
        except ImageValidationError as error:
            self.storage.delete(relative_path)
            raise IngestionError(error.code, error.message) from None
        return relative_path, absolute_path, file_size, metadata

    def ingest_photo(self, collection_id: str, filename: str, content_type: str | None, source: BinaryIO) -> PhotoRecord:
        collection = self._collection_or_raise(collection_id)
        collection.status = CollectionStatus.UPLOADING
        self.repository.save_collection(collection)
        try:
            relative_path, _, file_size, metadata = self._save_and_validate(collection_id, "photos", filename, content_type, source)
        except IngestionError:
            collection.failed_photo_count += 1
            collection.status = CollectionStatus.READY if collection.photos else CollectionStatus.FAILED
            self.repository.save_collection(collection)
            raise
        photo = PhotoRecord(id=uuid.uuid4().hex, collection_id=collection_id, original_filename=filename or "upload", storage_path=relative_path, mime_type=metadata.mime_type, file_size=file_size, width=metadata.width, height=metadata.height, image_format=metadata.image_format, created_at=datetime.now(timezone.utc))
        collection.photos.append(photo)
        collection.status = CollectionStatus.READY
        self.repository.save_collection(collection)
        return photo

    def ingest_selfie(self, collection_id: str, filename: str, content_type: str | None, source: BinaryIO) -> SelfieRecord:
        collection = self._collection_or_raise(collection_id)
        relative_path, _, file_size, metadata = self._save_and_validate(collection_id, "selfie", filename, content_type, source)
        selfie = SelfieRecord(id=uuid.uuid4().hex, collection_id=collection_id, storage_path=relative_path, original_filename=filename or "selfie", mime_type=metadata.mime_type, file_size=file_size, width=metadata.width, height=metadata.height, image_format=metadata.image_format, created_at=datetime.now(timezone.utc))
        collection.selfie = selfie
        collection.status = CollectionStatus.READY
        self.repository.save_collection(collection)
        return selfie

    def ingest_drive_photo(self, collection_id: str, drive_file_id: str, drive_folder_id: str, filename: str, content_type: str | None, source: BinaryIO) -> tuple[PhotoRecord, bool]:
        collection = self._collection_or_raise(collection_id)
        existing = next((photo for photo in collection.photos if photo.drive_file_id == drive_file_id), None)
        if existing:
            return existing, True
        collection.source = "google_drive"
        collection.drive_folder_id = drive_folder_id
        collection.status = CollectionStatus.UPLOADING
        self.repository.save_collection(collection)
        try:
            relative_path, _, file_size, metadata = self._save_and_validate(collection_id, "photos", filename, content_type, source)
        except IngestionError:
            collection.failed_photo_count += 1
            collection.status = CollectionStatus.READY if collection.photos else CollectionStatus.FAILED
            self.repository.save_collection(collection)
            raise
        photo = PhotoRecord(id=uuid.uuid4().hex, collection_id=collection_id, original_filename=filename or "drive-upload", storage_path=relative_path, mime_type=metadata.mime_type, file_size=file_size, width=metadata.width, height=metadata.height, image_format=metadata.image_format, created_at=datetime.now(timezone.utc), source="google_drive", drive_file_id=drive_file_id, drive_folder_id=drive_folder_id)
        collection.photos.append(photo)
        collection.status = CollectionStatus.READY
        self.repository.save_collection(collection)
        return photo, False

    def get_collection(self, collection_id: str) -> CollectionRecord:
        return self._collection_or_raise(collection_id)
