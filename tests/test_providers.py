"""Provider response-parsing logic, exercised with mocks (no network/GUI)."""
from unittest import mock

from pytextedit.cloud.gdrive import GoogleDriveProvider
from pytextedit.cloud.onedrive import OneDriveProvider


# --------------------------------------------------------------- OneDrive
def _onedrive():
    provider = OneDriveProvider()
    provider._acquire_token = lambda: "FAKE"  # skip real auth
    return provider


def test_onedrive_list_sorts_folders_first():
    provider = _onedrive()
    payload = {
        "value": [
            {"id": "a1", "name": "a.txt", "file": {"mimeType": "text/plain"},
             "size": 5, "lastModifiedDateTime": "2024"},
            {"id": "f1", "name": "docs", "folder": {},
             "lastModifiedDateTime": "2024"},
        ]
    }
    with mock.patch("requests.get") as rget:
        resp = mock.Mock()
        resp.json.return_value = payload
        resp.raise_for_status = lambda: None
        rget.return_value = resp
        files = provider.list_files(None)
    assert [f.name for f in files] == ["docs", "a.txt"]
    assert files[0].is_folder and not files[1].is_folder


def test_onedrive_upload_new_uses_path_url():
    provider = _onedrive()
    with mock.patch("requests.put") as rput:
        resp = mock.Mock()
        resp.raise_for_status = lambda: None
        resp.json.return_value = {"id": "n1", "name": "new.txt", "file": {}}
        rput.return_value = resp
        cf = provider.upload("new.txt", b"abc")
    assert cf.id == "n1"
    assert rput.call_args[0][0].endswith("root:/new.txt:/content")


def test_onedrive_upload_existing_uses_item_url():
    provider = _onedrive()
    with mock.patch("requests.put") as rput:
        resp = mock.Mock()
        resp.raise_for_status = lambda: None
        resp.json.return_value = {"id": "e1", "name": "e.txt", "file": {}}
        rput.return_value = resp
        provider.upload("e.txt", b"abc", file_id="e1")
    assert rput.call_args[0][0].endswith("items/e1/content")


# ------------------------------------------------------------- Google Drive
def _gdrive_with_service():
    provider = GoogleDriveProvider()
    svc = mock.Mock()
    provider._service = svc
    provider._ensure_service = lambda: svc
    return provider, svc


def test_gdrive_list_parses_folders_and_sizes():
    provider, svc = _gdrive_with_service()
    svc.files().list().execute.return_value = {
        "files": [
            {"id": "1", "name": "sub",
             "mimeType": "application/vnd.google-apps.folder",
             "modifiedTime": "2024"},
            {"id": "2", "name": "f.py", "mimeType": "text/x-python",
             "modifiedTime": "2024", "size": "10"},
        ]
    }
    files = provider.list_files(None)
    assert files[0].is_folder is True
    assert files[1].is_folder is False
    assert files[1].size == 10


def test_gdrive_upload_new_vs_update():
    provider, svc = _gdrive_with_service()
    svc.files().create().execute.return_value = {
        "id": "X", "name": "n.txt", "mimeType": "text/plain"}
    assert provider.upload("n.txt", b"d", folder_id="fid").id == "X"

    svc.files().update().execute.return_value = {
        "id": "Y", "name": "u.txt", "mimeType": "text/plain"}
    assert provider.upload("u.txt", b"d", file_id="Y").id == "Y"
