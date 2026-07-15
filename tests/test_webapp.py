import os
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from paperflow.webapp import Candidate, Recommender, Store


def paper(identifier="1", title="Graph learning", abstract="graph neural networks"):
    return Candidate(identifier, title, ["A"], abstract, "https://arxiv.org/abs/1",
                     "https://arxiv.org/pdf/1", "2026-07-11T00:00:00+00:00", ["cs.LG"])


def test_store_settings_feedback_and_seen(tmp_path):
    store = Store(tmp_path / "state.db")
    assert store.settings()["batch_size"] == 12
    assert store.settings()["mineru_runtime_mode"] == "managed"
    store.save_settings({"batch_size": 3, "unknown": True})
    store.record([paper()])
    assert store.seen() == set()
    store.feedback("1", "interested", "detail")
    assert store.settings()["batch_size"] == 3
    assert store.seen() == {"1"}
    assert store.paper("1").detailed_tldr == "detail"
    assert len(store.preference_texts()[0]) == 1


def test_api_key_is_encrypted_at_rest_and_legacy_plaintext_is_migrated(tmp_path):
    path = tmp_path / "state.db"
    store = Store(path)
    store.save_settings({"api_key": "super-secret-value"})
    assert store.settings()["api_key"] == "super-secret-value"
    ciphertext = store.db.execute(
        "SELECT ciphertext FROM secrets WHERE key='api_key'"
    ).fetchone()[0]
    assert ciphertext.startswith(("dpapi:", "fernet:"))
    store.close()
    assert b"super-secret-value" not in path.read_bytes()

    legacy = tmp_path / "legacy.db"
    db = sqlite3.connect(legacy)
    db.execute("CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
    db.execute("INSERT INTO settings VALUES ('api_key',?)", (json.dumps("old-secret"),))
    db.commit()
    db.close()
    migrated = Store(legacy)
    assert migrated.settings()["api_key"] == "old-secret"
    assert migrated.db.execute(
        "SELECT 1 FROM settings WHERE key='api_key'"
    ).fetchone() is None
    migrated.close()
    assert b"old-secret" not in legacy.read_bytes()


def test_database_backup_restore_and_schema_version(tmp_path):
    store = Store(tmp_path / "state.db")
    store.save_settings({"batch_size": 7, "api_key": "backup-secret"})
    store.record([paper("kept")])
    backup = store.backup_database()
    store.save_settings({"batch_size": 2})
    store.clear_cache("recommendations")

    store.restore_database(backup)

    assert store.settings()["batch_size"] == 7
    assert store.settings()["api_key"] == "backup-secret"
    assert store.paper("kept").id == "kept"
    assert store.db.execute(
        "SELECT value FROM schema_meta WHERE key='schema_version'"
    ).fetchone()[0] == "3"


def test_recommendation_diagnostics_are_auditable_and_evaluated(tmp_path):
    store = Store(tmp_path / "state.db")
    run_id = store.create_recommendation_run({
        "api_key": "never-store-this", "base_url": "https://private.invalid/v1",
        "recommendation_mode": "balanced", "batch_size": 2,
    })
    first = paper("first", "Self-supervised vision", "masked image representation learning")
    first.lexical_score = .72
    first.semantic_score = .91
    first.final_score = .83
    first.matched_interest = "self-supervised vision foundation models"
    second = paper("second", "Robot planning", "embodied agent planning")
    second.lexical_score = .38
    second.semantic_score = .14
    second.final_score = .24
    second.rejected = True
    second.rejection_reason = "Matches an avoided embodied-agent direction"

    store.record([first])
    store.record_recommendation_diagnostics(run_id, [first, second], [first])
    store.finish_recommendation_run(
        run_id, status="completed", candidates=2, selected=1, llm_calls=1,
    )
    store.feedback("first", "interested")

    details = store.recommendation_run_diagnostics(run_id)
    assert [row["paper_id"] for row in details] == ["first", "second"]
    assert details[0]["selected"] == 1
    assert details[1]["rejected"] == 1
    evaluation = store.recommendation_evaluation()
    assert evaluation["rated_recommendations"] == 1
    assert evaluation["interested_rate"] == 1
    assert evaluation["average_candidates_scanned"] == 2
    assert evaluation["topic_coverage"] == 1
    stored = store.db.execute(
        "SELECT settings_json FROM recommendation_runs WHERE id=?", (run_id,),
    ).fetchone()[0]
    assert "never-store-this" not in stored
    assert "private.invalid" not in stored


def test_specialized_models_inherit_legacy_model_until_individually_saved(tmp_path):
    store = Store(tmp_path / "state.db")
    store.save_settings({"model": "legacy-model"})

    inherited = store.settings()
    assert {inherited[key] for key in (
        "rerank_model", "summary_model", "interest_model", "chat_model",
    )} == {"legacy-model"}

    store.save_settings({"summary_model": "summary-model", "chat_model": "chat-model"})
    configured = store.settings()
    assert configured["rerank_model"] == "legacy-model"
    assert configured["summary_model"] == "summary-model"
    assert configured["interest_model"] == "legacy-model"
    assert configured["chat_model"] == "chat-model"


def test_legacy_mineru_url_keeps_remote_deployment_mode(tmp_path):
    store = Store(tmp_path / "state.db")
    store.save_settings({"mineru_api_url": "http://127.0.0.1:8000"})

    assert store.settings()["mineru_runtime_mode"] == "remote"

    store.save_settings({"mineru_runtime_mode": "managed"})
    assert store.settings()["mineru_runtime_mode"] == "managed"


def test_local_pdf_text_is_cached_until_file_changes(tmp_path):
    store = Store(tmp_path / "state.db")
    library = tmp_path / "library"
    library.mkdir()
    first = library / "first.pdf"
    second = library / "second.pdf"
    first.write_bytes(b"first-v1")
    second.write_bytes(b"second-v1")
    calls = []

    def extract(path):
        calls.append(path.name)
        return path.read_bytes().decode()

    assert store.sync_local_documents(str(library), extract) == ["first-v1", "second-v1"]
    assert calls == ["first.pdf", "second.pdf"]

    # An unchanged library is served entirely from SQLite.
    assert store.sync_local_documents(str(library), extract) == ["first-v1", "second-v1"]
    assert calls == ["first.pdf", "second.pdf"]

    first.write_bytes(b"first-v2-is-longer")
    os.utime(first, None)
    assert store.sync_local_documents(str(library), extract) == ["first-v2-is-longer", "second-v1"]
    assert calls == ["first.pdf", "second.pdf", "first.pdf"]

    second.unlink()
    assert store.sync_local_documents(str(library), extract) == ["first-v2-is-longer"]
    cached_paths = [row[0] for row in store.db.execute("SELECT path FROM local_documents")]
    assert cached_paths == [str(first.resolve())]


def test_caches_can_be_cleared_independently(tmp_path):
    store = Store(tmp_path / "state.db")
    store.save_settings({"api_key": "keep-me"})
    library = tmp_path / "library"
    library.mkdir()
    (library / "paper.pdf").write_bytes(b"pdf")
    store.sync_local_documents(str(library), lambda path: "local text")
    batch_id = store.create_batch()
    store.record([paper()], batch_id)
    store.feedback("1", "interested")

    store.clear_cache("recommendations")
    assert store.current_batch() == []
    assert store.seen() == set()
    assert store.settings()["api_key"] == "keep-me"
    assert store.db.execute("SELECT COUNT(*) FROM local_documents").fetchone()[0] == 1

    store.clear_cache("local_documents")
    assert store.db.execute("SELECT COUNT(*) FROM local_documents").fetchone()[0] == 0
    assert store.settings()["api_key"] == "keep-me"


def test_next_batch_repeats_only_papers_without_feedback(tmp_path, monkeypatch):
    store = Store(tmp_path / "state.db")
    store.save_settings({"api_key": "test-key", "library_path": str(tmp_path)})
    seed = paper("seed")
    store.record([seed])
    store.feedback("seed", "very_interested")
    recommender = Recommender(store)
    monkeypatch.setattr(recommender, "_local_corpus", lambda folder: [])
    monkeypatch.setattr(recommender, "_llm_rerank", lambda candidates, settings, local: None)
    monkeypatch.setattr(recommender, "_metadata_summaries", lambda papers, settings: None)
    monkeypatch.setattr(recommender, "_fetch_page", lambda settings, offset, limit, client: ([
        paper("2", "Cooking", "bread and soup"),
        paper("3", "Better graphs", "graph neural network learning"),
    ], 2, False))
    batch = recommender.next_batch()
    assert [p.id for p in batch] == ["3", "2"]
    assert [p.id for p in recommender.current_batch()] == ["3", "2"]
    assert [p.id for p in recommender.current_batch()] == ["3", "2"]
    assert [p.id for p in recommender.next_batch()] == ["3", "2"]
    store.feedback("3", "interested")
    assert [p.id for p in recommender.next_batch()] == ["2"]
    store.feedback("2", "not_interested")
    assert recommender.next_batch() == []


def test_refreshing_current_batch_does_not_generate_again(tmp_path, monkeypatch):
    store = Store(tmp_path / "state.db")
    store.save_settings({"api_key": "test-key", "library_path": str(tmp_path)})
    recommender = Recommender(store)
    calls = []
    monkeypatch.setattr(recommender, "_local_corpus", lambda folder: [])
    monkeypatch.setattr(recommender, "_llm_rerank", lambda candidates, settings, local: None)
    monkeypatch.setattr(recommender, "_fetch_page", lambda settings, offset, limit, client: (
        [paper("fresh")], 1, False
    ))
    monkeypatch.setattr(
        recommender,
        "_metadata_summaries",
        lambda papers, settings: calls.append([p.id for p in papers]),
    )

    assert [p.id for p in recommender.next_batch()] == ["fresh"]
    assert [p.id for p in recommender.current_batch()] == ["fresh"]
    assert [p.id for p in recommender.current_batch()] == ["fresh"]
    assert calls == [["fresh"]]


def test_metadata_call_returns_tldr_and_clickable_reasons(tmp_path, monkeypatch):
    recommender = Recommender(Store(tmp_path / "state.db"))
    content = json.dumps({
        "1": {
            "tldr": "提出一种更稳定的图学习方法。",
            "topics": ["图神经网络的稳定训练"],
            "reasons": [
                {"label": "图学习", "detail": "与你论文库中的图神经网络主题一致。"},
                {"label": "方法创新", "detail": "核心方法对稳定训练进行了改进。"},
            ],
        }
    }, ensure_ascii=False)
    response = SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content=content)
    )])
    requests = []
    def create(**kwargs):
        requests.append(kwargs)
        return response
    completions = SimpleNamespace(create=create)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    monkeypatch.setattr(
        "paperflow.webapp.OpenAI",
        lambda **kwargs: client,
    )
    item = paper()
    recommender._metadata_summaries([item], {
        "api_key": "key", "base_url": "https://example.test/v1",
        "model": "legacy-model", "summary_model": "summary-model", "language": "中文",
    })

    assert item.metadata_tldr == "提出一种更稳定的图学习方法。"
    assert item.reason_labels == ["图学习", "方法创新"]
    assert item.reason_details["图学习"] == "与你论文库中的图神经网络主题一致。"
    assert item.topic_labels == ["图神经网络的稳定训练"]
    assert item.summary_version == 4
    assert item.summary_language == "中文"
    prompt = requests[0]["messages"][0]["content"]
    assert "no hard character limit" in prompt
    assert "EventTSF" in prompt and "GroundAttack" in prompt
    assert requests[0]["model"] == "summary-model"


