import os
from dataclasses import dataclass, field
from dotenv import load_dotenv


load_dotenv()


# Support both .env (local) and Streamlit secrets (cloud)
def get_env(key: str, default=None):
    """Get environment variable from .env or Streamlit secrets."""
    # Try Streamlit secrets first (for cloud deployment)
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and key in st.secrets:
            return st.secrets[key]
    except (ImportError, FileNotFoundError, KeyError, AttributeError):
        pass

    # Fall back to os.getenv (for local .env)
    return os.getenv(key, default)


@dataclass
class ChunkConfig:
    size: int = int(get_env("CHUNK_SIZE", 600))
    overlap: int = int(get_env("CHUNK_OVERLAP", 80))


@dataclass
class RetrievalConfig:
    top_k: int = int(get_env("TOP_K_RESULTS", 6))


@dataclass
class VerificationConfig:
    faithfulness_threshold: float = float(get_env("FAITHFULNESS_THRESHOLD", 0.7))
    relevancy_threshold: float = float(get_env("RELEVANCY_THRESHOLD", 0.7))
    ragas_llm_backend: str = get_env("RAGAS_LLM_BACKEND", "heuristic")  # ollama | openai | heuristic


@dataclass
class QdrantConfig:
    host: str = get_env("QDRANT_HOST", "localhost")
    port: int = int(get_env("QDRANT_PORT", 6333))
    collection_name: str = get_env("QDRANT_COLLECTION_NAME", "pdf_documents")
    url: str | None = get_env("QDRANT_URL") or None
    api_key: str | None = get_env("QDRANT_API_KEY") or None
    profile: str = get_env("QDRANT_PROFILE", "auto")  # local | cloud | auto

    @property
    def is_cloud(self) -> bool:
        return self.active_profile == "cloud"

    @property
    def active_profile(self) -> str:
        if self.profile == "cloud" and self.url and self.api_key:
            return "cloud"
        if self.profile == "local":
            return "local"
        if self.url and self.api_key:
            return "cloud"
        return "local"


@dataclass
class OllamaConfig:
    base_url: str = get_env("OLLAMA_BASE_URL", "http://localhost:11434")
    model: str = get_env("OLLAMA_MODEL", "llama3.2:3b")


@dataclass
class OpenAIConfig:
    api_key: str | None = get_env("OPENAI_API_KEY")
    model: str = get_env("OPENAI_MODEL", "gpt-4o-mini")
    embedding_model: str = get_env("OPENAI_EMBED_MODEL", "text-embedding-3-small")


@dataclass
class LLMConfig:
    backend: str = get_env("LLM_BACKEND", "ollama")  # ollama | openai
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)


@dataclass
class VectorStoreConfig:
    backend: str = get_env("VECTOR_STORE_BACKEND", "qdrant")  # qdrant | pinecone (example)


@dataclass
class EmbeddingConfig:
    backend: str = get_env("EMBEDDING_BACKEND", "sentence")  # sentence | hashing | openai
    model_name: str = get_env("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    dimension: int = int(get_env("EMBEDDING_DIMENSION", 384))


@dataclass
class AppConfig:
    log_level: str = get_env("LOG_LEVEL", "INFO")

    @property
    def log_level_int(self) -> int:
        return getattr(__import__("logging"), self.log_level.upper(), __import__("logging").INFO)


@dataclass
class Settings:
    qdrant: QdrantConfig = field(default_factory=QdrantConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    vector_store: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    chunk: ChunkConfig = field(default_factory=ChunkConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    verification: VerificationConfig = field(default_factory=VerificationConfig)
    app: AppConfig = field(default_factory=AppConfig)
    langsmith_api_key: str | None = get_env("LANGCHAIN_API_KEY")
    langsmith_tracing: bool = get_env("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    langsmith_project: str | None = get_env("LANGCHAIN_PROJECT")


settings = Settings()
