import io
import math
import re
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

from pypdf import PdfReader

from app import storage
from app.config import get_settings

settings = get_settings()
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv", ".json"}
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_'-]{1,}")
STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "are", "was", "were", "have", "has", "had",
    "what", "when", "where", "which", "who", "why", "how", "your", "you", "our", "their", "about", "into",
    "can", "could", "would", "should", "will", "not", "but", "all", "any", "more", "than", "then", "them",
}


def safe_filename(name: str) -> str:
    cleaned = Path(name or "document").name.strip().replace("\x00", "")
    return cleaned[:255] or "document"


def extract_text(filename: str, data: bytes) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file type. Use PDF, DOCX, TXT, MD, CSV, or JSON.")

    if extension == ".pdf":
        try:
            reader = PdfReader(io.BytesIO(data))
            if len(reader.pages) > 250:
                raise ValueError("PDF has too many pages. Maximum is 250 pages per upload.")
            text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("The PDF could not be read. It may be encrypted or damaged.") from exc
    elif extension == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                info = archive.getinfo("word/document.xml")
                if info.file_size > settings.max_document_chars * 8:
                    raise ValueError("DOCX expands to too much text data.")
                xml = archive.read("word/document.xml")
            root = ElementTree.fromstring(xml)
            text = "\n".join(node.text or "" for node in root.iter() if node.tag.endswith("}t"))
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("The DOCX file could not be read.") from exc
    else:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("cp1252", errors="replace")

    text = text.replace("\x00", " ").strip()
    if not text:
        raise ValueError("No readable text was found in this document.")
    if len(text) > settings.max_document_chars:
        raise ValueError(f"Document text is too large. Maximum is {settings.max_document_chars:,} characters.")
    return text


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 180) -> list[str]:
    normalized = re.sub(r"[ \t]+", " ", text)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        if end < len(normalized):
            split = max(normalized.rfind("\n", start, end), normalized.rfind(". ", start, end))
            if split > start + chunk_size // 2:
                end = split + 1
        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(normalized):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in WORD_RE.findall(text) if token.lower() not in STOPWORDS]


def retrieve_knowledge(user_id: str, query: str) -> list[dict]:
    query_tokens = _tokens(query)
    if not query_tokens:
        return []
    chunks = storage.search_chunks_for_user(user_id, query_tokens)
    if not chunks:
        return []

    docs_tokens = [_tokens(item["content"]) for item in chunks]
    doc_frequency = Counter()
    for tokens in docs_tokens:
        doc_frequency.update(set(tokens))

    total_docs = len(chunks)
    query_counts = Counter(query_tokens)
    scored: list[tuple[float, dict]] = []
    lowered_query = " ".join(query_tokens)
    for item, tokens in zip(chunks, docs_tokens):
        if not tokens:
            continue
        counts = Counter(tokens)
        score = 0.0
        for term, qtf in query_counts.items():
            tf = counts.get(term, 0)
            if not tf:
                continue
            idf = math.log(1 + (total_docs - doc_frequency[term] + 0.5) / (doc_frequency[term] + 0.5))
            score += idf * (1 + math.log1p(tf)) * (1 + 0.15 * min(qtf, 3))
        normalized_chunk = " ".join(tokens)
        if lowered_query and lowered_query in normalized_chunk:
            score += 4.0
        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    selected: list[dict] = []
    used_chars = 0
    for score, item in scored[: settings.rag_top_k * 3]:
        if len(selected) >= settings.rag_top_k:
            break
        content = item["content"].strip()
        remaining = settings.rag_max_context_chars - used_chars
        if remaining <= 0:
            break
        clipped = content[:remaining]
        selected.append({**item, "content": clipped, "score": round(score, 4)})
        used_chars += len(clipped)
    return selected
