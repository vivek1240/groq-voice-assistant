"""
Metrics Visualization

This script provides simple ASCII-based visualizations of metrics.
For more advanced visualizations, consider using matplotlib or plotly.

Usage:
    python visualize_metrics.py --directory metrics/
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any


def create_bar_chart(data: List[tuple], title: str, max_width: int = 50):
    """Create a simple ASCII bar chart"""
    print(f"\n{title}")
    print("=" * 80)
    
    if not data:
        print("No data to display")
        return
    
    # Find max value for scaling
    max_val = max(val for _, val in data)
    if max_val == 0:
        max_val = 1
    
    for label, value in data:
        bar_length = int((value / max_val) * max_width)
        bar = "#" * bar_length
        print(f"{label:20} {bar} {value:.4f}")


def create_histogram(values: List[float], title: str, bins: int = 10):
    """Create a simple ASCII histogram"""
    print(f"\n{title}")
    print("=" * 80)
    
    if not values:
        print("No data to display")
        return
    
    min_val = min(values)
    max_val = max(values)
    range_val = max_val - min_val
    
    if range_val == 0:
        print(f"All values are {min_val:.2f}")
        return
    
    # Create bins
    bin_size = range_val / bins
    bin_counts = [0] * bins
    
    for value in values:
        bin_idx = min(int((value - min_val) / bin_size), bins - 1)
        bin_counts[bin_idx] += 1
    
    max_count = max(bin_counts)
    bar_width = 40
    
    for i in range(bins):
        bin_start = min_val + (i * bin_size)
        bin_end = bin_start + bin_size
        count = bin_counts[i]
        bar_length = int((count / max_count) * bar_width) if max_count > 0 else 0
        bar = "#" * bar_length
        print(f"{bin_start:7.0f}-{bin_end:7.0f} | {bar} ({count})")


def visualize_cost_breakdown(calls: List[Dict[str, Any]]):
    """Visualize cost breakdown across calls"""
    if not calls:
        return
    
    # Average costs per component
    avg_stt = sum(c['total_stt_cost'] for c in calls) / len(calls)
    avg_llm = sum(c['total_llm_cost'] for c in calls) / len(calls)
    avg_tts = sum(c['total_tts_cost'] for c in calls) / len(calls)
    avg_livekit = sum(c.get('total_livekit_cost', c.get('total_vapi_cost', 0)) for c in calls) / len(calls)
    
    data = [
        ("STT", avg_stt),
        ("LLM", avg_llm),
        ("TTS", avg_tts),
        ("LiveKit", avg_livekit),
    ]
    
    create_bar_chart(data, "AVERAGE COST BREAKDOWN (per call)")


def visualize_cost_per_call(calls: List[Dict[str, Any]]):
    """Visualize total cost for each call"""
    if not calls:
        return
    
    data = [(call['call_id'][-12:], call['total_cost']) for call in calls[:20]]
    create_bar_chart(data, "COST PER CALL (last 12 chars of ID, max 20 calls)")


def visualize_latency_distribution(calls: List[Dict[str, Any]]):
    """Visualize latency distributions"""
    if not calls:
        return
    
    # Collect all latencies
    stt_latencies = []
    llm_latencies = []
    tts_latencies = []
    e2e_latencies = []
    
    for call in calls:
        for response in call['responses']:
            if response.get('stt') and response['stt'].get('latency_ms'):
                stt_latencies.append(response['stt']['latency_ms'])
            if response.get('llm') and response['llm'].get('latency_ms'):
                llm_latencies.append(response['llm']['latency_ms'])
            if response.get('tts') and response['tts'].get('latency_ms'):
                tts_latencies.append(response['tts']['latency_ms'])
            if response.get('end_to_end_latency_ms'):
                e2e_latencies.append(response['end_to_end_latency_ms'])
    
    if e2e_latencies:
        create_histogram(e2e_latencies, "END-TO-END LATENCY DISTRIBUTION (ms)", bins=10)
    
    if stt_latencies:
        create_histogram(stt_latencies, "STT LATENCY DISTRIBUTION (ms)", bins=10)
    
    if llm_latencies:
        create_histogram(llm_latencies, "LLM LATENCY DISTRIBUTION (ms)", bins=10)
    
    if tts_latencies:
        create_histogram(tts_latencies, "TTS LATENCY DISTRIBUTION (ms)", bins=10)


def visualize_usage_over_time(calls: List[Dict[str, Any]]):
    """Show usage metrics over time"""
    if not calls:
        return
    
    # Sort calls by timestamp
    sorted_calls = sorted(calls, key=lambda c: c.get('start_timestamp', ''))
    
    print("\n" + "=" * 80)
    print("USAGE OVER TIME")
    print("=" * 80)
    print(f"\n{'Timestamp':<25} {'Duration':<12} {'Responses':<12} {'Cost':<12}")
    print("-" * 80)
    
    for call in sorted_calls[:20]:  # Show last 20 calls
        timestamp = call.get('start_timestamp', 'N/A')[:19]  # Just date and time
        duration = f"{call.get('duration_seconds', 0):.1f}s"
        responses = str(len(call.get('responses', [])))
        cost = f"${call.get('total_cost', 0):.4f}"
        
        print(f"{timestamp:<25} {duration:<12} {responses:<12} {cost:<12}")


def visualize_token_usage(calls: List[Dict[str, Any]]):
    """Visualize token usage"""
    if not calls:
        return
    
    data = []
    for call in calls[:10]:  # Show top 10
        call_id = call['call_id'][-12:]
        total_tokens = call.get('total_llm_input_tokens', 0) + call.get('total_llm_output_tokens', 0)
        data.append((call_id, total_tokens))
    
    create_bar_chart(data, "TOKEN USAGE PER CALL (total input + output)")


def generate_dashboard(directory: str):
    """Generate a complete dashboard"""
    metrics_dir = Path(directory)
    if not metrics_dir.exists():
        print(f"Directory not found: {directory}")
        return
    
    # Load all metrics
    calls = []
    for filepath in metrics_dir.glob("*.json"):
        try:
            with open(filepath, 'r') as f:
                calls.append(json.load(f))
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
    
    if not calls:
        print("No metrics files found")
        return
    
    print("\n" + "=" * 80)
    print("METRICS DASHBOARD")
    print("=" * 80)
    print(f"\nTotal calls loaded: {len(calls)}")
    
    # Generate visualizations
    visualize_cost_breakdown(calls)
    visualize_cost_per_call(calls)
    visualize_token_usage(calls)
    visualize_latency_distribution(calls)
    visualize_usage_over_time(calls)
    
    print("\n" + "=" * 80)
    print("DASHBOARD COMPLETE")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Visualize cost and latency metrics"
    )
    parser.add_argument(
        '--directory', '-d',
        default='metrics',
        help='Directory containing metrics JSON files (default: metrics/)'
    )
    
    args = parser.parse_args()
    generate_dashboard(args.directory)


if __name__ == "__main__":
    main()
