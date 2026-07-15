import json

from paperflow.mineru_runtime import MINERU_PACKAGE, ManagedMinerURuntime, bundled_uv_path


def _installed_runtime(tmp_path):
    uv = tmp_path / "uv.exe"
    uv.write_bytes(b"uv")
    runtime = ManagedMinerURuntime(tmp_path / "runtimes" / "mineru", uv)
    runtime.python_executable.parent.mkdir(parents=True)
    runtime.python_executable.write_bytes(b"python")
    runtime.api_executable.write_bytes(b"mineru-api")
    runtime.marker.write_text(json.dumps({
        "version": "3.4.4", "python_version": "3.12", "disk_bytes": 1234,
    }), encoding="utf-8")
    return runtime


def test_bundled_uv_honors_explicit_override(tmp_path, monkeypatch):
    uv = tmp_path / "custom-uv.exe"
    uv.write_bytes(b"uv")
    monkeypatch.setenv("PAPERFLOW_UV", str(uv))

    assert bundled_uv_path() == uv


def test_managed_install_uses_isolated_python_and_pipeline_extra(tmp_path, monkeypatch):
    uv = tmp_path / "uv.exe"
    uv.write_bytes(b"uv")
    runtime = ManagedMinerURuntime(tmp_path / "runtimes" / "mineru", uv)
    commands = []

    def run(command, log, environment):
        commands.append((command, environment))
        if command[1] == "venv":
            runtime.python_executable.parent.mkdir(parents=True, exist_ok=True)
            runtime.python_executable.write_bytes(b"python")
        if command[1:3] == ["pip", "install"]:
            runtime.api_executable.write_bytes(b"mineru-api")

    monkeypatch.setattr(runtime, "_run_install_command", run)
    runtime._repair_requested = True
    runtime._install_worker()

    status = runtime.status()
    assert status["installed"] is True
    assert status["version"] == "3.4.4"
    assert commands[0][0][1:] == ["python", "install", "3.12"]
    assert commands[1][0][1:4] == ["venv", "--python", "3.12"]
    assert commands[2][0][-1] == MINERU_PACKAGE
    assert commands[2][0][-3:-1] == ["--reinstall-package", "mineru"]
    assert commands[2][1]["UV_PYTHON_INSTALL_DIR"] == str(runtime.python_dir)


def test_worker_is_started_once_reused_and_stopped(tmp_path, monkeypatch):
    runtime = _installed_runtime(tmp_path)
    calls = []

    class Process:
        def __init__(self, command, **kwargs):
            calls.append((command, kwargs))
            self.pid = 321
            self.returncode = None

        def poll(self):
            return self.returncode

        def terminate(self):
            self.returncode = 0

        def wait(self, timeout=None):
            return self.returncode

        def kill(self):
            self.returncode = -9

    monkeypatch.setattr("paperflow.mineru_runtime.subprocess.Popen", Process)
    monkeypatch.setattr(runtime, "_free_port", lambda: 43210)
    monkeypatch.setattr(runtime, "_healthy", lambda url, timeout=2: True)

    first = runtime.ensure_running(model_source="modelscope")
    second = runtime.ensure_running(model_source="modelscope")

    assert first == second == "http://127.0.0.1:43210"
    assert len(calls) == 1
    assert calls[0][0][-4:] == ["--host", "127.0.0.1", "--port", "43210"]
    assert calls[0][1]["env"]["MINERU_MODEL_SOURCE"] == "modelscope"
    assert calls[0][1]["env"]["HF_HOME"].startswith(str(runtime.models_dir))
    assert calls[0][1]["env"]["MODELSCOPE_CACHE"].startswith(str(runtime.models_dir))
    assert runtime.status()["running"] is True
    assert runtime.stop()["running"] is False


def test_uninstall_removes_only_the_managed_runtime_root(tmp_path):
    runtime = _installed_runtime(tmp_path)
    sibling = runtime.root.parent / "keep.txt"
    sibling.write_text("keep", encoding="utf-8")

    status = runtime.uninstall()

    assert status["installed"] is False
    assert not runtime.root.exists()
    assert sibling.read_text(encoding="utf-8") == "keep"
