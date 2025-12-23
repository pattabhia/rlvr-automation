#!/bin/bash
set -e

echo "🚀 RLVR Automation - RunPod Deployment with Observability"
echo "=========================================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create directories
mkdir -p /workspace/observability/{prometheus,loki,tempo,grafana}
mkdir -p /workspace/logs

echo -e "${GREEN}✅ Step 1: Installing system dependencies${NC}"
apt-get update
apt-get install -y wget curl tar unzip

echo -e "${GREEN}✅ Step 2: Installing Ollama${NC}"
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.ai/install.sh | sh
    echo "Ollama installed"
else
    echo "Ollama already installed"
fi

# Start Ollama in background
OLLAMA_HOST=0.0.0.0:11434 ollama serve > /workspace/logs/ollama.log 2>&1 &
sleep 5

# Pull model
echo "Pulling llama3.2:3b model..."
ollama pull llama3.2:3b

echo -e "${GREEN}✅ Step 3: Installing Qdrant${NC}"
if [ ! -f /usr/local/bin/qdrant ]; then
    wget https://github.com/qdrant/qdrant/releases/download/v1.7.4/qdrant-x86_64-unknown-linux-gnu.tar.gz
    tar xzf qdrant-x86_64-unknown-linux-gnu.tar.gz
    mv qdrant /usr/local/bin/
    rm qdrant-x86_64-unknown-linux-gnu.tar.gz
fi

# Start Qdrant
qdrant > /workspace/logs/qdrant.log 2>&1 &
sleep 3

echo -e "${GREEN}✅ Step 4: Installing RabbitMQ${NC}"
if ! command -v rabbitmq-server &> /dev/null; then
    apt-get install -y rabbitmq-server
fi

# Start RabbitMQ
rabbitmq-server -detached
sleep 5

# Configure RabbitMQ
rabbitmqctl add_user rlvr rlvr_password || true
rabbitmqctl set_permissions -p / rlvr ".*" ".*" ".*" || true

echo -e "${GREEN}✅ Step 5: Installing Prometheus${NC}"
if [ ! -f /workspace/observability/prometheus/prometheus ]; then
    cd /workspace/observability/prometheus
    wget https://github.com/prometheus/prometheus/releases/download/v2.48.0/prometheus-2.48.0.linux-amd64.tar.gz
    tar xzf prometheus-2.48.0.linux-amd64.tar.gz --strip-components=1
    rm prometheus-2.48.0.linux-amd64.tar.gz
fi

# Create Prometheus config
cat > /workspace/observability/prometheus/prometheus.yml <<EOF
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
./prometheus --config.file=prometheus.yml --storage.tsdb.path=/workspace/observability/prometheus/data > /workspace/logs/prometheus.log 2>&1 &

echo -e "${GREEN}✅ Step 6: Installing Loki${NC}"
if [ ! -f /workspace/observability/loki/loki ]; then
    cd /workspace/observability/loki
    wget https://github.com/grafana/loki/releases/download/v2.9.3/loki-linux-amd64.zip
    unzip loki-linux-amd64.zip
    chmod +x loki-linux-amd64
    mv loki-linux-amd64 loki
    rm loki-linux-amd64.zip
fi

# Create Loki config
cat > /workspace/observability/loki/loki-config.yml <<EOF
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
./loki -config.file=loki-config.yml > /workspace/logs/loki.log 2>&1 &

echo -e "${GREEN}✅ Step 7: Installing Tempo${NC}"
if [ ! -f /workspace/observability/tempo/tempo ]; then
    cd /workspace/observability/tempo
    wget https://github.com/grafana/tempo/releases/download/v2.3.1/tempo_2.3.1_linux_amd64.tar.gz
    tar xzf tempo_2.3.1_linux_amd64.tar.gz
    rm tempo_2.3.1_linux_amd64.tar.gz
fi

# Create Tempo config
cat > /workspace/observability/tempo/tempo-config.yml <<EOF
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
./tempo -config.file=tempo-config.yml > /workspace/logs/tempo.log 2>&1 &