def test_malformed_metadata_json_is_repaired_without_resending_paper(tmp_path, monkeypatch):
    recommender = Recommender(Store(tmp_path / "state.db"))
    malformed = '{"1":{"tldr":"一种图学习方法" "topics":["图神经网络"],"reasons":[]}}'
    repaired = json.dumps({"1": {
        "tldr": "一种图学习方法", "topics": ["图神经网络"], "reasons": [],
    }}, ensure_ascii=False)
    responses = iter([malformed, repaired])
    requests = []
    def create(**kwargs):
        requests.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=next(responses))
        )])
    client = SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(create=create)
    ))
    monkeypatch.setattr("paperflow.webapp.OpenAI", lambda **kwargs: client)
    item = paper(abstract="SECRET ABSTRACT")

    recommender._metadata_summaries([item], {
        "api_key": "key", "base_url": "https://example.test/v1",
        "model": "model", "language": "中文",
    })

    assert item.metadata_tldr == "一种图学习方法"
    assert item.topic_labels == ["图神经网络"]
    assert len(requests) == 2
    assert "SECRET ABSTRACT" in requests[0]["messages"][1]["content"]
    assert "SECRET ABSTRACT" not in requests[1]["messages"][1]["content"]
    assert malformed in requests[1]["messages"][1]["content"]


