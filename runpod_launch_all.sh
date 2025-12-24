#!/bin/bash

echo "🚀 Launching all RLVR services for native RunPod deployment with Observability..."
echo ""

# Kill any conflicting services from RunPod base image
echo "🛑 Stopping conflicting services..."
pkill nginx || true
pkill -f uvicorn || true
pkill -f streamlit || true
pkill -f "python -m src.worker" || true
pkill -f qdrant || true
pkill -f prometheus || true
pkill -f grafana || true
pkill -f loki || true
pkill -f tempo || true
pkill -f otelcol || true
pkill -f rabbitmq || true
sleep 2

# Create directories for observability
echo "📁 Creating directories..."
mkdir -p /workspace/observability/{prometheus,loki,tempo,grafana}
mkdir -p /workspace/logs
mkdir -p /workspace/qdrant_storage

# Set environment variables for native deployment (localhost instead of Docker service names)
echo "⚙️  Setting environment variables..."
export PYTHONPATH=/workspace/rlvr-automation
export RABBITMQ_URL=amqp://rlvr:rlvr_password@localhost:5672/
export OLLAMA_HOST=http://localhost:11434
export OLLAMA_URL=http://localhost:11434
export OLLAMA_MODEL=llama3.2:3b
export QDRANT_URL=http://localhost:6333
export QDRANT_HOST=localhost
export QDRANT_PORT=6333
export MIN_SCORE_DIFF=0.3
export MIN_CHOSEN_SCORE=0.7
export ENABLE_QUALITY_FILTER=true
export TIMEOUT_MINUTES=30
export TRAINING_DATA_DIR=/workspace/rlvr-automation/data/training_data
export DPO_DATA_DIR=/workspace/rlvr-automation/data/dpo_data
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export ENVIRONMENT=production

# API Gateway service URLs (localhost for native deployment)
export QA_ORCHESTRATOR_URL=http://localhost:8001
export DOC_INGESTION_SERVICE_URL=http://localhost:8002
export TRAINING_DATA_SERVICE_URL=http://localhost:8005
export GROUND_TRUTH_SERVICE_URL=http://localhost:8007

cd /workspace/rlvr-automation

# Install system dependencies for observability
echo "📦 Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq wget curl tar unzip erlang-nox rabbitmq-server > /dev/null 2>&1

# Install Ollama if not present
if ! command -v ollama &> /dev/null; then
    echo "📦 Installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | sh
    echo "✅ Ollama installed"
else
    echo "✅ Ollama already installed"
fi

# Start Ollama
echo "🤖 Starting Ollama..."
OLLAMA_HOST=0.0.0.0:11434 nohup ollama serve > /workspace/logs/ollama.log 2>&1 &
echo "   Ollama PID: $!"
sleep 5

# Pull Ollama model
echo "📥 Pulling llama3.2:3b model..."
ollama pull llama3.2:3b

# Install Qdrant if not present
if ! command -v qdrant &> /dev/null; then
    echo "📦 Installing Qdrant binary..."
    cd /tmp
    wget -q https://github.com/qdrant/qdrant/releases/download/v1.7.4/qdrant-x86_64-unknown-linux-gnu.tar.gz
    tar -xzf qdrant-x86_64-unknown-linux-gnu.tar.gz
    mv qdrant /usr/local/bin/
    chmod +x /usr/local/bin/qdrant
    rm qdrant-x86_64-unknown-linux-gnu.tar.gz
    cd /workspace/rlvr-automation
    echo "✅ Qdrant installed"
else
    echo "✅ Qdrant already installed"
fi

# Start Qdrant (vector database)
echo "🗄️  Starting Qdrant..."
cd /workspace/qdrant_storage
nohup /usr/local/bin/qdrant > /workspace/logs/qdrant.log 2>&1 &
echo "   Qdrant PID: $!"
cd /workspace/rlvr-automation
sleep 5

# Start RabbitMQ
echo "🐰 Starting RabbitMQ..."
service rabbitmq-server start > /dev/null 2>&1 || rabbitmq-server -detached
sleep 5

# Configure RabbitMQ user
echo "⚙️  Configuring RabbitMQ..."
rabbitmqctl add_user rlvr rlvr_password 2>/dev/null || true
rabbitmqctl set_permissions -p / rlvr ".*" ".*" ".*" 2>/dev/null || true
rabbitmqctl set_user_tags rlvr administrator 2>/dev/null || true
rabbitmq-plugins enable rabbitmq_management 2>/dev/null || true
echo "✅ RabbitMQ configured"

