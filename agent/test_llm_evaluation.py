"""
Test LLM-Based Evaluation with Conversation Transcripts

This script tests that the LLM evaluator correctly processes conversation transcripts
and provides intelligent evaluation.
"""

import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add agent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from labs_evaluator import LabsCallEvaluator

# Load environment variables
load_dotenv()

# Sample call with conversation transcript
sample_call_with_transcript = {
    "call_id": "test_llm_eval_001",
    "start_timestamp": "2026-01-24T15:00:00.000000",
    "end_timestamp": "2026-01-24T15:03:30.000000",
    "duration_seconds": 210.0,
    "responses": [
        {
            "response_id": "test_llm_eval_001_response_1",
            "timestamp": "2026-01-24T15:00:10.000000",
            "stt": {
                "model": "whisper-large-v3-turbo",
                "duration_seconds": 2.5,
                "cost": 0.00083,
                "latency_ms": 850.0,
                "transcript_length": 45,
                "transcript": "Hi, I just received my lab test kit but I'm not sure how to register it.",
                "timestamp": "2026-01-24T15:00:10.000000"
            },
            "llm": {
                "model": "llama-3.3-70b-versatile",
                "input_tokens": 2000,
                "output_tokens": 120,
                "total_tokens": 2120,
                "input_cost": 0.00118,
                "output_cost": 0.0000948,
                "total_cost": 0.0012748,
                "latency_ms": 1200.0,
                "response_text": "Hello! I'd be happy to help you register your lab test kit. You'll need to visit our website and enter the unique kit ID that's printed on the barcode label inside your kit. Do you have the kit handy?",
                "timestamp": "2026-01-24T15:00:11.200000"
            },
            "tts": {
                "model": "canopylabs/orpheus-v1-english",
                "characters_processed": 180,
                "cost": 0.0018,
                "latency_ms": 900.0,
                "timestamp": "2026-01-24T15:00:12.100000"
            },
            "end_to_end_latency_ms": 2950.0,
            "total_cost": 0.0039548
        },
        {
            "response_id": "test_llm_eval_001_response_2",
            "timestamp": "2026-01-24T15:00:15.000000",
            "stt": {
                "model": "whisper-large-v3-turbo",
                "duration_seconds": 1.8,
                "cost": 0.0006,
                "latency_ms": 720.0,
                "transcript_length": 28,
                "transcript": "Yes, I have it here. Where exactly is the kit ID?",
                "timestamp": "2026-01-24T15:00:15.720000"
            },
            "llm": {
                "model": "llama-3.3-70b-versatile",
                "input_tokens": 2200,
                "output_tokens": 95,
                "total_tokens": 2295,
                "input_cost": 0.001298,
                "output_cost": 0.00007505,
                "total_cost": 0.00137305,
                "latency_ms": 1100.0,
                "response_text": "Great! The kit ID is a 10-digit alphanumeric code located on the barcode sticker inside the kit box. It usually starts with 'MHC-'. Can you find it?",
                "timestamp": "2026-01-24T15:00:16.820000"
            },
            "tts": {
                "model": "canopylabs/orpheus-v1-english",
                "characters_processed": 145,
                "cost": 0.00145,
                "latency_ms": 800.0,
                "timestamp": "2026-01-24T15:00:17.620000"
            },
            "end_to_end_latency_ms": 2620.0,
            "total_cost": 0.00352305
        }
    ],
    "conversation_transcript": [
        {
            "role": "user",
            "content": "Hi, I just received my lab test kit but I'm not sure how to register it."
        },
        {
            "role": "assistant",
            "content": "Hello! I'd be happy to help you register your lab test kit. You'll need to visit our website and enter the unique kit ID that's printed on the barcode label inside your kit. Do you have the kit handy?"
        },
        {
            "role": "user",
            "content": "Yes, I have it here. Where exactly is the kit ID?"
        },
        {
            "role": "assistant",
            "content": "Great! The kit ID is a 10-digit alphanumeric code located on the barcode sticker inside the kit box. It usually starts with 'MHC-'. Can you find it?"
        }
    ],
    "total_stt_cost": 0.00143,
    "total_llm_cost": 0.00264785,
    "total_tts_cost": 0.00325,
    "total_vapi_cost": 0.0175,
    "total_cost": 0.02482785,
    "total_stt_duration": 4.3,
    "total_llm_input_tokens": 4200,
    "total_llm_output_tokens": 215,
    "total_tts_characters": 325,
    "avg_stt_latency_ms": 785.0,
    "avg_llm_latency_ms": 1150.0,
    "avg_tts_latency_ms": 850.0,
    "avg_end_to_end_latency_ms": 2785.0
}


