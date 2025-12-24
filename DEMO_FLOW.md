# 🚀 RLVR Automation: Complete Flow from UI to DPO File Creation

## 📋 Overview
This document explains the complete end-to-end flow of how a user query transforms into DPO training data.

---

## 🔄 Complete Flow Diagram

```
┌─────────────┐
│   User UI   │ "What is AWS Lambda?"
│  (Browser)  │
└──────┬──────┘
       │ HTTP POST /ask/multi-candidate
       │ {question: "...", num_candidates: 3}
       ▼
┌─────────────────────┐
│   API Gateway       │ Port 8000
│   (FastAPI)         │ Routes request to orchestrator
└──────┬──────────────┘
       │ POST /ask/multi-candidate
       ▼
┌─────────────────────────────────────────────────────────────┐
│   QA Orchestrator (Port 8001)                               │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ 1. Generate batch_id for multi-candidate request   │   │
│   │ 2. Create 3 candidates with different temperatures │   │
│   │    - Candidate 0: temp=0.3 (conservative)          │   │
│   │    - Candidate 1: temp=0.7 (balanced)              │   │
│   │    - Candidate 2: temp=0.9 (creative)              │   │
│   └─────────────────────────────────────────────────────┘   │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ For each candidate (3 times):
       │
       ├─► 1. Retrieve context from Qdrant (vector DB)
       │   2. Generate answer using Ollama (llama3.2:3b)
       │   3. Publish "answer.generated" event to RabbitMQ
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│   RabbitMQ Event Bus                                        │
│   Exchange: rlvr_events                                     │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ Event: answer.generated                             │   │
│   │ {                                                   │   │
│   │   event_id: "abc-123",                              │   │
│   │   batch_id: "batch-xyz",                            │   │
│   │   question: "What is AWS Lambda?",                  │   │
│   │   answer: "AWS Lambda is...",                       │   │
│   │   contexts: [...],                                  │   │
│   │   temperature: 0.7                                  │   │
│   │ }                                                   │   │
│   └─────────────────────────────────────────────────────┘   │
└──────┬──────────────────────────────────────────────────────┘
       │
       │ Event consumed by 2 workers:
       │
       ├─────────────────────────────────────────────────┐
       │                                                 │
       ▼                                                 ▼
┌──────────────────────┐                    ┌──────────────────────┐
│ Verification Worker  │                    │ Dataset Worker       │
│                      │                    │                      │
│ 1. Receive event     │                    │ 1. Receive event     │
│ 2. Run RAGAS verify: │                    │ 2. Store in memory   │
│    - Faithfulness    │                    │    (waiting for      │
│    - Relevancy       │                    │     verification)    │
│ 3. Calculate score:  │                    │                      │
│    score = (f+r)/2   │                    │                      │
│ 4. Publish event ────┼────────────────────┼─►                    │
│    "verification.    │                    │                      │
│     completed"       │                    │                      │
└──────────────────────┘                    └──────────────────────┘
                                                     │
                                                     │ After receiving
                                                     │ all 3 verifications
                                                     ▼
                                            ┌──────────────────────┐
                                            │ Dataset Worker       │
                                            │ Event Aggregator     │
                                            │                      │
                                            │ Has complete entry:  │
                                            │ - 3 answers          │
                                            │ - 3 verifications    │
                                            │                      │
                                            │ Triggers:            │
                                            │ 1. Training data     │
                                            │ 2. DPO analysis      │
                                            └──────┬───────────────┘
                                                   │
                                                   ▼
                                            ┌──────────────────────┐
                                            │ DPO Writer           │
                                            │                      │
                                            │ 1. Sort by score     │
                                            │ 2. Check thresholds: │
                                            │    ✓ diff ≥ 0.05    │
                                            │    ✓ best ≥ 0.6     │
                                            │ 3. Create pair:      │
                                            │    chosen = best     │
                                            │    rejected = worst  │
                                            │ 4. Write to file     │
                                            └──────┬───────────────┘
                                                   │
                                                   ▼
                                            ┌──────────────────────┐
                                            │ DPO File Created!    │
                                            │                      │
                                            │ /app/data/dpo_data/  │
                                            │ dpo_data_202512.jsonl│
                                            └──────────────────────┘
```

