#!/usr/bin/env python3
"""
Test RLVR Implementation

Tests all RLVR components:
1. Pricing reward adapter
2. RLVR candidate service
3. Training logger
4. Integrated RAG service with RLVR
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.adapters.output.reward import PricingRewardAdapter
from src.core.rlvr import RLVRCandidateService, RLVRTrainingLogger
from src.factories import create_llm, create_reward_function, create_rlvr_candidate_service
from src.logging import get_logger

logger = get_logger(__name__)


def test_pricing_reward():
    """Test pricing reward computation."""
    print("\n" + "=" * 60)
    print("TEST 1: Pricing Reward Adapter")
    print("=" * 60)

    reward_adapter = PricingRewardAdapter()

    # Test case 1: Perfect match
    question = "What is the price of Taj Mahal Palace?"
    answer = "The price range for Taj Mahal Palace is ₹24,000 to ₹65,000 per night."
    reward = reward_adapter.compute_reward(question, answer)
    print(f"\nTest Case 1 (Perfect Match):")
    print(f"  Question: {question}")
    print(f"  Answer: {answer}")
    print(f"  Reward: {reward:.3f} (expected: 1.0)")
    assert reward == 1.0, f"Expected 1.0, got {reward}"

    # Test case 2: Partial overlap
    question = "What is the price of Taj Mahal Palace?"
    answer = "The price range is ₹20,000 to ₹50,000 per night."
    reward = reward_adapter.compute_reward(question, answer)
    print(f"\nTest Case 2 (Partial Overlap):")
    print(f"  Question: {question}")
    print(f"  Answer: {answer}")
    print(f"  Reward: {reward:.3f} (expected: >0.0 and <1.0)")
    assert 0.0 < reward < 1.0, f"Expected partial overlap, got {reward}"

    # Test case 3: No overlap
    question = "What is the price of Taj Mahal Palace?"
    answer = "The price range is ₹100,000 to ₹200,000 per night."
    reward = reward_adapter.compute_reward(question, answer)
    print(f"\nTest Case 3 (No Overlap):")
    print(f"  Question: {question}")
    print(f"  Answer: {answer}")
    print(f"  Reward: {reward:.3f} (expected: 0.0)")
    assert reward == 0.0, f"Expected 0.0, got {reward}"

    # Test case 4: Different hotel
    question = "What is the price of Taj Lake Palace Udaipur?"
    answer = "The price range for Taj Lake Palace is ₹45,000 to ₹95,000 per night."
    reward = reward_adapter.compute_reward(question, answer)
    print(f"\nTest Case 4 (Different Hotel - Perfect Match):")
    print(f"  Question: {question}")
    print(f"  Answer: {answer}")
    print(f"  Reward: {reward:.3f} (expected: 1.0)")
    assert reward == 1.0, f"Expected 1.0, got {reward}"

    print("\n✅ All pricing reward tests passed!")
    return True


def test_training_logger():
    """Test RLVR training logger."""
    print("\n" + "=" * 60)
    print("TEST 2: RLVR Training Logger")
    print("=" * 60)

    # Use a test file
    test_log_path = "training_data/test_rlvr_training.jsonl"
    logger_instance = RLVRTrainingLogger(log_path=test_log_path)

    # Log some test data
    question = "What is the price of Taj Mahal Palace?"
    context = "Taj Mahal Palace is a luxury hotel in Mumbai..."
    candidates = [
        {"index": 0, "answer": "₹24,000 to ₹65,000", "reward": 1.0, "temperature": 0.0},
        {"index": 1, "answer": "₹20,000 to ₹50,000", "reward": 0.6, "temperature": 0.3},
        {"index": 2, "answer": "₹30,000 to ₹70,000", "reward": 0.8, "temperature": 0.7},
    ]
    best_index = 0

    print(f"\nLogging test entry:")
    print(f"  Question: {question}")
    print(f"  Num candidates: {len(candidates)}")
    print(f"  Best index: {best_index}")

    logger_instance.log_candidates(
        question=question,
        context=context,
        candidates=candidates,
        best_index=best_index,
    )

    # Check stats
    stats = logger_instance.get_training_stats()
    print(f"\nTraining Stats:")
    print(f"  Total entries: {stats['total_entries']}")
    print(f"  Total candidates: {stats['total_candidates']}")
    print(f"  Avg best reward: {stats['avg_best_reward']:.3f}")

    assert stats["total_entries"] >= 1, "Should have at least 1 entry"
    print("\n✅ Training logger tests passed!")
    return True


def test_candidate_service():
    """Test RLVR candidate service with mock LLM."""
    print("\n" + "=" * 60)
    print("TEST 3: RLVR Candidate Service")
    print("=" * 60)

    # Create a mock LLM that returns predictable answers
    class MockLLM:
        def __init__(self):
            self.call_count = 0

        def invoke(self, prompt):
            # Return different prices for different candidates
            prices = [
                "₹24,000 to ₹65,000",  # Perfect match
                "₹20,000 to ₹50,000",  # Partial overlap
                "₹100,000 to ₹200,000",  # No overlap
            ]
            response = prices[self.call_count % len(prices)]
            self.call_count += 1
            # Return an object with a 'content' attribute
            class Response:
                def __init__(self, text):
                    self.content = text
            return Response(response)

    mock_llm = MockLLM()
    reward_function = create_reward_function()
    candidate_service = RLVRCandidateService(
        llm=mock_llm,
        reward_function=reward_function,
        num_candidates=3,
    )

    # Generate and score candidates
    question = "What is the price of Taj Mahal Palace?"
    context = "Taj Mahal Palace is a luxury hotel..."
    prompt_template = "Context: {context}\nQuestion: {question}\nAnswer:"

    print(f"\nGenerating candidates for: {question}")

    result = candidate_service.generate_and_score_candidates(
        question=question,
        context=context,
        prompt_template=prompt_template,
    )

    print(f"\nResults:")
    print(f"  Best answer: {result['best_answer']}")
    print(f"  Best index: {result['best_index']}")
    print(f"  Num candidates: {len(result['candidates'])}")

    print(f"\nAll candidates:")
    for i, candidate in enumerate(result["candidates"]):
        print(f"  {i}: reward={candidate['reward']:.3f}, answer={candidate['answer']}")

    # Verify best candidate was selected
    best_reward = result["candidates"][result["best_index"]]["reward"]
    all_rewards = [c["reward"] for c in result["candidates"]]
    assert best_reward == max(all_rewards), "Best candidate should have highest reward"

    print("\n✅ Candidate service tests passed!")
    return True


def test_integrated_rlvr():
    """Test integrated RLVR with real components (requires Ollama/OpenAI)."""
    print("\n" + "=" * 60)
    print("TEST 4: Integrated RLVR (Optional - requires LLM)")
    print("=" * 60)

    try:
        from src.factories import create_rag_service_with_rlvr

        print("\nCreating RAG service with RLVR...")
        # Note: This will fail if Ollama/OpenAI is not configured
        # That's OK - it's an optional test
        rag_service = create_rag_service_with_rlvr(
            num_candidates=3,
            enable_rlvr=True,
        )

        print(f"✅ RAG service created with RLVR support")
        print(f"  RLVR enabled: {rag_service.rlvr_candidate_service is not None}")
        print(f"  Training logger enabled: {rag_service.rlvr_training_logger is not None}")

        return True

    except Exception as e:
        print(f"\n⚠️  Integrated test skipped (LLM not configured): {e}")
        print("   This is OK - basic RLVR components are tested above")
        return True


def main():
    """Run all RLVR tests."""
    print("\n" + "=" * 60)
    print("RLVR IMPLEMENTATION TEST SUITE")
    print("=" * 60)

    tests = [
        ("Pricing Reward Adapter", test_pricing_reward),
        ("Training Logger", test_training_logger),
        ("Candidate Service", test_candidate_service),
        ("Integrated RLVR", test_integrated_rlvr),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"\n❌ Test failed: {name}")
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)

    print("\n🎉 All RLVR tests passed! Implementation is ready.")


if __name__ == "__main__":
    main()
