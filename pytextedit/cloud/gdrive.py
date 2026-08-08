"""Google Drive provider using the official Google API client libraries.

Setup (one-time, per user):

1. Create a Google Cloud project and enable the *Google Drive API*.
2. Create an OAuth client of type "Desktop app".
3. Download the client-secret JSON and save it to the path reported by
   ``pytextedit.config.GOOGLE_CLIENT_SECRET_FILE`` (shown in the Cloud menu).

The first ``authenticate`` call opens a browser for consent; the resulting
token is cached under the app's tokens directory and refreshed automatically.
"""
from __future__ import annotations

import io
import os
from typing import Optional

from .base import CloudError, CloudFile, CloudProvider
from ..config import GOOGLE_CLIENT_SECRET_FILE, TOKENS_DIR

# Full read/write access to files created or opened by this app is broad;
# "drive" scope keeps the picker able to browse the whole Drive. Users who
# want a tighter scope can switch this to "drive.file".
SCOPES = ["https://www.googleapis.com/auth/drive"]

FOLDER_MIME = "application/vnd.google-apps.folder"
# Google Docs/Sheets/Slides cannot be downloaded as raw bytes without export;
# we only ever edit plain files, so those are surfaced but not openable here.


class GoogleDriveProvider(CloudProvider):
    id = "gdrive"
    name = "Google Drive"

    def __init__(self) -> None:
        self._token_file = TOKENS_DIR / "gdrive_token.json"
        self._service = None

    # -- availability / auth ------------------------------------------------
    def is_available(self) -> bool:
        # Catch broadly: a *broken* optional dependency (e.g. a mis-built
        # transitive package) can raise something other than ImportError, and
        # that must not take down the whole editor when the menu is built.
        try:
            import google.auth  # noqa: F401
            import googleapiclient  # noqa: F401
            import google_auth_oauthlib  # noqa: F401
            return True
        except Exception:  # noqa: BLE001
            return False

    def is_authenticated(self) -> bool:
        return self._token_file.exists()

    def _load_credentials(self):
        from google.oauth2.credentials import Credentials

        if not self._token_file.exists():
            return None
        try:
            return Credentials.from_authorized_user_file(
                str(self._token_file), SCOPES
            )
        except (ValueError, OSError):
            return None

    def authenticate(self) -> None:
        if not self.is_available():
            raise CloudError(
                "Google Drive support requires: "
                "pip install google-api-python-client google-auth-oauthlib"
            )

        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow

        creds = self._load_credentials()

        if creds and creds.valid:
            self._build_service(creds)
            return

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self._save_credentials(creds)
                self._build_service(creds)
                return
            except Exception:  # noqa: BLE001 - fall through to full re-auth
                creds = None

        if not GOOGLE_CLIENT_SECRET_FILE.exists():
            raise CloudError(
                "Missing Google OAuth client secret.\n\n"
                f"Save your downloaded 'Desktop app' client JSON to:\n"
                f"{GOOGLE_CLIENT_SECRET_FILE}"
            )

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(GOOGLE_CLIENT_SECRET_FILE), SCOPES
            )
            # port=0 lets the OS pick a free localhost port for the redirect.
            creds = flow.run_local_server(port=0)
        except Exception as exc:  # noqa: BLE001
            raise CloudError(f"Google authentication failed: {exc}") from exc

        self._save_credentials(creds)
        self._build_service(creds)

    def _save_credentials(self, creds) -> None:
        TOKENS_DIR.mkdir(parents=True, exist_ok=True)
        with open(self._token_file, "w", encoding="utf-8") as fh:
            fh.write(creds.to_json())
        try:
            os.chmod(self._token_file, 0o600)
        except OSError:
            pass

    def _build_service(self, creds) -> None:
        from googleapiclient.discovery import build

        self._service = build("drive", "v3", credentials=creds, cache_discovery=False)

    def _ensure_service(self):
        if self._service is None:
            self.authenticate()
        if self._service is None:
            raise CloudError("Google Drive is not authenticated.")
        return self._service

    def sign_out(self) -> None:
        self._service = None
        try:
            self._token_file.unlink()
        except FileNotFoundError:
            pass

    # -- file operations ----------------------------------------------------
    def list_files(self, folder_id: Optional[str] = None) -> list[CloudFile]:
        service = self._ensure_service()
        parent = folder_id or "root"
        query = f"'{parent}' in parents and trashed = false"
        try:
            results: list[CloudFile] = []
            page_token = None
            while True:
                resp = (
                    service.files()
                    .list(
                        q=query,
                        spaces="drive",
                        fields="nextPageToken, files(id, name, mimeType, "
                        "modifiedTime, size)",
                        orderBy="folder,name",
                        pageSize=200,
                        pageToken=page_token,
                    )
                    .execute()
                )
                for item in resp.get("files", []):
                    results.append(
                        CloudFile(
                            id=item["id"],
                            name=item["name"],
                            is_folder=item["mimeType"] == FOLDER_MIME,
                            mime_type=item["mimeType"],
                            modified_time=item.get("modifiedTime", ""),
                            size=int(item["size"]) if item.get("size") else None,
                        )
                    )
                page_token = resp.get("nextPageToken")
                if not page_token:
                    break
            return results
        except Exception as exc:  # noqa: BLE001
            raise CloudError(f"Could not list Google Drive files: {exc}") from exc

    def download(self, file_id: str) -> bytes:
        service = self._ensure_service()
        from googleapiclient.http import MediaIoBaseDownload

        try:
            request = service.files().get_media(fileId=file_id)
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _status, done = downloader.next_chunk()
            return buffer.getvalue()
        except Exception as exc:  # noqa: BLE001
            raise CloudError(f"Could not download file: {exc}") from exc

    def upload(
        self,
        name: str,
        content: bytes,
        file_id: Optional[str] = None,
        folder_id: Optional[str] = None,
    ) -> CloudFile:
        service = self._ensure_service()
        from googleapiclient.http import MediaIoBaseUpload

        media = MediaIoBaseUpload(
            io.BytesIO(content), mimetype="text/plain", resumable=True
        )
        try:
            if file_id:
                item = (
                    service.files()
                    .update(fileId=file_id, media_body=media,
                            fields="id, name, mimeType, modifiedTime, size")
                    .execute()
                )
            else:
                metadata = {"name": name}
                if folder_id:
                    metadata["parents"] = [folder_id]
                item = (
                    service.files()
                    .create(body=metadata, media_body=media,
                            fields="id, name, mimeType, modifiedTime, size")
                    .execute()
                )
            return CloudFile(
                id=item["id"],
                name=item["name"],
                is_folder=False,
                mime_type=item.get("mimeType", "text/plain"),
                modified_time=item.get("modifiedTime", ""),
                size=int(item["size"]) if item.get("size") else None,
            )
        except Exception as exc:  # noqa: BLE001
            raise CloudError(f"Could not upload file: {exc}") from exc
