"""PDF Processor Port - Interface for PDF processing adapters."""

from typing import List, Protocol

try:
    from langchain.schema import Document
except ImportError:
    from langchain_core.documents import Document


class PDFProcessorPort(Protocol):
    """Port for PDF processing implementations."""

    def chunk(self, file_bytes: bytes, source_name: str) -> List[Document]:
        """
        Process PDF bytes and chunk into documents.

        Args:
            file_bytes: Raw PDF file bytes
            source_name: Name/identifier for the source file

        Returns:
            List of Document objects (chunks)
        """
        ...
