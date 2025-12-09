from __future__ import annotations

import io
from typing import Any, List, Tuple


def load_pdf_bytes(uploaded_file: Any) -> bytes:
    """Read bytes from a Streamlit UploadedFile-like object."""
    if hasattr(uploaded_file, "read"):
        return uploaded_file.read()
    if isinstance(uploaded_file, (bytes, bytearray)):
        return bytes(uploaded_file)
    raise ValueError("Unsupported file input")


def prepare_uploads(files) -> List[Tuple[str, bytes]]:
    """
    Prepare Streamlit uploaded files for processing.

    Streamlit uploads come as UploadedFile objects; this normalizes
    them to (name, bytes) tuples for processing.

    Args:
        files: List of Streamlit UploadedFile objects

    Returns:
        List of (filename, file_bytes) tuples
    """
    uploads: List[Tuple[str, bytes]] = []
    for f in files:
        uploads.append((f.name, load_pdf_bytes(f)))
    return uploads
