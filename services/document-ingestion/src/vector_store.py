"""
Vector Store Client - Qdrant client for storing and retrieving embeddings

Handles vector storage, collection management, and similarity search.
"""

import logging
import uuid
from typing import List, Dict, Optional

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http.models import Distance, VectorParams, PointStruct
except ImportError:
    QdrantClient = None
    Distance = None
    VectorParams = None
    PointStruct = None

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Qdrant vector store client.
    
    Manages vector collections and provides methods for:
    - Creating/ensuring collections exist
    - Adding documents with embeddings
    - Searching for similar documents
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        collection_name: str = "documents",
        vector_dimension: int = 384
    ):
        """
        Initialize Qdrant vector store client.
        
        Args:
            host: Qdrant server host
            port: Qdrant server port
            collection_name: Name of the collection to use
            vector_dimension: Dimension of embedding vectors
        """
        if QdrantClient is None:
            raise ImportError(
                "qdrant-client is required. "
                "Install with: pip install qdrant-client"
            )
        
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.vector_dimension = vector_dimension
        
        # Initialize client
        self.client = QdrantClient(host=host, port=port, prefer_grpc=False)
        
        # Ensure collection exists
        self._ensure_collection()
        
        logger.info(
            f"Vector Store initialized "
            f"(host={host}:{port}, collection={collection_name}, dim={vector_dimension})"
        )
    
    def _ensure_collection(self):
        """
        Ensure collection exists with correct vector dimension.
        
        Recreates collection if dimension mismatch detected.
        """
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name in collection_names:
                # Check dimension
                info = self.client.get_collection(self.collection_name)
                actual_dim = info.config.params.vectors.size
                
                if actual_dim != self.vector_dimension:
                    logger.warning(
                        f"Collection {self.collection_name} dimension mismatch "
                        f"(expected {self.vector_dimension}, found {actual_dim}). "
                        f"Recreating collection."
                    )
                    self.client.delete_collection(self.collection_name)
                else:
                    logger.info(f"Collection {self.collection_name} already exists")
                    return
            
            # Create collection
            logger.info(
                f"Creating collection {self.collection_name} "
                f"with dimension {self.vector_dimension}"
            )
            
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_dimension,
                    distance=Distance.COSINE
                )
            )
            
            logger.info(f"Collection {self.collection_name} created successfully")
            
        except Exception as e:
            logger.error(f"Failed to ensure collection: {e}", exc_info=True)
            raise
    
    def add_chunks(self, chunks: List[Dict], document_id: str = None) -> int:
        """
        Add chunks with embeddings to vector store.
        
        Args:
            chunks: List of chunk dictionaries with 'text', 'embedding', and 'metadata'
            document_id: Optional document ID to associate with chunks
            
        Returns:
            Number of chunks added
        """
        if not chunks:
            return 0
        
        document_id = document_id or str(uuid.uuid4())
        
        logger.info(f"Adding {len(chunks)} chunks to vector store (document_id={document_id})")
        
        try:
            points = []
            
            for chunk in chunks:
                # Generate unique point ID
                point_id = str(uuid.uuid4())
                
                # Create point
                point = PointStruct(
                    id=point_id,
                    vector=chunk["embedding"],
                    payload={
                        "page_content": chunk["text"],
                        "metadata": {
                            **chunk.get("metadata", {}),
                            "document_id": document_id
                        }
                    }
                )
                
                points.append(point)
            
            # Upload points in batches
            batch_size = 100
            for i in range(0, len(points), batch_size):
                batch = points[i:i + batch_size]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch
                )
            
            logger.info(f"Successfully added {len(chunks)} chunks to vector store")
            
            return len(chunks)
            
        except Exception as e:
            logger.error(f"Failed to add chunks to vector store: {e}", exc_info=True)
            raise
    
    def get_collection_info(self) -> Dict:
        """
        Get information about the collection.

        Returns:
            Dictionary with collection statistics
        """
        try:
            info = self.client.get_collection(self.collection_name)

            return {
                "collection_name": self.collection_name,
                "vectors_count": info.vectors_count or 0,
                "points_count": info.points_count or 0,
                "vector_dimension": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance.name
            }

        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            return {"error": str(e)}

