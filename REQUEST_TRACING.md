# Request Tracing with Correlation IDs

## Overview

Every request sent through the UI now gets a unique **correlation_id** that allows you to trace its complete lifecycle across all services and workers.

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                    REQUEST LIFECYCLE TRACING                     │
└─────────────────────────────────────────────────────────────────┘

1. UI sends question
   ↓
2. API Gateway generates correlation_id
   ↓
3. QA Orchestrator receives correlation_id + generates batch_id
   ↓
4. Events published with correlation_id + batch_id
   ↓
5. Workers log all processing with correlation_id
   ↓
6. DPO file created (if thresholds met)

All logs include: [correlation_id=xxx] [batch_id=yyy]
```

## Getting the Correlation ID

### From UI Response

When you send a question from the UI, the response now includes:

```json
{
  "question": "What is AWS Lambda?",
  "candidates": [...],
  "correlation_id": "abc-123-def-456",
  "batch_id": "xyz-789-ghi-012",
  "num_candidates": 3,
  "events_published": 3
}
```

**Copy the `correlation_id`** from the response!

### From Logs

You can also find recent correlation IDs in the logs:

```bash
# Show recent correlation IDs
tail -100 /workspace/logs/api-gateway.log | grep correlation_id
```

## Tracing a Request

### Using the Trace Script

```bash
# Trace by correlation_id (recommended)
./trace-request.sh abc-123-def-456

# Trace by batch_id (also works)
./trace-request.sh xyz-789-ghi-012
```

### Output Example

```
════════════════════════════════════════════════════════════════════════════
  🔍 REQUEST TRACE: abc-123-def-456
  2025-12-24 13:45:30
════════════════════════════════════════════════════════════════════════════

📄 api-gateway.log (2 matches)
────────────────────────────────────────────────────────────────────────────
  [correlation_id=abc-123-def-456] Multi-candidate request: What is AWS Lambda?...
  [correlation_id=abc-123-def-456] Multi-candidate response sent (batch_id=xyz-789)

📄 qa-orchestrator.log (5 matches)
────────────────────────────────────────────────────────────────────────────
  [correlation_id=abc-123-def-456] Received multi-candidate request: What is AWS Lambda? (num_candidates=3)
  [correlation_id=abc-123-def-456] [batch_id=xyz-789] Publishing 3 answer.generated events
  [correlation_id=abc-123-def-456] [batch_id=xyz-789] Published answer.generated event for candidate 1/3
  [correlation_id=abc-123-def-456] [batch_id=xyz-789] Published answer.generated event for candidate 2/3
  [correlation_id=abc-123-def-456] [batch_id=xyz-789] Published answer.generated event for candidate 3/3

📄 verification-worker.log (6 matches)
────────────────────────────────────────────────────────────────────────────
  [correlation_id=abc-123-def-456] [batch_id=xyz-789] Processing answer.generated event: event-001
  [correlation_id=abc-123-def-456] [batch_id=xyz-789] Verification complete: faithfulness=0.850, relevancy=0.920
  [correlation_id=abc-123-def-456] [batch_id=xyz-789] Published verification.completed event: verify-001
  ...

📄 dataset-worker.log (8 matches)
────────────────────────────────────────────────────────────────────────────
  [correlation_id=abc-123-def-456] [batch_id=xyz-789] Received answer.generated: event-001
  [correlation_id=abc-123-def-456] Received verification.completed: verify-001
  [correlation_id=abc-123-def-456] [batch_id=xyz-789] DPO pair created: score_diff=0.120
  ...

════════════════════════════════════════════════════════════════════════════
  ✅ Found 21 log entries for: abc-123-def-456
════════════════════════════════════════════════════════════════════════════

📊 Summary:
────────────────────────────────────────────────────────────────────────────
  Question: What is AWS Lambda?
  Answer events: 3
  Verification events: 3
  DPO pair created: ✅ YES
