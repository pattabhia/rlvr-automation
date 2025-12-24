#!/bin/bash

# Check Score Distribution and DPO Analysis

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                    SCORE ANALYSIS - WHY NO DPO FILES?                      ║"
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo ""

LOG_DIR="${LOG_DIR:-/workspace/logs}"
DATA_DIR="${DATA_DIR:-/workspace/rlvr-automation/data}"

echo "1. Recent Verification Scores (last 20):"
echo "────────────────────────────────────────────────────────────────────────────"
grep "Verification complete" "$LOG_DIR/verification-worker.log" | tail -20 | while read -r line; do
    # Extract scores
    if [[ $line =~ faithfulness=([0-9.]+) ]]; then
        faith="${BASH_REMATCH[1]}"
    fi
    if [[ $line =~ relevancy=([0-9.]+) ]]; then
        rel="${BASH_REMATCH[1]}"
    fi
    if [[ $line =~ confidence=([a-z]+) ]]; then
        conf="${BASH_REMATCH[1]}"
    fi
    
    # Calculate overall
    overall=$(echo "scale=3; ($faith + $rel) / 2" | bc 2>/dev/null || echo "0.000")
    
    echo "  Faith: $faith, Rel: $rel, Overall: $overall [$conf]"
done
echo ""

echo "2. DPO Analysis (last 20):"
echo "────────────────────────────────────────────────────────────────────────────"
grep -i "DPO:" "$LOG_DIR/dataset-worker.log" | tail -20
echo ""

echo "3. Score Statistics:"
echo "────────────────────────────────────────────────────────────────────────────"
# Extract all overall scores
scores=$(grep "Verification complete" "$LOG_DIR/verification-worker.log" | tail -50 | while read -r line; do
    if [[ $line =~ faithfulness=([0-9.]+) ]] && [[ $line =~ relevancy=([0-9.]+) ]]; then
        faith="${BASH_REMATCH[1]}"
        # Need to re-match for relevancy
        if [[ $line =~ relevancy=([0-9.]+) ]]; then
            rel="${BASH_REMATCH[1]}"
            overall=$(echo "scale=3; ($faith + $rel) / 2" | bc 2>/dev/null)
            echo "$overall"
        fi
    fi
done)

if [ ! -z "$scores" ]; then
    min=$(echo "$scores" | sort -n | head -1)
    max=$(echo "$scores" | sort -n | tail -1)
    count=$(echo "$scores" | wc -l)
    
    echo "  Total scores: $count"
    echo "  Min score: $min"
    echo "  Max score: $max"
    
    # Calculate difference
    diff=$(echo "scale=3; $max - $min" | bc 2>/dev/null)
    echo "  Max difference: $diff"
    echo ""
    
    if (( $(echo "$diff < 0.3" | bc -l 2>/dev/null || echo 0) )); then
        echo "  ❌ PROBLEM: Max difference ($diff) is LESS than 0.3"
        echo "     DPO pairs need score difference ≥ 0.3"
        echo ""
        echo "  This means your answers are too similar in quality!"
        echo ""
    else
        echo "  ✅ Difference ($diff) is enough for DPO"
        echo ""
    fi
else
    echo "  ❌ No scores found!"
    echo ""
fi

echo "4. Checking if RAGAS is still failing:"
echo "────────────────────────────────────────────────────────────────────────────"
ragas_errors=$(grep -i "ragas.*failed\|temperature.*unexpected" "$LOG_DIR/verification-worker.log" | tail -5)
if [ ! -z "$ragas_errors" ]; then
    echo "  ❌ RAGAS IS STILL FAILING!"
    echo ""
    echo "$ragas_errors"
    echo ""
    echo "  The verification worker needs to be restarted with the fix!"
    echo "  Run: ./restart-verification.sh"
    echo ""
else
    echo "  ✅ No RAGAS errors found"
    echo ""
fi

echo "5. Checking DPO folder:"
echo "────────────────────────────────────────────────────────────────────────────"
dpo_count=$(find "$DATA_DIR/dpo" -name "*.json" -type f 2>/dev/null | wc -l)
echo "  DPO files: $dpo_count"

if [ $dpo_count -gt 0 ]; then
    echo ""
    echo "  Latest DPO file:"
    latest=$(find "$DATA_DIR/dpo" -name "*.json" -type f 2>/dev/null | sort | tail -1)
    echo "  $latest"
    echo ""
    echo "  Content:"
    cat "$latest" | python3 -m json.tool 2>/dev/null | head -50
fi
echo ""

echo "6. Training data entries:"
echo "────────────────────────────────────────────────────────────────────────────"
training_count=$(find "$DATA_DIR/training_data" -name "*.jsonl" -type f -exec wc -l {} \; 2>/dev/null | awk '{sum+=$1} END {print sum}')
echo "  Training entries: $training_count"
echo ""

echo "════════════════════════════════════════════════════════════════════════════"
echo "  DIAGNOSIS"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

# Check if verification worker was restarted
restart_time=$(ps -eo pid,lstart,cmd | grep "verification-worker" | grep -v grep | head -1 | awk '{print $2, $3, $4, $5}')
if [ ! -z "$restart_time" ]; then
    echo "Verification worker started: $restart_time"
    echo ""
fi

# Check if scores are still identical
unique_scores=$(echo "$scores" | sort -u | wc -l)
total_scores=$(echo "$scores" | wc -l)

if [ $unique_scores -eq 1 ] && [ $total_scores -gt 1 ]; then
    echo "❌ ALL SCORES ARE IDENTICAL!"
    echo "   This means the fix hasn't been applied yet."
    echo ""
    echo "   Run: ./restart-verification.sh"
    echo ""
elif [ $unique_scores -lt 3 ] && [ $total_scores -gt 5 ]; then
    echo "⚠️  Very few unique scores ($unique_scores out of $total_scores)"
    echo "   Answers might be too similar"
    echo ""
else
    echo "✅ Scores are varying ($unique_scores unique scores)"
    echo ""
    
    if [ $dpo_count -eq 0 ]; then
        echo "But no DPO files created yet because:"
        echo "  - Score differences might be < 0.3"
        echo "  - Or best score might be < 0.7"
        echo ""
        echo "Try asking more diverse questions to get bigger score differences!"
        echo ""
    fi
fi

