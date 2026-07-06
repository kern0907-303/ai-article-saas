import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.knowledge_file import KnowledgeFile
from app.services.file_service import extract_text_from_file

DEFAULT_CONTEXT_CHAR_BUDGET = 24000
DEFAULT_CHUNK_CHAR_BUDGET = 2200


@dataclass(frozen=True)
class KnowledgeChunk:
    file_name: str
    heading: str
    text: str
    index: int


def _query_terms(query: str) -> set[str]:
    terms: set[str] = set()
    for token in re.findall(r"[A-Za-z0-9_#+.-]{2,}|[\u4e00-\u9fff]{2,}", query):
        normalized = token.lower()
        terms.add(normalized)
        if re.fullmatch(r"[\u4e00-\u9fff]{3,}", token):
            max_width = min(6, len(token))
            for width in range(2, max_width + 1):
                for index in range(0, len(token) - width + 1):
                    terms.add(token[index : index + width])
    return terms


def _split_long_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text.strip()]

    parts: list[str] = []
    current = ""
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) > max_chars:
            if current:
                parts.append(current.strip())
                current = ""
            parts.extend(paragraph[i : i + max_chars].strip() for i in range(0, len(paragraph), max_chars))
            continue
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) > max_chars:
            parts.append(current.strip())
            current = paragraph
        else:
            current = candidate
    if current:
        parts.append(current.strip())
    return [part for part in parts if part]


def _extract_frontmatter(text: str) -> tuple[str, str]:
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        return "", normalized

    end = normalized.find("\n---", 4)
    if end == -1:
        return "", normalized

    frontmatter_end = normalized.find("\n", end + 4)
    if frontmatter_end == -1:
        return normalized, ""
    return normalized[:frontmatter_end].strip(), normalized[frontmatter_end:].strip()


def split_knowledge_text(
    file_name: str,
    text: str,
    max_chunk_chars: int = DEFAULT_CHUNK_CHAR_BUDGET,
) -> list[KnowledgeChunk]:
    frontmatter, body = _extract_frontmatter(text)
    body = body.strip()
    if not body and frontmatter:
        body = frontmatter
        frontmatter = ""

    heading_matches = list(re.finditer(r"(?m)^(#{1,6}\s+.+)$", body))
    raw_sections: list[tuple[str, str]] = []

    if heading_matches:
        intro = body[: heading_matches[0].start()].strip()
        if intro:
            raw_sections.append(("摘要", intro))
        for index, match in enumerate(heading_matches):
            start = match.start()
            end = heading_matches[index + 1].start() if index + 1 < len(heading_matches) else len(body)
            heading = match.group(1).lstrip("#").strip()
            raw_sections.append((heading, body[start:end].strip()))
    elif body:
        raw_sections.append(("全文", body))

    chunks: list[KnowledgeChunk] = []
    for section_index, (heading, section_text) in enumerate(raw_sections):
        if section_index == 0 and frontmatter:
            section_text = f"{frontmatter}\n\n{section_text}".strip()
        for part in _split_long_text(section_text, max_chunk_chars):
            chunks.append(KnowledgeChunk(file_name=file_name, heading=heading, text=part, index=len(chunks)))

    return chunks


def _score_chunk(chunk: KnowledgeChunk, terms: set[str]) -> int:
    haystack = f"{chunk.file_name}\n{chunk.heading}\n{chunk.text}".lower()
    return sum(1 for term in terms if term.lower() in haystack)


def _format_chunk(chunk: KnowledgeChunk, max_chars: int | None = None) -> str:
    heading = f" | 區段: {chunk.heading}" if chunk.heading else ""
    formatted = f"[參考資料: {chunk.file_name}{heading}]\n{chunk.text.strip()}"
    if max_chars is not None and len(formatted) > max_chars:
        return formatted[: max(0, max_chars - 1)].rstrip() + "…"
    return formatted


def rank_knowledge_chunks(
    chunks: list[KnowledgeChunk],
    query: str,
    max_chars: int = DEFAULT_CONTEXT_CHAR_BUDGET,
) -> list[str]:
    terms = _query_terms(query)
    ranked = sorted(
        chunks,
        key=lambda chunk: (_score_chunk(chunk, terms), -chunk.index),
        reverse=True,
    )

    selected: list[str] = []
    used_chars = 0
    for chunk in ranked:
        remaining = max_chars - used_chars
        if remaining <= 0:
            break
        formatted = _format_chunk(chunk, max_chars=remaining)
        if not formatted.strip():
            break
        selected.append(formatted)
        used_chars += len(formatted)
    return selected


def _candidate_files(
    db: Session,
    user_id: str,
    selected_file_ids: list[int],
    use_default_references: bool,
    workspace_id: int | None = None,
    categories: list[str] | None = None,
) -> list[KnowledgeFile]:
    base_query = db.query(KnowledgeFile).filter(
        KnowledgeFile.user_id == user_id,
        KnowledgeFile.is_active.is_(True),
    )
    if workspace_id is not None:
        base_query = base_query.filter(KnowledgeFile.workspace_id == workspace_id)
    if categories:
        base_query = base_query.filter(KnowledgeFile.category.in_(categories))

    if selected_file_ids:
        records = base_query.filter(KnowledgeFile.id.in_(selected_file_ids)).all()
        by_id = {record.id: record for record in records}
        return [by_id[file_id] for file_id in selected_file_ids if file_id in by_id]

    if not use_default_references:
        return []

    return (
        base_query.filter(KnowledgeFile.is_default_reference.is_(True))
        .order_by(KnowledgeFile.created_at.desc())
        .all()
    )


def build_generation_contexts(
    db: Session,
    user_id: str,
    selected_file_ids: list[int],
    topic: str,
    outline: str,
    user_prompt: str | None,
    use_default_references: bool = True,
    workspace_id: int | None = None,
    categories: list[str] | None = None,
    max_chars: int = DEFAULT_CONTEXT_CHAR_BUDGET,
) -> tuple[list[str], list[int]]:
    records = _candidate_files(db, user_id, selected_file_ids, use_default_references, workspace_id, categories)
    chunks: list[KnowledgeChunk] = []
    for record in records:
        text = extract_text_from_file(record.stored_path)
        chunks.extend(split_knowledge_text(record.file_name, text))

    query = "\n".join(part for part in [topic, outline, user_prompt or ""] if part)
    contexts = rank_knowledge_chunks(chunks, query=query, max_chars=max_chars) if chunks else []
    return contexts, [record.id for record in records]
