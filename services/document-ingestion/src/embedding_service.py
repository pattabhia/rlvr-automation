"""
Embedding Service - Generate embeddings using sentence-transformers

Uses local transformer models for generating embeddings (free, open-source).
"""

import logging
from typing import List
from functools import lru_cache

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def load_embedding_model(model_name: str) -> 'SentenceTransformer':
    """
    Load sentence-transformer model (cached for reuse).
    
    Args:
        model_name: Name of the model to load
        
    Returns:
        Loaded SentenceTransformer model
    """
    if SentenceTransformer is None:
        raise ImportError(
            "sentence-transformers is required. "
            "Install with: pip install sentence-transformers"
        )
    
    logger.info(f"Loading embedding model: {model_name}")
    model = SentenceTransformer(model_name)
    logger.info(f"Model loaded successfully (dimension={model.get_sentence_embedding_dimension()})")
    
    return model


class EmbeddingService:
    """
    Embedding service using sentence-transformers.
    
    Supports models like:
    - all-MiniLM-L6-v2 (384 dim, fast, good quality)
    - multi-qa-mpnet-base-dot-v1 (768 dim, slower, better quality)
    - all-mpnet-base-v2 (768 dim, general purpose)
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding service.
        
        Args:
            model_name: Name of the sentence-transformer model
        """
        self.model_name = model_name
        self.model = load_embedding_model(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        
        logger.info(
            f"Embedding Service initialized "
            f"(model={model_name}, dimension={self.dimension})"
        )
    
    def embed_texts(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            batch_size: Batch size for processing
            
        Returns:
            List of embedding vectors (each is a list of floats)
        """
        if not texts:
            return []
        
        logger.info(f"Generating embeddings for {len(texts)} texts")
        
        try:
            # Generate embeddings in batches
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=len(texts) > 100,
                convert_to_numpy=True
            )
            
            # Convert to list of lists
            embeddings_list = embeddings.tolist()
            
            logger.info(f"Generated {len(embeddings_list)} embeddings")
            
            return embeddings_list
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}", exc_info=True)
            raise
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text string to embed
            
        Returns:
            Embedding vector (list of floats)
        """
        embeddings = self.embed_texts([text])
        return embeddings[0] if embeddings else []
    
    def get_dimension(self) -> int:
        """Get the dimension of the embedding vectors."""
        return self.dimension
    
    def get_model_name(self) -> str:
        """Get the name of the embedding model."""
        return self.model_name


class BatchEmbeddingProcessor:
    """
    Batch processor for efficient embedding generation.
    
    Processes large numbers of texts in batches to optimize memory usage.
    """
    
    def __init__(self, embedding_service: EmbeddingService, batch_size: int = 32):
        """
        Initialize batch processor.
        
        Args:
            embedding_service: EmbeddingService instance
            batch_size: Number of texts to process per batch
        """
        self.embedding_service = embedding_service
        self.batch_size = batch_size
        
        logger.info(f"Batch Embedding Processor initialized (batch_size={batch_size})")
    
    def process_chunks(self, chunks: List[dict]) -> List[dict]:
        """
        Process chunks and add embeddings.
        
        Args:
            chunks: List of chunk dictionaries with 'text' field
            
        Returns:
            List of chunk dictionaries with 'embedding' field added
        """
        if not chunks:
            return []
        
        logger.info(f"Processing {len(chunks)} chunks in batches of {self.batch_size}")
        
        # Extract texts
        texts = [chunk["text"] for chunk in chunks]
        
        # Generate embeddings
        embeddings = self.embedding_service.embed_texts(texts, batch_size=self.batch_size)
        
        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk["embedding"] = embedding
        
        logger.info(f"Added embeddings to {len(chunks)} chunks")
        
        return chunks