# Install Prometheus
echo "📊 Installing Prometheus..."
if [ ! -f /workspace/observability/prometheus/prometheus ]; then
    cd /workspace/observability/prometheus
    wget -q https://github.com/prometheus/prometheus/releases/download/v2.48.0/prometheus-2.48.0.linux-amd64.tar.gz
    tar xzf prometheus-2.48.0.linux-amd64.tar.gz --strip-components=1
    rm prometheus-2.48.0.linux-amd64.tar.gz
    echo "✅ Prometheus installed"
else
    echo "✅ Prometheus already installed"
fi

# Create Prometheus config
cat > /workspace/observability/prometheus/prometheus.yml <<'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'otel-collector'
    static_configs:
      - targets: ['localhost:8889']

  - job_name: 'rabbitmq'
    static_configs:
      - targets: ['localhost:15692']
EOF

# Start Prometheus
cd /workspace/observability/prometheus
nohup ./prometheus --config.file=prometheus.yml --storage.tsdb.path=/workspace/observability/prometheus/data > /workspace/logs/prometheus.log 2>&1 &
echo "   Prometheus PID: $!"
cd /workspace/rlvr-automation

# Install Loki
echo "📝 Installing Loki..."
if [ ! -f /workspace/observability/loki/loki ]; then
    cd /workspace/observability/loki
    wget -q https://github.com/grafana/loki/releases/download/v2.9.3/loki-linux-amd64.zip
    unzip -q loki-linux-amd64.zip
    chmod +x loki-linux-amd64
    mv loki-linux-amd64 loki
    rm loki-linux-amd64.zip
    echo "✅ Loki installed"
else
    echo "✅ Loki already installed"
fi

# Create Loki config
cat > /workspace/observability/loki/loki-config.yml <<'EOF'
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096

common:
  path_prefix: /workspace/observability/loki
  storage:
    filesystem:
      chunks_directory: /workspace/observability/loki/chunks
      rules_directory: /workspace/observability/loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h
EOF

# Start Loki
cd /workspace/observability/loki
nohup ./loki -config.file=loki-config.yml > /workspace/logs/loki.log 2>&1 &
echo "   Loki PID: $!"
cd /workspace/rlvr-automation

# Install Tempo
echo "🔍 Installing Tempo..."
if [ ! -f /workspace/observability/tempo/tempo ]; then
    cd /workspace/observability/tempo
    wget -q https://github.com/grafana/tempo/releases/download/v2.3.1/tempo_2.3.1_linux_amd64.tar.gz
    tar xzf tempo_2.3.1_linux_amd64.tar.gz
    rm tempo_2.3.1_linux_amd64.tar.gz
    echo "✅ Tempo installed"
else
    echo "✅ Tempo already installed"
fi

# Create Tempo config
cat > /workspace/observability/tempo/tempo-config.yml <<'EOF'
server:
  http_listen_port: 3200

distributor:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317
        http:
          endpoint: 0.0.0.0:4318

storage:
  trace:
    backend: local
    local:
      path: /workspace/observability/tempo/traces
    wal:
      path: /workspace/observability/tempo/wal
EOF

# Start Tempo
cd /workspace/observability/tempo
nohup ./tempo -config.file=tempo-config.yml > /workspace/logs/tempo.log 2>&1 &
echo "   Tempo PID: $!"
cd /workspace/rlvr-automation

# Install Grafana
echo "📈 Installing Grafana..."
if [ ! -d /workspace/observability/grafana/bin ]; then
    cd /workspace/observability/grafana
    wget -q https://dl.grafana.com/oss/release/grafana-10.2.2.linux-amd64.tar.gz
    tar xzf grafana-10.2.2.linux-amd64.tar.gz --strip-components=1
    rm grafana-10.2.2.linux-amd64.tar.gz
    echo "✅ Grafana installed"
else
    echo "✅ Grafana already installed"
fi

# Start Grafana
cd /workspace/observability/grafana
nohup ./bin/grafana-server > /workspace/logs/grafana.log 2>&1 &
echo "   Grafana PID: $!"
cd /workspace/rlvr-automation

# Install OpenTelemetry Collector
echo "🔭 Installing OpenTelemetry Collector..."
if [ ! -f /workspace/observability/otelcol ]; then
    cd /workspace/observability
    wget -q https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.91.0/otelcol_0.91.0_linux_amd64.tar.gz
    tar xzf otelcol_0.91.0_linux_amd64.tar.gz
    rm otelcol_0.91.0_linux_amd64.tar.gz
    echo "✅ OpenTelemetry Collector installed"
else
    echo "✅ OpenTelemetry Collector already installed"
fi

