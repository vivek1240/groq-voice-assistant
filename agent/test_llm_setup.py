#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test LLM Evaluation Setup

This script tests the LLM evaluation system to ensure it's configured correctly.
Run this to verify your GROQ_API_KEY is working and LLM evaluation is enabled.
"""

import os
import sys
import logging
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from labs_evaluator import LabsCallEvaluator

# Load environment
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("test-llm-evaluation")


def test_environment():
    """Test that environment is configured correctly"""
    print("\n" + "=" * 70)
    print("TESTING ENVIRONMENT CONFIGURATION")
    print("=" * 70)
    
    # Check GROQ_API_KEY
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ GROQ_API_KEY not found in environment")
        print("   Add it to .env file:")
        print("   GROQ_API_KEY=your_key_here")
        return False
    else:
        print(f"✅ GROQ_API_KEY found: {api_key[:10]}...{api_key[-4:]}")
    
    # Check USE_LLM_EVALUATION
    use_llm = os.getenv("USE_LLM_EVALUATION", "true")
    print(f"✅ USE_LLM_EVALUATION: {use_llm}")
    
    # Check model
    model = os.getenv("LABS_EVAL_MODEL", "llama-3.3-70b-versatile")
    print(f"✅ LABS_EVAL_MODEL: {model}")
    
    return True


def test_llm_initialization():
    """Test that LLM client initializes correctly"""
    print("\n" + "=" * 70)
    print("TESTING LLM INITIALIZATION")
    print("=" * 70)
    
    try:
        # Try to initialize evaluator with LLM
        evaluator = LabsCallEvaluator(use_llm=True)
        
        if evaluator.use_llm:
            print("✅ LLM evaluator initialized successfully")
            print(f"✅ Model: {evaluator.llm_model}")
            return True
        else:
            print("❌ LLM evaluator disabled (check logs above for reason)")
            return False
            
    except Exception as e:
        print(f"❌ Error initializing LLM evaluator: {e}")
        return False


def test_sample_evaluation():
    """Test evaluation with sample data"""
    print("\n" + "=" * 70)
    print("TESTING SAMPLE EVALUATION")
    print("=" * 70)
    
    # Sample call metrics
    sample_metrics = {
        "call_id": "test_llm_evaluation",
        "start_timestamp": "2026-01-24T10:00:00",
        "end_timestamp": "2026-01-24T10:02:30",
        "duration_seconds": 150.0,
        "total_cost": 0.05,
        "responses": [
            {"response_id": "r1", "end_to_end_latency_ms": 2000},
            {"response_id": "r2", "end_to_end_latency_ms": 1800},
            {"response_id": "r3", "end_to_end_latency_ms": 2200},
        ],
        "avg_end_to_end_latency_ms": 2000.0
    }
    
    try:
        evaluator = LabsCallEvaluator(use_llm=True, output_dir="test_evaluations")
        
        print("📊 Evaluating sample call...")
        print(f"   Duration: {sample_metrics['duration_seconds']}s")
        print(f"   Responses: {len(sample_metrics['responses'])}")
        
        evaluation = evaluator.evaluate_call(sample_metrics)
        
        print("\n✅ Evaluation completed!")
        print(f"\n📋 RESULTS:")
        print(f"   Method: {evaluation.evaluation_method}")
        print(f"   Sentiment: {evaluation.user_sentiment.value}")
        print(f"   Query Resolved: {evaluation.query_resolved}")
        print(f"   Category: {evaluation.query_category.value}")
        print(f"   Phase: {evaluation.testing_phase.value}")
        print(f"   Medical Boundary: {evaluation.medical_boundary_maintained}")
        print(f"   Summary: {evaluation.call_summary}")
        
        if evaluation.evaluation_method == "llm":
            print("\n🎉 LLM EVALUATION IS WORKING!")
            return True
        else:
            print("\n⚠️  Fell back to heuristic evaluation")
            return False
            
    except Exception as e:
        print(f"❌ Error during evaluation: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("LLM EVALUATION SYSTEM TEST")
    print("=" * 70)
    
    # Run tests
    results = {
        "Environment": test_environment(),
        "LLM Initialization": test_llm_initialization(),
        "Sample Evaluation": test_sample_evaluation()
    }
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL TESTS PASSED - LLM EVALUATION IS READY!")
        print("=" * 70)
        print("\nYour system is now using intelligent LLM-based evaluation.")
        print("Every call will be accurately analyzed for:")
        print("  • Sentiment and emotional state")
        print("  • Intent and query category")
        print("  • Compliance and medical boundaries")
        print("  • Disclaimer verification")
        print("  • Escalation requirements")
        print("\nCost: ~$0.0004 per call evaluation")
    else:
        print("⚠️  SOME TESTS FAILED")
        print("=" * 70)
        print("\nReview the errors above and:")
        print("  1. Ensure GROQ_API_KEY is set in .env")
        print("  2. Verify 'groq' package is installed: pip install groq")
        print("  3. Check your internet connection")
        print("  4. Verify API key is valid at console.groq.com")
    print("=" * 70 + "\n")
    
    # Cleanup test directory
    import shutil
    test_dir = Path("test_evaluations")
    if test_dir.exists():
        shutil.rmtree(test_dir)
        print("🧹 Cleaned up test files\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
