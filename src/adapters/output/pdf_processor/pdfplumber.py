from __future__ import annotations

import io
import re
from typing import List

import pdfplumber
import pypdf

# Text splitter compatibility across LangChain versions
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter  # LangChain <=0.1.x
except ImportError:  # LangChain 0.2+ splitters moved to langchain_text_splitters
    from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from langchain.schema import Document
except ImportError:
    from langchain_core.documents import Document

from src.config import settings
from src.logging import get_logger
from src.ports.output import PDFProcessorPort

logger = get_logger(__name__)


def _clean_text(raw: str) -> str:
    """Remove nulls, control chars, and CID artifacts that hurt tokenization/relevance."""
    if not raw:
        return ""

    # Remove null bytes and control characters
    cleaned = raw.replace("\x00", "")
    cleaned = re.sub(r"[\x01-\x08\x0b-\x0c\x0e-\x1f]", " ", cleaned)

    # Remove CID artifacts - common PDF encoding issues
    # Pattern: (cid:XXX) or CID:XXX or similar
    cleaned = re.sub(r'\(cid:\d+\)', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'CID:\d+\)', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\(cid:', '', cleaned, flags=re.IGNORECASE)

    # Common replacements for Indian currency
    # Replace malformed rupee symbols
    cleaned = re.sub(r'¹\s*\(cid:0\)', '₹', cleaned)
    cleaned = re.sub(r'¹', '₹', cleaned)  # Sometimes ¹ is used for ₹

    # Clean up extra spaces created by removals
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip()

    return cleaned


def extract_text_from_pdf(file_bytes: bytes) -> List[dict]:
    """Extract text per page to keep page metadata."""
    pages: list[dict] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for idx, page in enumerate(pdf.pages):
            try:
                text = _clean_text(page.extract_text() or "")
            except Exception as exc:
                logger.warning("Failed to extract text from page %s: %s", idx + 1, exc)
                text = ""
            pages.append({"page": idx + 1, "text": text})

    # Fallback to pypdf if pdfplumber yielded only blanks
    if all((p["text"] or "").strip() == "" for p in pages):
        logger.info("pdfplumber returned empty text; falling back to pypdf extractor")
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages = []
            for idx, page in enumerate(reader.pages):
                try:
                    text = _clean_text(page.extract_text() or "")
                except Exception as exc:
                    logger.warning("pypdf failed on page %s: %s", idx + 1, exc)
                    text = ""
                pages.append({"page": idx + 1, "text": text})
        except Exception as exc:
            logger.error("Fallback pypdf extraction failed: %s", exc)
    return pages


class PDFPlumberAdapter(PDFProcessorPort):
    """
    PDF processor adapter using pdfplumber library.

    Uses pdfplumber for text extraction with pypdf as fallback.
    Applies CID artifact cleaning and text chunking.
    """

    def chunk(self, file_bytes: bytes, source_name: str) -> List[Document]:
        pages = extract_text_from_pdf(file_bytes)
        logger.info(
            "Chunking %d pages from source=%s (size=%d, overlap=%d)",
            len(pages),
            source_name,
            settings.chunk.size,
            settings.chunk.overlap,
        )
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk.size,
            chunk_overlap=settings.chunk.overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        docs: list[Document] = []
        for page in pages:
            chunks = splitter.split_text(page["text"])
            for chunk in chunks:
                if not chunk.strip():
                    continue
                docs.append(
                    Document(
                        page_content=chunk,
                        metadata={
                            "source": source_name,
                            "page": page["page"],
                        },
                    )
                )
        return docs
