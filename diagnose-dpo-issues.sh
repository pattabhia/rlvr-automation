#!/bin/bash

# Diagnose why DPO files aren't being created

LOG_DIR="${LOG_DIR:-/workspace/logs}"

echo "════════════════════════════════════════════════════════════════════════════"
echo "  DIAGNOSING DPO ISSUES"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

echo "1. Check if new batch tracking code is running:"
echo "────────────────────────────────────────────────────────────────────────────"
batch_logs=$(strings "$LOG_DIR/dataset-worker.log" 2>/dev/null | grep -i "batch" | tail -5)
if [ -z "$batch_logs" ]; then
    echo "❌ NO BATCH TRACKING FOUND!"
    echo "   The workers are still running OLD code."
    echo ""
    echo "   ACTION REQUIRED:"
    echo "   1. git pull origin main"
    echo "   2. ./runpod-start.sh"
    echo ""
else
    echo "✅ Batch tracking is active:"
    echo "$batch_logs"
    echo ""
fi

echo "2. Check recent DPO attempts and why they failed:"
echo "────────────────────────────────────────────────────────────────────────────"
strings "$LOG_DIR/dataset-worker.log" 2>/dev/null | grep "DPO:" | tail -20
echo ""

echo "3. Analyze rejection reasons:"
echo "────────────────────────────────────────────────────────────────────────────"
total_attempts=$(strings "$LOG_DIR/dataset-worker.log" 2>/dev/null | grep "score diff:" | wc -l)
low_diff=$(strings "$LOG_DIR/dataset-worker.log" 2>/dev/null | grep "Score diff too small" | wc -l)
low_score=$(strings "$LOG_DIR/dataset-worker.log" 2>/dev/null | grep "Chosen score too low" | wc -l)
failed_verbatim=$(strings "$LOG_DIR/dataset-worker.log" 2>/dev/null | grep "failed verbatim test" | wc -l)

echo "Total DPO attempts: $total_attempts"
echo "Rejected - Low score diff (<0.3): $low_diff"
echo "Rejected - Low chosen score (<0.7): $low_score"
echo "Rejected - Failed verbatim test: $failed_verbatim"
echo ""

if [ $total_attempts -eq 0 ]; then
    echo "⚠️  NO DPO ATTEMPTS YET"
    echo "   Either no multi-candidate queries were sent, or workers need restart."
    echo ""
elif [ $low_diff -gt 0 ] || [ $low_score -gt 0 ]; then
    echo "📊 REJECTION ANALYSIS:"
    echo ""
    
    if [ $low_diff -gt 0 ]; then
        echo "   ❌ Score differences are too small (<0.3)"
        echo "      This means the LLM is generating very similar answers"
        echo "      even with different temperatures (0.3, 0.7, 0.9)."
        echo ""
        echo "      POSSIBLE CAUSES:"
        echo "      • Temperature not being applied correctly"
        echo "      • LLM ignoring temperature parameter"
        echo "      • Questions too simple (only one correct answer)"
        echo ""
    fi
    
    if [ $low_score -gt 0 ]; then
        echo "   ❌ Best scores are too low (<0.7)"
        echo "      This means even the BEST answer isn't good enough."
        echo ""
        echo "      POSSIBLE CAUSES:"
        echo "      • RAGAS is being too strict"
        echo "      • Context quality is poor"
        echo "      • LLM answers don't match context well"
        echo ""
    fi
fi

echo "4. Check if temperature is being applied:"
echo "────────────────────────────────────────────────────────────────────────────"
qa_log="$LOG_DIR/qa-orchestrator.log"
if [ -f "$qa_log" ]; then
    echo "Recent temperature usage in QA orchestrator:"
    strings "$qa_log" 2>/dev/null | grep -i "temp" | tail -10
    echo ""
else
    echo "⚠️  QA orchestrator log not found at $qa_log"
    echo ""
fi

echo "5. Sample verification scores:"
echo "────────────────────────────────────────────────────────────────────────────"
strings "$LOG_DIR/verification-worker.log" 2>/dev/null | grep "Verification complete" | tail -10
echo ""

echo "════════════════════════════════════════════════════════════════════════════"
echo "  RECOMMENDATIONS"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

if [ -z "$batch_logs" ]; then
    echo "🔧 IMMEDIATE ACTION: Restart workers with new code"
    echo "   cd /workspace/rlvr-automation"
    echo "   git pull origin main"
    echo "   ./runpod-start.sh"
    echo ""
elif [ $low_score -gt 0 ]; then
    echo "🔧 OPTION 1: Lower the min_chosen_score threshold"
    echo "   Current: 0.7"
    echo "   Suggested: 0.6 (to match your actual scores)"
    echo ""
    echo "   export MIN_CHOSEN_SCORE=0.6"
    echo "   ./runpod-start.sh"
    echo ""
    echo "🔧 OPTION 2: Improve answer quality"
    echo "   • Use better context/documents"
    echo "   • Ask questions that have clear answers in the docs"
    echo ""
elif [ $low_diff -gt 0 ]; then
    echo "🔧 OPTION 1: Lower the min_score_diff threshold"
    echo "   Current: 0.3"
    echo "   Suggested: 0.1 (to match your actual variance)"
    echo ""
    echo "   export MIN_SCORE_DIFF=0.1"
    echo "   ./runpod-start.sh"
    echo ""
    echo "🔧 OPTION 2: Increase temperature range for more diversity"
    echo "   Current: 0.3, 0.7, 0.9"
    echo "   Suggested: 0.1, 0.7, 1.2"
    echo ""
else
    echo "✅ Everything looks good! DPO pairs should be created."
    echo ""
fi

