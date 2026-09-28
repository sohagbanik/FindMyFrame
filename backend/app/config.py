from dataclasses import dataclass
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _allowed_origins() -> list[str]:
    value = os.getenv("FINDMYFRAME_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [origin.strip() for origin in value.split(",") if origin.strip()]


@dataclass(frozen=True)
class Settings:
    storage_root: Path
    max_image_size_bytes: int
    allowed_origins: list[str]

    @classmethod
    def from_environment(cls) -> "Settings":
        storage_root = Path(os.getenv("FINDMYFRAME_STORAGE_ROOT", str(PROJECT_ROOT / "backend" / "runtime")))
        max_image_size = int(os.getenv("FINDMYFRAME_MAX_IMAGE_SIZE_BYTES", str(50 * 1024 * 1024)))
        return cls(storage_root=storage_root, max_image_size_bytes=max_image_size, allowed_origins=_allowed_origins())


settings = Settings.from_environment()