---

## 📝 Detailed Step-by-Step Flow

### **Step 1: User Sends Query from UI**
```bash
# User clicks "Ask Question" in UI
Question: "What is AWS Lambda?"
Candidates: 3
```

**What happens:**
- UI sends HTTP POST to API Gateway at `http://localhost:8000/ask/multi-candidate`
- Request body: `{"question": "What is AWS Lambda?", "num_candidates": 3}`

---

### **Step 2: API Gateway Routes Request**
```python
# api-gateway/main.py
@app.post("/ask/multi-candidate")
async def ask_multi_candidate(request: MultiCandidateRequest):
    # Forward to QA Orchestrator
    response = await qa_orchestrator_client.post("/ask/multi-candidate", json=request)
    return response.json()
```

**What happens:**
- API Gateway receives request
- Routes to QA Orchestrator at `http://qa-orchestrator:8001/ask/multi-candidate`

---

### **Step 3: QA Orchestrator Generates Multiple Candidates**
```python
# qa-orchestrator/main.py
@app.post("/ask/multi-candidate")
async def ask_multi_candidate(request: MultiCandidateRequest):
    batch_id = str(uuid.uuid4())  # Generate unique batch ID
    
    # Generate 3 candidates with different temperatures
    temperatures = [0.3, 0.7, 0.9]
    candidates = []
    
    for i, temp in enumerate(temperatures):
        # 1. Retrieve context from Qdrant
        contexts = await retrieve_contexts(question)
        
        # 2. Generate answer with Ollama
        answer = await generate_answer(question, contexts, temperature=temp)
        
        # 3. Publish answer.generated event
        event = AnswerGeneratedEvent(
            event_id=str(uuid.uuid4()),
            batch_id=batch_id,
            question=question,
            answer=answer,
            contexts=contexts,
            metadata={"temperature": temp, "candidate_index": i}
        )
        await event_publisher.publish(event, routing_key="answer.generated")
        
        candidates.append({"answer": answer, "metadata": {...}})
    
    return {"candidates": candidates, "batch_id": batch_id}
```

**What happens:**
- Creates unique `batch_id` to group the 3 candidates
- For each candidate (3 times):
  1. **Retrieves context** from Qdrant vector database
  2. **Generates answer** using Ollama (llama3.2:3b) with different temperature
  3. **Publishes event** to RabbitMQ with routing key `answer.generated`
- Returns all 3 candidates to user immediately

---

### **Step 4: RabbitMQ Event Bus Distributes Events**
```
Exchange: rlvr_events (topic exchange)
Routing Key: answer.generated

Event Payload:
{
  "event_id": "abc-123",
  "batch_id": "batch-xyz",
  "question": "What is AWS Lambda?",
  "answer": "AWS Lambda is a serverless compute service...",
  "contexts": [
    {"content": "...", "score": 0.85},
    {"content": "...", "score": 0.78}
  ],
  "metadata": {
    "temperature": 0.7,
    "candidate_index": 1,
    "model": "ollama/llama3.2:3b"
  }
}
```

**What happens:**
- RabbitMQ receives 3 events (one per candidate)
- Events are distributed to **2 consumers**:
  1. **Verification Worker** (subscribes to `answer.generated`)
  2. **Dataset Worker** (subscribes to `answer.generated`)

---

### **Step 5: Verification Worker Processes Event**
```python
# verification-worker/src/worker.py
async def handle_answer_generated(event: AnswerGeneratedEvent):
    # 1. Extract data
    question = event.question
    answer = event.answer
    contexts = event.contexts
    
    # 2. Run RAGAS verification
    faithfulness, relevancy = await ragas_verifier.verify(
        question=question,
        answer=answer,
        contexts=contexts
    )
    
    # 3. Calculate combined score
    score = (faithfulness + relevancy) / 2
    confidence = "high" if score > 0.7 else "medium" if score > 0.5 else "low"
    
    # 4. Publish verification.completed event
    verification_event = VerificationCompletedEvent(
        event_id=str(uuid.uuid4()),
        answer_event_id=event.event_id,
        batch_id=event.batch_id,
        question=question,
        answer=answer,
        faithfulness=faithfulness,
        relevancy=relevancy,
        score=score,
        confidence=confidence
    )
    await event_publisher.publish(verification_event, routing_key="verification.completed")
```

