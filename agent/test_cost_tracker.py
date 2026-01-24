"""
Cost Tracker Testing Script

This script demonstrates and tests the cost tracking functionality.
"""

import time
import json
from cost_tracker import CostTracker


def test_basic_tracking():
    """Test basic cost tracking functionality"""
    print("=" * 80)
    print("TEST: Basic Cost Tracking")
    print("=" * 80)
    
    # Initialize tracker
    tracker = CostTracker(call_id="test_call_001")
    
    # Simulate 3 responses
    for i in range(3):
        print(f"\n--- Simulating Response {i+1} ---")
        
        # Start response
        tracker.start_response()
        
        # Simulate STT
        tracker.start_stt()
        time.sleep(0.1)  # Simulate processing time
        tracker.end_stt(
            duration=3.5 + i,  # Varying audio duration
            transcript=f"This is test message number {i+1}",
            model="whisper-large-v3-turbo"
        )
        
        # Simulate LLM
        tracker.start_llm()
        time.sleep(0.05)  # Simulate processing time
        tracker.end_llm(
            input_tokens=200 + (i * 50),  # Varying token counts
            output_tokens=100 + (i * 30),
            model="llama-3.3-70b-versatile"
        )
        
        # Simulate TTS
        tracker.start_tts()
        time.sleep(0.08)  # Simulate processing time
        tracker.end_tts(
            characters=250 + (i * 50),  # Varying character counts
            model="canopylabs/orpheus-v1-english"
        )
        
        # End response
        tracker.end_response()
        time.sleep(0.2)  # Small delay between responses
    
    # End call
    tracker.end_call()
    
    # Print summary
    summary = tracker.get_call_summary()
    print("\n" + "=" * 80)
    print("TEST RESULTS")
    print("=" * 80)
    print(f"Total Responses: {len(summary['responses'])}")
    print(f"Total Cost: ${summary['total_cost']:.6f}")
    print(f"  - STT:  ${summary['total_stt_cost']:.6f}")
    print(f"  - LLM:  ${summary['total_llm_cost']:.6f}")
    print(f"  - TTS:  ${summary['total_tts_cost']:.6f}")
    print(f"  - VAPI: ${summary['total_vapi_cost']:.6f}")
    print(f"\nAverage Latencies:")
    print(f"  - STT: {summary['avg_stt_latency_ms']:.0f}ms")
    print(f"  - LLM: {summary['avg_llm_latency_ms']:.0f}ms")
    print(f"  - TTS: {summary['avg_tts_latency_ms']:.0f}ms")
    print(f"  - E2E: {summary['avg_end_to_end_latency_ms']:.0f}ms")
    
    # Export to file
    test_file = "test_metrics.json"
    tracker.export_to_file(test_file)
    print(f"\nMetrics exported to: {test_file}")
    
    print("\n[OK] Test completed successfully!\n")
    return tracker


def test_edge_cases():
    """Test edge cases and error handling"""
    print("=" * 80)
    print("TEST: Edge Cases")
    print("=" * 80)
    
    # Test with minimal data
    tracker = CostTracker(call_id="test_edge_case")
    tracker.start_response()
    tracker.end_response()  # Empty response
    tracker.end_call()
    
    summary = tracker.get_call_summary()
    print(f"\nEmpty response test: {len(summary['responses'])} response(s)")
    print(f"Total cost: ${summary['total_cost']:.6f}")
    
    print("\n[OK] Edge case test completed!\n")


def test_json_export():
    """Test JSON export and loading"""
    print("=" * 80)
    print("TEST: JSON Export/Import")
    print("=" * 80)
    
    # Create and export
    tracker = test_basic_tracking()
    
    # Load and verify
    with open("test_metrics.json", 'r') as f:
        loaded_data = json.load(f)
    
    print(f"Loaded call_id: {loaded_data['call_id']}")
    print(f"Loaded responses: {len(loaded_data['responses'])}")
    print(f"Loaded total_cost: ${loaded_data['total_cost']:.6f}")
    
    print("\n[OK] JSON export/import test completed!\n")


def create_sample_data():
    """Create sample data for testing analysis scripts"""
    print("=" * 80)
    print("CREATING SAMPLE DATA")
    print("=" * 80)
    
    import os
    os.makedirs("metrics", exist_ok=True)
    
    # Create 5 sample calls with varying characteristics
    for call_num in range(1, 6):
        tracker = CostTracker(call_id=f"sample_call_{call_num:03d}")
        
        # Simulate varying number of responses
        num_responses = 3 + call_num
        for resp in range(num_responses):
            tracker.start_response()
            
            # STT
            tracker.start_stt()
            time.sleep(0.01)
            tracker.end_stt(
                duration=2.0 + (resp * 0.5),
                transcript=f"Sample message {resp+1} for call {call_num}",
                model="whisper-large-v3-turbo"
            )
            
            # LLM
            tracker.start_llm()
            time.sleep(0.01)
            tracker.end_llm(
                input_tokens=150 + (resp * 25) + (call_num * 20),
                output_tokens=80 + (resp * 15) + (call_num * 10),
                model="llama-3.3-70b-versatile"
            )
            
            # TTS
            tracker.start_tts()
            time.sleep(0.01)
            tracker.end_tts(
                characters=180 + (resp * 30) + (call_num * 20),
                model="canopylabs/orpheus-v1-english"
            )
            
            tracker.end_response()
            time.sleep(0.01)
        
        tracker.end_call()
        
        # Export
        filename = f"metrics/sample_call_{call_num:03d}.json"
        tracker.export_to_file(filename)
        print(f"[OK] Created {filename}")
    
    print(f"\n[OK] Created 5 sample metric files in metrics/ directory\n")


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("COST TRACKER TESTING SUITE")
    print("=" * 80 + "\n")
    
    # Run tests
    test_basic_tracking()
    test_edge_cases()
    test_json_export()
    
    # Create sample data
    response = input("Create sample data for testing analysis scripts? (y/n): ")
    if response.lower() == 'y':
        create_sample_data()
        print("\nYou can now test the analysis scripts:")
        print("  python analyze_metrics.py --directory metrics/")
        print("  python visualize_metrics.py --directory metrics/")
    
    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETED")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
