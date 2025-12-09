"""Vector Store Port - Interface for vector database adapters."""

from typing import Iterable, List, Protocol

try:
    from langchain.schema import Document
except ImportError:
    from langchain_core.documents import Document


class VectorStorePort(Protocol):
    """Port for vector store implementations."""

    def add_documents(self, documents: Iterable[Document]) -> List[str]:
        """
        Add documents to the vector store.

        Args:
            documents: Iterable of Document objects to add

        Returns:
            List of document IDs
        """
        ...

    def as_retriever(self, k: int):
        """
        Create a retriever from the vector store.

        Args:
            k: Number of documents to retrieve

        Returns:
            Retriever object
        """
        ...
