from pathlib import Path
from typing import BinaryIO
import re
import uuid


class LocalStorage:
    """Development storage adapter. Swap this class for S3/Supabase later."""

    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_name(filename: str) -> str:
        name = Path(filename or "upload").name
        name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")
        return name[:120] or "upload"

    def collection_dir(self, collection_id: str) -> Path:
        path = self.root / "collections" / collection_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_upload(self, collection_id: str, kind: str, filename: str, source: BinaryIO, max_bytes: int) -> tuple[str, Path, int]:
        upload_id = uuid.uuid4().hex
        safe_name = self._safe_name(filename)
        destination_dir = self.collection_dir(collection_id) / kind
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / f"{upload_id}-{safe_name}"
        partial = destination.with_suffix(destination.suffix + ".part")
        total = 0
        try:
            with partial.open("wb") as output:
                while chunk := source.read(1024 * 1024):
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError("file_too_large")
                    output.write(chunk)
            partial.replace(destination)
        except Exception:
            partial.unlink(missing_ok=True)
            destination.unlink(missing_ok=True)
            raise
        relative_path = destination.relative_to(self.root).as_posix()
        return relative_path, destination, total

    def delete(self, path: str) -> None:
        (self.root / path).unlink(missing_ok=True)