# Create OpenTelemetry Collector config
cat > /workspace/observability/otel-collector-config.yml <<'EOF'
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 10s

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"

  otlp/tempo:
    endpoint: localhost:4317
    tls:
      insecure: true

  loki:
    endpoint: http://localhost:3100/loki/api/v1/push

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [batch]
      exporters: [otlp/tempo]

    metrics:
      receivers: [otlp]
      processors: [batch]
      exporters: [prometheus]

    logs:
      receivers: [otlp]
      processors: [batch]
      exporters: [loki]
EOF

# Start OpenTelemetry Collector
cd /workspace/observability
nohup ./otelcol --config=otel-collector-config.yml > /workspace/logs/otel-collector.log 2>&1 &
echo "   OpenTelemetry Collector PID: $!"
cd /workspace/rlvr-automation

sleep 5

# Install/upgrade all service dependencies to override RunPod base image packages
echo "📦 Installing service dependencies..."
pip install --upgrade -q -r services/qa-orchestrator/requirements.txt
pip install --upgrade -q -r services/api-gateway/requirements.txt
pip install --upgrade -q -r services/document-ingestion/requirements.txt
pip install --upgrade -q -r ui/streamlit/requirements.txt
pip install --upgrade -q -r workers/verification-worker/requirements.txt
pip install --upgrade -q -r workers/dataset-generation-worker/requirements.txt

# Install OpenTelemetry instrumentation
echo "📦 Installing OpenTelemetry instrumentation..."
pip install --upgrade -q opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation \
    opentelemetry-instrumentation-fastapi opentelemetry-instrumentation-httpx \
    opentelemetry-instrumentation-pika opentelemetry-exporter-otlp

echo "✅ Dependencies installed"
echo ""

# Start Document Ingestion Service
echo "📄 Starting Document Ingestion Service..."
cd /workspace/rlvr-automation/services/document-ingestion
PYTHONPATH=/workspace/rlvr-automation/services/document-ingestion:/workspace/rlvr-automation nohup uvicorn src.main:app --host 0.0.0.0 --port 8002 > /workspace/logs/document-ingestion.log 2>&1 &
echo "   Document Ingestion PID: $!"
sleep 3

# Start QA Orchestrator (with correct environment variables for native deployment)
echo "🤖 Starting QA Orchestrator..."
cd /workspace/rlvr-automation/services/qa-orchestrator
PYTHONPATH=/workspace/rlvr-automation/services/qa-orchestrator:/workspace/rlvr-automation nohup uvicorn src.main:app --host 0.0.0.0 --port 8001 > /workspace/logs/qa-orchestrator.log 2>&1 &
echo "   QA Orchestrator PID: $!"
sleep 3

# Start Verification Worker (with correct module path)
echo "✅ Starting Verification Worker..."
cd /workspace/rlvr-automation/workers/verification-worker
PYTHONPATH=/workspace/rlvr-automation/workers/verification-worker:/workspace/rlvr-automation nohup python -m src.worker > /workspace/logs/verification-worker.log 2>&1 &
echo "   Verification Worker PID: $!"
sleep 2

# Start Dataset Generation Worker (with correct module path and data directories)
echo "📊 Starting Dataset Generation Worker..."
cd /workspace/rlvr-automation/workers/dataset-generation-worker
PYTHONPATH=/workspace/rlvr-automation/workers/dataset-generation-worker:/workspace/rlvr-automation nohup python -m src.worker > /workspace/logs/dataset-worker.log 2>&1 &
echo "   Dataset Worker PID: $!"
sleep 2

# Start API Gateway
echo "🌐 Starting API Gateway..."
cd /workspace/rlvr-automation/services/api-gateway
PYTHONPATH=/workspace/rlvr-automation/services/api-gateway:/workspace/rlvr-automation nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 > /workspace/logs/api-gateway.log 2>&1 &
echo "   API Gateway PID: $!"
sleep 3

# Start Streamlit UI
echo "🎨 Starting Streamlit UI..."
cd /workspace/rlvr-automation/ui/streamlit
PYTHONPATH=/workspace/rlvr-automation/ui/streamlit:/workspace/rlvr-automation nohup streamlit run src/app_simple.py > /workspace/logs/streamlit.log 2>&1 &
echo "   Streamlit UI PID: $!"

echo ""
echo "⏳ Waiting for services to initialize..."
sleep 10

echo ""
echo "=========================================="
echo "✅ All services started!"
echo "=========================================="
echo ""
echo "🏥 Running health checks..."
sleep 5

