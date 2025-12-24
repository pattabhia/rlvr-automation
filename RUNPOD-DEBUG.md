# 🐛 Runpod Debugging Guide

## Issue: Dashboard shows questions and workers but no RAGAS scores or DPO files

### Step 1: Pull Latest Fix

```bash
cd /workspace/rlvr-automation
git pull origin main
```

This fixes the `grep: binary file matches` errors.

### Step 2: Run Debug Script

```bash
./debug-logs.sh
```

This will show you:
- ✅ What RAGAS scores are in the logs
- ✅ What DPO activity is happening
- ✅ If verification.completed events are being published
- ✅ If dataset worker is receiving events
- ✅ What files exist in the data directory

### Step 3: Check the Output

**Expected Output:**

```
1. Checking verification-worker.log for RAGAS scores:
   2025-12-24 11:22:XX - INFO - Verification complete: faithfulness=0.500, relevancy=0.850, confidence=low

2. Checking dataset-worker.log for DPO activity:
   2025-12-24 11:22:XX - INFO - Received event: verification.completed
   2025-12-24 11:22:XX - INFO - Created DPO pair
   2025-12-24 11:22:XX - INFO - Saved to /workspace/rlvr-automation/data/dpo/...
```

### Step 4: Diagnose the Issue

#### Scenario A: RAGAS scores exist but dashboard doesn't show them

**Problem:** Log parsing regex might not match

**Solution:**
```bash
# Check exact format
tail -50 /workspace/logs/verification-worker.log | grep "Verification complete"

# The dashboard expects format like:
# faithfulness=0.500, relevancy=0.850, confidence=low
```

#### Scenario B: No verification.completed events

**Problem:** Verification worker isn't publishing events

**Solution:**
```bash
# Check verification worker log
tail -100 /workspace/logs/verification-worker.log

# Look for errors or "Published event: verification.completed"
```

#### Scenario C: Dataset worker not receiving events

**Problem:** RabbitMQ routing issue

**Solution:**
```bash
# Check dataset worker log
tail -100 /workspace/logs/dataset-worker.log

# Should see "Received event: verification.completed"
```

#### Scenario D: No DPO files being created

**Problem:** Dataset worker logic issue

**Solution:**
```bash
# Check dataset worker for errors
tail -100 /workspace/logs/dataset-worker.log | grep -i error

# Check if worker is even running
ps aux | grep dataset-generation-worker
```

### Step 5: Common Fixes

#### Fix 1: Restart Workers

```bash
./runpod-start.sh
```

#### Fix 2: Send Fresh Query

```bash
curl -X POST http://localhost:8001/ask/multi-candidate \
  -H 'Content-Type: application/json' \
  -d '{"question": "What is Kubernetes?", "num_candidates": 3}'

# Wait 20 seconds
sleep 20

# Check logs
./debug-logs.sh
```

#### Fix 3: Check RabbitMQ Queues

```bash
# List queues
rabbitmqctl list_queues

# Should see queues for:
# - answer.generated
# - verification.completed
```

#### Fix 4: Check Worker Subscriptions

```bash
# Verification worker should subscribe to: answer.generated
grep "Bound queue to routing key" /workspace/logs/verification-worker.log

# Dataset worker should subscribe to: verification.completed
grep "Bound queue to routing key" /workspace/logs/dataset-worker.log
```

### Step 6: View Updated Dashboard

```bash
./rlvr-dashboard.sh --auto
```

Should now show without `grep: binary file matches` errors.

---

## 🔍 Quick Diagnostic Commands

```bash
# 1. Check if workers are running
ps aux | grep -E "verification-worker|dataset-worker" | grep -v grep

# 2. Check recent verification scores
tail -50 /workspace/logs/verification-worker.log | grep "Verification complete"

# 3. Check dataset worker activity
tail -50 /workspace/logs/dataset-worker.log | grep -iE "dpo|pair|saved"

# 4. Check for DPO files
find /workspace/rlvr-automation/data -name "*.json" -type f

# 5. Check RabbitMQ
rabbitmqctl list_queues
```

---

## 📊 Expected Pipeline Flow

```
1. Question received → QA Orchestrator
2. Generate 3 candidates → Publish answer.generated events (3x)
3. Verification worker receives → Runs RAGAS → Publishes verification.completed (3x)
4. Dataset worker receives → Collects all 3 → Creates DPO pair → Saves JSON
```

---

## 🚨 If Still Not Working

**Share the output of:**

```bash
./debug-logs.sh > debug-output.txt
cat debug-output.txt
```

This will show exactly what's in the logs and help diagnose the issue.

