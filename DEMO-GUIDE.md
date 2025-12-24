# 🎬 RLVR Pipeline Demo Guide

This guide shows you how to run a live demo of the RLVR (Reinforcement Learning from Verifiable Rewards) pipeline with real-time monitoring across 4 terminals.

---

## 🎯 What You'll See

The demo shows the complete pipeline flow:

1. **Multi-Candidate Generation** - 3 different answers generated for each question
2. **RAGAS Evaluation** - Each answer scored for faithfulness and relevancy
3. **Reward Calculation** - Scores analyzed and compared
4. **DPO Pair Generation** - Best vs worst answers selected for training

---

## 🚀 Quick Start

### Step 1: Setup (Run Once)

```bash
./demo-setup.sh
```

This makes all monitoring scripts executable.

### Step 2: Open 4 Terminals

Arrange your terminals in a 2x2 grid for best viewing.

**Terminal 1 - Top Left:**
```bash
./monitor-candidates.sh
```
Shows candidate answer generation in real-time.

**Terminal 2 - Top Right:**
```bash
./monitor-ragas.sh
```
Shows RAGAS evaluation with score bars.

**Terminal 3 - Bottom Left:**
```bash
./monitor-rewards.sh
```
Shows reward calculation and score analysis.

**Terminal 4 - Bottom Right:**
```bash
./monitor-dpo.sh
```
Shows DPO pair creation (chosen vs rejected).

### Step 3: Send Questions

In a 5th terminal (or after starting monitors):

```bash
./demo-questions.sh
```

This sends 5 test questions with 25-second intervals.

---

## 📊 What Each Monitor Shows

### 1️⃣ Multi-Candidate Generation Monitor

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📥 NEW QUESTION [11:30:15]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Q: What is AWS Lambda and how does it work?

🎯 Generating 3 candidate answers...

  ⚙️  Generating candidate 1 of 3
  ✅ Candidate #1 generated (ID: a1b2c3d4)
     Preview: AWS Lambda is a serverless compute service...
  📤 Event published: answer.generated (a1b2c3d4)
  
  ⚙️  Generating candidate 2 of 3
  ✅ Candidate #2 generated (ID: e5f6g7h8)
  ...
```

### 2️⃣ RAGAS Evaluation Monitor

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📨 ANSWER RECEIVED FOR VERIFICATION [11:30:16]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Event ID: a1b2c3d4

  ⚙️  Starting RAGAS verification...
  📊 Mode: Heuristic evaluation
  📈 Analysis: overlap=0.65, length=245, quality=0.12

  ✅ VERIFICATION COMPLETE
  ═══════════════════════════════════════════════════════════════════
  
  Faithfulness:  ████████████████████████░░░░░░ 0.820
  Relevancy:     ██████████████████████████░░░░ 0.875
  Overall Score: █████████████████████████░░░░░ 0.848
  
  Confidence:    🟢 HIGH
  ═══════════════════════════════════════════════════════════════════
```

### 3️⃣ Reward Calculation Monitor

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 COMPLETE ENTRY - CALCULATING REWARDS [11:30:45]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Question: What is AWS Lambda and how does it work?

  📊 Using RAGAS scores (reward model not yet implemented)

  📊 SCORE ANALYSIS
  ─────────────────────────────────────────────────────────────────
  Answers collected: 3
  
  Best Answer:   ██████████████████████████░░░░ 0.875
  Worst Answer:  ████████████████░░░░░░░░░░░░░░ 0.542
  
  Score Difference: 0.333
  Required for DPO: 0.300
  
  ✅ DPO pair will be created!
  ─────────────────────────────────────────────────────────────────
```

### 4️⃣ DPO Pair Generation Monitor

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ DPO PAIR CREATED [11:30:45]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Question:
  What is AWS Lambda and how does it work?

Score Comparison:
  Chosen:   ██████████████████████████░░░░ 0.875
  Rejected: ████████████████░░░░░░░░░░░░░░ 0.542
  Margin:   ██████████░░░░░░░░░░░░░░░░░░░░ +0.333

Quality Metrics:
  ✅ Score difference: 0.333 (≥ 0.3 required)
  ✅ Best score: 0.875 (≥ 0.7 required)
  📊 Answers analyzed: 3

  💾 DPO pair saved: pair_20251224_113045.json
  
  📄 Pair Details:
  ✅ Chosen:   AWS Lambda is a serverless compute service that runs...
  ❌ Rejected: Lambda is a service for running code...
  
  📊 Total DPO pairs: 5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🎯 Manual Testing

Send individual questions:

```bash
curl -X POST http://localhost:8001/ask/multi-candidate \
  -H 'Content-Type: application/json' \
  -d '{"question": "What is AWS Lambda?", "num_candidates": 3}'
```

Wait 20-30 seconds to see the full pipeline flow.

---

## 📈 After the Demo

View the complete dashboard:

```bash
./rlvr-dashboard.sh --auto
```

Check debug logs:

```bash
./debug-logs.sh
```

View generated data:

```bash
# Training data
cat /workspace/rlvr-automation/data/training_data/training_data_202512.jsonl | tail -5

# DPO pairs
ls -lh /workspace/rlvr-automation/data/dpo/
cat /workspace/rlvr-automation/data/dpo/pair_*.json | head -1 | jq .
```

---

## 🎨 Terminal Layout Recommendation

```
┌─────────────────────────────┬─────────────────────────────┐
│  Terminal 1                 │  Terminal 2                 │
│  Multi-Candidate Generation │  RAGAS Evaluation           │
│  ./monitor-candidates.sh    │  ./monitor-ragas.sh         │
│                             │                             │
├─────────────────────────────┼─────────────────────────────┤
│  Terminal 3                 │  Terminal 4                 │
│  Reward Calculation         │  DPO Pair Generation        │
│  ./monitor-rewards.sh       │  ./monitor-dpo.sh           │
│                             │                             │
└─────────────────────────────┴─────────────────────────────┘
```

---

## 🔧 Troubleshooting

**No output in monitors?**
- Check if workers are running: `ps aux | grep worker`
- Check log files exist: `ls -lh /workspace/logs/`
- Restart workers: `./runpod-start.sh`

**Monitors showing old data?**
- They follow logs in real-time, old data is normal
- Send a new question to see fresh output

**DPO pairs not being created?**
- Check if score differences are >= 0.3
- The improved scoring should create more variation
- Monitor will show why pairs are skipped

---

## 📝 Notes

- Each question takes ~20-30 seconds to fully process
- Monitors show real-time updates as events flow through
- All monitors can be stopped with Ctrl+C
- Logs are preserved for later analysis

---

**Enjoy the demo! 🚀**

