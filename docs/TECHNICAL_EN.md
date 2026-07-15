# Paper Flow Technical Architecture

[English](TECHNICAL_EN.md) | [中文](TECHNICAL.md) | [README](../README.md)

## System boundary

Paper Flow is a single-user, local-first system. SQLite is the source of truth; arXiv is the paper source; all LLM calls use the endpoint and task-specific models configured by the user.

```text
Local PDFs + ratings + manual labels
                 │
                 ▼
       fine-grained interest profile
                 │
arXiv cache ──► hybrid retrieval ──► LLM screening ──► quota/MMR ──► feed
                                                                    │
PDF behavior ──► PyMuPDF or MinerU ──► structured sections ──► evidence chat
```

Ratings and behaviors are deliberately separate. Ratings train recommendation; opening a PDF and sending chat questions do not implicitly change preference.

## Recommendation v2

### Candidate service

The background candidate service caches newest-first arXiv metadata by category query. Recommendation requests consume the cache first and continue network pagination only when the final batch is still short.

Three settings have different meanings:

- `batch_size`: final papers shown to the user;
- `retrieval_batch_size`: candidates ranked together in one local/LLM screening group;
- `max_candidates`: maximum scanned before declaring that the current lookback has no more qualified papers.

The arXiv page size is independently configurable. HTTP failures update persistent `failure_count` and `next_retry_at` state with exponential backoff, so restarting or clicking repeatedly cannot cause a tight 429 loop. Background-job status is also persisted.

### Interest evidence

Recommendation uses several independent prototypes instead of one averaged user vector:

| Evidence | Base weight | Behavior |
| --- | ---: | --- |
| Manual preferred/avoided direction | 2.5 | Highest priority, no decay |
| LLM-learned positive direction | 1.8 | Cached semantic profile |
| LLM-learned negative direction | 2.1 | Strong exclusion evidence |
| Interested paper | 1.8 | Time-decayed |
| Okay paper | 0.45 | Weak, time-decayed |
| Not-interested paper | 1.8 negative | Time-decayed |
| Local PDF opening text | 0.45–0.55 | Cold-start seed |

Behavioral feedback uses configurable exponential half-life with a floor, allowing recent preference changes to matter without erasing long-term history. Manual directions never decay.

### Hybrid retrieval

The first channel is word TF-IDF over title and abstract with unigram/bigram features. It rewards the top matching positive prototypes and subtracts strong negative matches.

The second channel is character n-gram TF-IDF, which is robust to hyphenation, inflection, abbreviations, and reordered technical phrases. Users can optionally configure an embedding model; embedding cosine similarity replaces the character channel when available and silently falls back locally on failure.

Normalized channels are blended before semantic screening. A small publication-time term only breaks close relevance ties.

### LLM semantic screening and calibration

The reranker receives metadata for only the local retrieval pool plus:

- learned fine-grained positive and negative directions;
- high-weight manual directions;
- recent positive, neutral, and negative examples;
- local-library topic cues.

For each candidate it returns an interest probability, explicit reject flag, concrete reason, and matched canonical interest. Generic overlap such as “vision” or “learning” is insufficient.

After at least eight rated recommendations, Paper Flow sweeps thresholds against real feedback and selects the best precision/recall/negative-utility trade-off. Until then it uses the configured default.

### Precision, balanced, and explore modes

- **Precision** raises the semantic floor and has almost no exploration budget.
- **Balanced** uses the calibrated threshold with a modest adjacent-interest reserve.
- **Explore** lowers the adjacent-interest floor, reserves more exploration positions, and tightens the per-topic cap.

Final selection limits dominance by one matched interest, reserves mode-specific exploration positions, and applies MMR-style similarity penalties. This follows the mature “retrieval → ranking → post-ranking constraints” pattern used by large recommenders, adapted to a private cold-start stream rather than attempting to reproduce their scale.

## Fine-grained interest taxonomy

The interest-profile model creates concepts such as `self-supervised vision foundation models` and `test-time adaptation for vision foundation models`, not `cs.CV`.