# Health checks with better error handling
echo ""
echo "Service Status:"
curl -sf http://localhost:6333/collections > /dev/null 2>&1 && echo "  ✅ Qdrant (Vector DB)" || echo "  ❌ Qdrant - Check /workspace/logs/qdrant.log"
curl -sf http://localhost:11434/api/tags > /dev/null 2>&1 && echo "  ✅ Ollama (LLM)" || echo "  ❌ Ollama - Check /workspace/logs/ollama.log"
curl -sf http://localhost:8002/health > /dev/null 2>&1 && echo "  ✅ Document Ingestion" || echo "  ❌ Document Ingestion - Check /workspace/logs/document-ingestion.log"
curl -sf http://localhost:8001/health > /dev/null 2>&1 && echo "  ✅ QA Orchestrator" || echo "  ❌ QA Orchestrator - Check /workspace/logs/qa-orchestrator.log"
curl -sf http://localhost:8000/health > /dev/null 2>&1 && echo "  ✅ API Gateway" || echo "  ❌ API Gateway - Check /workspace/logs/api-gateway.log"
curl -sf http://localhost:8501 > /dev/null 2>&1 && echo "  ✅ Streamlit UI" || echo "  ❌ Streamlit UI - Check /workspace/logs/streamlit.log"

# Check workers
ps aux | grep -q "python -m src.worker" && echo "  ✅ Background Workers (2 running)" || echo "  ❌ Workers - Check /workspace/logs/verification-worker.log and /workspace/logs/dataset-worker.log"

# Check observability stack
curl -sf http://localhost:9090/-/healthy > /dev/null 2>&1 && echo "  ✅ Prometheus" || echo "  ❌ Prometheus - Check /workspace/logs/prometheus.log"
curl -sf http://localhost:3000/api/health > /dev/null 2>&1 && echo "  ✅ Grafana" || echo "  ❌ Grafana - Check /workspace/logs/grafana.log"
curl -sf http://localhost:3100/ready > /dev/null 2>&1 && echo "  ✅ Loki" || echo "  ❌ Loki - Check /workspace/logs/loki.log"
curl -sf http://localhost:3200/status > /dev/null 2>&1 && echo "  ✅ Tempo" || echo "  ❌ Tempo - Check /workspace/logs/tempo.log"
curl -sf http://localhost:15672 > /dev/null 2>&1 && echo "  ✅ RabbitMQ Management" || echo "  ❌ RabbitMQ - Check logs"

echo ""
echo "📊 Access URLs:"
echo "  🌐 Streamlit UI:        https://YOUR_RUNPOD_ID.proxy.runpod.net (port 8501)"
echo "  📚 API Gateway:         http://localhost:8000/docs"
echo "  🤖 QA Orchestrator:     http://localhost:8001/docs"
echo "  📄 Document Ingestion:  http://localhost:8002/docs"
echo "  🗄️  Qdrant Dashboard:    http://localhost:6333/dashboard"
echo ""
echo "📈 Observability Stack:"
echo "  📊 Grafana:             http://localhost:3000 (admin/admin)"
echo "  📉 Prometheus:          http://localhost:9090"
echo "  📝 Loki:                http://localhost:3100"
echo "  🔍 Tempo:               http://localhost:3200"
echo "  🐰 RabbitMQ Management: http://localhost:15672 (rlvr/rlvr_password)"
echo ""
echo "📋 View logs:"
echo "  tail -f /workspace/logs/qdrant.log"
echo "  tail -f /workspace/logs/ollama.log"
echo "  tail -f /workspace/logs/document-ingestion.log"
echo "  tail -f /workspace/logs/qa-orchestrator.log"
echo "  tail -f /workspace/logs/verification-worker.log"
echo "  tail -f /workspace/logs/dataset-worker.log"
echo "  tail -f /workspace/logs/api-gateway.log"
echo "  tail -f /workspace/logs/streamlit.log"
echo "  tail -f /workspace/logs/prometheus.log"
echo "  tail -f /workspace/logs/grafana.log"
echo "  tail -f /workspace/logs/loki.log"
echo "  tail -f /workspace/logs/tempo.log"
echo "  tail -f /workspace/logs/otel-collector.log"
echo ""
echo "📊 Data directories:"
echo "  Training data: /workspace/rlvr-automation/data/training_data/"
echo "  DPO dataset:   /workspace/rlvr-automation/data/dpo_data/"
echo "  Note: Workers also write to /app/data/ - copy files if needed"
echo ""
echo "🎯 GPU Status:"
nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader 2>/dev/null || echo "  No GPU detected"
echo ""
echo "🚀 Quick start:"
echo "  1. Upload PDF: curl -X POST http://localhost:8002/ingest -F 'file=@your-file.pdf'"
echo "  2. Ask question via UI: Open Streamlit URL above"
echo "  3. Check DPO data: cat /workspace/rlvr-automation/data/dpo_data/dpo_data_*.jsonl | wc -l"
echo "  4. View metrics in Grafana: http://localhost:3000"
echo ""

