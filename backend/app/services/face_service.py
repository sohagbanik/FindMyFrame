from typing import Protocol


class FaceProcessingService(Protocol):
    """Contract for the future detector/embedding worker."""

    def process_image(self, storage_path: str) -> None:
        ...


class NotImplementedFaceProcessingService:
    def process_image(self, storage_path: str) -> None:
        raise NotImplementedError("Face processing is intentionally not enabled in Phase 3.")
