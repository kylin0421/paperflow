# Paper Flow

[简体中文](README.md) | [English](README_EN.md)

<img src="branding/paperflow.svg" alt="Paper Flow" width="96">

Paper Flow is a local-first Windows application for discovering arXiv papers. It learns an initial research profile from a local PDF library, then continuously adapts to **Interested / Okay / Not interested** feedback.

Current version: **v0.0.0 pre-release**

## Features

- Retrieves recent papers from selected arXiv categories and displays their arXiv publication time.
- Uses title, abstract, categories, and other metadata for initial recommendations; full papers are not downloaded at this stage.
- **Interested / Okay / Not interested** only records a preference. It never opens a PDF, downloads a paper, or calls the LLM, and the rating can be changed later.
- Paper actions are separate: **Open original PDF** and **Chat with this paper** do not silently alter feedback.
- Paper chat starts with the default prompt “Give me a detailed explanation of this paper's method,” but supports free follow-up questions about experiments, equations, limitations, or any detail.
- Paper chat runs in a separate native window that can be moved, resized, and minimized, with persistent conversation history in the left sidebar.
- Semantic screening, recommendation summaries, interest profiling, and paper chat can use different models supported by the configured base URL.
- Real progress reports show arXiv requests, interest filtering, LLM screening, summary generation, and saving stages.
- Generates fine-grained LLM research topics instead of treating broad arXiv categories as the user's interests.
- Supports direct addition and removal of arbitrary preferred and avoided research directions. Manual labels receive the highest ranking weight.
- Provides complete recommendation history and local keyword/natural-language search over previously shown papers.
- Caches PDF parsing, summaries, translations, topic labels, and interest profiles locally.
- Chinese and English UI, summaries, reasons, settings, history, and dark mode.
- Stores settings, feedback, history, API credentials, and application data in a local SQLite database.

## Windows Installation

### Installer

1. Download `PaperFlow-Setup.exe` from Releases.
2. Run the installer and optionally create a desktop shortcut.
3. Start Paper Flow.
4. Select a local PDF folder and enter an API key, base URL, and model compatible with the OpenAI Chat Completions API.

The installer is per-user and does not require administrator privileges. It prepares Microsoft Edge WebView2 Runtime when necessary. Uninstalling the program does not delete personal data under `%LOCALAPPDATA%\Paper Flow`.

> v0.0.0 is not commercially code-signed. Windows SmartScreen may show an “Unknown publisher” warning.

### Portable build

Extract the complete `PaperFlow-portable.zip` and run `PaperFlow.exe`. Do not copy the executable by itself: the adjacent `_internal` directory contains required runtime components.

### Requirements

- 64-bit Windows 10 or Windows 11.
- Network access to arXiv and the configured LLM API.
- A local folder containing PDF research papers.

## First Run

Two settings are required:

1. **Local paper library**: Paper Flow scans PDFs in the selected folder without modifying them and uses their opening content to establish initial interests.
2. **LLM API key**: used for metadata TL;DRs, semantic interest profiles, reranking, translation, and on-demand paper chat.

Advanced settings include the download folder, arXiv categories, final recommendation batch size, maximum lookback window, API base URL, four task-specific models, and language.

Every model name must be supported by the configured base URL. When summary generation fails, Paper Flow preserves and displays the original abstract. Existing installations with one legacy model automatically inherit that value for all four model slots until the user saves specialized choices.

### Task-specific model configuration

| Setting | Responsibility | Boundary |
| --- | --- | --- |
| Semantic screening model | Interest probability and reject decisions for arXiv candidates | Independent from generation; can use a model optimized for relevance judgment |
| Recommendation summary model | Metadata TL;DRs, recommendation reasons, fine-grained topics, and translation of cached recommendation copy | These outputs share one structured recommendation-content pipeline |
| Interest profile model | Background synthesis of local papers, feedback, and manual labels into canonical interests | Independently cached and refreshed |
| Paper chat model | Multi-turn, full-paper question answering | Has the largest context and can use a stronger dedicated model |

## Recommendation Architecture

Paper Flow adapts the common industrial **candidate generation → scoring → reranking** architecture to a local, single-user, cold-start research workflow.

1. **Paginated arXiv retrieval**: broad arXiv categories constrain the search space but are not treated as user interests. The user setting controls the final recommendation batch. Internally, Paper Flow reads arXiv pages of 200 records and processes retrieval/reranking blocks of `max(final batch × 3, 60)`. If too few candidates pass the quality threshold, it continues at offsets `200/400/...` without replaying earlier pages.
2. **Weighted multi-prototype retrieval**: TF-IDF n-gram representations preserve multiple research interests rather than averaging everything into one diluted centroid. Local papers, learned semantic directions, explicit feedback, and manual labels have different weights. Manual labels use `2.5`, Interested papers `1.8`, Okay papers `0.45`, and learned positive directions `1.8`; learned and manual negative directions receive strong negative weights.
3. **Precision-focused LLM reranking**: the LLM receives a small metadata-only pool plus the cached semantic profile, recent real positive and negative examples, and manual high-weight labels. It returns an interest probability and an explicit reject decision. A candidate must score at least `0.58` and avoid rejected directions. The system continues retrieving until the configured final batch is full or the lookback window is genuinely exhausted.
4. **Freshness and diversity**: recent papers receive a small boost. Maximal Marginal Relevance-style selection reduces near-duplicate papers within the final batch.
5. **Explicit feedback loop**: papers are consumed only after an explicit rating. Unrated papers may appear again; rated papers are excluded from future recommendations. Ratings are fully decoupled from PDF and chat actions.

