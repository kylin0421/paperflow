# Changelog

## 0.1.0 - 2026-07-14

First stable Paper Flow release.

### Added

- Hybrid recommendation v2 with word/character retrieval, optional embeddings, time-decayed feedback, calibrated LLM screening, multi-interest quotas, MMR, and three recommendation modes.
- Persistent arXiv candidate cache, independent retrieval/final batch settings, continued pagination, background refresh, and durable 429 backoff.
- Recommendation diagnostics, decision-path inspection, and feedback-based quality evaluation.
- Fine-grained LLM interest taxonomy, semantic label consolidation, background profile refresh, and unlimited manual preferred/avoided directions.
- Natural-language recommendation-history search and complete history view.
- Separate resizable paper-chat window with persistent history, Markdown rendering, evidence IDs, and coherent long-section selection.
- Optional external MinerU 3.x parsing with PyMuPDF fallback.
- Per-task LLM models, optional embedding model, bilingual UI, dark mode, granular progress, and cancellation.
- SQLite schema v3, encrypted API keys, legacy-secret migration, connection tests, integrity-checked backup/restore, and clean database lifecycle.
- Lightweight localhost deployment plus Windows installer and portable packages.

### Changed

- Ratings are fully separated from opening PDFs and chatting with papers.
- Detailed TL;DR became the default general paper-chat question and no longer forces a fixed summary flow.
- Recommendation and profile generation use robust JSON cleanup/repair and Markdown is rendered in the UI.
- English README is the default; detailed architecture, MinerU, and development material moved into `docs/`.
- Windows release workflow now creates versioned artifacts and a GitHub Release without rebuilding the portable archive twice.

### Fixed

- Bundled PyMuPDF layout resources for Windows distributions.
- Old `Candidate` payload compatibility, stale distribution confusion, nested analytics scrolling, label caps, 429 loops, and intermittent malformed-JSON summary failures.
