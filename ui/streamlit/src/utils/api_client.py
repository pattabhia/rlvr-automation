"""
API Client for communicating with API Gateway

Provides:
- Question answering
- Document ingestion
- Training data management
- Ground truth management
"""

import os
import requests
from typing import Dict, Any, List, Optional
import streamlit as st


class APIClient:
    """Client for API Gateway communication."""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize API client.
        
        Args:
            base_url: API Gateway base URL (default: from env or localhost)
        """
        self.base_url = base_url or os.getenv("API_GATEWAY_URL", "http://localhost:8000")
    
    # ========================================================================
    # Health Check
    # ========================================================================
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check health of API Gateway and all services.
        
        Returns:
            Health status dictionary
        """
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {
                "gateway": "unreachable",
                "error": str(e),
                "overall_status": "error"
            }
    
    # ========================================================================
    # QA Orchestrator
    # ========================================================================
    
    def ask_question(self, question: str, collection_name: str = "documents") -> Dict[str, Any]:
        """
        Ask a question using RAG.

        Args:
            question: Question text
            collection_name: Vector store collection name

        Returns:
            Answer dictionary with question, answer, contexts, event_id
        """
        response = requests.post(
            f"{self.base_url}/api/ask",
            json={"question": question, "collection_name": collection_name},
            timeout=120  # 2 minutes for LLM generation
        )
        response.raise_for_status()
        return response.json()

    def ask_question_multi_candidate(
        self,
        question: str,
        num_candidates: int = None,
        publish_events: bool = True
    ) -> Dict[str, Any]:
        """
        Ask a question and generate multiple candidate answers for DPO training.

        This method:
        1. Generates multiple candidate answers (default: 3)
        2. Publishes events for background RAGAS verification
        3. Returns all candidates (UI should show the best one)

        Args:
            question: Question text
            num_candidates: Number of candidates to generate (uses server default if None)
            publish_events: Whether to publish events for background processing

        Returns:
            Dictionary with:
            - question: The question
            - candidates: List of candidate answers with contexts and metadata
            - num_candidates: Number of candidates generated
            - events_published: Number of events published
        """
        payload = {
            "question": question,
            "publish_events": publish_events
        }

        if num_candidates is not None:
            payload["num_candidates"] = num_candidates

        response = requests.post(
            f"{self.base_url}/api/ask/multi-candidate",
            json=payload,
            timeout=180  # 3 minutes for multiple LLM generations
        )
        response.raise_for_status()
        return response.json()

    # ========================================================================
    # Document Ingestion
    # ========================================================================
    
    def ingest_document(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Ingest a PDF document.
        
        Args:
            file_bytes: PDF file bytes
            filename: File name
            
        Returns:
            Ingestion result dictionary
        """
        files = {"file": (filename, file_bytes, "application/pdf")}
        response = requests.post(
            f"{self.base_url}/api/ingest",
            files=files,
            timeout=300  # 5 minutes for large PDFs
        )
        response.raise_for_status()
        return response.json()
    
    def get_collection_info(self) -> Dict[str, Any]:
        """
        Get vector store collection info.
        
        Returns:
            Collection info dictionary
        """
        response = requests.get(f"{self.base_url}/api/collection/info", timeout=10)
        response.raise_for_status()
        return response.json()
    
    # ========================================================================
    # Training Data
    # ========================================================================
    
    def list_datasets(self) -> Dict[str, Any]:
        """
        List all training datasets.
        
        Returns:
            Datasets list with statistics
        """
        response = requests.get(f"{self.base_url}/api/datasets", timeout=10)
        response.raise_for_status()
        return response.json()
    
    def get_dataset_stats(self, file_name: str) -> Dict[str, Any]:
        """
        Get statistics for a specific dataset.
        
        Args:
            file_name: Dataset file name
            
        Returns:
            Dataset statistics
        """
        response = requests.get(
            f"{self.base_url}/api/datasets/{file_name}/stats",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    def get_entries(
        self,
        file_name: Optional[str] = None,
        min_verification_score: Optional[float] = None,
        min_reward_score: Optional[float] = None,
        domains: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get training data entries with filtering.
        
        Args:
            file_name: Filter by file name
            min_verification_score: Minimum verification score
            min_reward_score: Minimum reward score
            domains: Filter by domains
            limit: Maximum number of entries
            offset: Offset for pagination
            
        Returns:
            List of training data entries
        """
        params = {"limit": limit, "offset": offset}
        if file_name:
            params["file_name"] = file_name
        if min_verification_score is not None:
            params["min_verification_score"] = min_verification_score
        if min_reward_score is not None:
            params["min_reward_score"] = min_reward_score
        if domains:
            params["domains"] = domains
        
        response = requests.get(f"{self.base_url}/api/entries", params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def export_dataset(
        self,
        format: str = "dpo",
        min_verification_score: Optional[float] = None,
        min_reward_score: Optional[float] = None,
        domains: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Export dataset to specified format.

        Args:
            format: Export format (dpo, sft, jsonl)
            min_verification_score: Minimum verification score
            min_reward_score: Minimum reward score
            domains: Filter by domains

        Returns:
            Export result dictionary
        """
        payload = {"format": format}
        if min_verification_score is not None:
            payload["min_verification_score"] = min_verification_score
        if min_reward_score is not None:
            payload["min_reward_score"] = min_reward_score
        if domains:
            payload["domains"] = domains

        response = requests.post(f"{self.base_url}/api/export", json=payload, timeout=60)
        response.raise_for_status()
        return response.json()

    # ========================================================================
    # Ground Truth
    # ========================================================================

    def list_domains(self) -> Dict[str, Any]:
        """
        List all ground truth domains.

        Returns:
            Domains list
        """
        response = requests.get(f"{self.base_url}/api/ground-truth/domains", timeout=10)
        response.raise_for_status()
        return response.json()

    def create_domain(
        self,
        domain_name: str,
        description: str,
        metadata_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new ground truth domain.

        Args:
            domain_name: Domain name
            description: Domain description
            metadata_schema: Metadata schema

        Returns:
            Created domain
        """
        payload = {
            "domain_name": domain_name,
            "description": description,
            "metadata_schema": metadata_schema
        }
        response = requests.post(
            f"{self.base_url}/api/ground-truth/domains",
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def list_ground_truth_entries(
        self,
        domain: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List ground truth entries for a domain.

        Args:
            domain: Domain name
            limit: Maximum number of entries
            offset: Offset for pagination

        Returns:
            List of ground truth entries
        """
        params = {"limit": limit, "offset": offset}
        response = requests.get(
            f"{self.base_url}/api/ground-truth/{domain}/entries",
            params=params,
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def create_ground_truth_entry(
        self,
        domain: str,
        question: str,
        expected_answer: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a ground truth entry.

        Args:
            domain: Domain name
            question: Question text
            expected_answer: Expected answer
            metadata: Additional metadata

        Returns:
            Created entry
        """
        payload = {
            "question": question,
            "expected_answer": expected_answer,
            "metadata": metadata or {}
        }
        response = requests.post(
            f"{self.base_url}/api/ground-truth/{domain}/entries",
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return response.json()


@st.cache_resource
def get_api_client() -> APIClient:
    """
    Get cached API client instance.

    Returns:
        APIClient instance
    """
    return APIClient()