This design is informed by:

- [Google Recommendation Systems Overview](https://developers.google.com/machine-learning/recommendation/overview/types)
- [Deep Neural Networks for YouTube Recommendations](https://research.google.com/pubs/archive/45530.pdf)
- [The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries](https://aclanthology.org/X98-1025.pdf)
- [Context-Aware Hierarchical Taxonomy Generation for Scientific Papers via LLM-Guided Multi-Aspect Clustering](https://aclanthology.org/2025.emnlp-main.788/)

Paper Flow is an engineering adaptation for a local single-user paper stream; it does not claim to reproduce the training scale or complete models of those systems.

## Semantic Interest Profile and Topics

The interest profile is generated by an LLM from truncated local-paper openings, real feedback, and manual labels. It produces a concise summary plus canonical research directions while filtering document artifacts such as `et al`, `omitted picture`, and isolated generic words.

Profile refreshes are event-driven and run in the background when the application starts or when the library, feedback, settings, or manual interests change. Opening the analytics panel only reads the SQLite cache and does not wait for an LLM call.

Each recommended paper receives one to three fine-grained topic labels, such as `self-supervised vision foundation models` or `test-time adaptation for vision foundation models`. The existing taxonomy is supplied to the LLM, and local normalization merges casing, punctuation, hyphenation, singular/plural, and word-order variants.

## History Search

The History & Search panel lists all previously recommended papers. Local search indexes titles, abstracts, metadata TL;DRs, legacy detailed TL;DRs, and fine-grained topics. Paper-chat history is available separately in the chat window sidebar. Neither history is sent to an external search service.

## Chat with a Paper

Chat opens in a separate native window that behaves like a normal Windows window: it can be moved, resized, minimized, and restored. Persistent paper conversations appear in the left sidebar, while the selected thread remains on the right. The paper is downloaded and parsed only after the user sends the first question. The default question covers the former detailed-TL;DR workflow, while the general system prompt follows the user's actual request and can explain methods, experiments, equations, assumptions, comparisons, or limitations without forcing a fixed summary template. Opening chat, switching history, or opening the PDF never changes the interest rating.

## Data and Privacy

Desktop database location:

```text
%LOCALAPPDATA%\Paper Flow\state.db
```

- The API key remains in the local database and is never sent to the project author.
- To build the initial semantic profile, truncated opening text from at most 12 local PDFs is sent to the user-configured LLM API. The result is cached.
- Longer full-paper content is sent only when the user explicitly sends a question through **Chat with this paper**.
- Paper-chat threads and messages are persisted in local SQLite. Browsing the left history sidebar does not call the LLM.
- Initial recommendations and semantic reranking send arXiv metadata only.
- Language changes translate cached generated text without resending paper source content.
- Clearing recommendation history and clearing the local PDF parsing cache are independent operations and never delete PDF files from disk.

On first desktop launch, an old development database at `~/.arxiv-daily/state.db` is copied to the new location only when the destination database does not yet exist.

## Run from Source

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/).

```powershell
git clone <repository-url> paperflow
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

The script generates the icon, synchronizes dependencies, builds the PyInstaller directory distribution, verifies the Microsoft-signed WebView2 bootstrapper, creates a portable archive, and uses Inno Setup when available.

Primary outputs:

```text
dist\PaperFlow\PaperFlow.exe
dist\PaperFlow-portable.zip
dist\installer\PaperFlow-Setup.exe
```

Run tests:

```powershell
uv run pytest
```

## Android Plan

The planned standalone Android app will use Kotlin and Jetpack Compose, Android Keystore for API credentials, native arXiv/LLM networking, Storage Access Framework for PDF access, WorkManager for scheduled updates, and an on-device rewrite of the lightweight retrieval logic. Browsing and cached content should remain available offline; arXiv updates and LLM generation require network access.

## Project Origin

Paper Flow is developed from [TideDra/zotero-arxiv-daily](https://github.com/TideDra/zotero-arxiv-daily). It retains inspiration and selected capabilities around arXiv, LLMs, and paper parsing, while removing Zotero, email delivery, bioRxiv/medRxiv, and the original GitHub Actions workflow in favor of a local interactive desktop application.

## License

AGPL-3.0-or-later. See [LICENSE](LICENSE).