**What happens:**
- Receives `answer.generated` event
- Runs **RAGAS verification**:
  - **Faithfulness**: Is the answer grounded in the context? (0.0-1.0)
  - **Relevancy**: Does the answer address the question? (0.0-1.0)
- Calculates **combined score**: `(faithfulness + relevancy) / 2`
- Publishes `verification.completed` event back to RabbitMQ

**Example scores:**
```
Candidate 0 (temp=0.3): faithfulness=0.6, relevancy=0.7 → score=0.65
Candidate 1 (temp=0.7): faithfulness=0.7, relevancy=0.7 → score=0.70
Candidate 2 (temp=0.9): faithfulness=0.5, relevancy=0.6 → score=0.55
```

---

### **Step 6: Dataset Worker Aggregates Events**
```python
# dataset-generation-worker/src/event_aggregator.py
class EventAggregator:
    def __init__(self):
        self.entries = {}  # Keyed by batch_id
    
    async def handle_answer_generated(self, event):
        batch_id = event.batch_id
        if batch_id not in self.entries:
            self.entries[batch_id] = {
                "question": event.question,
                "answers": [],
                "verifications": [],
                "created_at": datetime.now()
            }
        self.entries[batch_id]["answers"].append(event)
    
    async def handle_verification_completed(self, event):
        batch_id = event.batch_id
        if batch_id in self.entries:
            self.entries[batch_id]["verifications"].append(event)
            
            # Check if complete (3 answers + 3 verifications)
            if self._is_complete(batch_id):
                await self._process_complete_entry(batch_id)
    
    def _is_complete(self, batch_id):
        entry = self.entries[batch_id]
        return len(entry["answers"]) == 3 and len(entry["verifications"]) == 3
    
    async def _process_complete_entry(self, batch_id):
        entry = self.entries[batch_id]
        
        # 1. Write to training data
        await training_writer.write(entry)
        
        # 2. Analyze for DPO
        await dpo_writer.analyze_and_write(entry)
```

**What happens:**
- Receives both `answer.generated` and `verification.completed` events
- **Aggregates by batch_id** in memory
- Waits until complete: **3 answers + 3 verifications**
- When complete, triggers:
  1. **Training data writer** (writes to `training_data_202512.jsonl`)
  2. **DPO writer** (analyzes and creates DPO pairs)

---

### **Step 7: DPO Writer Creates Training Pairs**
```python
# dataset-generation-worker/src/dataset_writer.py
class DPODatasetWriter:
    def __init__(self, min_score_diff=0.05, min_chosen_score=0.6):
        self.min_score_diff = min_score_diff
        self.min_chosen_score = min_chosen_score
    
    async def analyze_and_write(self, entry):
        # 1. Merge answers with verification scores
        scored_answers = []
        for answer in entry["answers"]:
            verification = self._find_verification(answer.event_id, entry["verifications"])
            scored_answers.append({
                "answer": answer,
                "score": verification.score,
                "faithfulness": verification.faithfulness,
                "relevancy": verification.relevancy
            })
        
        # 2. Sort by score (best to worst)
        scored_answers.sort(key=lambda x: x["score"], reverse=True)
        
        best = scored_answers[0]   # Highest score
        worst = scored_answers[-1]  # Lowest score
        
        # 3. Calculate score difference
        score_diff = best["score"] - worst["score"]
        
        # 4. Check quality thresholds
        if score_diff < self.min_score_diff:
            logger.info(f"❌ Score diff too small: {score_diff:.3f} < {self.min_score_diff}")
            return
        
        if best["score"] < self.min_chosen_score:
            logger.info(f"❌ Chosen score too low: {best['score']:.3f} < {self.min_chosen_score}")
            return
        
        # 5. All checks passed - create DPO pair!
        logger.info(f"✅ All quality checks passed for '{entry['question'][:50]}...'")
        await self._write_dpo_pair(best, worst, score_diff)
    
    async def _write_dpo_pair(self, chosen, rejected, score_diff):
        dpo_entry = {
            "prompt": chosen["answer"].question,
            "chosen": chosen["answer"].answer,
            "rejected": rejected["answer"].answer,
            "score_diff": score_diff,
            "chosen_score": chosen["score"],
            "rejected_score": rejected["score"],
            "metadata": {
                "chosen_temp": chosen["answer"].metadata["temperature"],
                "rejected_temp": rejected["answer"].metadata["temperature"],
                "created_at": datetime.now().isoformat()
            }
        }
        
        # Write to JSONL file
        output_file = Path("/app/data/dpo_data/dpo_data_202512.jsonl")
        with open(output_file, "a") as f:
            f.write(json.dumps(dpo_entry) + "\n")
        
        logger.info(f"✅ Wrote DPO pair to {output_file}")
```

