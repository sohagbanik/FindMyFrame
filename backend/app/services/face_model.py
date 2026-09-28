"""YuNet detection + SFace inference. OpenCV executes pretrained ONNX networks.

No training, hand-crafted descriptors, matching, or identity classification.
"""
from dataclasses import dataclass
import hashlib
from pathlib import Path
from threading import Lock
from typing import Protocol

import cv2
import numpy as np
from PIL import Image, ImageOps

from app.models.faces import ModelMetadata
from app.services.model_manifest import MODELS
from app.utils.image_validation import validate_image_file


class FaceError(Exception):
    def __init__(self, code: str, message: str, status: int = 422):
        self.code, self.message, self.status = code, message, status
        super().__init__(message)


@dataclass
class Detection:
    row: np.ndarray  # YuNet xywh, five landmarks, score; in original oriented pixels
    bbox: tuple[float, float, float, float]
    confidence: float
    usable: bool


class FaceModel(Protocol):
    metadata: ModelMetadata

    def initialize(self) -> None: ...
    def detect(self, image: np.ndarray) -> list[Detection]: ...
    def embed(self, image: np.ndarray, face: Detection) -> list[float]: ...


def load_image(path: Path) -> np.ndarray:
    validate_image_file(path, None)
    with Image.open(path) as source:
        # Bound decoded memory as well as file bytes. Never disable Pillow's bomb checks.
        if source.width * source.height > 60_000_000:
            raise FaceError("image_too_large", "Please resize this photograph to under 60 megapixels.")
        rgb = np.asarray(ImageOps.exif_transpose(source).convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


class SFaceModel:
    def __init__(self, root: Path, device: str = "cpu"):
        self.root, self.device = root, device
        self._lock = Lock()
        self._detector = self._recognizer = None
        self.metadata = ModelMetadata(
            name=MODELS["recognizer"]["name"], version=MODELS["recognizer"]["version"],
            weights_sha256=MODELS["recognizer"]["sha256"], detector_sha256=MODELS["detector"]["sha256"],
            pipeline_id="yunet2023-sface2021-exif-long1600-score0.8-min16-align5-l2-v1",
            runtime=f"opencv-{cv2.__version__}-{device}",
        )

    def initialize(self) -> None:
        with self._lock:
            if self._recognizer is not None:
                return
            for item in MODELS.values():
                path = self.root / item["file"]
                if not path.is_file():
                    raise FaceError("model_unavailable", "Face processing needs local model setup. Run the model downloader and restart the backend.", 503)
                with path.open("rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
                if digest != item["sha256"]:
                    raise FaceError("model_invalid", "The local face model did not pass its integrity check.", 503)
            backend, target = cv2.dnn.DNN_BACKEND_OPENCV, cv2.dnn.DNN_TARGET_CPU
            if self.device == "cuda":
                if cv2.cuda.getCudaEnabledDeviceCount() == 0:
                    raise FaceError("model_unavailable", "CUDA needs a compatible OpenCV build. Use CPU for local development.", 503)
                backend, target = cv2.dnn.DNN_BACKEND_CUDA, cv2.dnn.DNN_TARGET_CUDA
            elif self.device != "cpu":
                raise FaceError("model_unavailable", "Unsupported face inference device.", 503)
            detector = cv2.FaceDetectorYN.create(str(self.root / MODELS["detector"]["file"]), "", (320, 320),
                                                0.8, 0.3, 5000, backend, target)
            recognizer = cv2.FaceRecognizerSF.create(str(self.root / MODELS["recognizer"]["file"]), "", backend, target)
            self._detector, self._recognizer = detector, recognizer

    def detect(self, image: np.ndarray) -> list[Detection]:
        self.initialize()
        height, width = image.shape[:2]
        scale = min(1.0, 1600 / max(height, width))
        resized = cv2.resize(image, (max(1, round(width * scale)), max(1, round(height * scale)))) if scale < 1 else image
        rh, rw = resized.shape[:2]
        with self._lock:  # OpenCV detector input size and network buffers are mutable.
            self._detector.setInputSize((rw, rh))
            _, rows = self._detector.detect(resized)
        detections = []
        for row in ([] if rows is None else rows):
            row = row.copy()
            if not np.isfinite(row).all():
                continue
            usable = min(row[2], row[3]) >= 16
            row[[0, 2, 4, 6, 8, 10, 12]] *= width / rw
            row[[1, 3, 5, 7, 9, 11, 13]] *= height / rh
            x, y, w, h = map(float, row[:4])
            bbox = (max(0., x), max(0., y), min(float(width), x + w), min(float(height), y + h))
            if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
                continue
            detections.append(Detection(row, bbox, float(np.clip(row[-1], 0, 1)), usable))
        return sorted(detections, key=lambda face: (face.bbox[0], face.bbox[1]))

    def embed(self, image: np.ndarray, face: Detection) -> list[float]:
        self.initialize()
        with self._lock:
            aligned = self._recognizer.alignCrop(image, face.row)
            vector = self._recognizer.feature(aligned).reshape(-1).astype(np.float32)
        # OpenCV FaceRecognizerSF's cosine path normalizes both vectors by L2 norm.
        # Store that representation; infer dimensionality from model output, not a constant.
        norm = float(np.linalg.norm(vector))
        if not vector.size or not np.isfinite(vector).all() or not np.isfinite(norm) or norm <= 0:
            raise FaceError("embedding_failed", "A face could not be processed clearly.")
        return (vector / norm).tolist()
