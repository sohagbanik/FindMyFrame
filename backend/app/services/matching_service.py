from typing import Protocol


class MatchingService(Protocol):
    """Contract for future selfie-to-event similarity search."""

    def find_matches(self, collection_id: str, selfie_id: str) -> list[str]:
        ...


class NotImplementedMatchingService:
    def find_matches(self, collection_id: str, selfie_id: str) -> list[str]:
        raise NotImplementedError("Face matching is intentionally not enabled in Phase 3.")
