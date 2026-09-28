"""Private biometric records. No public response schema includes these vectors."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelMetadata(BaseModel):
    name: str
    version: str
    weights_sha256: str
    detector_sha256: str
    pipeline_id: str
    runtime: str
    normalization: Literal["l2"] = "l2"


class FaceRecord(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    id: str
    collection_id: str
    source_id: str
    source_kind: Literal["photo", "selfie"]
    face_index: int = Field(ge=0)
    bbox: tuple[float, float, float, float]
    detection_confidence: float = Field(ge=0, le=1)
    embedding_status: Literal["complete", "skipped_small", "failed"]
    embedding: list[float] | None = None
    embedding_dimension: int | None = None
    error_code: str | None = None
    model: ModelMetadata
    created_at: datetime

    @model_validator(mode="after")
    def check_vector(self):
        if self.embedding_status == "complete":
            if not self.embedding or len(self.embedding) != self.embedding_dimension:
                raise ValueError("Invalid embedding dimension")
        elif self.embedding is not None:
            raise ValueError("Unusable faces must not carry embeddings")
        return self


class FaceArtifact(BaseModel):
    source_id: str
    collection_id: str
    source_kind: Literal["photo", "selfie"]
    coordinate_space: Literal["exif_oriented_pixels"] = "exif_oriented_pixels"
    image_width: int
    image_height: int
    model: ModelMetadata
    faces: list[FaceRecord]
