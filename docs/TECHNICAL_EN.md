# Paper Flow Technical Guide

[English](TECHNICAL_EN.md) | [中文](TECHNICAL.md) | [Back to README](../README.md)

This document describes Paper Flow's recommendation architecture, LLM responsibilities, interest profiles, paper chat, caching, and privacy boundaries. See the [README](../README.md) for installation and the [development guide](DEVELOPMENT_EN.md) for packaging and release work.

## Recommendation Pipeline

Paper Flow uses a layered **candidate generation → local scoring → LLM semantic screening → diversity reranking** pipeline adapted to a local, single-user, cold-start workflow.

```text
Local PDFs + explicit feedback + manual labels
                       ↓
        Interest prototypes and semantic profile
                       ↓
Paginated arXiv → local retrieval → LLM screening → freshness/MMR → final batch
```

### 1. Paginated arXiv candidates

- Broad arXiv categories constrain the search space but are not treated as user interests.
- The user setting controls the final batch; each network page retrieves 200 candidates.
- Local retrieval/reranking blocks contain `max(final batch × 3, 60)` papers.
- When too few candidates pass, Paper Flow continues through the block and requests offsets `200/400/...` as necessary.
- Retrieval stops only when the final batch is full or the lookback window is genuinely exhausted.
- HTTP 429 responses use backoff and retry instead of tight repeated requests.

### 2. Weighted multi-interest retrieval

Titles and abstracts use TF-IDF n-gram representations. Multiple positive and negative prototypes preserve smaller interests that would be diluted by one averaged centroid.

| Source | Role | Weight |
| --- | --- | ---: |
| Manual preferred label | Strong positive prototype | `2.5` |
| Interested paper | Strong positive feedback | `1.8` |
| LLM-learned preferred direction | Positive prototype | `1.8` |
| Okay paper | Weak positive feedback | `0.45` |
| Not-interested paper | Negative prototype | Strong negative |
| Manual avoided label | Strong negative prototype | Strong negative |

Manual labels have the highest positive weight and accept arbitrary text without natural-language command parsing.

### 3. LLM semantic screening

The LLM receives only a small locally retrieved metadata pool together with the cached semantic profile, recent positive and negative examples, and manual labels. It returns an interest probability and explicit rejection decision.

A candidate must reach `0.58` and avoid rejected directions. Precision takes priority, so a final batch may remain smaller when the lookback window contains too few qualified papers. Timeouts, malformed structured output, or API failures fall back to local ranking.

### 4. Freshness and diversity

Recent papers receive a small boost. Maximal Marginal Relevance-style selection balances relevance against within-batch similarity to reduce near-duplicate results.

### 5. Explicit feedback loop

Interested, Okay, and Not interested immediately affect the next recommendation batch. A paper is consumed only after an explicit rating; unrated papers may appear again.

Feedback remains separate from behavior: opening PDFs, opening chat, sending questions, and switching chat history never change ratings automatically.

## Semantic Interests and Topic Taxonomy

### Interest profile

The LLM produces a concise profile and interpretable directions from:

- truncated opening text from at most 12 local PDFs;
- positive and negative recommendation feedback;
- manually maintained preferred and avoided labels.

Artifacts such as `et al`, `omitted picture`, and isolated generic words are filtered. Interest directions are not capped at three.

Refreshes run as coalesced background tasks when the application starts or when the library, feedback, model settings, or manual labels change. The analytics view reads SQLite cache only and does not wait for an LLM call.

### Fine-grained topics and semantic merging

Each recommendation receives one to three specific topics such as `self-supervised vision foundation models` or `test-time adaptation for vision foundation models`, rather than broad labels such as `cs.CV`.

Paper Flow maintains an incremental canonical taxonomy:

1. Existing frequent labels are supplied to the LLM so semantic equivalents reuse established terms.
2. New labels are created only for genuinely different research problems.
3. Local normalization merges casing, punctuation, hyphenation, singular/plural, and word-order variants.
4. Topic generation shares the metadata-summary request and never requires full-paper content.

## Four Model Roles

All calls use the user-configured OpenAI Chat Completions-compatible endpoint. Each model must be supported by that base URL.

| Setting | Responsibility | Boundary |
| --- | --- | --- |
| Semantic screening | Candidate interest probability and rejection | Independent from generation; may use a relevance-focused model |
| Recommendation summary | Metadata TL;DR, reasons, fine-grained topics, and cached-copy translation | One shared structured recommendation-content pipeline |
| Interest profile | Background synthesis of PDFs, feedback, and manual labels | Independently cached and refreshed |
| Paper chat | Multi-turn, full-paper question answering | Largest context; can use a dedicated stronger model |

Legacy single-model installations initially inherit that value for all four slots.

## Chat with Paper

Paper chat runs in a separate native window that can be moved, resized, minimized, and restored. Persistent conversations appear by recent activity in the left sidebar.

- The full paper is downloaded and parsed only after the first question is sent.
- The default question asks for a detailed explanation of the method.
- A general system prompt follows questions about methods, experiments, equations, assumptions, comparisons, or limitations.
- The latest 16 messages build multi-turn context.
- Switching history reads local data and does not call the LLM.
- Chat replaces the old fixed detailed-TL;DR action.

## History and Local Search

History & Search stores every recommended paper and locally indexes titles, abstracts, metadata TL;DRs, legacy detailed TL;DRs, and fine-grained topics. It accepts both keywords and descriptive natural-language queries. Paper-chat history remains separate in the chat sidebar.

Neither history is sent to an external search service.

## Data, Caching, and Privacy

Desktop database:

```text
%LOCALAPPDATA%\Paper Flow\state.db
```

- API credentials, settings, feedback, recommendations, profiles, and chats remain in local SQLite.
- Initial recommendation and semantic screening send arXiv metadata only.
- Profiling may send truncated openings from at most 12 local PDFs to the configured LLM; the result is cached.
- Full-paper content is processed and sent only after an explicit paper-chat question.
- Language changes translate cached summaries and reasons without resending source papers.
- Local PDF parsing is cached incrementally using file state.
- Recommendation-history and PDF-cache clearing are independent and never delete source PDFs.
- Uninstalling does not automatically delete the personal database.

On first desktop launch, `~/.arxiv-daily/state.db` is migrated only when the new destination database does not already exist.

## Resilience and Progress

- LLM JSON passes through cleanup, tolerant parsing, and structural validation.
- Summary failures preserve and display the original abstract.
- arXiv 429 responses use backoff; network retrieval pages are separate from the final recommendation batch.
- The UI reports real arXiv request, local filtering, LLM screening, generation, download, extraction, and saving stages.
- Generated summaries, reasons, translations, topics, and profiles are cached to avoid repeated token use.

## Design References

- [Google Recommendation Systems Overview](https://developers.google.com/machine-learning/recommendation/overview/types)
- [Deep Neural Networks for YouTube Recommendations](https://research.google.com/pubs/archive/45530.pdf)
- [The Use of MMR, Diversity-Based Reranking for Reordering Documents and Producing Summaries](https://aclanthology.org/X98-1025.pdf)
- [Context-Aware Hierarchical Taxonomy Generation for Scientific Papers via LLM-Guided Multi-Aspect Clustering](https://aclanthology.org/2025.emnlp-main.788/)

Paper Flow is an engineering adaptation for a single-user paper stream; it does not claim to reproduce the scale or complete models of commercial recommenders.
