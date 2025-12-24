#!/bin/bash

# Show what happened with the last query - SIMPLE and RELIABLE

LOG_DIR="${LOG_DIR:-/workspace/logs}"
DATA_DIR="${DATA_DIR:-/workspace/rlvr-automation/data}"

echo "════════════════════════════════════════════════════════════════════════════"
echo "  LAST QUERY RESULTS"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

echo "📥 LAST QUESTION:"
echo "────────────────────────────────────────────────────────────────────────────"
grep "Received question:" "$LOG_DIR/qa-orchestrator.log" | tail -1
echo ""

echo "✅ CANDIDATES GENERATED:"
echo "────────────────────────────────────────────────────────────────────────────"
grep "Generated candidate" "$LOG_DIR/qa-orchestrator.log" | tail -3
echo ""

echo "📊 VERIFICATION SCORES (last 3):"
echo "────────────────────────────────────────────────────────────────────────────"
grep "Verification complete:" "$LOG_DIR/verification-worker.log" | tail -3
echo ""

echo "🎯 DPO ANALYSIS (last 3):"
echo "────────────────────────────────────────────────────────────────────────────"
grep "DPO:" "$LOG_DIR/dataset-worker.log" | tail -3
echo ""

echo "💾 TRAINING DATA WRITTEN:"
echo "────────────────────────────────────────────────────────────────────────────"
grep "Complete entry written" "$LOG_DIR/dataset-worker.log" | tail -1
echo ""

echo "📁 DPO FILES:"
echo "────────────────────────────────────────────────────────────────────────────"
dpo_count=$(find "$DATA_DIR/dpo" -name "*.json" -type f 2>/dev/null | wc -l)
echo "Total DPO files: $dpo_count"

if [ $dpo_count -gt 0 ]; then
    echo ""
    echo "Latest DPO file:"
    latest=$(find "$DATA_DIR/dpo" -name "*.json" -type f 2>/dev/null | sort | tail -1)
    ls -lh "$latest"
    echo ""
    echo "Preview:"
    cat "$latest" | python3 -m json.tool 2>/dev/null | head -30
fi
echo ""

echo "════════════════════════════════════════════════════════════════════════════"

