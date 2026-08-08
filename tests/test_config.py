"""Settings store behavior (no GUI required)."""
import importlib

from pytextedit import config as config_module


def _fresh_settings(tmp_path, monkeypatch):
    """Point the config module at a temp dir and return a Settings instance."""
    monkeypatch.setattr(config_module, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config_module, "TOKENS_DIR", tmp_path / "tokens")
    monkeypatch.setattr(config_module, "SETTINGS_FILE", tmp_path / "settings.json")
    return config_module.Settings()


def test_defaults(tmp_path, monkeypatch):
    settings = _fresh_settings(tmp_path, monkeypatch)
    assert settings.get("theme") == "light"
    assert settings.get("tab_width") == 4


def test_set_save_and_reload(tmp_path, monkeypatch):
    settings = _fresh_settings(tmp_path, monkeypatch)
    settings.set("theme", "dark")
    settings.save()

    reloaded = config_module.Settings()
    assert reloaded.get("theme") == "dark"


def test_recent_files_dedup_and_order(tmp_path, monkeypatch):
    settings = _fresh_settings(tmp_path, monkeypatch)
    settings.add_recent_file("/a.txt")
    settings.add_recent_file("/b.txt")
    settings.add_recent_file("/a.txt")  # move to front, no duplicate
    recent = settings.get("recent_files")
    assert recent == ["/a.txt", "/b.txt"]


def test_recent_files_limit(tmp_path, monkeypatch):
    settings = _fresh_settings(tmp_path, monkeypatch)
    for i in range(15):
        settings.add_recent_file(f"/f{i}.txt", limit=10)
    assert len(settings.get("recent_files")) == 10
