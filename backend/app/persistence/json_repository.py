from dataclasses import asdict, fields
from datetime import datetime
import json
from pathlib import Path
from threading import Lock
from typing import Any, Callable

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
        photo_fields = {field.name for field in fields(PhotoRecord)}
        photos = [PhotoRecord(**{key: value for key, value in {**item, "created_at": datetime.fromisoformat(item["created_at"]), "processing_status": PhotoStatus(item["processing_status"])}.items() if key in photo_fields}) for item in data.get("photos", [])]
        selfie_data = data.get("selfie")
        selfie = None
        if selfie_data:
            selfie = SelfieRecord(**{**selfie_data, "created_at": datetime.fromisoformat(selfie_data["created_at"]), "processing_status": SelfieStatus(selfie_data["processing_status"])})
        faces = [FaceRecord.model_validate(item) for item in data.get("face_records", [])]
        drive_fields = {f.name: data[f.name] for f in fields(CollectionRecord) if f.name.startswith("drive_") and f.name in data}
        return CollectionRecord(id=data["id"], created_at=datetime.fromisoformat(data["created_at"]), status=CollectionStatus(data["status"]), photos=photos, selfie=selfie, failed_photo_count=data.get("failed_photo_count", 0), face_records=faces, face_processing_status=data.get("face_processing_status", "not_started"), face_processing_error_count=data.get("face_processing_error_count", 0), photos_processed=data.get("photos_processed", 0), photos_processing_failed=data.get("photos_processing_failed", 0), matching_status=data.get("matching_status", "not_started"), match_count=data.get("match_count", 0), source=data.get("source", "local_upload"), **drive_fields)

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

    def update_collection(self, collection_id: str, mutate: Callable[[CollectionRecord], None]) -> CollectionRecord:
        """Apply a short metadata update without overwriting newer photo records."""
        with self._lock:
            data = self._read()
            record = self._dict_to_record(data[collection_id])
            mutate(record)
            data[collection_id] = self._record_to_dict(record)
            self._write(data)
            return record

    def recover_interrupted_imports(self) -> None:
        # The development adapter runs in one process; background jobs do not survive restart.
        with self._lock:
            data = self._read()
            changed = False
            for item in data.values():
                if item.get("drive_import_status") in {"discovering", "processing"}:
                    item["drive_import_status"] = "failed"
                    item["drive_import_error"] = "The server restarted before the Drive import finished. Retry to import the remaining files."
                    item["status"] = "ready" if item.get("photos") else "failed"
                    changed = True
            if changed:
                self._write(data)
