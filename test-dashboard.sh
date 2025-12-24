#!/bin/bash

echo "=========================================="
echo "  TESTING DASHBOARD LOG PARSING"
echo "=========================================="
echo ""

LOG_DIR="/workspace/logs"

echo "1. Checking for questions in QA Orchestrator log:"
if [ -f "$LOG_DIR/qa-orchestrator.log" ]; then
    tail -100 "$LOG_DIR/qa-orchestrator.log" | grep "Generating.*candidate answers for question" | tail -3 | while read line; do
        timestamp=$(echo "$line" | cut -d',' -f1 | sed 's/.*\([0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\} [0-9]\{2\}:[0-9]\{2\}:[0-9]\{2\}\).*/\1/')
        question=$(echo "$line" | sed 's/.*question: //' | sed 's/"//g')
        echo "  ✓ [$timestamp] $question"
    done
else
    echo "  ⚠ Log file not found"
fi

echo ""
echo "2. Checking for verification results:"
if [ -f "$LOG_DIR/verification-worker.log" ]; then
    tail -100 "$LOG_DIR/verification-worker.log" | grep "Verification complete" | tail -3 | while read line; do
        timestamp=$(echo "$line" | cut -d',' -f1 | sed 's/.*\([0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\} [0-9]\{2\}:[0-9]\{2\}:[0-9]\{2\}\).*/\1/')
        
        faith=""
        rel=""
        conf=""
        
        if [[ $line =~ faithfulness=([0-9.]+) ]]; then
            faith="${BASH_REMATCH[1]}"
        fi
        
        if [[ $line =~ relevancy=([0-9.]+) ]]; then
            rel="${BASH_REMATCH[1]}"
        fi
        
        if [[ $line =~ confidence=([a-z]+) ]]; then
            conf="${BASH_REMATCH[1]}"
        fi
        
        echo "  ✓ [$timestamp] Faithfulness=$faith, Relevance=$rel, Confidence=$conf"
    done
else
    echo "  ⚠ Log file not found"
fi

echo ""
echo "3. Checking for worker events:"
if [ -f "$LOG_DIR/qa-orchestrator.log" ]; then
    count=$(tail -100 "$LOG_DIR/qa-orchestrator.log" | grep "Published event: answer.generated" | wc -l)
    echo "  ✓ Found $count answer.generated events"
fi

echo ""
echo "4. Checking for DPO files:"
dpo_count=$(find /workspace/rlvr-automation/data -name "*.json" -type f 2>/dev/null | wc -l)
echo "  ✓ Found $dpo_count JSON files in data directory"

echo ""
echo "=========================================="
echo "  DASHBOARD READY!"
echo "=========================================="
echo ""
echo "Run the dashboard with:"
echo "  ./rlvr-dashboard.sh          # Manual refresh (press ENTER)"
echo "  ./rlvr-dashboard.sh --auto   # Auto-refresh every 5 seconds"
echo ""