Existing canonical labels are included in generation. New labels are locally normalized for punctuation, casing, singular/plural forms, token overlap, and edit similarity; semantic equivalents reuse the existing label. The result is cached and refreshed in a coalesced background job when PDFs, feedback, manual directions, or relevant model settings change. There is no three-label cap.

## Diagnostics and offline evaluation

Every recommendation run stores:

- safe settings snapshot (never credentials or base URL);
- retrieval, character/embedding, LLM, and final scores;
- arXiv source offset, rejection flag/reason, matched interest, exploration flag;
- final selection state and position;
- candidate, selected, and LLM-call counts.

Later feedback is joined to these decisions to calculate interest rate, dislike rate, empty-batch rate, average scanned candidates, and topic coverage. The analytics UI exposes recent decision paths, making algorithm changes measurable instead of subjective.

## Long-PDF chat

Paper chat stores independent threads and uses a general research-assistant prompt. The default user prompt asks for a detailed method explanation, while any follow-up about equations, results, limitations, or specific details is allowed.

PDF parsing is cached by SHA-256 fingerprint:

1. `auto` uses the managed MinerU Worker when installed, or a configured remote service, with PyMuPDF fallback.
2. `mineru` requires the selected local/remote MinerU deployment and surfaces errors.
3. `pymupdf` always uses the lightweight local parser.

The managed runtime is isolated from the Python 3.13 application. Bundled `uv` creates an application-owned Python 3.12 environment and installs the pinned CPU pipeline on demand. A loopback-only Worker is started lazily, reused across papers, restarted after failure, and stopped on cancellation or application exit. This keeps the base localhost deployment light while removing manual API setup for Windows users.

Short papers preserve the complete structured Markdown. Long papers first produce a document map, then select coherent heading-level sections with adjacent context and method/result/limitation anchors. The selected sections receive stable evidence IDs such as `[S4]`; answers are instructed to cite them and the UI shows their headings. This avoids both naive full-text truncation and tiny-fragment RAG. See [MinerU and long-PDF chat](MINERU_EN.md).

## LLM task boundaries

| Model setting | Responsibility |
| --- | --- |
| Semantic screening | Candidate relevance, rejection, matched interest |
| Recommendation summary | Metadata TL;DR, reasons, topic labels, translation |
| Interest profile | Background fine-grained profile synthesis |
| Paper chat | Structured full-paper multi-turn answers |
| Embedding (optional) | Hybrid semantic retrieval |

Legacy installations inherit the shared model until a specialized value is saved. Requests use configurable timeouts and retries. JSON generation receives one syntax-repair attempt before a safe fallback.

## Storage, security, and recovery

Schema version 3 includes settings, encrypted secrets, papers, batches, diagnostics, candidate cache, source state, local/parsed documents, activity, chats, and background jobs.

- API keys are never stored in the settings table. Windows uses user-bound DPAPI; other systems use Fernet with a per-installation key file.
- A one-time migration encrypts and vacuums legacy plaintext keys.
- SQLite uses WAL, a busy timeout, serialized writes, startup interruption recovery, integrity-checked backups, and validated restore.
- Recommendation diagnostics remove credentials and the private base URL.
- Full-paper content is sent only after an explicit chat question; recommendations use arXiv metadata.
- Language changes translate cached generated copy without resending source papers.

Long operations report concrete stages and can be cancelled between network/model steps.

## Design references

- [Google: Recommendation systems overview](https://developers.google.com/machine-learning/recommendation/overview/types)
- [Covington et al.: Deep Neural Networks for YouTube Recommendations](https://research.google.com/pubs/archive/45530.pdf)
- [Carbonell and Goldstein: MMR diversity reranking](https://aclanthology.org/X98-1025.pdf)
- [MinerU](https://github.com/opendatalab/MinerU)

Paper Flow is an engineering adaptation for a local research workflow and does not claim to reproduce any commercial system's complete models or scale.
