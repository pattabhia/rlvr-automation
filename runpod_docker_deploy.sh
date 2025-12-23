#!/bin/bash

echo "🐳 RLVR RunPod Docker Deployment"
echo "=================================="
echo ""

# Check if docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed!"
    echo "This script requires Docker to be available."
    exit 1
fi

# Parse command line arguments
ACTION=${1:-"start"}

case $ACTION in
    build)
        echo "🔨 Building Docker image..."
        docker build -f Dockerfile.runpod -t rlvr-all-in-one:latest .
        
        if [ $? -eq 0 ]; then
            echo "✅ Docker image built successfully!"
            echo ""
            echo "Image details:"
            docker images | grep rlvr-all-in-one
        else
            echo "❌ Docker build failed!"
            exit 1
        fi
        ;;
    
    start)
        echo "🚀 Starting RLVR services in Docker..."
        
        # Create data directories
        mkdir -p data/training_data data/dpo_data data/uploads qdrant_storage
        
        # Start with docker-compose
        docker-compose -f docker-compose.runpod.yml up -d
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "✅ Services started!"
            echo ""
            echo "⏳ Waiting for services to initialize (this may take 2-3 minutes)..."
            sleep 30
            
            echo ""
            echo "📊 Container status:"
            docker-compose -f docker-compose.runpod.yml ps
            
            echo ""
            echo "🏥 Health checks (waiting 60s for startup)..."
            sleep 60
            
            echo "Checking services..."
            curl -sf http://localhost:6333/collections > /dev/null 2>&1 && echo "  ✅ Qdrant" || echo "  ⏳ Qdrant (still starting...)"
            curl -sf http://localhost:11434/api/tags > /dev/null 2>&1 && echo "  ✅ Ollama" || echo "  ⏳ Ollama (still starting...)"
            curl -sf http://localhost:8002/health > /dev/null 2>&1 && echo "  ✅ Document Ingestion" || echo "  ⏳ Document Ingestion (still starting...)"
            curl -sf http://localhost:8001/health > /dev/null 2>&1 && echo "  ✅ QA Orchestrator" || echo "  ⏳ QA Orchestrator (still starting...)"
            curl -sf http://localhost:8000/health > /dev/null 2>&1 && echo "  ✅ API Gateway" || echo "  ⏳ API Gateway (still starting...)"
            curl -sf http://localhost:8501 > /dev/null 2>&1 && echo "  ✅ Streamlit UI" || echo "  ⏳ Streamlit UI (still starting...)"
            
            echo ""
            echo "📋 View logs:"
            echo "  docker-compose -f docker-compose.runpod.yml logs -f"
            echo "  docker-compose -f docker-compose.runpod.yml logs -f rlvr-all-in-one"
            echo ""
            echo "📊 Access URLs:"
            echo "  🌐 Streamlit UI:    http://localhost:8501"
            echo "  📚 API Gateway:     http://localhost:8000/docs"
            echo "  🤖 QA Orchestrator: http://localhost:8001/docs"
            echo "  📄 Doc Ingestion:   http://localhost:8002/docs"
            echo "  🗄️  Qdrant:          http://localhost:6333/dashboard"
            echo ""
        else
            echo "❌ Failed to start services!"
            exit 1
        fi
        ;;
    
    stop)
        echo "🛑 Stopping RLVR services..."
        docker-compose -f docker-compose.runpod.yml down
        echo "✅ Services stopped!"
        ;;
    
    restart)
        echo "🔄 Restarting RLVR services..."
        docker-compose -f docker-compose.runpod.yml restart
        echo "✅ Services restarted!"
        ;;
    
    logs)
        echo "📋 Showing logs (Ctrl+C to exit)..."
        docker-compose -f docker-compose.runpod.yml logs -f
        ;;
    
    status)
        echo "📊 Service status:"
        docker-compose -f docker-compose.runpod.yml ps
        echo ""
        echo "🏥 Health checks:"
        curl -sf http://localhost:6333/collections > /dev/null 2>&1 && echo "  ✅ Qdrant" || echo "  ❌ Qdrant"
        curl -sf http://localhost:11434/api/tags > /dev/null 2>&1 && echo "  ✅ Ollama" || echo "  ❌ Ollama"
        curl -sf http://localhost:8002/health > /dev/null 2>&1 && echo "  ✅ Document Ingestion" || echo "  ❌ Document Ingestion"
        curl -sf http://localhost:8001/health > /dev/null 2>&1 && echo "  ✅ QA Orchestrator" || echo "  ❌ QA Orchestrator"
        curl -sf http://localhost:8000/health > /dev/null 2>&1 && echo "  ✅ API Gateway" || echo "  ❌ API Gateway"
        curl -sf http://localhost:8501 > /dev/null 2>&1 && echo "  ✅ Streamlit UI" || echo "  ❌ Streamlit UI"
        ;;
    
    shell)
        echo "🐚 Opening shell in container..."
        docker-compose -f docker-compose.runpod.yml exec rlvr-all-in-one /bin/bash
        ;;
    
    clean)
        echo "🧹 Cleaning up Docker resources..."
        docker-compose -f docker-compose.runpod.yml down -v
        docker rmi rlvr-all-in-one:latest 2>/dev/null || true
        echo "✅ Cleanup complete!"
        ;;
    
    *)
        echo "Usage: $0 {build|start|stop|restart|logs|status|shell|clean}"
        echo ""
        echo "Commands:"
        echo "  build   - Build the Docker image"
        echo "  start   - Start all services (default)"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  logs    - View logs (follow mode)"
        echo "  status  - Check service status"
        echo "  shell   - Open shell in container"
        echo "  clean   - Stop and remove all containers and images"
        exit 1
        ;;
esac

