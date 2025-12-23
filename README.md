# Reinforcement Learning PDF Chat (RLVR)

Multi-document PDF QA with Retrieval-Augmented Generation and verification (RAGAS), using open-source components and a WhatsApp-inspired Streamlit UI.

## Quickstart (Local)

```bash
cd infrastructure
docker-compose up -d  # Start all microservices
# Access UI: http://localhost:8501
```

## Profiles

- **Local (default):** Uses Docker Qdrant at `localhost:6333` and Ollama `llama3.2:3b` on `http://localhost:11434`.
- **Cloud:** Set `QDRANT_URL` and `QDRANT_API_KEY` to switch to Qdrant Cloud (`QDRANT_PROFILE=cloud`), or use `auto` to select cloud when credentials exist. LangSmith keys are optional but recommended for tracing.

## Features

- Multi-PDF upload and ingestion
- Configurable chunking and retrieval (chunk size/overlap, top-k)
- Llama 3.2 via Ollama + sentence-transformers embeddings
- RAGAS verification scores with confidence badges
- WhatsApp-themed Streamlit chat with sources per answer
- Structured logging (timestamp | level | module | message) to trace ingestion, retrieval, and verification
- Hexagonal architecture with ports/adapters for embeddings, vector store, LLM, PDF processing, and verification
- Adapter factories to swap LLMs/vector stores without touching domain logic

## Configuration

Tune via `.env`:

- `CHUNK_SIZE`, `CHUNK_OVERLAP`, `TOP_K_RESULTS`
- `QDRANT_*` for local/cloud (`QDRANT_PROFILE=local|cloud|auto`)
- `OLLAMA_*` for model endpoint
- `LLM_BACKEND` (`ollama` default; extendable)
- `VECTOR_STORE_BACKEND` (`qdrant` default; extendable)
- `LANGCHAIN_*` for LangSmith tracing
- `LOG_LEVEL` for logging verbosity

## Run

1. Upload one or more PDFs in the sidebar, adjust chunk/retrieval sliders, click **Process PDFs**.
2. Ask questions in the chat; answers show verification score and sources.

## Project Structure (Hexagonal-aligned)

```
rlvr-automation/
├── app.py                  # UI adapter (Streamlit - legacy monolith)
├── docs/
│   ├── architecture.md     # Hexagonal overview
│   ├── DEPLOYMENT_GUIDE.md # Microservices deployment
│   └── RUNPOD_DEPLOYMENT.md# RunPod deployment
├── infrastructure/
│   └── docker-compose.yml  # Local microservices
├── services/               # Microservices
│   ├── api-gateway/
│   ├── qa-orchestrator/
│   ├── document-ingestion/
│   └── ...
├── ui/streamlit/           # Streamlit UI service
├── workers/                # Background workers
├── runpod_launch_all.sh    # RunPod deployment script
├── requirements.txt
├── .env.example
├── .streamlit/
│   └── config.toml
└── src/
    ├── __init__.py
    ├── config.py           # Settings/value objects
    ├── factories.py        # Adapter selection (LLM, vector store, etc.)
    ├── ports.py            # Port interfaces
    ├── embedding_service.py# Embedding adapter
    ├── vector_store.py     # Vector store adapter(s)
    ├── pdf_processor.py    # PDF processing adapter
    ├── langchain_rag.py    # RAGService + build wiring
    ├── verification.py     # Verification adapter (RAGAS)
    ├── utils.py            # Helpers (I/O utilities)
```

## Deployment Options

### 🏠 Local Development (Microservices)

```bash
cd infrastructure
docker-compose up -d  # Start all services
# Access UI: http://localhost:8501
```

**What you get:**

- Qdrant (vector DB)
- Ollama (LLM)
- RabbitMQ (event bus)
- PostgreSQL (metadata)
- All microservices
- Streamlit UI

See `docs/DEPLOYMENT_GUIDE.md` for complete setup.

### ☁️ RunPod GPU Deployment (Production)

```bash
# On RunPod pod
git clone <your-repo-url>
cd rlvr-automation
./runpod_launch_all.sh
```

**Performance:** 5x faster than CPU (2-5s vs 20-25s per answer)

**Documentation:** See `docs/RUNPOD_DEPLOYMENT.md` for complete guide.

### 🌐 Streamlit Cloud

Push repo with `requirements.txt`, `app.py`, `.streamlit/config.toml`; add secrets `QDRANT_URL`, `QDRANT_API_KEY`, optionally `LANGCHAIN_API_KEY`; verify locally with `streamlit run app.py` using `.streamlit/secrets.toml`, then deploy via Streamlit Cloud.

## Architecture (Hexagonal)

- **Domain service:** `RAGService` orchestrates ingestion, retrieval, generation, and verification.
- **Ports (interfaces):** defined in `src/ports.py` for embeddings, vector store, LLM, PDF processing, verification.
- **Adapters:** `SentenceTransformerEmbeddingAdapter`, `QdrantVectorStoreAdapter`, `ChatOllamaAdapter`, `PDFProcessorAdapter`, `RagasVerificationAdapter`.
- **Factories:** `src/factories.py` selects adapters via `LLM_BACKEND`, `VECTOR_STORE_BACKEND`.
- **Composition:** `build_service` wires adapters into `RAGService`; Streamlit UI is an outer adapter consuming the domain service.

### Hexagonal Diagram

```
UI (Streamlit)
       |
   RAGService (domain)
   |    |    |    |    |
Emb  VS   LLM  PDF  Verify  (ports)
 |    |    |    |     |
Adapters: SentenceTransformer | Qdrant | ChatOllama | pdfplumber+split | RAGAS
```

## Swapping LLM or Vector DB (no core changes)

- **LLM:** Set `LLM_BACKEND=ollama` (default). To add another backend (e.g., OpenAI), implement an adapter that satisfies `LLMPort` and register it in `src/factories.py` (switch on `LLM_BACKEND`). No changes to `RAGService` or UI needed.
- **Vector DB:** Set `VECTOR_STORE_BACKEND=qdrant` (default). To add another store (e.g., Pinecone/Weaviate), implement `VectorStorePort` and extend the `create_vector_store` factory. Domain and UI remain unchanged.
- **Embeddings/Verification:** Follow the same pattern: implement the port, register in factory, update env to select.

Example (OpenAI LLM):

1. Create `OpenAIAdapter(LLMPort)` that wraps `ChatOpenAI`.
2. Update `create_llm` in `src/factories.py` to return `OpenAIAdapter` when `LLM_BACKEND=openai`.
3. Set env `LLM_BACKEND=openai` and add your API key. No other code changes.

## Stack

- Streamlit UI, LangChain RAG, Qdrant vector DB, sentence-transformers embeddings, Llama 3.2 via Ollama, RAGAS verification, pdfplumber extraction.

## RLVR (Reinforcement Learning with Verifiable Rewards)

- Current implementation delivers RAG + Verification (faithfulness/relevancy via RAGAS) and exposes the verification signal as the “reward” for future RL fine-tuning.
- Response example:

```
Q: What authentication methods are supported?
A: The system supports OAuth 2.0 and API key authentication.
Verification: faithfulness=0.92, relevancy=0.95, overall=0.935, confidence=high
Sources: Page 3 (chunk 7), Page 5 (chunk 12)
```

- Low-confidence example:

```
Q: What is the pricing?
A: The pricing information is not available in this document.
Verification: faithfulness=0.30, relevancy=0.85, overall=0.575, confidence=low
```

- These scores can be logged (e.g., LangSmith) and used later for DPO/iterative fine-tuning without changing the serving path.