**What happens:**
1. **Merges** answers with their verification scores
2. **Sorts** by score (best to worst)
3. **Calculates** score difference between best and worst
4. **Checks quality thresholds**:
   - ✅ Score diff ≥ 0.05 (relaxed from 0.3)
   - ✅ Best score ≥ 0.6 (relaxed from 0.7)
   - ✅ Quality filter disabled (for testing)
5. **Creates DPO pair**:
   - `chosen` = best answer (highest score)
   - `rejected` = worst answer (lowest score)
6. **Writes** to `/app/data/dpo_data/dpo_data_202512.jsonl`

**Example DPO pair:**
```json
{
  "prompt": "What is AWS Lambda?",
  "chosen": "AWS Lambda is a serverless compute service that runs code in response to events...",
  "rejected": "Lambda is a thing in AWS that does stuff...",
  "score_diff": 0.15,
  "chosen_score": 0.70,
  "rejected_score": 0.55,
  "metadata": {
    "chosen_temp": 0.7,
    "rejected_temp": 0.9,
    "created_at": "2025-12-24T13:02:38"
  }
}
```

---

## 🎯 Key Metrics

| Metric | Value | Description |
|--------|-------|-------------|
| **Candidates per query** | 3 | Different temperatures (0.3, 0.7, 0.9) |
| **Events per query** | 6 | 3 answer.generated + 3 verification.completed |
| **DPO pairs per query** | 0-1 | Only if quality thresholds pass |
| **Min score diff** | 0.05 | Relaxed from 0.3 for testing |
| **Min chosen score** | 0.6 | Relaxed from 0.7 for testing |
| **Processing time** | ~30s | From query to DPO file |

---

## 🔍 Monitoring Commands

```bash
# Check DPO file status
./check-dpo-status.sh

# Monitor in real-time
watch -n 5 ./check-dpo-status.sh

# View DPO pairs
cat /app/data/dpo_data/dpo_data_202512.jsonl | python3 -m json.tool

# Check worker logs
tail -f /workspace/logs/verification-worker.log
tail -f /workspace/logs/dataset-worker.log

# Count DPO pairs
wc -l /app/data/dpo_data/dpo_data_202512.jsonl
```

---

## ✅ Success Criteria

For a DPO pair to be created, ALL must be true:
1. ✅ 3 answers generated (different temperatures)
2. ✅ 3 verifications completed (RAGAS scores)
3. ✅ Score difference ≥ 0.05
4. ✅ Best score ≥ 0.6
5. ✅ Quality filter passed (currently disabled)

---

## 🚀 Demo Script

```bash
# 1. Start workers
./runpod-start-relaxed-thresholds.sh

# 2. Send test query
curl -X POST http://localhost:8001/ask/multi-candidate \
  -H 'Content-Type: application/json' \
  -d '{"question": "What is AWS Lambda?", "num_candidates": 3}'

# 3. Wait 30 seconds
sleep 30

# 4. Check DPO status
./check-dpo-status.sh

# 5. View DPO pairs
cat /app/data/dpo_data/dpo_data_202512.jsonl | python3 -m json.tool | head -50
```

---

**🎉 End Result:** High-quality DPO training data ready for fine-tuning!