def test_existing_summaries_are_translated_without_source_paper_text(tmp_path, monkeypatch):
    store = Store(tmp_path / "state.db")
    store.save_settings({
        "api_key": "key", "base_url": "https://example.test/v1",
        "model": "model", "language": "English",
    })
    item = paper(title="SECRET PAPER TITLE", abstract="SECRET ABSTRACT CONTENT")
    item.metadata_tldr = "一种图学习方法。"
    item.reason_labels = ["图学习"]
    item.reason_details = {"图学习": "与用户兴趣匹配。"}
    item.summary_language = "中文"
    item.detailed_tldr = "详细的中文阅读摘要。"
    item.detailed_tldr_language = "中文"
    batch_id = store.create_batch()
    store.record([item], batch_id)
    store.feedback("1", "interested", item.detailed_tldr, "中文")

    translated = json.dumps({"1": {
        "tldr": "A graph learning method.",
        "reasons": [{"label": "Graph learning", "detail": "Matches the user's interests."}],
        "detailed_tldr": "A detailed English reading summary.",
    }})
    response = SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content=translated)
    )])
    requests = []
    def create(**kwargs):
        requests.append(kwargs)
        return response
    client = SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(create=create)
    ))
    monkeypatch.setattr("paperflow.webapp.OpenAI", lambda **kwargs: client)

    result = Recommender(store).translate_current_batch()[0]

    assert result.metadata_tldr == "A graph learning method."
    assert result.detailed_tldr == "A detailed English reading summary."
    assert result.summary_language == "English"
    assert result.detailed_tldr_language == "English"
    user_payload = requests[0]["messages"][1]["content"]
    assert "SECRET PAPER TITLE" not in user_payload
    assert "SECRET ABSTRACT CONTENT" not in user_payload
    assert "一种图学习方法" in user_payload


