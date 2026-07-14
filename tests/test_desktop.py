import sys
from pathlib import Path
from types import SimpleNamespace

from paperflow.desktop import DesktopApi, default_data_dir, migrate_legacy_data


def test_default_desktop_data_dir_uses_local_appdata(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert default_data_dir() == tmp_path / "Paper Flow"


def test_desktop_folder_picker_returns_native_selection(monkeypatch, tmp_path):
    selected = tmp_path / "papers"
    selected.mkdir()
    calls = []

    class Window:
        def create_file_dialog(self, dialog_type, directory=""):
            calls.append((dialog_type, directory))
            return (str(selected),)

    fake_webview = SimpleNamespace(
        windows=[Window()],
        FOLDER_DIALOG="folder",
    )
    monkeypatch.setitem(sys.modules, "webview", fake_webview)

    result = DesktopApi("http://127.0.0.1:8765").pick_directory("Choose", str(tmp_path))

    assert result == str(selected)
    assert calls == [("folder", str(tmp_path))]


def test_desktop_chat_opens_a_resizable_native_window(monkeypatch):
    calls = []
    window = SimpleNamespace()
    fake_webview = SimpleNamespace(
        create_window=lambda title, **kwargs: calls.append((title, kwargs)) or window,
    )
    monkeypatch.setitem(sys.modules, "webview", fake_webview)

    api = DesktopApi("http://127.0.0.1:4321/")
    assert api.open_chat("2607.12345", "Paper title") is True

    assert calls[0][0] == "Paper title"
    assert calls[0][1]["url"] == (
        "http://127.0.0.1:4321/chat.html?paper_id=2607.12345"
    )
    assert calls[0][1]["resizable"] is True
    assert calls[0][1]["min_size"] == (760, 520)


def test_legacy_database_is_migrated_only_once(monkeypatch, tmp_path):
    home = tmp_path / "home"
    legacy = home / ".arxiv-daily" / "state.db"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"legacy database")
    target_dir = tmp_path / "local" / "Paper Flow"
    monkeypatch.setattr(Path, "home", lambda: home)

    assert migrate_legacy_data(target_dir) is True
    assert (target_dir / "state.db").read_bytes() == b"legacy database"
    legacy.write_bytes(b"new legacy content")
    assert migrate_legacy_data(target_dir) is False
    assert (target_dir / "state.db").read_bytes() == b"legacy database"
