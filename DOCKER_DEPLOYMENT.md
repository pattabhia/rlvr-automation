# Docker Deployment Guide for RunPod

## 🐳 Overview

This deployment uses a **single all-in-one Docker container** that runs all RLVR services internally. This approach works on RunPod because it doesn't require Docker-in-Docker.

### What's Inside the Container:
- **RabbitMQ** - Message broker
- **Qdrant** - Vector database
- **Ollama** - LLM inference server
- **Document Ingestion Service** - PDF processing
- **QA Orchestrator** - Question answering
- **API Gateway** - Main API
- **Streamlit UI** - Web interface
- **Verification Worker** - Quality scoring
- **Dataset Worker** - DPO generation

All services are managed by **Supervisor** inside the container.

---

## 🚀 Quick Start

### Option 1: Using the Deployment Script (Recommended)

```bash
cd /workspace/rlvr-automation

# Build the Docker image
chmod +x runpod_docker_deploy.sh
./runpod_docker_deploy.sh build

# Start all services
./runpod_docker_deploy.sh start

# Check status
./runpod_docker_deploy.sh status

# View logs
./runpod_docker_deploy.sh logs
```

### Option 2: Using Docker Compose Directly

```bash
cd /workspace/rlvr-automation

# Build and start
docker-compose -f docker-compose.runpod.yml up -d --build

# View logs
docker-compose -f docker-compose.runpod.yml logs -f

# Stop
docker-compose -f docker-compose.runpod.yml down
```

---

## 📋 Deployment Script Commands

```bash
./runpod_docker_deploy.sh <command>
```

| Command | Description |
|---------|-------------|
| `build` | Build the Docker image |
| `start` | Start all services (default) |
| `stop` | Stop all services |
| `restart` | Restart all services |
| `logs` | View logs (follow mode) |
| `status` | Check service health |
| `shell` | Open bash shell in container |
| `clean` | Remove all containers and images |

---

## 🔍 Verify Deployment

### Check Container Status
```bash
docker ps
# Should show: rlvr-all-in-one container running
```

### Check Services Inside Container
```bash
# Open shell
./runpod_docker_deploy.sh shell

# Inside container, check supervisor status
supervisorctl status

# Should show all services RUNNING:
# - rabbitmq
# - qdrant
# - ollama
# - document-ingestion
# - qa-orchestrator
# - api-gateway
# - verification-worker
# - dataset-worker
# - streamlit
```

### Health Checks
```bash
curl http://localhost:6333/collections  # Qdrant
curl http://localhost:11434/api/tags    # Ollama
curl http://localhost:8002/health       # Document Ingestion
curl http://localhost:8001/health       # QA Orchestrator
curl http://localhost:8000/health       # API Gateway
curl http://localhost:8501              # Streamlit UI
```

---

## 📊 Access URLs

| Service | URL | Description |
|---------|-----|-------------|
| Streamlit UI | `http://localhost:8501` | Web interface |
| API Gateway | `http://localhost:8000/docs` | API documentation |
| QA Orchestrator | `http://localhost:8001/docs` | QA API docs |
| Document Ingestion | `http://localhost:8002/docs` | Upload API docs |
| Qdrant Dashboard | `http://localhost:6333/dashboard` | Vector DB UI |

**For RunPod:** Replace `localhost` with your RunPod proxy URL:
- Streamlit: `https://YOUR_POD_ID.proxy.runpod.net` (port 8501)

---

## 📄 Upload PDF and Test

```bash
# Upload a PDF
curl -X POST http://localhost:8002/ingest \
  -F "file=@aws-support-guide.pdf"

# Ask a question via API
curl -X POST http://localhost:8001/ask/multi-candidate \
  -H "Content-Type: application/json" \
  -d '{"question": "What is AWS Support?", "num_candidates": 3, "publish_events": true}'

# Or use the Streamlit UI
# Open http://localhost:8501 in your browser
```

---

## 📋 View Logs

### All Services
```bash
./runpod_docker_deploy.sh logs
```

### Specific Service (inside container)
```bash
# Open shell
./runpod_docker_deploy.sh shell

# View supervisor logs
tail -f /var/log/supervisor/qa-orchestrator.log
tail -f /var/log/supervisor/verification-worker.log
tail -f /var/log/supervisor/dataset-worker.log
tail -f /var/log/supervisor/streamlit.log
```

---

## 📊 Check DPO Dataset

```bash
# Open shell in container
./runpod_docker_deploy.sh shell

# Inside container
cat /app/data/dpo_data/dpo_data_*.jsonl | wc -l

# View latest DPO pairs
tail -3 /app/data/dpo_data/dpo_data_*.jsonl
```

---

## 🔧 Troubleshooting

### Container won't start
```bash
# Check Docker logs
docker logs rlvr-all-in-one

# Check if ports are already in use
netstat -tulpn | grep -E '8501|8000|8001|8002|6333|11434'
```

### Service not running inside container
```bash
# Open shell
./runpod_docker_deploy.sh shell

# Check supervisor status
supervisorctl status

# Restart a specific service
supervisorctl restart qa-orchestrator

# View service logs
tail -50 /var/log/supervisor/qa-orchestrator.log
```

### GPU not detected
```bash
# Check if GPU is available in container
./runpod_docker_deploy.sh shell
nvidia-smi

# If not working, ensure docker-compose has GPU configuration
```

---

## 💾 Data Persistence

Data is persisted in Docker volumes and host directories:

```yaml
volumes:
  - ./data:/workspace/rlvr-automation/data          # Training/DPO data
  - ./qdrant_storage:/workspace/qdrant_storage    # Vector DB
  - ollama_models:/root/.ollama                   # LLM models
```

**Important:** DPO data is written to `/app/data/dpo_data/` inside the container. To persist it:

```bash
# Copy from container to host
docker cp rlvr-all-in-one:/app/data/dpo_data ./data/

# Or mount it in docker-compose.runpod.yml:
# - ./data/dpo_data:/app/data/dpo_data
```

---

## 🔄 Update Code

### Development Mode (code mounted as volume)
```bash
# Edit code on host
vim services/qa-orchestrator/src/qa_service.py

# Restart service in container
./runpod_docker_deploy.sh shell
supervisorctl restart qa-orchestrator
```

### Production Mode (rebuild image)
```bash
# Rebuild image with new code
./runpod_docker_deploy.sh build

# Restart container
./runpod_docker_deploy.sh restart
```

---

## 🆚 Docker vs Native Deployment

| Aspect | Docker (All-in-One) | Native |
|--------|---------------------|--------|
| Setup | Single command | Multiple steps |
| Isolation | Fully isolated | Shares host |
| Updates | Rebuild image | Git pull + restart |
| Debugging | Need shell access | Direct access |
| Performance | Slight overhead | Native speed |
| Portability | Highly portable | Platform-specific |

**Recommendation:** Use Docker for production, Native for development/debugging.

---

## 🎯 Next Steps

1. ✅ Build and start the container
2. ✅ Upload your PDF documents
3. ✅ Ask questions via UI or API
4. ✅ Monitor DPO dataset generation
5. ✅ Use dataset for fine-tuning