```

## Manual Searching

### Search All Logs

```bash
# Search for correlation_id in all logs
grep -r "correlation_id=abc-123-def-456" /workspace/logs/

# Search for batch_id
grep -r "batch_id=xyz-789" /workspace/logs/
```

### Search Specific Service

```bash
# API Gateway
grep "correlation_id=abc-123-def-456" /workspace/logs/api-gateway.log

# QA Orchestrator
grep "correlation_id=abc-123-def-456" /workspace/logs/qa-orchestrator.log

# Verification Worker
grep "correlation_id=abc-123-def-456" /workspace/logs/verification-worker.log

# Dataset Worker
grep "correlation_id=abc-123-def-456" /workspace/logs/dataset-worker.log
```

### Live Monitoring

```bash
# Watch for a specific correlation_id in real-time
tail -f /workspace/logs/*.log | grep "correlation_id=abc-123-def-456"
```

## Log Format

All logs now follow this format:

```
[correlation_id=xxx] [batch_id=yyy] Message
```

- **correlation_id**: Unique ID for the entire request (from UI to DPO file)
- **batch_id**: Unique ID for the multi-candidate batch (groups 3 candidates together)
- **event_id**: Unique ID for each individual event

## Use Cases

### 1. Debug Why DPO Pair Wasn't Created

```bash
./trace-request.sh <correlation_id>

# Look for rejection messages:
# - "Score diff too small"
# - "Chosen score too low"
```

### 2. Check Processing Time

```bash
# See timestamps for each step
grep "correlation_id=abc-123" /workspace/logs/*.log | sort
```

### 3. Verify All Events Were Processed

```bash
./trace-request.sh <correlation_id>

# Check summary:
# - Answer events: should be 3 (for 3 candidates)
# - Verification events: should be 3
# - DPO pair created: YES/NO
```

### 4. Find Recent Requests

```bash
# Show last 10 correlation IDs
tail -100 /workspace/logs/api-gateway.log | grep -oP 'correlation_id=\K[a-f0-9-]+' | tail -10
```

## Tips

1. **Always copy the correlation_id from the UI response** - it's the easiest way to trace your request
2. **Use the trace script** - it's faster than manual searching
3. **Check the summary** - it tells you if DPO was created and why not
4. **Look for timestamps** - helps identify bottlenecks

## Example Workflow

```bash
# 1. Send question from UI
curl -X POST http://localhost:8001/ask/multi-candidate \
  -H 'Content-Type: application/json' \
  -d '{"question": "What is AWS Lambda?"}'

# Response includes:
# "correlation_id": "abc-123-def-456"

# 2. Trace the request
./trace-request.sh abc-123-def-456

# 3. Check if DPO was created
# Look for "DPO pair created: ✅ YES" in the summary

# 4. If NO, check rejection reason
grep "correlation_id=abc-123-def-456" /workspace/logs/dataset-worker.log | grep -i "reject\|too small\|too low"
```

## Architecture

```
┌─────────────┐
│     UI      │ Sends question
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│   API Gateway       │ Generates correlation_id
│  correlation_id=X   │ Returns it in response
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  QA Orchestrator    │ Receives correlation_id
│  correlation_id=X   │ Generates batch_id
│  batch_id=Y         │ Logs both IDs
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   RabbitMQ Events   │ Events include both IDs
│  correlation_id=X   │
│  batch_id=Y         │
└──────┬──────────────┘
       │
       ├──────────────────────┬──────────────────────┐
       ▼                      ▼                      ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Verification │    │   Dataset    │    │  DPO Writer  │
│   Worker     │    │   Worker     │    │              │
│ Logs with    │    │ Logs with    │    │ Logs with    │
│ both IDs     │    │ both IDs     │    │ both IDs     │
└──────────────┘    └──────────────┘    └──────────────┘
```

All services log with `[correlation_id=X] [batch_id=Y]` for complete traceability!

