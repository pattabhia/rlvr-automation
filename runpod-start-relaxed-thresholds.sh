#!/bin/bash

echo "=========================================="
echo "  RLVR AUTOMATION - RUNPOD STARTUP"
echo "  (RELAXED DPO THRESHOLDS)"
echo "=========================================="
echo ""

# Set RabbitMQ URL for localhost (using rlvr credentials)
export RABBITMQ_URL="amqp://rlvr:rlvr_password@localhost:5672/"

# RELAXED DPO thresholds to match actual data
export MIN_SCORE_DIFF=0.05  # Was 0.3, now 0.05 (you're seeing 0.025-0.105)
export MIN_CHOSEN_SCORE=0.6  # Was 0.7, now 0.6 (you're seeing 0.640-0.675)
export ENABLE_QUALITY_FILTER=false  # Disable verbatim test for now

echo "DPO Configuration (RELAXED for testing):"
echo "  MIN_SCORE_DIFF: $MIN_SCORE_DIFF (was 0.3)"
echo "  MIN_CHOSEN_SCORE: $MIN_CHOSEN_SCORE (was 0.7)"
echo "  ENABLE_QUALITY_FILTER: $ENABLE_QUALITY_FILTER (was true)"
echo ""

# Create log directory
mkdir -p /workspace/logs

# Stop any existing workers
echo "1. Stopping existing workers..."
pkill -f "verification-worker" 2>/dev/null
pkill -f "dataset-generation-worker" 2>/dev/null
sleep 2

# Start Verification Worker
echo ""
echo "2. Starting Verification Worker..."
cd /workspace/rlvr-automation/workers/verification-worker
RABBITMQ_URL="amqp://rlvr:rlvr_password@localhost:5672/" \
nohup python -m src.worker > /workspace/logs/verification-worker.log 2>&1 &
VERIFY_PID=$!
sleep 3

# Check verification worker
if grep -q "Consumer started" /workspace/logs/verification-worker.log 2>/dev/null; then
    echo "   ✅ Verification worker connected (PID: $VERIFY_PID)"
else
    echo "   ⚠️  Verification worker may have issues"
    echo "   Last 5 lines of log:"
    tail -5 /workspace/logs/verification-worker.log
fi

# Start Dataset Worker with RELAXED thresholds
echo ""
echo "3. Starting Dataset Worker (with relaxed thresholds)..."
cd /workspace/rlvr-automation/workers/dataset-generation-worker
RABBITMQ_URL="amqp://rlvr:rlvr_password@localhost:5672/" \
MIN_SCORE_DIFF=$MIN_SCORE_DIFF \
MIN_CHOSEN_SCORE=$MIN_CHOSEN_SCORE \
ENABLE_QUALITY_FILTER=$ENABLE_QUALITY_FILTER \
nohup python -m src.worker > /workspace/logs/dataset-worker.log 2>&1 &
DATASET_PID=$!
sleep 3

# Check dataset worker
if ps -p $DATASET_PID > /dev/null 2>&1; then
    echo "   ✅ Dataset worker running (PID: $DATASET_PID)"
else
    echo "   ⚠️  Dataset worker failed"
    echo "   Last 5 lines of log:"
    tail -5 /workspace/logs/dataset-worker.log
fi

echo ""
echo "=========================================="
echo "  ✅ WORKERS STARTED!"
echo "=========================================="
echo ""
echo "Worker Status:"
echo "  • Verification Worker: PID $VERIFY_PID"
echo "  • Dataset Worker:      PID $DATASET_PID"
echo ""
echo "DPO Thresholds (RELAXED):"
echo "  • MIN_SCORE_DIFF:      $MIN_SCORE_DIFF (was 0.3)"
echo "  • MIN_CHOSEN_SCORE:    $MIN_CHOSEN_SCORE (was 0.7)"
echo "  • QUALITY_FILTER:      $ENABLE_QUALITY_FILTER (was true)"
echo ""
echo "Next Steps:"
echo "  1. Send a test query:"
echo "     curl -X POST http://localhost:8001/ask/multi-candidate \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"question\": \"What is AWS Lambda?\", \"num_candidates\": 3}'"
echo ""
echo "  2. Wait 30 seconds, then check:"
echo "     ./check-if-fixed.sh"
echo ""
echo "  3. Monitor logs:"
echo "     tail -f /workspace/logs/verification-worker.log"
echo "     tail -f /workspace/logs/dataset-worker.log"
echo ""
echo "NOTE: These are RELAXED thresholds for testing."
echo "      Once DPO files are being created, you can gradually"
echo "      increase the thresholds for better quality."
echo ""