echo -e "${GREEN}✅ Step 8: Installing Grafana${NC}"
if [ ! -d /workspace/observability/grafana/bin ]; then
    cd /workspace/observability/grafana
    wget https://dl.grafana.com/oss/release/grafana-10.2.2.linux-amd64.tar.gz
    tar xzf grafana-10.2.2.linux-amd64.tar.gz --strip-components=1
    rm grafana-10.2.2.linux-amd64.tar.gz
fi

# Start Grafana
cd /workspace/observability/grafana
./bin/grafana-server > /workspace/logs/grafana.log 2>&1 &

echo -e "${GREEN}✅ Step 9: Installing OpenTelemetry Collector${NC}"
if [ ! -f /workspace/observability/otel-collector ]; then
    cd /workspace/observability
    wget https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.91.0/otelcol_0.91.0_linux_amd64.tar.gz
    tar xzf otelcol_0.91.0_linux_amd64.tar.gz
    rm otelcol_0.91.0_linux_amd64.tar.gz
fi

# Create OpenTelemetry Collector config
cat > /workspace/observability/otel-collector-config.yml <<EOF
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
    send_batch_size: 1024

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"
  
  loki:
    endpoint: http://localhost:3100/loki/api/v1/push
  
  otlp/tempo:
    endpoint: localhost:4317
    tls:
      insecure: true

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
./otelcol --config=otel-collector-config.yml > /workspace/logs/otel-collector.log 2>&1 &

sleep 5

echo -e "${GREEN}✅ Step 10: Installing Python dependencies${NC}"
pip install -r requirements.txt

# Install OpenTelemetry packages
pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation \
    opentelemetry-instrumentation-fastapi opentelemetry-instrumentation-httpx \
    opentelemetry-instrumentation-pika opentelemetry-exporter-otlp

echo -e "${GREEN}✅ Step 11: Starting microservices${NC}"

# Set environment variables
export QDRANT_URL="http://localhost:6333"
export RABBITMQ_URL="amqp://rlvr:rlvr_password@localhost:5672/"
export OLLAMA_BASE_URL="http://localhost:11434"
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"

# Start services
cd services/api-gateway
uvicorn src.main:app --host 0.0.0.0 --port 8000 > /workspace/logs/api-gateway.log 2>&1 &

cd ../qa-orchestrator
uvicorn src.main:app --host 0.0.0.0 --port 8001 > /workspace/logs/qa-orchestrator.log 2>&1 &

cd ../document-ingestion
uvicorn src.main:app --host 0.0.0.0 --port 8002 > /workspace/logs/document-ingestion.log 2>&1 &

cd ../training-data
uvicorn src.main:app --host 0.0.0.0 --port 8005 > /workspace/logs/training-data.log 2>&1 &

cd ../ground-truth
uvicorn src.main:app --host 0.0.0.0 --port 8007 > /workspace/logs/ground-truth.log 2>&1 &

echo -e "${GREEN}✅ Step 12: Starting workers${NC}"
cd ../../workers/verification-worker
python src/worker.py > /workspace/logs/verification-worker.log 2>&1 &

cd ../reward-computation-worker
python src/worker.py > /workspace/logs/reward-worker.log 2>&1 &

cd ../dataset-generation-worker
python src/worker.py > /workspace/logs/dataset-worker.log 2>&1 &

echo -e "${GREEN}✅ Step 13: Starting Streamlit UI${NC}"
cd ../../ui/streamlit
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 > /workspace/logs/streamlit.log 2>&1 &

sleep 5

echo ""
echo "=========================================================="
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo "=========================================================="
echo ""
echo "📊 Access your services:"
echo "  - Streamlit UI:    http://$(curl -s ifconfig.me):8501"
echo "  - API Gateway:     http://$(curl -s ifconfig.me):8000/docs"
echo "  - Grafana:         http://$(curl -s ifconfig.me):3000 (admin/admin)"
echo "  - Prometheus:      http://$(curl -s ifconfig.me):9090"
echo ""
echo "📝 Logs location: /workspace/logs/"
echo ""
echo "🔍 Check service status:"
echo "  ps aux | grep -E 'ollama|qdrant|rabbitmq|uvicorn|streamlit|prometheus|grafana'"
echo ""

