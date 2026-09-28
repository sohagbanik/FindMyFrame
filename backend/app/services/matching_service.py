from dataclasses import dataclass
from typing import Iterable

import numpy as np

from app.config import Settings
from app.models.entities import CollectionRecord, PhotoRecord
from app.models.faces import FaceRecord
from app.persistence.json_repository import JsonRepository


class MatchingError(Exception):
    def __init__(self, code: str, message: str, status: int = 422):
        self.code, self.message, self.status = code, message, status
        super().__init__(message)


@dataclass(frozen=True)
class RankedFace:
    face_id: str
    photo_id: str
    score: float
    match_type: str


@dataclass(frozen=True)
class PhotoMatch:
    photo: PhotoRecord
    face_id: str
    score: float
    match_type: str


class MatchingService:
    """Pure embedding matching; it never loads images or exposes vectors."""

    def __init__(self, settings: Settings, repository: JsonRepository):
        self.settings = settings
        self.repository = repository

    @staticmethod
    def calculate_similarity(query: list[float], candidate: list[float]) -> float:
        query_array = np.asarray(query, dtype=np.float32)
        candidate_array = np.asarray(candidate, dtype=np.float32)
        if query_array.ndim != 1 or candidate_array.ndim != 1 or query_array.shape != candidate_array.shape:
            raise MatchingError("model_incompatible", "The stored face embeddings are not compatible with this selfie.", 409)
        query_norm = float(np.linalg.norm(query_array))
        candidate_norm = float(np.linalg.norm(candidate_array))
        if not np.isfinite(query_norm) or not np.isfinite(candidate_norm) or query_norm <= 0 or candidate_norm <= 0:
            raise MatchingError("invalid_embedding", "A stored face embedding is not usable.", 422)
        return float(np.clip(np.dot(query_array, candidate_array) / (query_norm * candidate_norm), -1.0, 1.0))

    @staticmethod
    def _compatible(query: FaceRecord, candidate: FaceRecord) -> bool:
        return query.embedding_dimension == candidate.embedding_dimension and query.model.model_dump() == candidate.model.model_dump()

    def _rank_faces(self, query: FaceRecord, candidates: Iterable[FaceRecord]) -> list[RankedFace]:
        ranked: list[RankedFace] = []
        for candidate in candidates:
            if candidate.embedding_status != "complete" or not candidate.embedding or not self._compatible(query, candidate):
                continue
            score = self.calculate_similarity(query.embedding or [], candidate.embedding)
            if score < self.settings.face_match_possible_threshold:
                continue
            ranked.append(RankedFace(face_id=candidate.id, photo_id=candidate.source_id, score=score, match_type="strong" if score >= self.settings.face_match_strong_threshold else "possible"))
        return sorted(ranked, key=lambda item: item.score, reverse=True)

    @staticmethod
    def _group_by_photo(ranked_faces: Iterable[RankedFace], photos: Iterable[PhotoRecord]) -> list[PhotoMatch]:
        photo_by_id = {photo.id: photo for photo in photos}
        best_by_photo: dict[str, RankedFace] = {}
        for face in ranked_faces:
            current = best_by_photo.get(face.photo_id)
            if current is None or face.score > current.score:
                best_by_photo[face.photo_id] = face
        results = [PhotoMatch(photo=photo_by_id[photo_id], face_id=face.face_id, score=face.score, match_type=face.match_type) for photo_id, face in best_by_photo.items() if photo_id in photo_by_id]
        return sorted(results, key=lambda item: item.score, reverse=True)

    def match_selfie_to_collection(self, collection_id: str) -> list[PhotoMatch]:
        collection = self.repository.get_collection(collection_id)
        if not collection:
            raise MatchingError("collection_not_found", "That photo collection could not be found.", 404)
        if not collection.selfie or collection.selfie.processing_status.value != "complete":
            raise MatchingError("selfie_not_processed", "Process a clear selfie before matching.", 409)
        if collection.face_processing_status not in {"complete", "complete_with_errors"}:
            raise MatchingError("faces_not_processed", "Process the event photos before matching.", 409)
        query_candidates = [face for face in collection.face_records if getattr(face, "source_kind", None) == "selfie" and face.embedding_status == "complete" and face.source_id == collection.selfie.id]
        if len(query_candidates) != 1:
            raise MatchingError("selfie_embedding_missing", "The selfie embedding is not available.", 409)
        query = query_candidates[0]
        event_faces = [face for face in collection.face_records if getattr(face, "source_kind", None) == "photo"]
        complete_event_faces = [face for face in event_faces if face.embedding_status == "complete" and face.embedding]
        if complete_event_faces and any(not self._compatible(query, face) for face in complete_event_faces):
            raise MatchingError("model_incompatible", "The event faces were produced by a different compatible model configuration.", 409)
        return self._group_by_photo(self._rank_faces(query, complete_event_faces), collection.photos)

    def set_matching_status(self, collection_id: str, status: str, match_count: int = 0) -> None:
        collection = self.repository.get_collection(collection_id)
        if collection:
            collection.matching_status = status
            collection.match_count = match_count
            self.repository.save_collection(collection)
