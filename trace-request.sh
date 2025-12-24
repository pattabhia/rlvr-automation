#!/bin/bash

# Request Tracer - Trace the complete lifecycle of a request using correlation_id or batch_id
#
# Usage: ./trace-request.sh <correlation_id|batch_id>
#
# The correlation_id is returned in the API response when you send a question from the UI.
# Use it to trace the entire lifecycle of your request across all services.

if [ -z "$1" ]; then
    echo "════════════════════════════════════════════════════════════════════════════"
    echo "  🔍 REQUEST TRACER - Trace the complete lifecycle of a request"
    echo "════════════════════════════════════════════════════════════════════════════"
    echo ""
    echo "Usage: ./trace-request.sh <correlation_id|batch_id>"
    echo ""
    echo "Examples:"
    echo "  ./trace-request.sh abc-123-def-456"
    echo "  ./trace-request.sh batch-xyz"
    echo ""
    echo "The correlation_id is returned in the API response when you send a question."
    echo "Copy it from the UI response and use it here to trace the entire lifecycle."
    echo ""
    echo "This will search all logs and show:"
    echo "  • API Gateway request"
    echo "  • QA Orchestrator processing"
    echo "  • Answer generation events"
    echo "  • Verification events"
    echo "  • Dataset generation"
    echo "  • DPO pair creation (if applicable)"
    echo ""
    exit 1
fi

TRACE_ID="$1"

# Log files to search
LOGS=(
    "/workspace/logs/verification-worker.log"
    "/workspace/logs/dataset-worker.log"
    "/workspace/logs/qa-orchestrator.log"
    "/workspace/logs/api-gateway.log"
)

echo "════════════════════════════════════════════════════════════════════════════"
echo "  🔍 REQUEST TRACE: $TRACE_ID"
echo "  $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

# Search all logs for the trace ID
total_matches=0

for log_file in "${LOGS[@]}"; do
    if [ ! -f "$log_file" ]; then
        continue
    fi
    
    # Count matches in this log
    matches=$(strings "$log_file" 2>/dev/null | grep -i "$TRACE_ID" | wc -l)
    
    if [ $matches -gt 0 ]; then
        total_matches=$((total_matches + matches))
        
        echo "📄 $(basename $log_file) ($matches matches)"
        echo "────────────────────────────────────────────────────────────────────────────"
        
        # Show all matching lines with context
        strings "$log_file" 2>/dev/null | grep -i "$TRACE_ID" | while read line; do
            echo "  $line"
        done
        echo ""
    fi
done

if [ $total_matches -eq 0 ]; then
    echo "❌ No matches found for: $TRACE_ID"
    echo ""
    echo "Possible reasons:"
    echo "  1. Request hasn't been processed yet (wait a few seconds)"
    echo "  2. Wrong ID (check the response from UI)"
    echo "  3. Logs have been rotated/cleared"
    echo ""
    echo "Recent batch IDs (last 10):"
    echo "────────────────────────────────────────────────────────────────────────────"
    for log_file in "${LOGS[@]}"; do
        if [ -f "$log_file" ]; then
            strings "$log_file" 2>/dev/null | grep -oP 'batch_id["\s:=]+\K[a-f0-9-]+' | tail -10
        fi
    done | sort -u | tail -10
    echo ""
else
    echo "════════════════════════════════════════════════════════════════════════════"
    echo "  ✅ Found $total_matches log entries for: $TRACE_ID"
    echo "════════════════════════════════════════════════════════════════════════════"
    echo ""
    
    # Try to extract key information
    echo "📊 Summary:"
    echo "────────────────────────────────────────────────────────────────────────────"
    
    # Extract question
    question=$(for log_file in "${LOGS[@]}"; do
        if [ -f "$log_file" ]; then
            strings "$log_file" 2>/dev/null | grep -i "$TRACE_ID" | grep -oP 'question["\s:=]+\K[^"]+' | head -1
        fi
    done | head -1)
    
    if [ ! -z "$question" ]; then
        echo "  Question: $question"
    fi
    
    # Count events
    answer_events=$(for log_file in "${LOGS[@]}"; do
        if [ -f "$log_file" ]; then
            strings "$log_file" 2>/dev/null | grep -i "$TRACE_ID" | grep "answer.generated"
        fi
    done | wc -l)
    
    verify_events=$(for log_file in "${LOGS[@]}"; do
        if [ -f "$log_file" ]; then
            strings "$log_file" 2>/dev/null | grep -i "$TRACE_ID" | grep "verification.completed"
        fi
    done | wc -l)
    
    echo "  Answer events: $answer_events"
    echo "  Verification events: $verify_events"
    
    # Check if DPO was created
    dpo_created=$(for log_file in "${LOGS[@]}"; do
        if [ -f "$log_file" ]; then
            strings "$log_file" 2>/dev/null | grep -i "$TRACE_ID" | grep -i "wrote dpo\|dpo pair"
        fi
    done | wc -l)
    
    if [ $dpo_created -gt 0 ]; then
        echo "  DPO pair created: ✅ YES"
    else
        echo "  DPO pair created: ❌ NO"
        
        # Check why it was rejected
        rejection=$(for log_file in "${LOGS[@]}"; do
            if [ -f "$log_file" ]; then
                strings "$log_file" 2>/dev/null | grep -i "$TRACE_ID" | grep -E "Score diff too small|Chosen score too low|rejected"
            fi
        done | head -1)
        
        if [ ! -z "$rejection" ]; then
            echo "  Rejection reason: $rejection"
        fi
    fi
    
    echo ""
fi

echo "════════════════════════════════════════════════════════════════════════════"
echo "  Tip: To see more context, check the individual log files:"
echo "  tail -f /workspace/logs/verification-worker.log | grep '$TRACE_ID'"
echo "  tail -f /workspace/logs/dataset-worker.log | grep '$TRACE_ID'"
echo "════════════════════════════════════════════════════════════════════════════"

