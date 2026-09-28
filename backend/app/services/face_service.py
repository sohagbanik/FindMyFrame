from datetime import datetime, timezone
import uuid
from pathlib import Path

from app.models.entities import CollectionRecord, CollectionStatus, PhotoRecord, PhotoStatus, SelfieRecord, SelfieStatus
from app.models.faces import FaceRecord
from app.persistence.json_repository import JsonRepository
from app.services.face_model import FaceError, FaceModel, load_image


class FaceService:
    """Orchestrates one-image-at-a-time inference; it never performs matching."""

    def __init__(self, model: FaceModel, storage_root: Path, repository: JsonRepository):
        self.model = model
        self.storage_root = storage_root
        self.repository = repository

    def _face_records(self, collection_id: str, source_id: str, source_kind: str, image, detections) -> list[FaceRecord]:
        records: list[FaceRecord] = []
        for index, detection in enumerate(detections):
            base = {
                "id": uuid.uuid4().hex,
                "collection_id": collection_id,
                "source_id": source_id,
                "source_kind": source_kind,
                "face_index": index,
                "bbox": detection.bbox,
                "detection_confidence": detection.confidence,
                "model": self.model.metadata,
                "created_at": datetime.now(timezone.utc),
            }
            if not detection.usable:
                records.append(FaceRecord(**base, embedding_status="skipped_small", error_code="face_too_small"))
                continue
            try:
                embedding = self.model.embed(image, detection)
                records.append(FaceRecord(**base, embedding_status="complete", embedding=embedding, embedding_dimension=len(embedding)))
            except FaceError as error:
                records.append(FaceRecord(**base, embedding_status="failed", error_code=error.code))
        return records

    def process_photo(self, collection: CollectionRecord, photo: PhotoRecord) -> list[FaceRecord]:
        image = load_image(self.storage_root / photo.storage_path)
        detections = self.model.detect(image)
        records = self._face_records(collection.id, photo.id, "photo", image, detections)
        photo.face_count = len(detections)
        photo.faces_embedded = sum(record.embedding_status == "complete" for record in records)
        photo.face_processing_error = None if all(record.embedding_status != "failed" for record in records) else "one_or_more_embeddings_failed"
        photo.processing_status = PhotoStatus.COMPLETE
        return records

    def process_selfie(self, collection: CollectionRecord, selfie: SelfieRecord) -> FaceRecord:
        image = load_image(self.storage_root / selfie.storage_path)
        detections = self.model.detect(image)
        if not detections:
            raise FaceError("no_face", "We couldn't detect a face in this reference photo. Try a clearer photo.")
        if len(detections) != 1:
            raise FaceError("multiple_faces", "Please use a reference photo with one clear face.")
        if not detections[0].usable:
            raise FaceError("face_too_small", "Your face is too small in this reference photo. Try moving closer.")
        records = self._face_records(collection.id, selfie.id, "selfie", image, detections)
        record = records[0]
        if record.embedding_status != "complete":
            raise FaceError("embedding_failed", "We couldn't prepare this reference photo. Try another clear photo.")
        selfie.face_count = 1
        selfie.faces_embedded = 1
        selfie.face_processing_error = None
        selfie.processing_status = SelfieStatus.COMPLETE
        return record

    def process_collection(self, collection_id: str) -> dict[str, int | str]:
        collection = self.repository.get_collection(collection_id)
        if not collection:
            raise FaceError("collection_not_found", "That photo collection could not be found.", 404)
        collection.face_processing_status = "processing"
        collection.status = CollectionStatus.PROCESSING
        collection.face_processing_error_count = 0
        collection.photos_processed = 0
        collection.photos_processing_failed = 0
        collection.face_records = [face for face in collection.face_records if getattr(face, "source_kind", None) != "photo"]
        self.repository.save_collection(collection)
        photos_processed = photos_failed = 0
        faces_detected = faces_embedded = 0
        for photo in collection.photos:
            photo.processing_status = PhotoStatus.PROCESSING
            self.repository.save_collection(collection)
            try:
                records = self.process_photo(collection, photo)
                collection.face_records.extend(records)
                photos_processed += 1
                collection.photos_processed = photos_processed
                faces_detected += photo.face_count
                faces_embedded += photo.faces_embedded
            except (FaceError, OSError, ValueError):
                photo.processing_status = PhotoStatus.FAILED
                photo.face_processing_error = "image_processing_failed"
                collection.face_processing_error_count += 1
                photos_failed += 1
                collection.photos_processing_failed = photos_failed
            finally:
                self.repository.save_collection(collection)
        collection.face_processing_status = "complete" if photos_failed == 0 else "complete_with_errors"
        collection.status = CollectionStatus.COMPLETE
        self.repository.save_collection(collection)
        return {"collection_id": collection.id, "status": collection.face_processing_status, "photos_processed": photos_processed, "photos_failed": photos_failed, "faces_detected": faces_detected, "faces_embedded": faces_embedded}

    def mark_collection_failed(self, collection_id: str, error_code: str) -> None:
        collection = self.repository.get_collection(collection_id)
        if not collection:
            return
        collection.face_processing_status = "failed"
        collection.status = CollectionStatus.FAILED
        collection.face_processing_error_count += 1
        self.repository.save_collection(collection)

    def process_selfie_for_collection(self, collection_id: str) -> FaceRecord:
        collection = self.repository.get_collection(collection_id)
        if not collection:
            raise FaceError("collection_not_found", "That photo collection could not be found.", 404)
        if not collection.selfie:
            raise FaceError("selfie_missing", "Upload a reference photo before processing it.", 400)
        selfie = collection.selfie
        selfie.processing_status = SelfieStatus.PROCESSING
        self.repository.save_collection(collection)
        try:
            record = self.process_selfie(collection, selfie)
        except FaceError as error:
            selfie.processing_status = SelfieStatus.FAILED
            selfie.face_processing_error = error.code
            self.repository.save_collection(collection)
            raise
        collection.face_records = [face for face in collection.face_records if getattr(face, "source_kind", None) != "selfie"]
        collection.face_records.append(record)
        self.repository.save_collection(collection)
        return record
