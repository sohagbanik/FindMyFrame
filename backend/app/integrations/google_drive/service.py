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
    modified_time: str | None = None
    resource_key: str | None = None
    can_download: bool | None = None
    shortcut_target_resource_key: str | None = None


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

    @staticmethod
    def extract_folder_resource_key(folder_url: str) -> str | None:
        parsed = urlparse(folder_url.strip())
        values = parse_qs(parsed.query)
        return (values.get("resourcekey") or values.get("resourceKey") or [None])[0]

    @staticmethod
    def _resource_key_header(resource_keys: dict[str, str] | None) -> str | None:
        if not resource_keys:
            return None
        return ",".join(f"{file_id}/{resource_key}" for file_id, resource_key in resource_keys.items() if file_id and resource_key)

    @staticmethod
    def _error_details(error: HTTPError) -> tuple[str | None, str | None]:
        try:
            payload = json.loads(error.read().decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            return None, None
        details = payload.get("error", {}) if isinstance(payload, dict) else {}
        reasons = details.get("errors", []) if isinstance(details, dict) else []
        reason = reasons[0].get("reason") if reasons and isinstance(reasons[0], dict) else None
        message = details.get("message") if isinstance(details, dict) else None
        return reason, message

    @classmethod
    def _raise_http_error(cls, error: HTTPError, *, file_scope: bool) -> None:
        reason, _ = cls._error_details(error)
        normalized = (reason or "").lower()
        if error.code == 404:
            code = "drive_file_not_found" if file_scope else "drive_folder_not_found"
            message = "One of the Drive photos is no longer available." if file_scope else "We couldn’t find that Google Drive folder."
            raise DriveIntegrationError(code, message, 404) from None
        if error.code == 401 or normalized in {"autherror", "keyinvalid"}:
            raise DriveIntegrationError("drive_api_credentials_invalid", "The Google Drive API credentials were rejected by Google.", 503) from None
        if error.code == 429 or normalized in {"ratelimitexceeded", "userratelimitexceeded", "dailylimitexceeded", "quotaexceeded"}:
            raise DriveIntegrationError("drive_rate_limited", "Google Drive is asking us to slow down. Try again in a moment.", 429) from None
        if normalized in {"filenotdownloadable", "download_restricted_for_revision", "downloadrestricted"}:
            raise DriveIntegrationError("drive_file_not_downloadable", "Google Drive does not allow this file to be downloaded through the API.", 403) from None
        if normalized in {"appnotauthorizedtofile", "domainpolicy", "teamdrivemembershiprequired"}:
            raise DriveIntegrationError("drive_file_additional_access", "Google Drive requires additional access before this file can be downloaded.", 403) from None
        if error.code in {401, 403}:
            code = "drive_file_inaccessible" if file_scope else "drive_folder_inaccessible"
            message = "One of the Drive photos could not be downloaded with the configured access." if file_scope else "We can’t access this folder with the configured Google Drive access."
            raise DriveIntegrationError(code, message, error.code) from None
        raise DriveIntegrationError("drive_api_error" if not file_scope else "drive_download_failed", "Google Drive could not complete that request.", 502) from None

    def _request_json(self, path: str, params: dict[str, str], resource_keys: dict[str, str] | None = None) -> dict:
        if not self.settings.google_drive_api_key:
            raise DriveIntegrationError("drive_not_configured", "Google Drive import is not configured on this server yet.", 503)
        query = urlencode({**params, "key": self.settings.google_drive_api_key})
        headers = {"Accept": "application/json"}
        resource_key_header = self._resource_key_header(resource_keys)
        if resource_key_header:
            headers["X-Goog-Drive-Resource-Keys"] = resource_key_header
        request = Request(f"{self.settings.google_drive_api_base_url.rstrip('/')}/{path.lstrip('/')}?{query}", headers=headers)
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            self._raise_http_error(error, file_scope=False)
        except (URLError, TimeoutError, json.JSONDecodeError):
            raise DriveIntegrationError("drive_unavailable", "Google Drive is unavailable right now. Try again shortly.", 502) from None

    def list_images(self, folder_id: str, folder_resource_key: str | None = None) -> Iterator[DriveFile]:
        page_token = ""
        query = f"'{folder_id}' in parents and trashed = false and mimeType != 'application/vnd.google-apps.folder'"
        while True:
            params = {"q": query, "pageSize": "1000", "fields": "nextPageToken,files(id,name,mimeType,size,modifiedTime,resourceKey,capabilities/canDownload,shortcutDetails(targetId,targetResourceKey))", "orderBy": "name_natural"}
            if page_token:
                params["pageToken"] = page_token
            payload = self._request_json("files", params, {folder_id: folder_resource_key} if folder_resource_key else None)
            for item in payload.get("files", []):
                if item.get("mimeType") in self.SUPPORTED_MIME_TYPES and item.get("id"):
                    shortcut = item.get("shortcutDetails") or {}
                    yield DriveFile(file_id=item["id"], name=item.get("name") or "drive-photo", mime_type=item["mimeType"], size=int(item["size"]) if item.get("size") else None, modified_time=item.get("modifiedTime"), resource_key=item.get("resourceKey"), can_download=(item.get("capabilities") or {}).get("canDownload"), shortcut_target_resource_key=shortcut.get("targetResourceKey"))
            page_token = payload.get("nextPageToken", "")
            if not page_token:
                return

    def download_file(self, file_id: str, resource_key: str | None = None, *, folder_id: str | None = None, folder_resource_key: str | None = None, can_download: bool | None = None) -> BinaryIO:
        if not self.settings.google_drive_api_key:
            raise DriveIntegrationError("drive_not_configured", "Google Drive import is not configured on this server yet.", 503)
        if can_download is False:
            raise DriveIntegrationError("drive_file_download_disabled", "Google Drive does not allow this file to be downloaded.", 403)
        params = {"alt": "media", "key": self.settings.google_drive_api_key, "supportsAllDrives": "true"}
        query = urlencode(params)
        resource_keys = {file_id: resource_key or ""}
        if folder_id and folder_resource_key:
            resource_keys[folder_id] = folder_resource_key
        headers = {"Accept": "application/octet-stream"}
        resource_key_header = self._resource_key_header(resource_keys)
        if resource_key_header:
            headers["X-Goog-Drive-Resource-Keys"] = resource_key_header
        request = Request(f"{self.settings.google_drive_api_base_url.rstrip('/')}/files/{file_id}?{query}", headers=headers)
        try:
            return urlopen(request, timeout=120)
        except HTTPError as error:
            self._raise_http_error(error, file_scope=True)
        except (URLError, TimeoutError):
            raise DriveIntegrationError("drive_unavailable", "Google Drive is unavailable right now. Try again shortly.", 502) from None


class GoogleDriveImportService:
    def __init__(self, client: GoogleDriveClient, ingestion: IngestionService):
        self.client = client
        self.ingestion = ingestion

    def import_folder(self, collection_id: str, folder_url: str) -> dict:
        folder_id = self.client.extract_folder_id(folder_url)
        folder_resource_key = self.client.extract_folder_resource_key(folder_url)
        discovered = imported = duplicates = 0
        failures: list[dict[str, str]] = []
        for drive_file in self.client.list_images(folder_id, folder_resource_key):
            discovered += 1
            try:
                resource_key = drive_file.resource_key or drive_file.shortcut_target_resource_key
                with self.client.download_file(drive_file.file_id, resource_key, folder_id=folder_id, folder_resource_key=folder_resource_key, can_download=drive_file.can_download) as content:
                    _, duplicate = self.ingestion.ingest_drive_photo(collection_id, drive_file.file_id, folder_id, drive_file.name, drive_file.mime_type, content, drive_file.modified_time)
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
