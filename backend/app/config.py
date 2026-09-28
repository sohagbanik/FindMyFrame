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
    model_root: Path = PROJECT_ROOT / "backend" / "models"
    cv_device: str = "cpu"
    face_match_strong_threshold: float = 0.55
    face_match_possible_threshold: float = 0.363

    @classmethod
    def from_environment(cls) -> "Settings":
        storage_root = Path(os.getenv("FINDMYFRAME_STORAGE_ROOT", str(PROJECT_ROOT / "backend" / "runtime")))
        max_image_size = int(os.getenv("FINDMYFRAME_MAX_IMAGE_SIZE_BYTES", str(50 * 1024 * 1024)))
        strong_threshold = float(os.getenv("FACE_MATCH_STRONG_THRESHOLD", "0.55"))
        possible_threshold = float(os.getenv("FACE_MATCH_POSSIBLE_THRESHOLD", "0.363"))
        if not 0 <= possible_threshold <= strong_threshold <= 1:
            raise ValueError("FACE_MATCH thresholds must satisfy 0 <= possible <= strong <= 1")
        return cls(storage_root=storage_root, max_image_size_bytes=max_image_size, allowed_origins=_allowed_origins(),
                   model_root=Path(os.getenv("FINDMYFRAME_MODEL_ROOT", str(PROJECT_ROOT / "backend" / "models"))),
                   cv_device=os.getenv("FINDMYFRAME_CV_DEVICE", "cpu"), face_match_strong_threshold=strong_threshold, face_match_possible_threshold=possible_threshold)


settings = Settings.from_environment()
