# Dataset Generation Worker Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY workers/dataset-generation-worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy worker code
COPY workers/dataset-generation-worker/src/ ./src/

# Copy shared libraries
COPY shared /app/shared

# Set Python path
ENV PYTHONPATH=/app

# Run worker
CMD ["python", "-m", "src.worker"]

