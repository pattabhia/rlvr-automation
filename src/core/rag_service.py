from __future__ import annotations

from typing import List, Tuple, Optional
from string import Template

from langchain_ollama import ChatOllama

try:
    from langchain.schema import Document
except ImportError:
    from langchain_core.documents import Document

from src.config import settings
from src.logging import get_logger
from src.ports.output import EmbeddingsPort, LLMPort, PDFProcessorPort, VerificationPort, VectorStorePort
from src.core.training_logger import TrainingDataLogger


QA_PROMPT = Template(
    "You are a helpful assistant. Use the following context to answer the question.\n"
    "Answer based on the information provided in the context. "
    "If the exact answer is not available, provide the most relevant information from the context.\n\n"
    "Context:\n${context}\n\n"
    "Question: ${question}\n\n"
    "Answer:"
)


logger = get_logger(__name__)


class RAGService:
    """Hexagonal core service wiring ports/adapters for ingestion and QA."""

    def __init__(
        self,
        vector_store: VectorStorePort,
        embeddings: EmbeddingsPort,
        pdf_processor: PDFProcessorPort,
        verifier: VerificationPort,
        llm: LLMPort,
        top_k: int,
        enable_training_logging: bool = True,
        rlvr_candidate_service: Optional[object] = None,
        rlvr_training_logger: Optional[object] = None,
    ):
        self.vector_store = vector_store
        self.embeddings = embeddings
        self.pdf_processor = pdf_processor
        self.verifier = verifier
        self.llm = llm
        self.top_k = top_k
        self.retriever = self.vector_store.as_retriever(k=self.top_k)
        self.training_logger = TrainingDataLogger(enabled=enable_training_logging)

        # RLVR components (optional)
        self.rlvr_candidate_service = rlvr_candidate_service
        self.rlvr_training_logger = rlvr_training_logger

        logger.info("RAGService initialized (profile=%s, top_k=%d, training_logging=%s, rlvr_enabled=%s)",
                   settings.qdrant.active_profile, self.top_k, enable_training_logging,
                   rlvr_candidate_service is not None)

    def update_top_k(self, top_k: int) -> None:
        self.top_k = top_k
        self.retriever = self.vector_store.as_retriever(k=top_k)
        logger.info("Updated retriever top_k to %d", top_k)

    def _retrieve(self, question: str):
        """Retrieve using direct client call to avoid search API incompatibilities."""
        if hasattr(self.vector_store, "client"):
            client = getattr(self.vector_store, "client")
            query_vec = self.embeddings.embed_query(question)
            try:
                resp = client.query_points(
                    collection_name=settings.qdrant.collection_name,
                    query=query_vec,
                    limit=self.top_k,
                    with_payload=True,
                    with_vectors=False,
                )
                # Correctly handle QueryResponse object from qdrant-client v1.16+
                if hasattr(resp, "points"):
                    # Modern qdrant-client: QueryResponse has .points attribute
                    points = resp.points or []
                    logger.debug("Using QueryResponse.points (found %d points)", len(points))
                else:
                    # Fallback for older versions
                    points_raw = getattr(resp, "result", resp)
                    if isinstance(points_raw, tuple):
                        points = points_raw[0] or []
                    else:
                        points = points_raw or []
                    logger.debug("Using fallback response handling (found %d points)", len(points))

                logger.info("Retrieved %d points from Qdrant for question", len(points))

                docs = []
                for pt in points:
                    payload = getattr(pt, "payload", {}) or {}
                    text = payload.get("page_content") or payload.get("text") or payload.get("content") or ""
                    if not text.strip():
                        logger.warning("Skipping point with empty text content")
                        continue
                    meta = {k: v for k, v in payload.items() if k not in {"page_content", "text", "content"}}
                    if hasattr(pt, "id"):
                        meta.setdefault("id", getattr(pt, "id"))
                    docs.append(Document(page_content=text, metadata=meta))

                logger.info("Converted %d points to %d Document objects", len(points), len(docs))
                return docs
            except Exception as exc:
                logger.error("Direct Qdrant query_points failed: %s", exc, exc_info=True)
                return []
        logger.warning("Vector store has no client attribute, returning empty results")
        return []

    def process_pdfs(self, uploaded_files: List[Tuple[str, bytes]]) -> int:
        """Ingest multiple PDFs; returns count of added chunks."""
        chunks_added = 0
        for filename, file_bytes in uploaded_files:
            docs = self.pdf_processor.chunk(file_bytes, source_name=filename)
            if not docs:
                logger.warning("No chunks extracted from %s; skipping", filename)
                continue
            self.vector_store.add_documents(docs)
            chunks_added += len(docs)
        logger.info("Finished ingesting PDFs; total chunks added=%d", chunks_added)
        return chunks_added

    def answer_question(self, question: str):
        logger.info("Answering question with top_k=%d", self.top_k)
        source_docs = self._retrieve(question)
        logger.info("Retrieved %d docs for question", len(source_docs))
        for idx, doc in enumerate(source_docs[:3]):
            preview = (doc.page_content or "").replace("\n", " ")
            logger.info("Doc %d meta=%s preview=%s", idx, doc.metadata, preview[:200])
        context = "\n\n".join(doc.page_content for doc in source_docs)
        prompt = QA_PROMPT.safe_substitute(context=context, question=question)
        llm_response = self.llm.invoke(prompt)
        answer = getattr(llm_response, "content", llm_response)
        contexts = [doc.page_content for doc in source_docs]
        verification = self.verifier.verify(question, answer, contexts)

        # Log for future RL training
        self.training_logger.log_interaction(
            question=question,
            answer=answer,
            contexts=contexts,
            verification_scores=verification,
            sources=source_docs,
        )

        return {
            "answer": answer,
            "sources": source_docs,
            "verification": verification,
        }

    def answer_question_rlvr(self, question: str):
        """
        Answer question using RLVR multi-candidate generation and selection.

        This method:
        1. Retrieves context from vector store
        2. Generates multiple candidate answers with different parameters
        3. Scores each candidate with verifiable reward function
        4. Selects and returns the best candidate
        5. Logs all candidates for DPO training

        Args:
            question: User's question

        Returns:
            Dictionary with:
            - answer: Best selected answer
            - sources: Retrieved source documents
            - verification: RAGAS verification scores
            - rlvr_candidates: All generated candidates with rewards
            - rlvr_best_index: Index of selected candidate
        """
        if self.rlvr_candidate_service is None:
            logger.warning("RLVR mode requested but no candidate service configured; falling back to standard mode")
            return self.answer_question(question)

        logger.info("Answering question with RLVR mode (top_k=%d)", self.top_k)

        # Step 1: Retrieve context
        source_docs = self._retrieve(question)
        logger.info("Retrieved %d docs for RLVR question", len(source_docs))

        context = "\n\n".join(doc.page_content for doc in source_docs)
        prompt_template = QA_PROMPT.template

        # Step 2: Generate and score multiple candidates
        rlvr_result = self.rlvr_candidate_service.generate_and_score_candidates(
            question=question,
            context=context,
            prompt_template=prompt_template,
        )

        answer = rlvr_result["best_answer"]
        candidates = rlvr_result["candidates"]
        best_index = rlvr_result["best_index"]

        logger.info(
            f"RLVR selected best answer (index={best_index}, "
            f"reward={candidates[best_index]['reward']:.3f})"
        )

        # Step 3: Verify best answer with RAGAS
        contexts = [doc.page_content for doc in source_docs]
        verification = self.verifier.verify(question, answer, contexts)

        # Step 4: Log for DPO training
        if self.rlvr_training_logger:
            self.rlvr_training_logger.log_candidates(
                question=question,
                context=context,
                candidates=candidates,
                best_index=best_index,
            )

        # Also log to regular training logger for consistency
        self.training_logger.log_interaction(
            question=question,
            answer=answer,
            contexts=contexts,
            verification_scores=verification,
            sources=source_docs,
        )

        return {
            "answer": answer,
            "sources": source_docs,
            "verification": verification,
            "rlvr_candidates": candidates,
            "rlvr_best_index": best_index,
        }