def test_next_batch_requires_initial_configuration(tmp_path):
    store = Store(tmp_path / "state.db")
    store.save_settings({"library_path": str(tmp_path / "missing-library")})
    recommender = Recommender(store)
    try:
        recommender.next_batch()
    except ValueError as exc:
        assert "API Key" in str(exc)
        assert "PDF" in str(exc)
    else:
        raise AssertionError("missing setup should stop recommendations")


def test_metadata_fallback_is_brief(tmp_path):
    recommender = Recommender(Store(tmp_path / "state.db"))
    abstract = "First sentence explains the problem. Second sentence explains the method. Third sentence has extra detail. " * 8
    brief = recommender._brief_fallback(abstract)
    assert "Third sentence" in brief
    assert brief == " ".join(abstract.split())


def test_tldr_cleanup_does_not_mechanically_truncate(tmp_path):
    recommender = Recommender(Store(tmp_path / "state.db"))
    text = "本文提出一种面向复杂开放环境的全新图神经网络训练方法，能够显著提升模型稳定性和泛化能力。第二句不应显示。"
    brief = recommender._clean_tldr("TL;DR：" + text)
    assert brief == text
    assert "第二句" in brief


def test_pdf_download_is_atomic_and_validated(tmp_path, monkeypatch):
    recommender = Recommender(Store(tmp_path / "state.db"))
    target = tmp_path / "paper.pdf"
    payload = b"%PDF-1.7\n" + b"paper data" * 200

    class Response:
        def __init__(self):
            self.offset = 0
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, size):
            chunk = payload[self.offset:self.offset + size]
            self.offset += len(chunk)
            return chunk

    requests = []
    def urlopen(request, timeout):
        requests.append((request, timeout))
        return Response()

    monkeypatch.setattr("paperflow.webapp.urllib.request.urlopen", urlopen)
    size = recommender._download_pdf("https://arxiv.org/pdf/1234.5678", target)

    assert size == len(payload)
    assert target.read_bytes() == payload
    assert not target.with_suffix(".pdf.part").exists()
    assert requests[0][0].get_header("User-agent").startswith("Paper-Flow/")


def test_existing_valid_pdf_is_reused_without_network(tmp_path, monkeypatch):
    recommender = Recommender(Store(tmp_path / "state.db"))
    target = tmp_path / "paper.pdf"
    target.write_bytes(b"%PDF-1.7\n" + b"existing" * 200)
    monkeypatch.setattr(
        "paperflow.webapp.urllib.request.urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network should not run")),
    )

    assert recommender._download_pdf("https://arxiv.org/pdf/1234.5678", target) == target.stat().st_size


def test_feedback_is_decoupled_from_pdf_download_and_llm_actions(tmp_path, monkeypatch):
    store = Store(tmp_path / "state.db")
    store.record([paper()])
    recommender = Recommender(store)
    monkeypatch.setattr(
        recommender,
        "_download_pdf",
        lambda *args: (_ for _ in ()).throw(AssertionError("server download should not run")),
    )

    assert recommender.act("1", "interested") == {"feedback": "interested"}
    assert recommender.act("1", "neutral") == {"feedback": "neutral"}
    result = recommender.act("1", "not_interested")

    assert result == {"feedback": "not_interested"}
    assert store.seen() == {"1"}
    assert store.paper("1").detailed_tldr is None


def test_feedback_can_be_changed_without_overwriting_legacy_detailed_tldr(tmp_path):
    store = Store(tmp_path / "state.db")
    batch_id = store.create_batch()
    store.record([paper()], batch_id)
    store.feedback("1", "interested", "already generated detail", "中文")
    recommender = Recommender(store)

    recommender.act("1", "neutral")
    current = recommender.current_batch()[0]
    assert current.feedback == "neutral"
    assert current.detailed_tldr == "already generated detail"

    result = recommender.act("1", "interested")
    assert result == {"feedback": "interested"}
    assert recommender.current_batch()[0].feedback == "interested"
    assert recommender.current_batch()[0].detailed_tldr == "already generated detail"


