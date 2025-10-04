FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/qa-orchestrator/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY services/qa-orchestrator/src/ ./src/

# Copy shared libraries
COPY shared /app/shared

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8001

# Run the service
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]

