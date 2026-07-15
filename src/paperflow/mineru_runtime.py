"""Lifecycle management for Paper Flow's optional local MinerU worker."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


MINERU_VERSION = "3.4.4"
MINERU_PACKAGE = f"mineru[pipeline]=={MINERU_VERSION}"
PYTHON_VERSION = "3.12"


def _hidden_process_flags() -> int:
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0


def bundled_uv_path() -> Path | None:
    """Find uv from an explicit override, the frozen app, or PATH."""
    override = os.environ.get("PAPERFLOW_UV", "").strip()
    if override and Path(override).is_file():
        return Path(override)
    candidates: list[Path] = []
    bundle = getattr(sys, "_MEIPASS", "")
    if bundle:
        candidates.extend([Path(bundle) / "uv.exe", Path(bundle) / "uv"])
    executable = Path(sys.executable).resolve().parent
    candidates.extend([
        executable / "_internal" / "uv.exe",
        executable / "_internal" / "uv",
        executable / "uv.exe",
        executable / "uv",
    ])
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    resolved = shutil.which("uv")
    return Path(resolved) if resolved else None


class ManagedMinerURuntime:
    """Install and supervise an isolated Python 3.12 ``mineru-api`` worker."""

    def __init__(self, root: str | Path, uv_path: str | Path | None = None):
        self.root = Path(root).expanduser().resolve()
        self.venv = self.root / "venv"
        self.python_dir = self.root / "python"
        self.cache_dir = self.root / "uv-cache"
        self.models_dir = self.root / "models"
        self.marker = self.root / "install.json"
        self.install_log = self.root / "install.log"
        self.worker_log = self.root / "worker.log"
        self._uv = Path(uv_path).resolve() if uv_path else None
        self._lock = threading.RLock()
        self._start_lock = threading.Lock()
        self._install_thread: threading.Thread | None = None
        self._install_process: subprocess.Popen | None = None
        self._install_cancel = threading.Event()
        self._repair_requested = False
        self._worker: subprocess.Popen | None = None
        self._worker_log_handle = None
        self._worker_url = ""
        self._worker_source = ""
        self._phase = "ready" if self._is_installed() else "not_installed"
        self._percent = 100 if self._is_installed() else 0
        self._message = ""
        self._error = ""

    @property
    def python_executable(self) -> Path:
        if os.name == "nt":
            return self.venv / "Scripts" / "python.exe"
        return self.venv / "bin" / "python"

    @property
    def api_executable(self) -> Path:
        if os.name == "nt":
            return self.venv / "Scripts" / "mineru-api.exe"
        return self.venv / "bin" / "mineru-api"

    def _is_installed(self) -> bool:
        return self.marker.is_file() and self.python_executable.is_file() and self.api_executable.is_file()

    def _marker_data(self) -> dict[str, Any]:
        try:
            value = json.loads(self.marker.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _directory_size(root: Path) -> int:
        total = 0
        try:
            for path in root.rglob("*"):
                try:
                    if path.is_file():
                        total += path.stat().st_size
                except OSError:
                    continue
        except OSError:
            return total
        return total

    def _worker_running(self) -> bool:
        with self._lock:
            if self._worker is None:
                return False
            if self._worker.poll() is None:
                return True
            self._worker = None
            self._worker_url = ""
            self._worker_source = ""
            self._close_worker_log()
            return False

    def status(self) -> dict[str, Any]:
        installed = self._is_installed()
        running = self._worker_running()
        marker = self._marker_data()
        with self._lock:
            thread_running = bool(self._install_thread and self._install_thread.is_alive())
            return {
                "installed": installed,
                "root_exists": self.root.exists(),
                "installing": thread_running,
                "running": running,
                "phase": self._phase,
                "percent": self._percent,
                "message": self._message,
                "error": self._error,
                "version": marker.get("version", ""),
                "python_version": marker.get("python_version", PYTHON_VERSION),
                "disk_bytes": int(marker.get("disk_bytes", 0) or 0),
                "root": str(self.root),
                "log_path": str(self.install_log),
                "worker_url": self._worker_url if running else "",
                "pid": self._worker.pid if running and self._worker else None,
                "uv_available": bool(self._uv_path()),
                "package": MINERU_PACKAGE,
            }

    def _set_status(self, phase: str, percent: int, message: str = "", error: str = "") -> None:
        with self._lock:
            self._phase = phase
            self._percent = max(0, min(100, int(percent)))
            self._message = str(message)
            self._error = str(error)

    def _uv_path(self) -> Path | None:
        return self._uv if self._uv and self._uv.is_file() else bundled_uv_path()

    def install_async(self, *, repair: bool = False) -> dict[str, Any]:
        with self._lock:
            if self._install_thread and self._install_thread.is_alive():
                return self.status()
            if self._is_installed() and not repair:
                self._set_status("ready", 100, "MinerU is already installed")
                return self.status()
            if not self._uv_path():
                raise RuntimeError("uv was not found; install uv or use the Windows Paper Flow build")
            self._install_cancel.clear()
            self._repair_requested = bool(repair)
            self._set_status("preparing", 3, "Preparing the isolated MinerU runtime")
            self._install_thread = threading.Thread(
                target=self._install_worker,
                name="paperflow-mineru-install",
                daemon=True,
            )
            self._install_thread.start()
        return self.status()

    def _install_environment(self) -> dict[str, str]:
        environment = dict(os.environ)
        environment.update({
            "UV_CACHE_DIR": str(self.cache_dir),
            "UV_PYTHON_INSTALL_DIR": str(self.python_dir),
            "UV_PYTHON_PREFERENCE": "only-managed",
            "PYTHONUTF8": "1",
        })
        return environment

    def _run_install_command(self, command: list[str], log, environment: dict[str, str]) -> None:
        log.write(("\n> " + subprocess.list2cmdline(command) + "\n").encode("utf-8"))
        log.flush()
        process = subprocess.Popen(
            command,
            stdout=log,
            stderr=subprocess.STDOUT,
            cwd=str(self.root),
            env=environment,
            creationflags=_hidden_process_flags(),
        )
        with self._lock:
            self._install_process = process
        try:
            while process.poll() is None:
                if self._install_cancel.wait(.25):
                    process.terminate()
                    try:
                        process.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        process.kill()
                    raise RuntimeError("MinerU installation was cancelled")
            if process.returncode:
                raise RuntimeError(f"Installer command failed with exit code {process.returncode}")
        finally:
            with self._lock:
                self._install_process = None

    def _install_worker(self) -> None:
        try:
            self.stop()
            self.root.mkdir(parents=True, exist_ok=True)
            uv = self._uv_path()
            if not uv:
                raise RuntimeError("uv is unavailable")
            environment = self._install_environment()
            with self.install_log.open("ab") as log:
                self._set_status("python", 12, f"Installing managed Python {PYTHON_VERSION}")
                self._run_install_command(
                    [str(uv), "python", "install", PYTHON_VERSION], log, environment,
                )
                self._set_status("environment", 25, "Creating the isolated Python environment")
                self._run_install_command(
                    [str(uv), "venv", "--python", PYTHON_VERSION, str(self.venv)],
                    log,
                    environment,
                )
                self._set_status("packages", 38, "Installing MinerU and the CPU pipeline")
                install_command = [
                    str(uv), "pip", "install", "--python", str(self.python_executable),
                    "--upgrade",
                ]
                if self._repair_requested:
                    install_command.extend(["--reinstall-package", "mineru"])
                install_command.append(MINERU_PACKAGE)
                self._run_install_command(install_command, log, environment)
                self._set_status("verifying", 90, "Verifying the MinerU installation")
                self._run_install_command(
                    [
                        str(self.python_executable), "-c",
                        "from mineru.version import __version__; print(__version__)",
                    ],
                    log,
                    environment,
                )
            marker = {
                "version": MINERU_VERSION,
                "package": MINERU_PACKAGE,
                "python_version": PYTHON_VERSION,
                "installed_at": datetime.now(timezone.utc).isoformat(),
                "disk_bytes": 0,
            }
            self.marker.write_text(json.dumps(marker, indent=2), encoding="utf-8")
            marker["disk_bytes"] = self._directory_size(self.root)
            self.marker.write_text(json.dumps(marker, indent=2), encoding="utf-8")
            self._set_status("ready", 100, "MinerU is installed and ready")
        except Exception as exc:
            phase = "cancelled" if self._install_cancel.is_set() else "error"
            self._set_status(phase, 0, "", str(exc))
        finally:
            with self._lock:
                self._install_process = None

    def cancel_install(self) -> dict[str, Any]:
        self._install_cancel.set()
        with self._lock:
            process = self._install_process
        if process and process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass
        return self.status()

    @staticmethod
    def _free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    @staticmethod
    def _healthy(url: str, timeout: float = 2.0) -> bool:
        try:
            response = httpx.get(f"{url}/health", timeout=timeout)
            response.raise_for_status()
            return True
        except Exception:
            return False

    def _model_environment(self, source: str) -> dict[str, str]:
        environment = dict(os.environ)
        normalized = str(source or "auto").strip().lower()
        if normalized in {"huggingface", "modelscope"}:
            environment["MINERU_MODEL_SOURCE"] = normalized
        else:
            environment.pop("MINERU_MODEL_SOURCE", None)
        environment.update({
            "HF_HOME": str(self.models_dir / "huggingface"),
            "HF_HUB_CACHE": str(self.models_dir / "huggingface" / "hub"),
            "HUGGINGFACE_HUB_CACHE": str(self.models_dir / "huggingface" / "hub"),
            "TRANSFORMERS_CACHE": str(self.models_dir / "huggingface" / "transformers"),
            "MODELSCOPE_CACHE": str(self.models_dir / "modelscope"),
            "TORCH_HOME": str(self.models_dir / "torch"),
            "XDG_CACHE_HOME": str(self.models_dir / "cache"),
        })
        environment["PYTHONUTF8"] = "1"
        return environment

    def ensure_running(self, *, model_source: str = "auto", timeout: float = 90,
                       cancel_event: threading.Event | None = None) -> str:
        if not self._is_installed():
            raise RuntimeError("Local MinerU is not installed; install it in Settings first")
        normalized_source = str(model_source or "auto").strip().lower()
        with self._start_lock:
            if (
                self._worker_running()
                and self._worker_source == normalized_source
                and self._healthy(self._worker_url)
            ):
                return self._worker_url
            self.stop()
            port = self._free_port()
            url = f"http://127.0.0.1:{port}"
            self.root.mkdir(parents=True, exist_ok=True)
            log = self.worker_log.open("ab")
            command = [
                str(self.api_executable), "--host", "127.0.0.1", "--port", str(port),
            ]
            log.write(("\n> " + subprocess.list2cmdline(command) + "\n").encode("utf-8"))
            log.flush()
            try:
                process = subprocess.Popen(
                    command,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    cwd=str(self.root),
                    env=self._model_environment(normalized_source),
                    creationflags=_hidden_process_flags(),
                )
            except Exception:
                log.close()
                raise
            with self._lock:
                self._worker = process
                self._worker_log_handle = log
                self._worker_url = url
                self._worker_source = normalized_source
            deadline = time.monotonic() + max(10.0, float(timeout))
            while time.monotonic() < deadline:
                if cancel_event and cancel_event.is_set():
                    self.stop()
                    raise RuntimeError("Operation cancelled by the user")
                if process.poll() is not None:
                    code = process.returncode
                    self.stop()
                    raise RuntimeError(f"Local MinerU worker exited with code {code}")
                if self._healthy(url):
                    return url
                time.sleep(.5)
            self.stop()
            raise RuntimeError("Local MinerU worker did not become ready before the timeout")

    def _close_worker_log(self) -> None:
        handle, self._worker_log_handle = self._worker_log_handle, None
        if handle:
            try:
                handle.close()
            except OSError:
                pass

    def stop(self) -> dict[str, Any]:
        with self._lock:
            process = self._worker
            self._worker = None
            self._worker_url = ""
            self._worker_source = ""
        if process and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            except OSError:
                pass
        with self._lock:
            self._close_worker_log()
        return self.status()

    def _assert_safe_root(self) -> None:
        if self.root.name.lower() != "mineru" or len(self.root.parts) < 3:
            raise RuntimeError("Refusing to remove an unexpected MinerU runtime path")

    def uninstall(self) -> dict[str, Any]:
        self.cancel_install()
        with self._lock:
            thread = self._install_thread
        if thread and thread.is_alive():
            thread.join(timeout=15)
        if thread and thread.is_alive():
            raise RuntimeError("MinerU installation is still stopping; try again shortly")
        self.stop()
        self._assert_safe_root()
        if self.root.exists():
            shutil.rmtree(self.root)
        self._set_status("not_installed", 0, "Local MinerU has been removed")
        return self.status()

    def close(self) -> None:
        self.cancel_install()
        self.stop()