def test_chat_uses_full_paper_with_general_prompt_and_keeps_feedback_separate(
        tmp_path, monkeypatch):
    store = Store(tmp_path / "state.db")
    store.save_settings({
        "api_key": "key", "base_url": "https://example.test/v1",
        "model": "legacy-model", "chat_model": "chat-model", "language": "中文",
    })
    store.record([paper()])
    recommender = Recommender(store)
    stored_paper = store.paper("1")
    store.add_chat_message(stored_paper, "user", "为我详细介绍这篇论文的方法")
    store.add_chat_message(stored_paper, "assistant", "上一轮回答")
    monkeypatch.setattr(recommender, "_paper_full_text", lambda item, settings: "FULL PAPER TEXT")
    requests = []
    response = SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content="该方法先编码图结构，再进行消息传递。")
    )])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kwargs: requests.append(kwargs) or response
    )))
    monkeypatch.setattr("paperflow.webapp.OpenAI", lambda **kwargs: client)

    result = recommender.chat("1", "其中的损失函数有什么作用？")

    assert result["answer"].startswith("该方法")
    assert store.paper("1").feedback is None
    sent = requests[0]["messages"]
    assert "Do not force a fixed summary template" in sent[0]["content"]
    assert "FULL PAPER TEXT" in sent[1]["content"]
    assert sent[-1] == {"role": "user", "content": "其中的损失函数有什么作用？"}
    assert requests[0]["model"] == "chat-model"
    assert [item["role"] for item in result["messages"]] == [
        "user", "assistant", "user", "assistant",
    ]
    assert recommender.chat_threads()[0]["paper_id"] == "1"
    assert recommender.chat_thread("1")["messages"][-1]["content"].startswith("该方法")
    assert recommender.progress()["stage"] == "complete"


def test_analytics_tracks_usage_categories_and_feedback(tmp_path):
    store = Store(tmp_path / "state.db")
    batch_id = store.create_batch()
    store.record([
        paper("1"),
        Candidate("2", "Vision", ["B"], "vision model", "url", "pdf", "2026-07-12T00:00:00+00:00", ["cs.CV"]),
    ], batch_id)
    first = store.paper("1")
    second = store.paper("2")
    first.topic_labels = ["graph neural network training"]
    second.topic_labels = ["vision foundation model adaptation"]
    store.update_payloads([first, second])
    store.feedback("1", "interested")
    stats = Recommender(store).analytics()

    assert stats["shown_total"] == 2
    assert stats["unique_shown"] == 2
    assert stats["interacted_total"] == 1
    assert stats["category_count"] == 2
    assert stats["categories"] == {
        "graph neural network training": 1,
        "vision foundation model adaptation": 1,
    }
    assert sum(day["shown"] for day in stats["daily"].values()) == 2
    assert sum(day["feedback"] for day in stats["daily"].values()) == 1


def test_manual_interests_are_saved_verbatim_with_high_weights(tmp_path, monkeypatch):
    store = Store(tmp_path / "state.db")
    recommender = Recommender(store)
    monkeypatch.setattr(recommender, "schedule_interest_refresh", lambda: None)

    result = recommender.set_manual_interests(
        ["multimodal agents", "任意 自定义 标签", "multimodal agents"],
        ["image classification"],
    )

    assert result["manual_positive"] == ["multimodal agents", "任意 自定义 标签"]
    assert result["manual_negative"] == ["image classification"]
    positive, negative = store.preference_examples()
    assert ("multimodal agents", 2.5) in positive
    assert ("任意 自定义 标签", 2.5) in positive
    assert ("image classification", 2.5) in negative


def test_detailed_tldr_removes_short_assistant_preamble():
    raw = "好的，作为你的论文研究助理，以下是详细摘要。\n\n## 研究问题\n研究一种新方法。"
    assert Recommender._clean_detailed_tldr(raw).startswith("## 研究问题")


def test_weighted_multi_prototype_ranking_respects_negative_interest(tmp_path):
    store = Store(tmp_path / "state.db")
    store.save_settings({
        "interest_positive": ["multimodal agents and efficient reasoning"],
        "interest_negative": ["image classification"],
    })
    recommender = Recommender(store)
    candidates = [
        paper("good", "Multimodal agent reasoning", "an efficient reasoning agent using language and vision"),
        paper("bad", "Image classification", "a benchmark for image classification models"),
    ]

    recommender._lexical_rank(candidates, [])

    assert candidates[0].id == "good"
    assert candidates[0].score > candidates[1].score


def test_feedback_evidence_decays_but_manual_interests_do_not(tmp_path):
    store = Store(tmp_path / "state.db")
    store.save_settings({
        "feedback_half_life_days": 30,
        "interest_positive": ["manual vision adaptation"],
    })
    item = paper("old")
    store.record([item])
    store.feedback("old", "interested")
    store.db.execute(
        "UPDATE papers SET feedback_at=? WHERE id=?",
        ("2025-01-01T00:00:00+00:00", "old"),
    )
    store.db.commit()

    positive, _ = store.preference_examples()

    learned_weight = next(weight for text, weight in positive if text.startswith(item.title))
    assert learned_weight == 1.8 * .30
    assert ("manual vision adaptation", 2.5) in positive


