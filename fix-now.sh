#!/bin/bash

# Emergency Fix Script - Get it working NOW

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                    EMERGENCY FIX - LET'S GET THIS WORKING                  ║"
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo ""

LOG_DIR="${LOG_DIR:-/workspace/logs}"
DATA_DIR="${DATA_DIR:-/workspace/rlvr-automation/data}"

echo "Step 1: Checking what's actually running..."
echo "────────────────────────────────────────────────────────────────────────────"
ps aux | grep -E "python.*worker|python.*orchestrator" | grep -v grep
echo ""

echo "Step 2: Checking log files..."
echo "────────────────────────────────────────────────────────────────────────────"
ls -lh $LOG_DIR/*.log 2>/dev/null || echo "NO LOG FILES FOUND!"
echo ""

echo "Step 3: Checking data directory..."
echo "────────────────────────────────────────────────────────────────────────────"
echo "DPO folder:"
ls -lh $DATA_DIR/dpo/ 2>/dev/null || echo "DPO folder is empty or doesn't exist"
echo ""
echo "Training data folder:"
ls -lh $DATA_DIR/training_data/ 2>/dev/null || echo "Training data folder is empty or doesn't exist"
echo ""

echo "Step 4: Checking last 20 lines of each log..."
echo "────────────────────────────────────────────────────────────────────────────"

if [ -f "$LOG_DIR/qa-orchestrator.log" ]; then
    echo "QA ORCHESTRATOR (last 20 lines):"
    tail -20 "$LOG_DIR/qa-orchestrator.log"
    echo ""
else
    echo "❌ qa-orchestrator.log NOT FOUND"
    echo ""
fi

if [ -f "$LOG_DIR/verification-worker.log" ]; then
    echo "VERIFICATION WORKER (last 20 lines):"
    tail -20 "$LOG_DIR/verification-worker.log"
    echo ""
else
    echo "❌ verification-worker.log NOT FOUND"
    echo ""
fi

if [ -f "$LOG_DIR/dataset-worker.log" ]; then
    echo "DATASET WORKER (last 20 lines):"
    tail -20 "$LOG_DIR/dataset-worker.log"
    echo ""
else
    echo "❌ dataset-worker.log NOT FOUND"
    echo ""
fi

echo "════════════════════════════════════════════════════════════════════════════"
echo "  DIAGNOSIS"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

# Count workers
worker_count=$(ps aux | grep -E "python.*worker|python.*orchestrator" | grep -v grep | wc -l)

if [ $worker_count -eq 0 ]; then
    echo "❌ NO WORKERS ARE RUNNING!"
    echo ""
    echo "This is why nothing is working."
    echo ""
    echo "FIX IT NOW:"
    echo "  cd /workspace/rlvr-automation"
    echo "  ./runpod-start.sh"
    echo ""
    exit 1
fi

# Check if logs have recent activity
if [ -f "$LOG_DIR/qa-orchestrator.log" ]; then
    recent_lines=$(tail -100 "$LOG_DIR/qa-orchestrator.log" | grep "$(date +%Y-%m-%d)" | wc -l)
    if [ $recent_lines -eq 0 ]; then
        echo "⚠️  QA Orchestrator log has NO activity today"
        echo ""
        echo "This means:"
        echo "  - Either the service isn't receiving requests"
        echo "  - Or it's not logging properly"
        echo ""
        echo "Try sending a test request:"
        echo "  curl -X POST http://localhost:8001/ask/multi-candidate \\"
        echo "    -H 'Content-Type: application/json' \\"
        echo "    -d '{\"question\": \"test\", \"num_candidates\": 3}'"
        echo ""
    else
        echo "✅ QA Orchestrator has activity today ($recent_lines log lines)"
        echo ""
    fi
fi

# Check DPO folder
dpo_count=$(find "$DATA_DIR/dpo" -name "*.json" -type f 2>/dev/null | wc -l)
if [ $dpo_count -eq 0 ]; then
    echo "❌ NO DPO FILES FOUND"
    echo ""
    echo "This could mean:"
    echo "  1. Score differences are too small (< 0.3)"
    echo "  2. Dataset worker isn't running"
    echo "  3. Verification isn't completing"
    echo ""
    echo "Check dataset worker log for 'DPO' messages:"
    echo "  grep -i dpo $LOG_DIR/dataset-worker.log | tail -20"
    echo ""
else
    echo "✅ Found $dpo_count DPO files"
    echo ""
    echo "Latest DPO file:"
    latest=$(find "$DATA_DIR/dpo" -name "*.json" -type f 2>/dev/null | sort | tail -1)
    if [ ! -z "$latest" ]; then
        echo "  $latest"
        echo ""
        echo "Content:"
        cat "$latest" | python3 -m json.tool 2>/dev/null || cat "$latest"
    fi
    echo ""
fi

echo "════════════════════════════════════════════════════════════════════════════"
echo "  NEXT STEPS"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "Run this command and paste the output:"
echo "  grep -i 'dpo\|score diff\|verification complete' $LOG_DIR/*.log | tail -30"
echo ""

