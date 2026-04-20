"""
pdf_utils.py
------------
Robust PDF text-extraction and chunking utilities.

Strategy (in priority order):
  1. PyMuPDF (fitz) — fast, handles most PDFs including scanned pages.
  2. pdfplumber   — excellent for table-heavy documents.
  3. PyPDF2       — lightweight fallback for simple text PDFs.

Chunking uses LangChain's RecursiveCharacterTextSplitter so chunks
respect sentence and paragraph boundaries wherever possible.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ExtractionResult:
    """Result of a PDF extraction attempt."""
    text: str
    page_count: int
    method_used: str
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """Checks if text was actually found and no critical errors occurred."""
        return bool(self.text and self.text.strip()) and self.error is None


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------

def _extract_with_pymupdf(file_bytes: bytes) -> ExtractionResult:
    """Primary extractor using PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages: list[str] = []
        for page in doc:
            pages.append(page.get_text("text"))
        doc.close()

        full_text = "\n\n".join(pages)
        return ExtractionResult(
            text=full_text,
            page_count=len(pages),
            method_used="PyMuPDF",
        )
    except Exception as exc:
        logger.warning("PyMuPDF extraction failed: %s", exc)
        return ExtractionResult(text="", page_count=0, method_used="PyMuPDF", error=str(exc))


def _extract_with_pdfplumber(file_bytes: bytes) -> ExtractionResult:
    """Secondary extractor using pdfplumber (good for tables)."""
    try:
        import pdfplumber

        pages: list[str] = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages.append(text)

        full_text = "\n\n".join(pages)
        return ExtractionResult(
            text=full_text,
            page_count=len(pages),
            method_used="pdfplumber",
        )
    except Exception as exc:
        logger.warning("pdfplumber extraction failed: %s", exc)
        return ExtractionResult(text="", page_count=0, method_used="pdfplumber", error=str(exc))


def _extract_with_pypdf2(file_bytes: bytes) -> ExtractionResult:
    """Tertiary fallback using PyPDF2."""
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        full_text = "\n\n".join(pages)
        return ExtractionResult(
            text=full_text,
            page_count=len(pages),
            method_used="PyPDF2",
        )
    except Exception as exc:
        logger.warning("PyPDF2 extraction failed: %s", exc)
        return ExtractionResult(text="", page_count=0, method_used="PyPDF2", error=str(exc))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_text_from_pdf(file_bytes: bytes) -> ExtractionResult:
    """
    Extract all text from a PDF using a cascading strategy.
    Tries PyMuPDF → pdfplumber → PyPDF2.
    """
    last_result = None
    for extractor in (_extract_with_pymupdf, _extract_with_pdfplumber, _extract_with_pypdf2):
        last_result = extractor(file_bytes)
        if last_result.success:
            logger.info(f"PDF extracted via {last_result.method_used} ({last_result.page_count} pages)")
            return last_result

    # If all methods fail to find text, return a specific error for the UI
    logger.error("All PDF extractors failed to find readable text.")
    return ExtractionResult(
        text="", 
        page_count=0, 
        method_used="None", 
        error="No readable text found. The PDF might be a scanned image without OCR."
    )


def chunk_text(
    text: str,
    chunk_size: int = 2000,
    chunk_overlap: int = 200,
) -> list[str]:
    """
    Split a long text into overlapping chunks for LLM context windows.
    """
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    docs = splitter.split_documents([Document(page_content=text)])
    chunks = [doc.page_content for doc in docs]
    logger.info(f"Text split into {len(chunks)} chunks")
    return chunks


def truncate_text(text: str, max_chars: int = 12_000) -> str:
    """Hard-truncate text to prevent token overflow in single-shot calls."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n\n[... Document truncated to {max_chars} characters for processing ...]"