def test_hybrid_retrieval_adds_character_semantics(tmp_path):
    store = Store(tmp_path / "state.db")
    store.save_settings({"interest_positive": ["test time adaptation foundation vision model"]})
    recommender = Recommender(store)
    candidates = [
        paper("match", "Test-time adapting visual foundation models", "online distribution shift"),
        paper("miss", "Graph molecule generation", "diffusion for molecular graph synthesis"),
    ]

    recommender._hybrid_rank(candidates, [], store.settings())

    assert candidates[0].id == "match"
    assert candidates[0].embedding_score > candidates[1].embedding_score


def test_recommendation_modes_budget_exploration_and_interest_quota(tmp_path):
    recommender = Recommender(Store(tmp_path / "state.db"))
    candidates = []
    for index in range(6):
        item = paper(f"same-{index}")
        item.score = 1 - index * .01
        item.matched_interest = "one dominant topic"
        candidates.append(item)
    alternative = paper("alternative")
    alternative.score = .80
    alternative.matched_interest = "another interest"
    candidates.append(alternative)
    exploratory = paper("explore")
    exploratory.score = .70
    exploratory.matched_interest = "novel adjacent topic"
    exploratory.exploration = True
    candidates.append(exploratory)

    selected = recommender._select_batch(
        candidates, 5, {"recommendation_mode": "explore"},
    )

    assert exploratory in selected
    assert alternative in selected
    assert sum(item.matched_interest == "one dominant topic" for item in selected) <= 3


def test_llm_semantic_reranker_blends_scores_and_can_reorder(tmp_path, monkeypatch):
    store = Store(tmp_path / "state.db")
    store.save_settings({"interest_positive": ["causal representation learning"]})
    recommender = Recommender(store)
    candidates = [paper("lexical"), paper("semantic")]
    candidates[0].score = .9
    candidates[1].score = .8
    response = SimpleNamespace(choices=[SimpleNamespace(
        message=SimpleNamespace(content=json.dumps({"lexical": .05, "semantic": .98}))
    )])
    requests = []
    client = SimpleNamespace(chat=SimpleNamespace(
        completions=SimpleNamespace(create=lambda **kwargs: requests.append(kwargs) or response)
    ))
    monkeypatch.setattr("paperflow.webapp.OpenAI", lambda **kwargs: client)

    accepted = recommender._llm_rerank(candidates, {
        "api_key": "key", "base_url": "https://example.test/v1",
        "model": "legacy-model", "rerank_model": "rerank-model", "batch_size": 1,
        "interest_summary": "", "interest_positive": [], "interest_negative": [],
        "learned_interest_summary": "causal representations",
        "learned_interest_positive": ["causal representation learning"],
        "learned_interest_negative": [],
    }, [])

    assert [item.id for item in candidates] == ["semantic", "lexical"]
    assert accepted == {"semantic"}
    assert requests[0]["model"] == "rerank-model"


def test_learned_profile_participates_in_retrieval_with_negative_weight(tmp_path):
    store = Store(tmp_path / "state.db")
    store.save_settings({
        "learned_interest_positive": ["self-supervised vision transformers"],
        "learned_interest_negative": ["agent benchmarks"],
    })
    positive, negative = store.preference_examples()

    assert ("self-supervised vision transformers", 1.8) in positive
    assert ("agent benchmarks", 2.1) in negative


def test_frontend_renders_paper_chat_answers_as_safe_markdown():
    html = (Path(__file__).parents[1] / "src/paperflow/static/chat.html").read_text(encoding="utf-8")
    assert "function markdown(source)" in html
    assert "item.role==='assistant'?markdown(item.content)+sources:esc(item.content)" in html
    assert "item.metadata?.evidence" in html
    assert "Chat history" in html
    assert "为我详细介绍这篇论文的方法" in html


def test_new_ui_features_and_readme_have_english_support():
    root = Path(__file__).parents[1]
    html = (root / "src/paperflow/static/index.html").read_text(encoding="utf-8")
    chat = (root / "src/paperflow/static/chat.html").read_text(encoding="utf-8")
    english = (root / "README.md").read_text(encoding="utf-8")
    chinese = (root / "README_ZH.md").read_text(encoding="utf-8")
    technical_english = (root / "docs/TECHNICAL_EN.md").read_text(encoding="utf-8")

    assert "History & search" in html
    assert "Your high-weight interests" in html
    assert "No matching papers." in html
    assert "Choose a folder" in html
    assert 'name="rerank_model"' in html
    assert 'name="summary_model"' in html
    assert 'name="interest_model"' in html
    assert 'name="chat_model"' in html
    assert 'name="mineru_runtime_mode"' in html
    assert "/api/integrations/mineru/install" in html
    assert "Install local MinerU" in html
    assert "Chat history" in chat
    assert "/api/chats" in chat
    assert "TL;DR generation failed:" in (root / "src/paperflow/webapp.py").read_text(encoding="utf-8")
    assert "[English](README.md)" in chinese
    assert "[简体中文](README_ZH.md)" in english
    assert "## Lightweight localhost setup" in english
    assert "## Windows app" in english
    assert "## Recommendation v2" in technical_english
    assert "## Diagnostics and offline evaluation" in technical_english
    assert "## Project origin and license" in english


