#!/bin/bash
set -e

echo "=========================================="
echo "🚀 RLVR Native Start (No Docker-in-Docker)"
echo "=========================================="

# Check GPU
echo ""
echo "🔍 GPU Info:"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

# Install system dependencies
echo ""
echo "📦 Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq \
    curl \
    wget \
    postgresql-client \
    rabbitmq-server \
    redis-server

# Install Ollama
echo ""
echo "📦 Installing Ollama..."
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
fi

# Start Ollama with GPU
echo ""
echo "🚀 Starting Ollama with GPU..."
export OLLAMA_HOST=0.0.0.0:11434
export OLLAMA_GPU_LAYERS=999
pkill ollama || true
ollama serve > /tmp/ollama.log 2>&1 &
OLLAMA_PID=$!
echo "Ollama PID: $OLLAMA_PID"
sleep 10

# Pull model
echo ""
echo "📥 Pulling Llama 3.2:3b model..."
ollama pull llama3.2:3b

# Verify Ollama
echo ""
echo "✅ Verifying Ollama..."
curl -s http://localhost:11434/api/tags | head -20

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
cd /workspace/rlvr-automation

# Install all service dependencies (in correct order to avoid conflicts)
pip install -q --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    pydantic==2.5.0 \
    pydantic-settings==2.1.0 \
    sentence-transformers==2.7.0 \
    qdrant-client==1.7.0 \
    pdfplumber==0.10.3 \
    pika==1.3.2 \
    streamlit==1.29.0 \
    requests==2.31.0 \
    python-multipart==0.0.6 \
    psycopg2-binary==2.9.9 \
    python-dotenv==1.0.0

# Install langchain and RAGAS dependencies (separate to avoid conflicts)
pip install -q --no-cache-dir \
    langchain==0.2.0 \
    langchain-core==0.2.20 \
    langchain-community==0.2.0 \
    langchain-huggingface==0.0.1 \
    datasets==2.16.1

# Install ollama and langchain-ollama (compatible versions)
pip install -q --no-cache-dir \
    ollama \
    langchain-ollama

# Install RAGAS last
pip install -q --no-cache-dir ragas==0.1.9

# Start RabbitMQ
echo ""
echo "🐰 Starting RabbitMQ..."
service rabbitmq-server start
sleep 5

# Create RabbitMQ user
echo ""
echo "👤 Setting up RabbitMQ user..."
rabbitmqctl add_user rlvr rlvr_password || true
rabbitmqctl set_permissions -p / rlvr ".*" ".*" ".*" || true

# Start Qdrant (using Docker if available, otherwise skip)
echo ""
echo "🔍 Starting Qdrant..."
if command -v docker &> /dev/null && docker info &> /dev/null; then
    docker run -d --name qdrant -p 6333:6333 -p 6334:6334 \
        -v $(pwd)/data/qdrant_storage:/qdrant/storage \
        qdrant/qdrant:latest || echo "⚠️  Qdrant already running or failed"
else
    echo "⚠️  Docker not available, skipping Qdrant (will use in-memory mode)"
fi

# Start PostgreSQL (if available)
echo ""
echo "🗄️  Starting PostgreSQL..."
service postgresql start || echo "⚠️  PostgreSQL not available"

# Create data directories
mkdir -p /workspace/rlvr-automation/data/{training_data,dpo_data,uploads,qdrant_storage}

# Set environment variables
export PYTHONPATH=/workspace/rlvr-automation
export RABBITMQ_URL=amqp://rlvr:rlvr_password@localhost:5672/
export OLLAMA_HOST=http://localhost:11434
export QDRANT_URL=http://localhost:6333

echo ""
echo "=========================================="
echo "✅ Infrastructure Ready!"
echo "=========================================="
echo ""
echo "🎯 Next: Start services manually in separate terminals"
echo ""
echo "Terminal 1 - QA Orchestrator:"
echo "  cd /workspace/rlvr-automation/services/qa-orchestrator/src"
echo "  OLLAMA_HOST=http://localhost:11434 uvicorn main:app --host 0.0.0.0 --port 8001"
echo ""
echo "Terminal 2 - Verification Worker:"
echo "  cd /workspace/rlvr-automation/workers/verification-worker/src"
echo "  RABBITMQ_URL=amqp://rlvr:rlvr_password@localhost:5672/ OLLAMA_HOST=http://localhost:11434 python -m worker"
echo ""
echo "Terminal 3 - Dataset Worker:"
echo "  cd /workspace/rlvr-automation/workers/dataset-generation-worker/src"
echo "  RABBITMQ_URL=amqp://rlvr:rlvr_password@localhost:5672/ python -m worker"
echo ""
echo "Terminal 4 - Streamlit UI:"
echo "  cd /workspace/rlvr-automation/ui/streamlit/src"
echo "  streamlit run app_simple.py --server.port=8501 --server.address=0.0.0.0"
echo ""
echo "📊 Or use the all-in-one launcher:"
echo "  ./runpod_launch_all.sh"
echo ""

