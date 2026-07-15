# Paper Flow Development Guide

[English](DEVELOPMENT_EN.md) | [中文](DEVELOPMENT.md) | [Back to README](../README.md)

## Requirements

- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- For the Windows package only: 64-bit Windows 10/11 and Inno Setup

## Run from Source

```powershell
git clone https://github.com/kylin0421/paperflow.git
cd paperflow
uv sync
uv run paperflow --host 127.0.0.1 --port 8765
```

Windows desktop mode:

```powershell
uv sync --extra desktop --group dev
uv run paperflow-desktop
```

Default desktop data directory:

```text
%LOCALAPPDATA%\Paper Flow
```

## Checks and Tests

```powershell
uv run pytest
uv run ruff check src tests
python -m compileall src tests
```

The suite covers secret/schema migration, backup/restore, recommendation calibration and caching, arXiv backoff, structured PDF context, model routing, chat persistence, static pages, and native-window behavior.

## Windows Build

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1
```

The script:

1. Generates deterministic Paper Flow icons.
2. Synchronizes minimal runtime and build dependencies.
3. Creates a PyInstaller directory distribution.
4. Collects dynamic PyMuPDF layout/ONNX resources.
5. Downloads and verifies the Microsoft-signed WebView2 Bootstrapper.
6. Creates a portable ZIP and, when Inno Setup is available, a per-user installer.

Primary outputs:

```text
dist\PaperFlow\PaperFlow.exe
dist\PaperFlow-portable.zip
dist\installer\PaperFlow-Setup.exe
```

Distribute the entire portable package. `PaperFlow.exe` depends on the adjacent `_internal` folder for Python, WebView, PyMuPDF, and other runtime components.

## GitHub Actions

- `.github/workflows/ci.yml` runs Ruff, compilation, tests, and coverage on every main push and pull request.
- `.github/workflows/windows-release.yml` builds Windows artifacts on `v*` tags and publishes them to a GitHub Release.

Before a release, keep workflow versions aligned with Python, uv, PyInstaller, and the lockfile, then validate both installer and portable packages in a clean environment.

## Release Checklist

- [x] Native Windows window without launching an external browser.
- [x] Per-user installation and uninstall.
- [x] WebView2 Runtime preparation.
- [x] Single instance, native folder selection, and local data directory.
- [x] Chinese/English UI and README plus dark mode.
- [x] Legacy Zotero, email, bioRxiv/medRxiv, and training dependencies removed.
- [x] PyMuPDF layout/ONNX resources included in the directory build.
- [x] Schema v3 migration, encrypted secrets, and backup/restore.
- [x] Optional managed-local MinerU runtime, remote mode, and lightweight fallback.
- [x] Automated tests and versioned GitHub release packaging.
- [ ] Authenticode code signing.
- [ ] Manual acceptance tests on clean Windows 10 and Windows 11 virtual machines.

## Database Compatibility

New settings should have defaults and preserve inheritance behavior when older databases lack specialized fields. The four current model settings inherit the legacy `model` value. Cache signatures must include the effective model and every input state that materially changes output.

Never commit API keys, real user databases, build directories, portable archives, or temporary installer downloads.

## Standalone Android Roadmap

The goal is an independent APK that does not require a desktop service:

1. Stabilize models for papers, feedback, interests, batches, analytics, and migrations.
2. Rebuild the cards, history, settings, analytics, dark mode, and bilingual UI with Kotlin and Jetpack Compose.
3. Store API credentials in Android Keystore and access arXiv and compatible OpenAI APIs natively.
4. Rewrite lightweight TF-IDF retrieval in Kotlin instead of shipping the full Python scientific stack.
5. Import PDFs with Storage Access Framework and cache by URI, size, modification time, and content fingerprint.
6. Validate extraction quality for two-column papers, equations, and scans; add a specialized parser only if necessary.
7. Use WorkManager for daily updates, retry, and notifications.
8. Complete signed APK/AAB packaging, database upgrades, crash recovery, and release testing.

Browsing, history, analytics, and cached content should remain available offline. arXiv updates and LLM generation still require network access.
