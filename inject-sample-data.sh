#!/bin/bash

# This script injects sample log data to demonstrate the dashboard

LOG_FILE="/workspace/logs/qa-orchestrator.log"

echo "Injecting sample pipeline data into logs..."

# Create logs directory if it doesn't exist
mkdir -p /workspace/logs

# Inject sample data
cat >> "$LOG_FILE" << 'EOF'
2025-12-24 10:00:01 INFO: Received question: "What is the capital of France?"
2025-12-24 10:00:02 INFO: Starting multi-candidate generation with 3 workers
2025-12-24 10:00:03 INFO: Worker-1 generating response...
2025-12-24 10:00:04 INFO: Worker-1 response: "Paris is the capital and largest city of France, located in the north-central part of the country"
2025-12-24 10:00:04 INFO: Worker-2 generating response...
2025-12-24 10:00:05 INFO: Worker-2 response: "The capital of France is Paris, which has been the capital since 987 AD"
2025-12-24 10:00:05 INFO: Worker-3 generating response...
2025-12-24 10:00:06 INFO: Worker-3 response: "France capital is Paris"
2025-12-24 10:00:07 INFO: Starting RAGAS evaluation for Worker-1
2025-12-24 10:00:08 INFO: Worker-1 RAGAS - Faithfulness: 0.95
2025-12-24 10:00:08 INFO: Worker-1 RAGAS - Relevance: 0.92
2025-12-24 10:00:09 INFO: Worker-1 RAGAS - Correctness: 0.90
2025-12-24 10:00:09 INFO: Worker-1 Total Reward: 0.92
2025-12-24 10:00:10 INFO: Starting RAGAS evaluation for Worker-2
2025-12-24 10:00:11 INFO: Worker-2 RAGAS - Faithfulness: 0.88
2025-12-24 10:00:11 INFO: Worker-2 RAGAS - Relevance: 0.85
2025-12-24 10:00:12 INFO: Worker-2 RAGAS - Correctness: 0.87
2025-12-24 10:00:12 INFO: Worker-2 Total Reward: 0.87
2025-12-24 10:00:13 INFO: Starting RAGAS evaluation for Worker-3
2025-12-24 10:00:14 INFO: Worker-3 RAGAS - Faithfulness: 0.65
2025-12-24 10:00:14 INFO: Worker-3 RAGAS - Relevance: 0.70
2025-12-24 10:00:15 INFO: Worker-3 RAGAS - Correctness: 0.60
2025-12-24 10:00:15 INFO: Worker-3 Total Reward: 0.65
2025-12-24 10:00:16 INFO: Reward calculation complete - Best: Worker-1 (0.92), Worst: Worker-3 (0.65)
2025-12-24 10:00:17 INFO: Creating DPO preference pair
2025-12-24 10:00:18 INFO: DPO Chosen response from Worker-1: "Paris is the capital and largest city of France, located in the north-central part of the country"
2025-12-24 10:00:18 INFO: DPO Rejected response from Worker-3: "France capital is Paris"
2025-12-24 10:00:19 INFO: DPO preference pair created successfully
2025-12-24 10:00:20 INFO: Saved DPO pair to /workspace/rlvr-automation/data/dpo/pair_20251224_100020.json