def test_llm_evaluation():
    """Test LLM-based evaluation with conversation transcript"""
    
    print("=" * 80)
    print("TESTING LLM-BASED EVALUATION")
    print("=" * 80)
    
    # Check if GROQ_API_KEY is set
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("[ERROR] GROQ_API_KEY not found in environment")
        print("Please ensure your .env file contains GROQ_API_KEY")
        return False
    
    print("[OK] GROQ_API_KEY found")
    print(f"[OK] API Key: {api_key[:20]}...{api_key[-10:]}")
    
    # Create evaluator with LLM enabled
    print("\n" + "=" * 80)
    print("Initializing LLM Evaluator...")
    print("=" * 80)
    
    evaluator = LabsCallEvaluator(use_llm=True)
    
    if not evaluator.use_llm:
        print("[ERROR] LLM evaluation not enabled despite use_llm=True")
        return False
    
    print("[OK] LLM evaluator initialized successfully")
    
    # Prepare conversation data
    conversation_data = {
        'messages': sample_call_with_transcript['conversation_transcript']
    }
    
    print(f"\n[OK] Conversation transcript loaded: {len(conversation_data['messages'])} turns")
    
    # Evaluate the call
    print("\n" + "=" * 80)
    print("Running LLM Evaluation...")
    print("=" * 80)
    
    try:
        evaluation = evaluator.evaluate_call(
            sample_call_with_transcript,
            conversation_data=conversation_data
        )
        
        print("\n[OK] Evaluation completed successfully!")
        
        # Display results
        print("\n" + "=" * 80)
        print("EVALUATION RESULTS")
        print("=" * 80)
        
        print(f"\nEvaluation Method: {evaluation.evaluation_method}")
        
        print("\nCORE METRICS:")
        print(f"  User Sentiment: {evaluation.user_sentiment.value}")
        print(f"  Query Resolved: {evaluation.query_resolved}")
        print(f"  Escalation Required: {evaluation.escalation_required}")
        
        print("\nDOMAIN METRICS:")
        print(f"  Query Category: {evaluation.query_category.value}")
        print(f"  Testing Phase: {evaluation.testing_phase.value}")
        
        print("\nCOMPLIANCE METRICS:")
        print(f"  Medical Boundary Maintained: {evaluation.medical_boundary_maintained}")
        print(f"  Proper Disclaimer Given: {evaluation.proper_disclaimer_given}")
        
        print("\nCALL SUMMARY:")
        print(f"  {evaluation.call_summary}")
        
        print(f"\nNotes: {evaluation.notes}")
        
        if evaluation.flags:
            print("\nCOMPLIANCE FLAGS:")
            for flag in evaluation.flags:
                print(f"  - {flag}")
        
        print("\n" + "=" * 80)
        
        # Validate it's actually LLM evaluation
        if evaluation.evaluation_method == "llm":
            print("[SUCCESS] LLM evaluation is working!")
            return True
        else:
            print(f"[WARNING] Expected 'llm' method but got '{evaluation.evaluation_method}'")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] during evaluation: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_llm_evaluation()
    
    if success:
        print("\n" + "=" * 80)
        print("[SUCCESS] ALL TESTS PASSED - LLM EVALUATION IS WORKING!")
        print("=" * 80)
        sys.exit(0)
    else:
        print("\n" + "=" * 80)
        print("[FAILED] TESTS FAILED - Please check configuration")
        print("=" * 80)
        sys.exit(1)
