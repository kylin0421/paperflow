# Paper Flow Development Guide

[中文](DEVELOPMENT.md) | [Back to English README](../README_EN.md)

## Requirements

- 64-bit Windows 10 or Windows 11
- Python 3.13
- [uv](https://docs.astral.sh/uv/)
- Inno Setup for installer creation; the build script can obtain the WebView2 Bootstrapper

## Run from Source

```powershell
git clone https://github.com/kylin0421/paperflow.git
cd paperflow
uv sync --group dev
uv run paperflow-desktop
```

Browser development mode:

```powershell
uv run paperflow --host 127.0.0.1 --port 8765
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

The current suite covers settings migration, model routing, recommendation/profile caching, chat persistence, APIs, static pages, and native-window behavior.

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

- `.github/workflows/ci.yml` runs tests and quality checks.
- `.github/workflows/windows-release.yml` builds Windows artifacts.

Before a release, keep workflow versions aligned with Python, uv, PyInstaller, and the lockfile, then validate both installer and portable packages in a clean environment.

## Release Checklist

- [x] Native Windows window without launching an external browser.
- [x] Per-user installation and uninstall.
- [x] WebView2 Runtime preparation.
- [x] Single instance, native folder selection, and local data directory.
- [x] Chinese/English UI and README plus dark mode.
- [x] Legacy Zotero, email, bioRxiv/medRxiv, and training dependencies removed.
- [x] PyMuPDF layout/ONNX resources included in the directory build.
- [x] Automated tests and packaging script.
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
