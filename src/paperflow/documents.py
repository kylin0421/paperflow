"""Structured PDF parsing and long-document context selection for paper chat."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class Section:
    evidence_id: str
    heading: str
    content: str
    level: int = 1
    page: int | None = None


@dataclass
class ParsedDocument:
    markdown: str
    parser: str
    structure: list[dict[str, Any]]


def file_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def markdown_sections(markdown: str) -> list[Section]:
    """Split at headings while keeping each section as a substantial unit."""
    text = str(markdown or "").replace("\r", "").strip()
    if not text:
        return []
    matches = list(re.finditer(r"(?m)^(#{1,6})\s+(.+?)\s*$", text))
    sections: list[Section] = []
    if not matches:
        blocks = [block.strip() for block in re.split(r"\n\s*\n(?=\S)", text) if block.strip()]
        for start in range(0, len(blocks), 8):
            content = "\n\n".join(blocks[start:start + 8])
            sections.append(Section(f"S{len(sections) + 1}", "Document", content))
        return sections
    preamble = text[:matches[0].start()].strip()
    if preamble:
        sections.append(Section("S1", "Preamble", preamble))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content = text[match.end():end].strip()
        if not content:
            continue
        sections.append(Section(
            f"S{len(sections) + 1}", match.group(2).strip(), content,
            level=len(match.group(1)),
        ))
    return sections


def structured_context(markdown: str, question: str, max_chars: int = 70000
                       ) -> tuple[str, list[dict[str, Any]]]:
    """Select coherent sections for long papers and return auditable evidence."""
    sections = markdown_sections(markdown)
    if not sections:
        return str(markdown or "")[:max_chars], []
    document_map = "\n".join(
        f"[{section.evidence_id}] {section.heading}" for section in sections
    )
    overhead = len(document_map) + 100
    if len(markdown) + overhead <= max_chars:
        selected_indices = list(range(len(sections)))
    else:
        docs = [f"{section.heading}. {section.content[:5000]}" for section in sections]
        query = str(question or "paper method experiments results limitations")
        try:
            matrix = TfidfVectorizer(
                stop_words="english", ngram_range=(1, 2), sublinear_tf=True,
                analyzer="word", max_features=24000,
            ).fit_transform(docs + [query])
            scores = cosine_similarity(matrix[:-1], matrix[-1]).ravel()
        except ValueError:
            scores = np.zeros(len(sections))
        anchors = re.compile(
            r"abstract|introduction|overview|method|approach|architecture|algorithm|"
            r"training|objective|loss|experiment|evaluation|result|ablation|discussion|"
            r"limitation|conclusion|摘要|引言|方法|实验|结果|消融|局限|结论",
            re.IGNORECASE,
        )
        ranked = list(np.argsort(scores)[::-1])
        seeds = {index for index, section in enumerate(sections) if anchors.search(section.heading)}
        seeds.update(int(index) for index in ranked[:10])
        expanded = set(seeds)
        for index in list(seeds):
            if index > 0:
                expanded.add(index - 1)
            if index + 1 < len(sections):
                expanded.add(index + 1)
        selected_indices, used = [], overhead
        for index in sorted(expanded, key=lambda i: (-scores[i], i)):
            cost = len(sections[index].content) + len(sections[index].heading) + 20
            if selected_indices and used + cost > max_chars:
                continue
            selected_indices.append(index)
            used += cost
        selected_indices.sort()
    evidence = [{
        "evidence_id": sections[index].evidence_id,
        "heading": sections[index].heading,
        "page": sections[index].page,
    } for index in selected_indices]
    body = ["Document map:\n" + document_map, "Selected structured evidence:"]
    for index in selected_indices:
        section = sections[index]
        body.append(f"\n[{section.evidence_id}] ## {section.heading}\n{section.content}")
    return "\n".join(body), evidence


class MinerUClient:
    """Small client for MinerU 3.x's optional external ``mineru-api`` service."""

    def __init__(self, base_url: str, timeout: float = 900):
        self.base_url = str(base_url).rstrip("/")
        self.timeout = max(30.0, float(timeout))

    def health(self) -> dict[str, Any]:
        with httpx.Client(timeout=20) as client:
            response = client.get(f"{self.base_url}/health")
            response.raise_for_status()
            data = response.json()
        return data if isinstance(data, dict) else {"status": str(data)}

    def parse(self, path: Path, backend: str = "pipeline") -> ParsedDocument:
        with path.open("rb") as stream, httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/file_parse",
                files={"files": (path.name, stream, "application/pdf")},
                data={
                    "backend": backend or "pipeline",
                    "return_md": "true",
                    "return_content_list": "true",
                    "response_format_zip": "false",
                },
            )
            response.raise_for_status()
            payload = response.json()
        results = payload.get("results") or {}
        if not results:
            raise ValueError("MinerU returned no parsed document")
        result = next(iter(results.values()))
        markdown = str(result.get("md_content") or "").strip()
        if not markdown:
            raise ValueError("MinerU returned empty Markdown")
        content_list = result.get("content_list") or []
        if isinstance(content_list, str):
            try:
                content_list = json.loads(content_list)
            except json.JSONDecodeError:
                content_list = []
        return ParsedDocument(markdown, "mineru", content_list if isinstance(content_list, list) else [])


def parse_with_pymupdf(path: Path) -> ParsedDocument:
    import pymupdf4llm

    markdown = pymupdf4llm.to_markdown(path)
    return ParsedDocument(str(markdown), "pymupdf", [])
