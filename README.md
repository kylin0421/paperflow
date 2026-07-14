# Paper Flow

[English](README.md) | [简体中文](README_ZH.md)

<img src="branding/paperflow.svg" alt="Paper Flow" width="96">

Paper Flow is a local-first Windows application for discovering arXiv papers. It learns from a local PDF library and explicit feedback, combining lightweight local retrieval with LLM semantic screening.

Current version: **v0.0.0 pre-release**

## Highlights

- Discovers papers by arXiv publication time and automatically retrieves more pages when the candidate pool is insufficient.
- **Interested / Okay / Not interested** records preference only and is fully decoupled from PDF and chat actions.
- Builds fine-grained LLM interest directions with semantic label merging instead of treating broad arXiv categories as interests.
- Supports freely editable, high-weight preferred and avoided directions plus natural-language search over recommendation history.
- Provides a separate movable, resizable, and minimizable paper-chat window with history and free-form follow-up questions.
- Allows separate models for semantic screening, recommendation summaries, interest profiling, and paper chat.
- Reports real retrieval, screening, generation, and saving progress with Chinese/English UI and dark mode.
- Caches PDF parsing, recommendation copy, interest profiles, and chat history locally.

See the [technical guide](docs/TECHNICAL_EN.md) for recommendation architecture, model boundaries, topic merging, caching, and privacy details.

## Windows Installation

### Installer

1. Download `PaperFlow-Setup.exe` from Releases.
2. Run the installer and start Paper Flow.
3. Select a local PDF folder and enter an API key, base URL, and model names compatible with the OpenAI Chat Completions API.

The per-user installer does not require administrator privileges and prepares Microsoft Edge WebView2 Runtime when necessary. Uninstalling does not delete the personal database under `%LOCALAPPDATA%\Paper Flow`.

> This pre-release is not commercially code-signed, so Windows SmartScreen may show an “Unknown publisher” warning.

### Portable build

Extract the complete `PaperFlow-portable.zip` and run `PaperFlow.exe`. Do not copy the executable alone; the adjacent `_internal` folder contains required components.

Requirements: 64-bit Windows 10/11, network access to arXiv and the configured LLM API, and a local folder containing PDF papers.

## First Run

Basic settings are the local paper library and LLM API key. Advanced settings cover the download folder, arXiv categories, recommendation batch size, lookback window, API base URL, language, and four task-specific models.

Legacy single-model settings automatically populate all four model slots. Each model name must be supported by the configured base URL. Recommendations use arXiv metadata only; full-paper content is processed only after the user sends a paper-chat question.

## Run from Source

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/).

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

## Build Windows Packages

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1
```

Primary outputs:

```text
dist\PaperFlow\PaperFlow.exe
dist\PaperFlow-portable.zip
dist\installer\PaperFlow-Setup.exe
```

Tests: `uv run pytest`

See the [development guide](docs/DEVELOPMENT_EN.md) for complete build and release details.

## Data and Privacy

- The database is stored at `%LOCALAPPDATA%\Paper Flow\state.db`; API credentials, settings, feedback, and history remain local.
- Initial profiling sends truncated opening text from at most 12 local PDFs to the user-configured LLM and caches the result.
- Full-paper content is processed only after the user sends a chat question. Opening PDFs or switching chat history neither calls the LLM nor changes feedback.

See [Data, Caching, and Privacy](docs/TECHNICAL_EN.md#data-caching-and-privacy) for the complete boundary.

## Documentation

- [Technical guide: recommendation, LLMs, profiles, and privacy](docs/TECHNICAL_EN.md)
- [Development guide: running, packaging, release checks, and roadmap](docs/DEVELOPMENT_EN.md)
- [Changelog](CHANGELOG.md)

## Project Origin

Paper Flow is developed from [TideDra/zotero-arxiv-daily](https://github.com/TideDra/zotero-arxiv-daily). The current version removes Zotero, email delivery, bioRxiv/medRxiv, and the old scheduled workflow in favor of a local interactive desktop application.

## License

AGPL-3.0-or-later. See [LICENSE](LICENSE).
