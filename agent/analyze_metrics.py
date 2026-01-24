"""
Metrics Analysis Utility

This script provides tools to analyze cost and latency metrics from multiple calls.

Usage:
    python analyze_metrics.py --directory metrics/
    python analyze_metrics.py --file metrics/call_123.json
    python analyze_metrics.py --summary
"""

import json
import os
import argparse
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path
import statistics


class MetricsAnalyzer:
    """Analyze cost and latency metrics from one or more calls"""
    
    def __init__(self):
        self.calls: List[Dict[str, Any]] = []
    
    def load_file(self, filepath: str):
        """Load a single metrics file"""
        try:
            with open(filepath, 'r') as f:
                call_data = json.load(f)
                self.calls.append(call_data)
                print(f"[OK] Loaded: {filepath}")
        except Exception as e:
            print(f"[ERROR] Error loading {filepath}: {e}")
    
    def load_directory(self, directory: str):
        """Load all metrics files from a directory"""
        metrics_dir = Path(directory)
        if not metrics_dir.exists():
            print(f"Directory not found: {directory}")
            return
        
        json_files = list(metrics_dir.glob("*.json"))
        if not json_files:
            print(f"No JSON files found in: {directory}")
            return
        
        print(f"Loading {len(json_files)} metric files...")
        for filepath in json_files:
            self.load_file(str(filepath))
        
        print(f"\nLoaded {len(self.calls)} calls successfully\n")
    
    def analyze_costs(self):
        """Analyze cost metrics across all calls"""
        if not self.calls:
            print("No calls loaded")
            return
        
        print("=" * 80)
        print("COST ANALYSIS")
        print("=" * 80)
        
        total_costs = [call['total_cost'] for call in self.calls]
        stt_costs = [call['total_stt_cost'] for call in self.calls]
        llm_costs = [call['total_llm_cost'] for call in self.calls]
        tts_costs = [call['total_tts_cost'] for call in self.calls]
        vapi_costs = [call['total_vapi_cost'] for call in self.calls]
        
        print(f"\nTotal Calls: {len(self.calls)}")
        print(f"\nAGGREGATE COSTS:")
        print(f"  Total across all calls: ${sum(total_costs):.4f}")
        print(f"  Average per call: ${statistics.mean(total_costs):.4f}")
        print(f"  Median per call: ${statistics.median(total_costs):.4f}")
        print(f"  Min per call: ${min(total_costs):.4f}")
        print(f"  Max per call: ${max(total_costs):.4f}")
        
        print(f"\nCOST BREAKDOWN (Average per call):")
        print(f"  STT:  ${statistics.mean(stt_costs):.4f} ({statistics.mean(stt_costs)/statistics.mean(total_costs)*100:.1f}%)")
        print(f"  LLM:  ${statistics.mean(llm_costs):.4f} ({statistics.mean(llm_costs)/statistics.mean(total_costs)*100:.1f}%)")
        print(f"  TTS:  ${statistics.mean(tts_costs):.4f} ({statistics.mean(tts_costs)/statistics.mean(total_costs)*100:.1f}%)")
        print(f"  VAPI: ${statistics.mean(vapi_costs):.4f} ({statistics.mean(vapi_costs)/statistics.mean(total_costs)*100:.1f}%)")
        
        # Find most expensive call
        most_expensive = max(self.calls, key=lambda c: c['total_cost'])
        print(f"\nMOST EXPENSIVE CALL:")
        print(f"  Call ID: {most_expensive['call_id']}")
        print(f"  Total Cost: ${most_expensive['total_cost']:.4f}")
        print(f"  Duration: {most_expensive['duration_seconds']:.1f}s")
        print(f"  Responses: {len(most_expensive['responses'])}")
    
    def analyze_latencies(self):
        """Analyze latency metrics across all calls"""
        if not self.calls:
            print("No calls loaded")
            return
        
        print("\n" + "=" * 80)
        print("LATENCY ANALYSIS")
        print("=" * 80)
        
        # Collect all latency measurements
        all_stt = []
        all_llm = []
        all_tts = []
        all_e2e = []
        
        for call in self.calls:
            for response in call['responses']:
                if response.get('stt') and response['stt'].get('latency_ms'):
                    all_stt.append(response['stt']['latency_ms'])
                if response.get('llm') and response['llm'].get('latency_ms'):
                    all_llm.append(response['llm']['latency_ms'])
                if response.get('tts') and response['tts'].get('latency_ms'):
                    all_tts.append(response['tts']['latency_ms'])
                if response.get('end_to_end_latency_ms'):
                    all_e2e.append(response['end_to_end_latency_ms'])
        
        print(f"\nTotal Responses Analyzed: {sum(len(call['responses']) for call in self.calls)}")
        
        if all_stt:
            print(f"\nSTT LATENCY (ms):")
            print(f"  Average: {statistics.mean(all_stt):.0f}ms")
            print(f"  Median:  {statistics.median(all_stt):.0f}ms")
            print(f"  Min:     {min(all_stt):.0f}ms")
            print(f"  Max:     {max(all_stt):.0f}ms")
            print(f"  StdDev:  {statistics.stdev(all_stt):.0f}ms" if len(all_stt) > 1 else "")
        
        if all_llm:
            print(f"\nLLM LATENCY (ms):")
            print(f"  Average: {statistics.mean(all_llm):.0f}ms")
            print(f"  Median:  {statistics.median(all_llm):.0f}ms")
            print(f"  Min:     {min(all_llm):.0f}ms")
            print(f"  Max:     {max(all_llm):.0f}ms")
            print(f"  StdDev:  {statistics.stdev(all_llm):.0f}ms" if len(all_llm) > 1 else "")
        
        if all_tts:
            print(f"\nTTS LATENCY (ms):")
            print(f"  Average: {statistics.mean(all_tts):.0f}ms")
            print(f"  Median:  {statistics.median(all_tts):.0f}ms")
            print(f"  Min:     {min(all_tts):.0f}ms")
            print(f"  Max:     {max(all_tts):.0f}ms")
            print(f"  StdDev:  {statistics.stdev(all_tts):.0f}ms" if len(all_tts) > 1 else "")
        
        if all_e2e:
            print(f"\nEND-TO-END LATENCY (ms):")
            print(f"  Average: {statistics.mean(all_e2e):.0f}ms")
            print(f"  Median:  {statistics.median(all_e2e):.0f}ms")
            print(f"  Min:     {min(all_e2e):.0f}ms")
            print(f"  Max:     {max(all_e2e):.0f}ms")
            print(f"  StdDev:  {statistics.stdev(all_e2e):.0f}ms" if len(all_e2e) > 1 else "")
            
            # Percentiles
            sorted_e2e = sorted(all_e2e)
            p50 = sorted_e2e[len(sorted_e2e) // 2]
            p95 = sorted_e2e[int(len(sorted_e2e) * 0.95)]
            p99 = sorted_e2e[int(len(sorted_e2e) * 0.99)]
            print(f"\n  Percentiles:")
            print(f"    P50: {p50:.0f}ms")
            print(f"    P95: {p95:.0f}ms")
            print(f"    P99: {p99:.0f}ms")
    
    def analyze_usage(self):
        """Analyze resource usage across all calls"""
        if not self.calls:
            print("No calls loaded")
            return
        
        print("\n" + "=" * 80)
        print("USAGE ANALYSIS")
        print("=" * 80)
        
        total_duration = sum(call['duration_seconds'] for call in self.calls)
        total_responses = sum(len(call['responses']) for call in self.calls)
        total_stt_duration = sum(call['total_stt_duration'] for call in self.calls)
        total_input_tokens = sum(call['total_llm_input_tokens'] for call in self.calls)
        total_output_tokens = sum(call['total_llm_output_tokens'] for call in self.calls)
        total_characters = sum(call['total_tts_characters'] for call in self.calls)
        
        print(f"\nAGGREGATE USAGE:")
        print(f"  Total call duration: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
        print(f"  Total responses: {total_responses}")
        print(f"  Avg responses per call: {total_responses / len(self.calls):.1f}")
        
        print(f"\nSTT USAGE:")
        print(f"  Total audio processed: {total_stt_duration:.1f}s ({total_stt_duration/60:.2f} minutes)")
        print(f"  Avg per call: {total_stt_duration / len(self.calls):.1f}s")
        
        print(f"\nLLM USAGE:")
        print(f"  Total input tokens: {total_input_tokens:,}")
        print(f"  Total output tokens: {total_output_tokens:,}")
        print(f"  Total tokens: {total_input_tokens + total_output_tokens:,}")
        print(f"  Avg per call: {(total_input_tokens + total_output_tokens) / len(self.calls):.0f} tokens")
        print(f"  Avg per response: {(total_input_tokens + total_output_tokens) / total_responses:.0f} tokens")
        
        print(f"\nTTS USAGE:")
        print(f"  Total characters: {total_characters:,}")
        print(f"  Avg per call: {total_characters / len(self.calls):.0f} chars")
        print(f"  Avg per response: {total_characters / total_responses:.0f} chars")
    
    def generate_summary(self):
        """Generate a comprehensive summary"""
        if not self.calls:
            print("No calls loaded")
            return
        
        self.analyze_costs()
        self.analyze_latencies()
        self.analyze_usage()
        
        print("\n" + "=" * 80)
        print("SUMMARY COMPLETE")
        print("=" * 80 + "\n")
    
    def list_calls(self):
        """List all loaded calls"""
        if not self.calls:
            print("No calls loaded")
            return
        
        print("=" * 80)
        print("LOADED CALLS")
        print("=" * 80)
        
        for i, call in enumerate(self.calls, 1):
            timestamp = call.get('start_timestamp', 'N/A')
            duration = call.get('duration_seconds', 0)
            cost = call.get('total_cost', 0)
            responses = len(call.get('responses', []))
            
            print(f"\n{i}. {call['call_id']}")
            print(f"   Timestamp: {timestamp}")
            print(f"   Duration: {duration:.1f}s")
            print(f"   Responses: {responses}")
            print(f"   Cost: ${cost:.4f}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze cost and latency metrics from voice assistant calls"
    )
    parser.add_argument(
        '--directory', '-d',
        default='metrics',
        help='Directory containing metrics JSON files (default: metrics/)'
    )
    parser.add_argument(
        '--file', '-f',
        help='Single metrics file to analyze'
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List all loaded calls'
    )
    parser.add_argument(
        '--costs', '-c',
        action='store_true',
        help='Show only cost analysis'
    )
    parser.add_argument(
        '--latencies', '-t',
        action='store_true',
        help='Show only latency analysis'
    )
    parser.add_argument(
        '--usage', '-u',
        action='store_true',
        help='Show only usage analysis'
    )
    parser.add_argument(
        '--summary', '-s',
        action='store_true',
        help='Show complete summary (default if no specific flag)'
    )
    
    args = parser.parse_args()
    
    analyzer = MetricsAnalyzer()
    
    # Load files
    if args.file:
        analyzer.load_file(args.file)
    else:
        analyzer.load_directory(args.directory)
    
    if not analyzer.calls:
        print("No metrics data loaded. Exiting.")
        return
    
    # Determine what to show
    show_all = args.summary or not (args.list or args.costs or args.latencies or args.usage)
    
    if args.list:
        analyzer.list_calls()
    
    if args.costs or show_all:
        analyzer.analyze_costs()
    
    if args.latencies or show_all:
        analyzer.analyze_latencies()
    
    if args.usage or show_all:
        analyzer.analyze_usage()
    
    if show_all:
        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