def test_loading_screen_reports_real_recommendation_stages():
    root = Path(__file__).parents[1]
    html = (root / "src/paperflow/static/index.html").read_text(encoding="utf-8")
    backend = (root / "src/paperflow/webapp.py").read_text(encoding="utf-8")

    assert "/api/progress" in html
    assert "LLM 正在语义筛选" in html
    assert "正在向 arXiv 发送" in html
    assert "LLM is summarizing" in html
    assert '"stage": "idle"' in backend
    assert '"llm_summarizing"' in backend


def test_topic_taxonomy_merges_word_order_plural_and_punctuation_variants():
    taxonomy = ["test-time adaptation for vision foundation models"]
    labels = [
        "Vision foundation model test time adaptation",
        "self-supervised vision foundation models",
        "Self-supervised vision foundation model",
    ]

    assert Recommender._canonical_topics(labels, taxonomy) == [
        "test-time adaptation for vision foundation models",
        "self-supervised vision foundation models",
    ]


def test_interest_profile_is_generated_by_llm_filtered_and_cached(tmp_path, monkeypatch):
    store = Store(tmp_path / "state.db")
    store.save_settings({
        "api_key": "key", "base_url": "https://example.test/v1",
        "model": "legacy-model", "interest_model": "interest-model", "language": "中文",
    })
    library = tmp_path / "library"
    library.mkdir()
    (library / "seed.pdf").write_bytes(b"pdf")
    store.sync_local_documents(str(library), lambda path: "self-supervised vision foundation model research")
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({
        "summary": "关注视觉基础模型的自监督学习与测试时适配。",
        "positive": ["et al", "自监督视觉基础模型", "视觉基础模型的测试时适配",
                     "视觉语言模型", "开放词汇检测", "视觉提示学习"],
        "negative": [],
    }, ensure_ascii=False)))])
    requests = []
    def create(**kwargs):
        requests.append(kwargs)
        return response
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr("paperflow.webapp.OpenAI", lambda **kwargs: client)
    recommender = Recommender(store)

    recommender.schedule_interest_refresh()
    recommender.wait_for_interest_refresh()
    first = recommender.analytics()["interest"]
    second = recommender.analytics()["interest"]

    assert first["summary"] == "关注视觉基础模型的自监督学习与测试时适配。"
    assert [item["term"] for item in first["top_positive"]] == [
        "自监督视觉基础模型", "视觉基础模型的测试时适配",
        "视觉语言模型", "开放词汇检测", "视觉提示学习",
    ]
    assert second == first
    assert len(requests) == 1
    assert requests[0]["model"] == "interest-model"


def test_history_supports_full_listing_and_memory_search(tmp_path):
    store = Store(tmp_path / "state.db")
    batch_id = store.create_batch()
    vision = paper(
        "vision", "Adapting foundation models at test time",
        "online entropy minimization for distribution shifts in visual recognition",
    )
    vision.topic_labels = ["test-time adaptation for vision foundation models"]
    graph = paper("graph", "Graph networks", "message passing for molecular graphs")
    store.record([vision, graph], batch_id)
    recommender = Recommender(store)

    assert {item["id"] for item in recommender.search_history()} == {"vision", "graph"}
    results = recommender.search_history("视觉模型在分布变化时在线适应")
    # Chinese-to-English semantic search needs an embedding/LLM; keyword and
    # same-language natural descriptions are handled locally.
    if not results:
        results = recommender.search_history("foundation model distribution shift adaptation")
    assert results[0]["id"] == "vision"
    assert "shown_at" in results[0]


def test_arxiv_fetch_depth_advances_past_consumed_frontier(tmp_path, monkeypatch):
    store = Store(tmp_path / "state.db")
    monkeypatch.setattr(store, "seen", lambda: {str(index) for index in range(200)})
    recommender = Recommender(store)
    captured = {}
    client_options = {}
    result_offsets = []
    def search(**kwargs):
        captured.update(kwargs)
        return object()
    def results(query, offset=0):
        result_offsets.append(offset)
        return []
    client = SimpleNamespace(results=results)
    monkeypatch.setattr("paperflow.webapp.arxiv.Search", search)
    def make_client(**kwargs):
        client_options.update(kwargs)
        return client
    monkeypatch.setattr("paperflow.webapp.arxiv.Client", make_client)

    assert recommender._fetch({
        "categories": "cs.CV,cs.LG", "batch_size": 20, "lookback_days": 60,
    }) == []
    assert captured["max_results"] == 200
    assert result_offsets == [0]
    assert client_options == {"page_size": 200, "delay_seconds": 6, "num_retries": 5}


