#!/bin/bash

# Watch ONLY the important stuff - scores and DPO decisions

LOG_DIR="${LOG_DIR:-/workspace/logs}"

echo "════════════════════════════════════════════════════════════════════════════"
echo "  WATCHING SCORES & DPO DECISIONS"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "Press Ctrl+C to exit"
echo ""

# Get current line count
qa_lines=$(wc -l < "$LOG_DIR/qa-orchestrator.log" 2>/dev/null || echo 0)
ver_lines=$(wc -l < "$LOG_DIR/verification-worker.log" 2>/dev/null || echo 0)
ds_lines=$(wc -l < "$LOG_DIR/dataset-worker.log" 2>/dev/null || echo 0)

while true; do
    # Check QA orchestrator for new questions
    new_qa_lines=$(wc -l < "$LOG_DIR/qa-orchestrator.log" 2>/dev/null || echo 0)
    if [ $new_qa_lines -gt $qa_lines ]; then
        tail -n +$((qa_lines + 1)) "$LOG_DIR/qa-orchestrator.log" | grep -i "received question\|generated.*candidate"
        qa_lines=$new_qa_lines
    fi
    
    # Check verification worker for scores
    new_ver_lines=$(wc -l < "$LOG_DIR/verification-worker.log" 2>/dev/null || echo 0)
    if [ $new_ver_lines -gt $ver_lines ]; then
        tail -n +$((ver_lines + 1)) "$LOG_DIR/verification-worker.log" | grep -i "verification complete"
        ver_lines=$new_ver_lines
    fi
    
    # Check dataset worker for DPO decisions
    new_ds_lines=$(wc -l < "$LOG_DIR/dataset-worker.log" 2>/dev/null || echo 0)
    if [ $new_ds_lines -gt $ds_lines ]; then
        tail -n +$((ds_lines + 1)) "$LOG_DIR/dataset-worker.log" | grep -i "dpo:\|complete entry written"
        ds_lines=$new_ds_lines
    fi
    
    sleep 1
done

