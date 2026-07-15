# MinerU and Long-PDF Chat

[English](MINERU_EN.md) | [中文](MINERU.md) | [README](../README.md)

## Managed local runtime

Paper Flow 0.1.1 can install and supervise [MinerU](https://github.com/opendatalab/MinerU) locally. Users do not need to create a virtual environment, choose a port, start `mineru-api`, or enter an API URL.

The Windows application bundles `uv`. When **Install local MinerU** is selected, Paper Flow:

1. creates an application-owned Python 3.12 installation under the Paper Flow data directory;
2. creates an isolated virtual environment;
3. installs the pinned `mineru[pipeline]` package;
4. verifies the installation and records its version and disk use.

MinerU and its models are optional on-demand downloads and are not embedded in `PaperFlow.exe`. The main application remains Python 3.13 and its lightweight PyMuPDF parser remains available at all times. Source deployments use `uv` from `PATH`.

## Worker lifecycle

The managed Worker is lazy: installation alone does not keep a background service running. Paper Flow starts `mineru-api` on an unused loopback-only port when the first paper needs parsing or when **Start & test** is selected.

- The port and URL are private implementation details and require no user configuration.
- One Worker is reused across papers so model initialization is not repeated.
- A stopped or crashed Worker is restarted on the next request.
- Changing the model source restarts the Worker with the new environment.
- **Stop worker**, cancellation, application exit, and uninstall terminate the child process.
- Installation logs and Worker logs remain inside the managed runtime directory for diagnostics.

The Settings panel reports installation phase, progress, version, Python version, disk use, Worker state, and actionable errors. **Repair / update** reruns the pinned installation, while **Uninstall** removes only the managed MinerU runtime and downloaded models.

## Modes and fallback

Advanced Settings provide two MinerU deployment modes:

- **Managed locally** (default): Paper Flow owns the Python 3.12 runtime and localhost Worker.
- **Remote service**: advanced users can still provide an independently managed MinerU 3.x API URL.

PDF parser behavior remains explicit:

- **Auto** uses managed MinerU when installed, or the configured remote service, and falls back to PyMuPDF after startup, health, timeout, or parse failures.
- **MinerU** requires the selected MinerU deployment and surfaces failures.
- **PyMuPDF** never starts or contacts MinerU.

The Worker startup timeout and parsing timeout are stored as `mineru_worker_startup_seconds` and `mineru_timeout_seconds`. Parsed results are cached by paper ID and PDF SHA-256 fingerprint.

## Parsing and context strategy

Paper Flow checks `GET /health`, submits the PDF to MinerU's synchronous `POST /file_parse`, and requests Markdown plus the content list. It then uses structure-aware context selection instead of arbitrary fixed-size RAG chunks:

- short papers keep the full Markdown and document map;
- long papers are split at real headings;
- question similarity selects complete sections and adjacent sections;
- abstract, method, objective, experiments, results, limitations, and conclusion are anchor candidates;
- selected evidence is labelled `[S1]`, `[S2]`, and so on for citations in Paper Chat.

The MinerU content list is cached for future page/table/figure-level evidence work; v0.1.1 context selection primarily consumes the reconstructed Markdown.

## Privacy and resource use

Managed mode binds only to `127.0.0.1`, so PDFs stay on the computer. Remote mode sends the full PDF to the configured operator. The optional installation and models may use several GB and the first parse may download models; the UI asks for confirmation before installation.