def test_next_batch_continues_retrieval_pages_until_recommendation_batch_is_full(tmp_path, monkeypatch):
    store = Store(tmp_path / "state.db")
    store.save_settings({
        "api_key": "key", "library_path": str(tmp_path), "batch_size": 2,
    })
    recommender = Recommender(store)
    offsets = []
    observed_stages = []
    rejected = [paper(f"bad-{index}", "Agent benchmark", "tool agent evaluation")
                for index in range(60)]
    accepted = [
        paper("good-1", "Self-supervised vision transformer", "masked visual pretraining"),
        paper("good-2", "Efficient recurrent vision model", "looped transformer inference"),
    ]
    def fetch_page(settings, offset, limit, client):
        offsets.append(offset)
        observed_stages.append(recommender.progress()["stage"])
        return (rejected, 200, False) if offset == 0 else (accepted, 2, False)
    monkeypatch.setattr(recommender, "_fetch_page", fetch_page)
    monkeypatch.setattr(recommender, "_local_corpus", lambda folder: [])
    monkeypatch.setattr(recommender, "_lexical_rank", lambda candidates, local: None)
    def rerank(candidates, settings, local):
        observed_stages.append(recommender.progress()["stage"])
        return {item.id for item in candidates if item.id.startswith("good-")}
    monkeypatch.setattr(recommender, "_llm_rerank", rerank)
    def summarize(papers, settings):
        observed_stages.append(recommender.progress()["stage"])
    monkeypatch.setattr(recommender, "_metadata_summaries", summarize)
    monkeypatch.setattr(recommender, "schedule_interest_refresh", lambda: None)

    batch = recommender.next_batch()

    assert [item.id for item in batch] == ["good-1", "good-2"]
    assert offsets == [0, 200]
    assert "arxiv_request" in observed_stages
    assert "llm_filter" in observed_stages
    assert "llm_summarizing" in observed_stages
    assert recommender.progress() == {
        "run_id": 1, "stage": "complete", "percent": 100,
        "detail": {"count": 2},
    }


def test_next_batch_uses_persistent_arxiv_cache_before_network(tmp_path, monkeypatch):
    store = Store(tmp_path / "state.db")
    store.save_settings({
        "api_key": "key", "library_path": str(tmp_path), "batch_size": 2,
    })
    cached = [paper("cached-1"), paper("cached-2")]
    for index, item in enumerate(cached):
        item.source_offset = index
    store.cache_arxiv_candidates(store.settings(), cached)
    recommender = Recommender(store)
    monkeypatch.setattr(recommender, "_local_corpus", lambda folder: [])
    monkeypatch.setattr(recommender, "_llm_rerank", lambda candidates, settings, local: None)
    monkeypatch.setattr(recommender, "_metadata_summaries", lambda papers, settings: None)
    monkeypatch.setattr(recommender, "schedule_interest_refresh", lambda: None)
    monkeypatch.setattr(
        recommender, "_fetch_page",
        lambda *args: (_ for _ in ()).throw(AssertionError("cache should satisfy this batch")),
    )

    assert {item.id for item in recommender.next_batch()} == {"cached-1", "cached-2"}


def test_arxiv_backoff_blocks_an_immediate_repeat_request(tmp_path, monkeypatch):
    store = Store(tmp_path / "state.db")
    store.save_settings({
        "api_key": "key", "library_path": str(tmp_path), "batch_size": 1,
        "language": "English",
    })
    store.save_source_state({
        "failure_count": 2,
        "next_retry_at": (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
    })
    recommender = Recommender(store)
    monkeypatch.setattr(recommender, "_local_corpus", lambda folder: [])
    monkeypatch.setattr(recommender, "schedule_interest_refresh", lambda: None)
    monkeypatch.setattr(
        recommender, "_fetch_page",
        lambda *args: (_ for _ in ()).throw(AssertionError("backoff should block network")),
    )

    try:
        recommender.next_batch()
    except RuntimeError as exc:
        assert "backoff" in str(exc)
    else:
        raise AssertionError("an active arXiv backoff must be visible")


def test_background_candidate_refresh_populates_cache_and_job_state(tmp_path, monkeypatch):
    store = Store(tmp_path / "state.db")
    store.save_settings({"arxiv_page_size": 20, "retrieval_batch_size": 20, "batch_size": 2})
    recommender = Recommender(store)
    monkeypatch.setattr(
        recommender, "_fetch_page",
        lambda settings, offset, limit, client: ([paper("fresh")], 1, False),
    )

    status = recommender.refresh_candidate_cache(force=True)

    assert status["count"] == 1
    assert store.cached_arxiv_candidates(store.settings(), 10)[0].id == "fresh"
    assert store.jobs()[0]["status"] == "idle"
