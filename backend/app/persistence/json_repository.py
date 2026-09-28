from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
from threading import Lock
from typing import Any

from app.models.entities import (
    CollectionRecord,
    CollectionStatus,
    PhotoRecord,
    PhotoStatus,
    SelfieRecord,
    SelfieStatus,
)
from app.models.faces import FaceRecord


class JsonRepository:
    """File-backed repository for local development; replace with PostgreSQL later."""

    def __init__(self, root: Path):
        self.path = root / "collections.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write(self, data: dict[str, Any]) -> None:
        # Direct replacement is intentionally kept simple for the local adapter.
        # A database transaction will replace this boundary in production.
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @staticmethod
    def _record_to_dict(record: CollectionRecord) -> dict[str, Any]:
        data = asdict(record)
        data["created_at"] = record.created_at.isoformat()
        data["status"] = record.status.value
        data["photos"] = []
        for photo in record.photos:
            item = asdict(photo)
            item["created_at"] = photo.created_at.isoformat()
            item["processing_status"] = photo.processing_status.value
            data["photos"].append(item)
        if record.selfie:
            selfie = asdict(record.selfie)
            selfie["created_at"] = record.selfie.created_at.isoformat()
            selfie["processing_status"] = record.selfie.processing_status.value
            data["selfie"] = selfie
        data["face_records"] = [face.model_dump(mode="json") for face in record.face_records]
        return data

    @staticmethod
    def _dict_to_record(data: dict[str, Any]) -> CollectionRecord:
        photos = [PhotoRecord(**{**item, "created_at": datetime.fromisoformat(item["created_at"]), "processing_status": PhotoStatus(item["processing_status"])}) for item in data.get("photos", [])]
        selfie_data = data.get("selfie")
        selfie = None
        if selfie_data:
            selfie = SelfieRecord(**{**selfie_data, "created_at": datetime.fromisoformat(selfie_data["created_at"]), "processing_status": SelfieStatus(selfie_data["processing_status"])})
        faces = [FaceRecord.model_validate(item) for item in data.get("face_records", [])]
        return CollectionRecord(id=data["id"], created_at=datetime.fromisoformat(data["created_at"]), status=CollectionStatus(data["status"]), photos=photos, selfie=selfie, failed_photo_count=data.get("failed_photo_count", 0), face_records=faces, face_processing_status=data.get("face_processing_status", "not_started"), face_processing_error_count=data.get("face_processing_error_count", 0), matching_status=data.get("matching_status", "not_started"), match_count=data.get("match_count", 0))

    def create_collection(self, record: CollectionRecord) -> CollectionRecord:
        with self._lock:
            data = self._read()
            data[record.id] = self._record_to_dict(record)
            self._write(data)
        return record

    def get_collection(self, collection_id: str) -> CollectionRecord | None:
        with self._lock:
            data = self._read().get(collection_id)
        return self._dict_to_record(data) if data else None

    def save_collection(self, record: CollectionRecord) -> CollectionRecord:
        with self._lock:
            data = self._read()
            data[record.id] = self._record_to_dict(record)
            self._write(data)
        return record
