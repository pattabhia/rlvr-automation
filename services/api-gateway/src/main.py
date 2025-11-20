"""
API Gateway - Unified entry point for all microservices

Provides:
- Request routing to backend services
- Health check aggregation
- CORS support
- API documentation
"""

import os
import sys
import logging
from typing import Dict, Any, Optional

import httpx
from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

# Add parent directory to path for shared module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))

from shared.observability import setup_observability

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="API Gateway",
    description="Unified entry point for RLVR PDF Chat microservices",
    version="1.0.0"
)

# Set up OpenTelemetry observability
tracer, meter = setup_observability(
    app=app,
    service_name="api-gateway",
    service_version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs (loaded from environment)
SERVICES = {}


@app.on_event("startup")
async def startup_event():
    """Initialize service URLs on startup."""
    global SERVICES
    
    logger.info("Starting API Gateway...")
    
    # Load service URLs from environment
    SERVICES = {
        "qa-orchestrator": os.getenv("QA_ORCHESTRATOR_URL", "http://qa-orchestrator:8001"),
        "document-ingestion": os.getenv("DOC_INGESTION_SERVICE_URL", "http://document-ingestion:8002"),
        "training-data": os.getenv("TRAINING_DATA_SERVICE_URL", "http://training-data:8005"),
        "ground-truth": os.getenv("GROUND_TRUTH_SERVICE_URL", "http://ground-truth:8007"),
    }
    
    logger.info(f"Service URLs configured: {SERVICES}")
    logger.info("API Gateway started successfully")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "API Gateway",
        "status": "running",
        "version": "1.0.0",
        "services": list(SERVICES.keys())
    }


@app.get("/health")
async def health():
    """
    Aggregate health check from all backend services.
    
    Returns:
        Health status of gateway and all backend services
    """
    health_status = {
        "gateway": "healthy",
        "services": {}
    }
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for service_name, service_url in SERVICES.items():
            try:
                response = await client.get(f"{service_url}/health")
                if response.status_code == 200:
                    health_status["services"][service_name] = {
                        "status": "healthy",
                        "url": service_url
                    }
                else:
                    health_status["services"][service_name] = {
                        "status": "unhealthy",
                        "url": service_url,
                        "error": f"HTTP {response.status_code}"
                    }
            except Exception as e:
                health_status["services"][service_name] = {
                    "status": "unreachable",
                    "url": service_url,
                    "error": str(e)
                }
    
    # Determine overall status
    all_healthy = all(
        s.get("status") == "healthy" 
        for s in health_status["services"].values()
    )
    health_status["overall_status"] = "healthy" if all_healthy else "degraded"
    
    return health_status


# ============================================================================
# QA Orchestrator Routes
# ============================================================================

@app.post("/api/ask")
async def ask_question(request: Request):
    """
    Ask a question using RAG.

    Proxies to QA Orchestrator service.
    """
    try:
        body = await request.json()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{SERVICES['qa-orchestrator']}/ask",
                json=body
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(f"QA Orchestrator error: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to proxy request to QA Orchestrator: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ask/multi-candidate")
async def ask_question_multi_candidate(request: Request):
    """
    Ask a question and generate multiple candidate answers for DPO training.

    Proxies to QA Orchestrator service.
    """
    try:
        body = await request.json()

        async with httpx.AsyncClient(timeout=180.0) as client:  # 3 minutes for multiple candidates
            response = await client.post(
                f"{SERVICES['qa-orchestrator']}/ask/multi-candidate",
                json=body
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(f"QA Orchestrator multi-candidate error: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to proxy multi-candidate request to QA Orchestrator: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Document Ingestion Routes
# ============================================================================

@app.post("/api/ingest")
async def ingest_document(file: UploadFile = File(...)):
    """
    Ingest a PDF document.
    
    Proxies to Document Ingestion service.
    """
    try:
        # Read file content
        file_content = await file.read()
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{SERVICES['document-ingestion']}/ingest",
                files={"file": (file.filename, file_content, file.content_type)}
            )
            response.raise_for_status()
            return response.json()
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Document Ingestion error: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to proxy request to Document Ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/collection/info")
async def get_collection_info():
    """
    Get vector store collection info.
    
    Proxies to Document Ingestion service.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICES['document-ingestion']}/collection/info")
            response.raise_for_status()
            return response.json()
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Document Ingestion error: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to proxy request to Document Ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Training Data Routes
# ============================================================================

@app.get("/api/datasets")
async def list_datasets():
    """
    List all training datasets.

    Proxies to Training Data service.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICES['training-data']}/datasets")
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(f"Training Data error: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to proxy request to Training Data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/datasets/{file_name}/stats")
async def get_dataset_stats(file_name: str):
    """
    Get statistics for a specific dataset.

    Proxies to Training Data service.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICES['training-data']}/datasets/{file_name}/stats")
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(f"Training Data error: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to proxy request to Training Data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/entries")
async def get_entries(request: Request):
    """
    Get training data entries with filtering.

    Proxies to Training Data service.
    """
    try:
        # Forward query parameters
        query_params = dict(request.query_params)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{SERVICES['training-data']}/entries",
                params=query_params
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(f"Training Data error: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to proxy request to Training Data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export")
async def export_dataset(request: Request):
    """
    Export dataset to specified format.

    Proxies to Training Data service.
    """
    try:
        body = await request.json()

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{SERVICES['training-data']}/export",
                json=body
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(f"Training Data error: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to proxy request to Training Data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Ground Truth Routes
# ============================================================================

@app.get("/api/ground-truth/domains")
async def list_domains():
    """
    List all ground truth domains.

    Proxies to Ground Truth service.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICES['ground-truth']}/domains")
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(f"Ground Truth error: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to proxy request to Ground Truth: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ground-truth/domains")
async def create_domain(request: Request):
    """
    Create a new ground truth domain.

    Proxies to Ground Truth service.
    """
    try:
        body = await request.json()

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{SERVICES['ground-truth']}/domains",
                json=body
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(f"Ground Truth error: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to proxy request to Ground Truth: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ground-truth/{domain}/entries")
async def list_entries(domain: str, request: Request):
    """
    List ground truth entries for a domain.

    Proxies to Ground Truth service.
    """
    try:
        query_params = dict(request.query_params)

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{SERVICES['ground-truth']}/{domain}/entries",
                params=query_params
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(f"Ground Truth error: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to proxy request to Ground Truth: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ground-truth/{domain}/entries")
async def create_entry(domain: str, request: Request):
    """
    Create a ground truth entry.

    Proxies to Ground Truth service.
    """
    try:
        body = await request.json()

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{SERVICES['ground-truth']}/{domain}/entries",
                json=body
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        logger.error(f"Ground Truth error: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to proxy request to Ground Truth: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

