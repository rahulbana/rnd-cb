"""OneDrive provider using MSAL for auth and Microsoft Graph for storage.

Setup (one-time, per user):

1. Register an application at https://portal.azure.com (Azure AD app
   registrations). Use "Mobile and desktop applications" and add the redirect
   URI ``http://localhost``. Grant delegated Microsoft Graph permission
   ``Files.ReadWrite``.
2. Create a JSON file at the path reported by
   ``pytextedit.config.ONEDRIVE_CONFIG_FILE`` containing::

       {"client_id": "<application-client-id>",
        "authority": "https://login.microsoftonline.com/common"}

Authentication uses the device-code flow, which works without a bundled
client secret and on headless machines: the app prints a URL and a code to
enter there.
"""
from __future__ import annotations

import json
import os
from typing import Optional

from .base import CloudError, CloudFile, CloudProvider
from ..config import ONEDRIVE_CONFIG_FILE, TOKENS_DIR

GRAPH_ROOT = "https://graph.microsoft.com/v1.0"
SCOPES = ["Files.ReadWrite", "User.Read"]


class OneDriveProvider(CloudProvider):
    id = "onedrive"
    name = "OneDrive"

    def __init__(self) -> None:
        self._cache_file = TOKENS_DIR / "onedrive_token.json"
        self._app = None
        self._account = None
        # Optional hook so the UI can show the device-code prompt to the user.
        self.device_code_callback = None

    # -- availability / auth ------------------------------------------------
    def is_available(self) -> bool:
        # Catch broadly: a *broken* optional dependency can raise something
        # other than ImportError, and that must not take down the editor.
        try:
            import msal  # noqa: F401
            import requests  # noqa: F401
            return True
        except Exception:  # noqa: BLE001
            return False

    def _load_config(self) -> dict:
        if not ONEDRIVE_CONFIG_FILE.exists():
            raise CloudError(
                "Missing OneDrive configuration.\n\n"
                f"Create {ONEDRIVE_CONFIG_FILE} with your Azure app's\n"
                '{"client_id": "...", "authority": "..."}'
            )
        try:
            with open(ONEDRIVE_CONFIG_FILE, "r", encoding="utf-8") as fh:
                cfg = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            raise CloudError(f"Invalid OneDrive config: {exc}") from exc
        if not cfg.get("client_id"):
            raise CloudError("OneDrive config is missing 'client_id'.")
        cfg.setdefault("authority", "https://login.microsoftonline.com/common")
        return cfg

    def _build_app(self):
        import msal

        cfg = self._load_config()
        cache = msal.SerializableTokenCache()
        if self._cache_file.exists():
            try:
                cache.deserialize(self._cache_file.read_text(encoding="utf-8"))
            except OSError:
                pass
        app = msal.PublicClientApplication(
            cfg["client_id"], authority=cfg["authority"], token_cache=cache
        )
        self._app = app
        self._cache = cache
        return app

    def _persist_cache(self) -> None:
        if getattr(self, "_cache", None) is None:
            return
        if self._cache.has_state_changed:
            TOKENS_DIR.mkdir(parents=True, exist_ok=True)
            self._cache_file.write_text(self._cache.serialize(), encoding="utf-8")
            try:
                os.chmod(self._cache_file, 0o600)
            except OSError:
                pass

    def is_authenticated(self) -> bool:
        if not self._cache_file.exists():
            return False
        try:
            app = self._build_app()
        except CloudError:
            return False
        return bool(app.get_accounts())

    def _acquire_token(self) -> str:
        app = self._app or self._build_app()

        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(SCOPES, account=accounts[0])
            if result and "access_token" in result:
                self._persist_cache()
                return result["access_token"]

        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            raise CloudError(
                "Failed to start device-code flow: "
                f"{flow.get('error_description', flow)}"
            )
        message = flow["message"]
        if self.device_code_callback:
            try:
                self.device_code_callback(message)
            except Exception:  # noqa: BLE001 - UI callback must not break auth
                pass
        else:
            print(message)

        result = app.acquire_token_by_device_flow(flow)
        if "access_token" not in result:
            raise CloudError(
                "OneDrive authentication failed: "
                f"{result.get('error_description', result)}"
            )
        self._persist_cache()
        return result["access_token"]

    def authenticate(self) -> None:
        if not self.is_available():
            raise CloudError(
                "OneDrive support requires: pip install msal requests"
            )
        # Acquiring a token both validates config and primes the cache.
        self._acquire_token()

    def sign_out(self) -> None:
        self._app = None
        try:
            self._cache_file.unlink()
        except FileNotFoundError:
            pass

    # -- HTTP helper --------------------------------------------------------
    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._acquire_token()}"}

    # -- file operations ----------------------------------------------------
    def list_files(self, folder_id: Optional[str] = None) -> list[CloudFile]:
        import requests

        if folder_id and folder_id != "root":
            url = f"{GRAPH_ROOT}/me/drive/items/{folder_id}/children"
        else:
            url = f"{GRAPH_ROOT}/me/drive/root/children"

        results: list[CloudFile] = []
        try:
            while url:
                resp = requests.get(url, headers=self._headers(), timeout=30)
                resp.raise_for_status()
                data = resp.json()
                for item in data.get("value", []):
                    is_folder = "folder" in item
                    results.append(
                        CloudFile(
                            id=item["id"],
                            name=item["name"],
                            is_folder=is_folder,
                            mime_type=item.get("file", {}).get(
                                "mimeType", "" if is_folder else "text/plain"
                            ),
                            modified_time=item.get("lastModifiedDateTime", ""),
                            size=item.get("size"),
                        )
                    )
                url = data.get("@odata.nextLink")
        except requests.RequestException as exc:
            raise CloudError(f"Could not list OneDrive files: {exc}") from exc

        results.sort(key=lambda f: (not f.is_folder, f.name.lower()))
        return results

    def download(self, file_id: str) -> bytes:
        import requests

        url = f"{GRAPH_ROOT}/me/drive/items/{file_id}/content"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=60)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as exc:
            raise CloudError(f"Could not download file: {exc}") from exc

    def upload(
        self,
        name: str,
        content: bytes,
        file_id: Optional[str] = None,
        folder_id: Optional[str] = None,
    ) -> CloudFile:
        import requests

        # Simple upload (PUT ...content) supports files up to 250 MB, which is
        # far beyond any realistic text document.
        if file_id:
            url = f"{GRAPH_ROOT}/me/drive/items/{file_id}/content"
        elif folder_id and folder_id != "root":
            url = f"{GRAPH_ROOT}/me/drive/items/{folder_id}:/{name}:/content"
        else:
            url = f"{GRAPH_ROOT}/me/drive/root:/{name}:/content"

        headers = self._headers()
        headers["Content-Type"] = "text/plain"
        try:
            resp = requests.put(url, headers=headers, data=content, timeout=60)
            resp.raise_for_status()
            item = resp.json()
            return CloudFile(
                id=item["id"],
                name=item["name"],
                is_folder=False,
                mime_type=item.get("file", {}).get("mimeType", "text/plain"),
                modified_time=item.get("lastModifiedDateTime", ""),
                size=item.get("size"),
            )
        except requests.RequestException as exc:
            raise CloudError(f"Could not upload file: {exc}") from exc