2025-12-24 10:05:01 INFO: Received question: "Explain neural networks in simple terms"
2025-12-24 10:05:02 INFO: Starting multi-candidate generation with 3 workers
2025-12-24 10:05:03 INFO: Worker-1 generating response...
2025-12-24 10:05:05 INFO: Worker-1 response: "Neural networks are computing systems inspired by biological neural networks in animal brains, consisting of interconnected nodes that process information"
2025-12-24 10:05:05 INFO: Worker-2 generating response...
2025-12-24 10:05:07 INFO: Worker-2 response: "A neural network is like a brain made of math - it learns patterns from examples and makes predictions"
2025-12-24 10:05:07 INFO: Worker-3 generating response...
2025-12-24 10:05:09 INFO: Worker-3 response: "Neural networks use layers of neurons to transform input data into useful outputs through weighted connections"
2025-12-24 10:05:10 INFO: Starting RAGAS evaluation for Worker-1
2025-12-24 10:05:11 INFO: Worker-1 RAGAS - Faithfulness: 0.93
2025-12-24 10:05:11 INFO: Worker-1 RAGAS - Relevance: 0.90
2025-12-24 10:05:12 INFO: Worker-1 RAGAS - Correctness: 0.91
2025-12-24 10:05:12 INFO: Worker-1 Total Reward: 0.91
2025-12-24 10:05:13 INFO: Starting RAGAS evaluation for Worker-2
2025-12-24 10:05:14 INFO: Worker-2 RAGAS - Faithfulness: 0.85
2025-12-24 10:05:14 INFO: Worker-2 RAGAS - Relevance: 0.88
2025-12-24 10:05:15 INFO: Worker-2 RAGAS - Correctness: 0.82
2025-12-24 10:05:15 INFO: Worker-2 Total Reward: 0.85
2025-12-24 10:05:16 INFO: Starting RAGAS evaluation for Worker-3
2025-12-24 10:05:17 INFO: Worker-3 RAGAS - Faithfulness: 0.89
2025-12-24 10:05:17 INFO: Worker-3 RAGAS - Relevance: 0.87
2025-12-24 10:05:18 INFO: Worker-3 RAGAS - Correctness: 0.88
2025-12-24 10:05:18 INFO: Worker-3 Total Reward: 0.88
2025-12-24 10:05:19 INFO: Reward calculation complete - Best: Worker-1 (0.91), Worst: Worker-2 (0.85)
2025-12-24 10:05:20 INFO: Creating DPO preference pair
2025-12-24 10:05:21 INFO: DPO Chosen response from Worker-1: "Neural networks are computing systems inspired by biological neural networks"
2025-12-24 10:05:21 INFO: DPO Rejected response from Worker-2: "A neural network is like a brain made of math"
2025-12-24 10:05:22 INFO: DPO preference pair created successfully
2025-12-24 10:05:23 INFO: Saved DPO pair to /workspace/rlvr-automation/data/dpo/pair_20251224_100523.json
EOF

# Create sample DPO files
mkdir -p /workspace/rlvr-automation/data/dpo

cat > /workspace/rlvr-automation/data/dpo/pair_20251224_100020.json << 'EOF'
{
  "question": "What is the capital of France?",
  "chosen": {
    "response": "Paris is the capital and largest city of France, located in the north-central part of the country",
    "worker_id": "Worker-1",
    "reward": 0.92,
    "ragas_scores": {
      "faithfulness": 0.95,
      "relevance": 0.92,
      "correctness": 0.90
    }
  },
  "rejected": {
    "response": "France capital is Paris",
    "worker_id": "Worker-3",
    "reward": 0.65,
    "ragas_scores": {
      "faithfulness": 0.65,
      "relevance": 0.70,
      "correctness": 0.60
    }
  },
  "timestamp": "2025-12-24T10:00:20Z"
}
EOF

cat > /workspace/rlvr-automation/data/dpo/pair_20251224_100523.json << 'EOF'
{
  "question": "Explain neural networks in simple terms",
  "chosen": {
    "response": "Neural networks are computing systems inspired by biological neural networks in animal brains, consisting of interconnected nodes that process information",
    "worker_id": "Worker-1",
    "reward": 0.91,
    "ragas_scores": {
      "faithfulness": 0.93,
      "relevance": 0.90,
      "correctness": 0.91
    }
  },
  "rejected": {
    "response": "A neural network is like a brain made of math - it learns patterns from examples and makes predictions",
    "worker_id": "Worker-2",
    "reward": 0.85,
    "ragas_scores": {
      "faithfulness": 0.85,
      "relevance": 0.88,
      "correctness": 0.82
    }
  },
  "timestamp": "2025-12-24T10:05:23Z"
}
EOF

echo "✓ Sample data injected successfully!"
echo ""
echo "Sample log entries added to: $LOG_FILE"
echo "Sample DPO files created in: /workspace/rlvr-automation/data/dpo/"
echo ""
echo "Now run the dashboard to see the data:"
echo "  ./rlvr-dashboard.sh"
echo ""

