# MinerU and Long-PDF Chat

[English](MINERU_EN.md) | [中文](MINERU.md) | [README](../README.md)

## Why it is optional

[MinerU](https://github.com/opendatalab/MinerU) is designed to reconstruct scientific PDF structure, including reading order, formulas, tables, OCR, and multi-column layouts. That is valuable for paper chat, but its complete local runtime is much heavier than Paper Flow and has different Windows/Python constraints.

Paper Flow therefore treats MinerU as an external parsing service. The lightweight installation remains Python 3.13 with PyMuPDF; a MinerU environment can use the versions and accelerators recommended by MinerU itself.

## Connection

Install and start MinerU's `mineru-api` by following the upstream documentation. A typical service is reachable at:

```text
http://127.0.0.1:8000
```

In Paper Flow Advanced Settings:

1. Set **PDF parser** to **Auto** for MinerU with PyMuPDF fallback, or **MinerU** to require it.
2. Set **MinerU API URL** to the service root.
3. Save, then use **Test MinerU** under Connection Tests.

Paper Flow checks `GET /health` and submits the PDF to MinerU 3.x's synchronous `POST /file_parse` endpoint with Markdown and content-list output enabled. Parsed Markdown is cached by paper ID and PDF SHA-256 fingerprint.

## Context strategy

Paper Flow does not split a paper into arbitrary fixed-size chunks:

- Short papers keep the full Markdown and a document map.
- Long papers are split at real headings.
- Question similarity selects full sections; adjacent sections preserve local argument flow.
- Abstract, method, objective, experiments, results, limitations, and conclusion headings are anchor candidates.
- The model sees a complete section map plus selected evidence labelled `[S1]`, `[S2]`, and so on.
- Answers are instructed to cite those IDs; the chat UI shows evidence headings.

This structure-aware approach is intended for relatively small collections of individually long, irregular papers. It prioritizes continuity and inspectable evidence over vector-database scale.

## Failure behavior

- **Auto**: health, network, timeout, or parse failures fall back to local PyMuPDF.
- **MinerU**: failures are shown to the user; no silent parser change occurs.
- **PyMuPDF**: MinerU is never contacted.

The MinerU request timeout is configurable in SQLite settings (`mineru_timeout_seconds`, default 900 seconds). Reopening the same unchanged PDF uses the local parse cache and does not call either parser again.

## Privacy

The PDF is sent to the configured MinerU URL only after the user sends a paper-chat question. When the service runs on localhost, the parse remains on the same machine. If a remote MinerU URL is configured, that operator receives the PDF; Paper Flow cannot enforce the remote service's retention policy.
