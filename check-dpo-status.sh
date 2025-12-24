#!/bin/bash

# DPO Status Checker - Monitor DPO file creation in real-time

DPO_FILE="/app/data/dpo_data/dpo_data_202512.jsonl"
LOG_FILE="/workspace/logs/dataset-worker.log"

echo "════════════════════════════════════════════════════════════════════════════"
echo "  DPO DATASET STATUS"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

# Check if DPO file exists
if [ ! -f "$DPO_FILE" ]; then
    echo "❌ DPO file not found: $DPO_FILE"
    echo ""
    echo "   Possible reasons:"
    echo "   1. No DPO pairs created yet (score diffs too small)"
    echo "   2. Dataset worker not running"
    echo "   3. Wrong file path"
    echo ""
    exit 1
fi

# Count DPO pairs
total_pairs=$(wc -l < "$DPO_FILE")
file_size=$(du -h "$DPO_FILE" | cut -f1)

echo "📊 DPO File Statistics:"
echo "────────────────────────────────────────────────────────────────────────────"
echo "  File:        $DPO_FILE"
echo "  Total Pairs: $total_pairs"
echo "  File Size:   $file_size"
echo ""

# Show recent DPO creation activity
echo "📝 Recent DPO Pair Creation (last 10):"
echo "────────────────────────────────────────────────────────────────────────────"
strings "$LOG_FILE" 2>/dev/null | grep "✅ All quality checks passed" | tail -10
if [ $? -ne 0 ]; then
    echo "  (No quality check logs found - checking for DPO writes...)"
    strings "$LOG_FILE" 2>/dev/null | grep "Wrote DPO pair" | tail -10
fi
echo ""

# Show DPO analysis (score diffs)
echo "📈 Recent DPO Analysis (last 10):"
echo "────────────────────────────────────────────────────────────────────────────"
strings "$LOG_FILE" 2>/dev/null | grep "DPO: Question" | tail -10
echo ""

# Show latest DPO pair
echo "🔍 Latest DPO Pair (formatted):"
echo "────────────────────────────────────────────────────────────────────────────"
tail -1 "$DPO_FILE" | python3 -m json.tool 2>/dev/null | head -40
echo "  ... (truncated, use 'tail -1 $DPO_FILE | python3 -m json.tool' for full output)"
echo ""

# Show first DPO pair for comparison
echo "🔍 First DPO Pair (for comparison):"
echo "────────────────────────────────────────────────────────────────────────────"
head -1 "$DPO_FILE" | python3 -m json.tool 2>/dev/null | head -40
echo "  ... (truncated)"
echo ""

# Show rejection stats
echo "❌ Rejection Statistics:"
echo "────────────────────────────────────────────────────────────────────────────"
rejected_score_diff=$(strings "$LOG_FILE" 2>/dev/null | grep "rejected_low_score_diff" | tail -1)
rejected_chosen=$(strings "$LOG_FILE" 2>/dev/null | grep "rejected_low_chosen_score" | tail -1)
rejected_quality=$(strings "$LOG_FILE" 2>/dev/null | grep "rejected_quality" | tail -1)

if [ -z "$rejected_score_diff" ] && [ -z "$rejected_chosen" ] && [ -z "$rejected_quality" ]; then
    echo "  (No rejection stats available in logs)"
else
    echo "  Score Diff Too Small: $rejected_score_diff"
    echo "  Chosen Score Too Low: $rejected_chosen"
    echo "  Quality Filter:       $rejected_quality"
fi
echo ""

# Show current thresholds
echo "⚙️  Current DPO Thresholds:"
echo "────────────────────────────────────────────────────────────────────────────"
strings "$LOG_FILE" 2>/dev/null | grep "DPO Dataset Writer initialized" | tail -1
echo ""

# Show worker status
echo "🔧 Worker Status:"
echo "────────────────────────────────────────────────────────────────────────────"
dataset_pid=$(ps aux | grep "dataset-generation-worker" | grep -v grep | awk '{print $2}')
if [ -z "$dataset_pid" ]; then
    echo "  ❌ Dataset worker: NOT RUNNING"
else
    echo "  ✅ Dataset worker: Running (PID: $dataset_pid)"
fi
echo ""

echo "════════════════════════════════════════════════════════════════════════════"
echo "  SUMMARY"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "  ✅ DPO file exists: $DPO_FILE"
echo "  ✅ Total DPO pairs: $total_pairs"
echo "  ✅ File size: $file_size"
echo ""
echo "Next Steps:"
echo "  • To view full DPO pairs: cat $DPO_FILE | python3 -m json.tool"
echo "  • To monitor in real-time: watch -n 5 ./check-dpo-status.sh"
echo "  • To tail the log: tail -f $LOG_FILE | grep DPO"
echo ""

