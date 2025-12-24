#!/bin/bash

# SIMPLE WATCH - Just show the raw logs, no fancy parsing

LOG_DIR="${LOG_DIR:-/workspace/logs}"

echo "════════════════════════════════════════════════════════════════════════════"
echo "  SIMPLE LOG WATCHER - Raw output, no BS"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "Watching these logs:"
echo "  - $LOG_DIR/qa-orchestrator.log"
echo "  - $LOG_DIR/verification-worker.log"
echo "  - $LOG_DIR/dataset-worker.log"
echo ""
echo "Press Ctrl+C to exit"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

# Just tail all three logs together
tail -f \
  "$LOG_DIR/qa-orchestrator.log" \
  "$LOG_DIR/verification-worker.log" \
  "$LOG_DIR/dataset-worker.log" \
  2>/dev/null

