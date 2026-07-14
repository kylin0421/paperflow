"""Native Windows desktop shell for Paper Flow."""

from __future__ import annotations

import argparse
import ctypes
import os
import shutil
import threading
import urllib.parse
from http.server import ThreadingHTTPServer
from pathlib import Path

from paperflow.webapp import AppHandler, Recommender, Store


APP_TITLE = "Paper Flow"
MUTEX_NAME = "Local\\PaperFlowDesktopApp"
ERROR_ALREADY_EXISTS = 183


def default_data_dir() -> Path:
    """Use the conventional per-user application data directory on Windows."""
    root = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(root) / APP_TITLE


def migrate_legacy_data(data_dir: Path) -> bool:
    """Copy the previous development database on first desktop launch."""
    target = data_dir / "state.db"
    legacy = Path.home() / ".arxiv-daily" / "state.db"
    if target.exists() or not legacy.is_file():
        return False
    data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(legacy, target)
    return True


def acquire_single_instance():
    """Keep a Windows mutex alive for the lifetime of the process."""
    if os.name != "nt":
        return None
    handle = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if not handle:
        raise OSError("Could not create the Paper Flow application mutex")
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        ctypes.windll.user32.MessageBoxW(
            None,
            "Paper Flow is already running.\n\nPaper Flow 已经在运行。",
            APP_TITLE,
            0x40,
        )
        ctypes.windll.kernel32.CloseHandle(handle)
        return False
    return handle


class DesktopApi:
    """Small native bridge exposed to the existing web interface."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.chat_window = None

    def pick_directory(self, title: str = "Choose a folder", initial: str = "") -> str:
        import webview

        window = webview.windows[0]
        result = window.create_file_dialog(
            webview.FOLDER_DIALOG,
            directory=initial if initial and Path(initial).is_dir() else "",
        )
        return str(result[0]) if result else ""

    def open_chat(self, paper_id: str, title: str = "") -> bool:
        """Open or reuse a native, independently manageable paper-chat window."""
        import webview

        query = urllib.parse.urlencode({"paper_id": paper_id})
        url = f"{self.base_url}/chat.html?{query}"
        if self.chat_window is not None:
            try:
                self.chat_window.load_url(url)
                self.chat_window.restore()
                self.chat_window.show()
                return True
            except Exception:
                self.chat_window = None
        self.chat_window = webview.create_window(
            title or "Paper Flow Chat",
            url=url,
            width=1120,
            height=780,
            min_size=(760, 520),
            resizable=True,
            background_color="#0f1012",
            text_select=True,
        )
        return True


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run Paper Flow as a native desktop app")
    parser.add_argument("--data-dir", default=str(default_data_dir()))
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args(argv)

    mutex = acquire_single_instance()
    if mutex is False:
        return

    import webview

    data_dir = Path(args.data_dir).expanduser().resolve()
    migrate_legacy_data(data_dir)
    AppHandler.app = Recommender(Store(data_dir / "state.db"))
    AppHandler.app.schedule_interest_refresh()
    server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    url = f"http://127.0.0.1:{server.server_port}/"

    webview.create_window(
        APP_TITLE,
        url=url,
        js_api=DesktopApi(url),
        width=1180,
        height=820,
        min_size=(860, 620),
        background_color="#0f1012",
        text_select=True,
    )
    try:
        webview.start(gui="edgechromium", debug=args.debug)
    except Exception as exc:
        if os.name == "nt":
            ctypes.windll.user32.MessageBoxW(
                None,
                "Paper Flow could not start its Windows interface.\n\n"
                "Please install Microsoft Edge WebView2 Runtime and try again.\n\n"
                "Paper Flow 无法启动 Windows 界面，请安装 Microsoft Edge WebView2 Runtime 后重试。\n\n"
                f"Details: {exc}",
                APP_TITLE,
                0x10,
            )
        raise
    finally:
        server.shutdown()
        server.server_close()
        if mutex not in (None, False) and os.name == "nt":
            ctypes.windll.kernel32.CloseHandle(mutex)


if __name__ == "__main__":
    main()
