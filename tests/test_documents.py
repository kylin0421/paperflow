from paperflow.documents import MinerUClient, ParsedDocument, markdown_sections, structured_context


def test_structured_context_keeps_document_map_and_coherent_sections():
    markdown = "\n\n".join([
        "# Abstract\nWe introduce a visual adaptation method.",
        "# Method\nThe model updates normalization statistics at test time. " * 80,
        "## Objective\nThe entropy loss controls the update. " * 80,
        "# Experiments\nThe method is evaluated under corruptions. " * 80,
        "# Unrelated appendix\nImplementation logs and license text. " * 200,
        "# Conclusion\nThe method improves robustness.",
    ])

    context, evidence = structured_context(
        markdown, "How does the entropy objective work?", max_chars=5000,
    )

    assert "Document map:" in context
    assert "Selected structured evidence:" in context
    assert any(item["heading"] == "Objective" for item in evidence)
    assert all("content" not in item for item in evidence)
    assert "[S" in context


def test_markdown_without_headings_is_grouped_in_substantial_blocks():
    sections = markdown_sections("\n\n".join(f"paragraph {index}" for index in range(20)))

    assert len(sections) == 3
    assert sections[0].content.startswith("paragraph 0")
    assert "paragraph 7" in sections[0].content


def test_mineru_client_uses_file_parse_and_reads_markdown(tmp_path, monkeypatch):
    path = tmp_path / "paper.pdf"
    path.write_bytes(b"%PDF-1.7\nexample")
    calls = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "results": {
                    "paper": {"md_content": "# Method\nStructured text", "content_list": []}
                }
            }

    class Client:
        def __init__(self, **kwargs):
            calls.append(("init", kwargs))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return Response()

    monkeypatch.setattr("paperflow.documents.httpx.Client", Client)

    parsed = MinerUClient("http://mineru.test", 120).parse(path)

    assert parsed == ParsedDocument("# Method\nStructured text", "mineru", [])
    assert calls[1][0] == "http://mineru.test/file_parse"
    assert calls[1][1]["data"]["return_md"] == "true"
