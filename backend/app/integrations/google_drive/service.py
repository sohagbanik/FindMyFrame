from dataclasses import dataclass
import json
import re
from typing import BinaryIO, Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

from app.config import Settings
from app.models.entities import CollectionStatus
from app.services.ingestion_service import IngestionError, IngestionService


class DriveIntegrationError(Exception):
    def __init__(self, code: str, message: str, status: int = 422):
        self.code, self.message, self.status = code, message, status
        super().__init__(message)


@dataclass(frozen=True)
class DriveFile:
    file_id: str
    name: str
    mime_type: str
    size: int | None
    resource_key: str | None = None


class GoogleDriveClient:
    SUPPORTED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
    FOLDER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{10,}$")

    def __init__(self, settings: Settings):
        self.settings = settings

    @classmethod
    def extract_folder_id(cls, folder_url: str) -> str:
        if not folder_url or not folder_url.strip():
            raise DriveIntegrationError("drive_url_empty", "Paste a Google Drive folder link to continue.", 400)
        parsed = urlparse(folder_url.strip())
        if parsed.scheme != "https" or parsed.netloc.lower() not in {"drive.google.com", "www.drive.google.com"}:
            raise DriveIntegrationError("drive_url_invalid", "That does not look like a Google Drive folder link.", 400)
        path_match = re.search(r"/folders/([^/?#]+)", parsed.path)
        folder_id = path_match.group(1) if path_match else parse_qs(parsed.query).get("id", [None])[0]
        if not folder_id or not cls.FOLDER_ID_PATTERN.fullmatch(folder_id):
            raise DriveIntegrationError("drive_folder_invalid", "Please use a Google Drive folder link, not a file link.", 400)
        return folder_id

    def _request_json(self, path: str, params: dict[str, str]) -> dict:
        if not self.settings.google_drive_api_key:
            raise DriveIntegrationError("drive_not_configured", "Google Drive import is not configured on this server yet.", 503)
        query = urlencode({**params, "key": self.settings.google_drive_api_key})
        request = Request(f"{self.settings.google_drive_api_base_url.rstrip('/')}/{path.lstrip('/')}?{query}", headers={"Accept": "application/json"})
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code == 404:
                raise DriveIntegrationError("drive_folder_not_found", "We couldn’t find that Google Drive folder.", 404) from None
            if error.code in {401, 403}:
                raise DriveIntegrationError("drive_folder_inaccessible", "We can’t access this folder. Make sure it is shared appropriately and try again.", 403) from None
            if error.code == 429:
                raise DriveIntegrationError("drive_rate_limited", "Google Drive is asking us to slow down. Try again in a moment.", 429) from None
            raise DriveIntegrationError("drive_api_error", "Google Drive could not complete that request.", 502) from None
        except (URLError, TimeoutError, json.JSONDecodeError):
            raise DriveIntegrationError("drive_unavailable", "Google Drive is unavailable right now. Try again shortly.", 502) from None

    def list_images(self, folder_id: str) -> Iterator[DriveFile]:
        page_token = ""
        query = f"'{folder_id}' in parents and trashed = false and mimeType != 'application/vnd.google-apps.folder'"
        while True:
            params = {"q": query, "pageSize": "1000", "fields": "nextPageToken,files(id,name,mimeType,size,resourceKey)", "orderBy": "name_natural"}
            if page_token:
                params["pageToken"] = page_token
            payload = self._request_json("files", params)
            for item in payload.get("files", []):
                if item.get("mimeType") in self.SUPPORTED_MIME_TYPES and item.get("id"):
                    yield DriveFile(file_id=item["id"], name=item.get("name") or "drive-photo", mime_type=item["mimeType"], size=int(item["size"]) if item.get("size") else None, resource_key=item.get("resourceKey"))
            page_token = payload.get("nextPageToken", "")
            if not page_token:
                return

    def download_file(self, file_id: str, resource_key: str | None = None) -> BinaryIO:
        if not self.settings.google_drive_api_key:
            raise DriveIntegrationError("drive_not_configured", "Google Drive import is not configured on this server yet.", 503)
        params = {"alt": "media", "key": self.settings.google_drive_api_key}
        if resource_key:
            params["resourceKey"] = resource_key
        query = urlencode(params)
        request = Request(f"{self.settings.google_drive_api_base_url.rstrip('/')}/files/{file_id}?{query}", headers={"Accept": "application/octet-stream"})
        try:
            return urlopen(request, timeout=120)
        except HTTPError as error:
            if error.code in {401, 403}:
                raise DriveIntegrationError("drive_file_inaccessible", "One of the Drive photos could not be accessed.", 403) from None
            if error.code == 404:
                raise DriveIntegrationError("drive_file_not_found", "One of the Drive photos is no longer available.", 404) from None
            if error.code == 429:
                raise DriveIntegrationError("drive_rate_limited", "Google Drive is asking us to slow down. Try again in a moment.", 429) from None
            raise DriveIntegrationError("drive_download_failed", "A Drive photo could not be downloaded.", 502) from None
        except (URLError, TimeoutError):
            raise DriveIntegrationError("drive_unavailable", "Google Drive is unavailable right now. Try again shortly.", 502) from None


class GoogleDriveImportService:
    def __init__(self, client: GoogleDriveClient, ingestion: IngestionService):
        self.client = client
        self.ingestion = ingestion

    def import_folder(self, collection_id: str, folder_url: str) -> dict:
        folder_id = self.client.extract_folder_id(folder_url)
        discovered = imported = duplicates = 0
        failures: list[dict[str, str]] = []
        for drive_file in self.client.list_images(folder_id):
            discovered += 1
            try:
                with self.client.download_file(drive_file.file_id, drive_file.resource_key) as content:
                    _, duplicate = self.ingestion.ingest_drive_photo(collection_id, drive_file.file_id, folder_id, drive_file.name, drive_file.mime_type, content)
                if duplicate:
                    duplicates += 1
                else:
                    imported += 1
            except IngestionError as error:
                failures.append({"filename": drive_file.name, "code": error.code, "message": error.message})
            except DriveIntegrationError as error:
                failures.append({"filename": drive_file.name, "code": error.code, "message": error.message})
        collection = self.ingestion.get_collection(collection_id)
        collection.source = "google_drive"
        collection.drive_folder_id = folder_id
        collection.status = CollectionStatus.READY if collection.photos else CollectionStatus.FAILED
        self.ingestion.repository.save_collection(collection)
        return {"collection_id": collection_id, "source": "google_drive", "drive_folder_id": folder_id, "discovered_count": discovered, "imported_count": imported, "duplicate_count": duplicates, "failed_count": len(failures), "failed_files": failures}
