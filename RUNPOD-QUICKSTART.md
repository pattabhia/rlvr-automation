# RLVR Automation - Runpod Quick Start Guide

## 🚀 Quick Start (3 Steps)

### 1. Start the Workers

```bash
cd /workspace/rlvr-automation
chmod +x runpod-start.sh
./runpod-start.sh
```

This will:
- ✅ Configure RabbitMQ connection for localhost
- ✅ Start Verification Worker (RAGAS evaluation)
- ✅ Start Dataset Worker (DPO pair generation)

### 2. Send a Test Query

```bash
curl -X POST http://localhost:8001/ask/multi-candidate \
  -H 'Content-Type: application/json' \
  -d '{"question": "What is Docker?", "num_candidates": 3}'
```

### 3. View the Real-Time Dashboard

```bash
cd /workspace/rlvr-automation
./rlvr-dashboard.sh --auto
```

**Dashboard Modes:**
- `./rlvr-dashboard.sh` - Manual refresh (press ENTER)
- `./rlvr-dashboard.sh --auto` - Auto-refresh every 5 seconds

---

## 📊 What You'll See in the Dashboard

The dashboard shows the complete RLVR pipeline lifecycle:

1. **Incoming Requests** - Questions received by QA Orchestrator
2. **Multi-Candidate Generation** - Multiple answer candidates generated
3. **RAGAS Evaluation** - Faithfulness, Relevance, and Confidence scores
4. **DPO Pair Generation** - Best (chosen) vs Worst (rejected) responses
5. **Data Storage** - DPO files saved for training

---

## 🔧 Troubleshooting

### Check Worker Status

```bash
# Check if workers are running
ps aux | grep -E "verification-worker|dataset-worker" | grep -v grep

# View logs
tail -f /workspace/logs/verification-worker.log
tail -f /workspace/logs/dataset-worker.log
```

### Restart Workers

```bash
./runpod-start.sh
```

### Test Dashboard Parsing

```bash
chmod +x test-dashboard.sh
./test-dashboard.sh
```

This will show you what data the dashboard can extract from your logs.

---

## 📁 File Locations

- **Logs:** `/workspace/logs/`
- **DPO Data:** `/workspace/rlvr-automation/data/dpo/`
- **Workers:** `/workspace/rlvr-automation/workers/`

---

## 🎯 Pipeline Flow

```
[Question] → [QA Orchestrator] → [Generate 3 Candidates]
                                         ↓
                              [Verification Worker]
                                         ↓
                              [RAGAS Evaluation]
                                         ↓
                              [Dataset Worker]
                                         ↓
                              [Create DPO Pair]
                                         ↓
                              [Save to JSON]
```

---

## 💡 Tips

1. **Auto-refresh dashboard** for real-time monitoring during testing
2. **Send multiple queries** to see the pipeline in action
3. **Check DPO files** to verify training data is being generated
4. **Monitor logs** if you see any issues

---

## 🐛 Common Issues

### Verification Worker Won't Connect

**Symptom:** `Address resolution failed: gaierror`

**Solution:**
```bash
export RABBITMQ_URL="amqp://guest:guest@localhost:5672/"
./runpod-start.sh
```

### Dashboard Shows No Data

**Symptom:** All sections say "No data found"

**Solution:**
1. Send a test query first
2. Wait 10-15 seconds for processing
3. Refresh the dashboard
4. Run `./test-dashboard.sh` to verify log parsing

### RAGAS Temperature Error

**Symptom:** `TypeError: AsyncClient.chat() got an unexpected keyword argument 'temperature'`

**Impact:** Verification worker uses fallback heuristic scores (still works!)

**Fix:** This is a known issue with RAGAS + Ollama compatibility. The worker will still generate scores using a fallback method.

---

## 📞 Need Help?

Check the logs for detailed error messages:
```bash
tail -100 /workspace/logs/verification-worker.log
tail -100 /workspace/logs/dataset-worker.log
tail -100 /workspace/logs/qa-orchestrator.log
```

