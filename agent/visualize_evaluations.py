"""
Evaluation Visualization Tool

This module provides visualization capabilities for call evaluation data,
creating charts and reports to analyze quality metrics over time.
"""

import csv
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


def create_bar_chart(title: str, labels: List[str], values: List[float], 
                     max_width: int = 50) -> str:
    """
    Create a simple ASCII bar chart.
    
    Args:
        title: Chart title
        labels: Bar labels
        values: Bar values
        max_width: Maximum width of bars in characters
        
    Returns:
        ASCII art bar chart as string
    """
    if not values:
        return f"{title}\n(No data)"
    
    max_value = max(values) if values else 1
    lines = [f"\n{title}", "=" * (max_width + 20)]
    
    for label, value in zip(labels, values):
        bar_length = int((value / max_value) * max_width) if max_value > 0 else 0
        bar = "#" * bar_length  # Use # instead of █ for Windows compatibility
        lines.append(f"{label:20s} {bar} {value:.1f}")
    
    lines.append("=" * (max_width + 20))
    return "\n".join(lines)


def create_histogram(title: str, data: List[float], bins: int = 10,
                    max_width: int = 40) -> str:
    """
    Create a simple ASCII histogram.
    
    Args:
        title: Histogram title
        data: Data points
        bins: Number of bins
        max_width: Maximum width of bars
        
    Returns:
        ASCII art histogram
    """
    if not data:
        return f"{title}\n(No data)"
    
    min_val = min(data)
    max_val = max(data)
    range_val = max_val - min_val if max_val > min_val else 1
    bin_width = range_val / bins
    
    # Count values in each bin
    bin_counts = [0] * bins
    for value in data:
        bin_idx = min(int((value - min_val) / bin_width), bins - 1)
        bin_counts[bin_idx] += 1
    
    # Create chart
    lines = [f"\n{title}", "=" * (max_width + 30)]
    max_count = max(bin_counts) if bin_counts else 1
    
    for i, count in enumerate(bin_counts):
        bin_start = min_val + (i * bin_width)
        bin_end = bin_start + bin_width
        bar_length = int((count / max_count) * max_width) if max_count > 0 else 0
        bar = "#" * bar_length  # Use # instead of █ for Windows compatibility
        lines.append(f"{bin_start:6.1f}-{bin_end:6.1f} {bar} ({count})")
    
    lines.append("=" * (max_width + 30))
    return "\n".join(lines)


def load_evaluations(csv_file: str) -> List[Dict[str, Any]]:
    """
    Load evaluations from CSV file.
    
    Args:
        csv_file: Path to CSV file
        
    Returns:
        List of evaluation dictionaries
    """
    evaluations = []
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert numeric fields
                eval_dict = {
                    'call_id': row['call_id'],
                    'timestamp': row['timestamp'],
                    'duration': float(row['duration']),
                    'total_cost': float(row['total_cost']),
                    'accuracy_score': float(row['accuracy_score']),
                    'flow_score': float(row['flow_score']),
                    'intent_accuracy': float(row['intent_accuracy']),
                    'task_completion': float(row['task_completion']),
                    'sentiment': row['sentiment'],
                    'avg_latency': float(row['avg_latency']),
                    'cost_efficiency': float(row['cost_efficiency']),
                    'user_satisfaction': float(row['user_satisfaction']),
                    'interruption_count': int(row['interruption_count']),
                    'escalation_needed': row['escalation_needed'].lower() == 'true',
                    'total_turns': int(row['total_turns']),
                    'intents_detected': row['intents_detected'].split(',') if row['intents_detected'] else [],
                    'notes': row['notes'],
                }
                evaluations.append(eval_dict)
    
    except Exception as e:
        print(f"Error loading evaluations: {e}")
        return []
    
    return evaluations


def visualize_evaluations(csv_file: str):
    """
    Create comprehensive visualizations of evaluation data.
    
    Args:
        csv_file: Path to evaluation CSV file
    """
    evaluations = load_evaluations(csv_file)
    
    if not evaluations:
        print("No evaluation data found.")
        return
    
    print("\n" + "=" * 80)
    print("CALL EVALUATION VISUALIZATION")
    print("=" * 80)
    print(f"Total Evaluations: {len(evaluations)}")
    print("=" * 80)
    
    # 1. Average Scores Bar Chart
    avg_accuracy = sum(e['accuracy_score'] for e in evaluations) / len(evaluations)
    avg_flow = sum(e['flow_score'] for e in evaluations) / len(evaluations)
    avg_intent = sum(e['intent_accuracy'] for e in evaluations) / len(evaluations)
    avg_task = sum(e['task_completion'] for e in evaluations) / len(evaluations)
    avg_cost_eff = sum(e['cost_efficiency'] for e in evaluations) / len(evaluations)
    avg_satisfaction = sum(e['user_satisfaction'] for e in evaluations) / len(evaluations)
    
    print(create_bar_chart(
        "Average Scores Across All Calls",
        ["Accuracy", "Flow Quality", "Intent Accuracy", "Task Completion", 
         "Cost Efficiency", "User Satisfaction"],
        [avg_accuracy, avg_flow, avg_intent, avg_task, avg_cost_eff, avg_satisfaction]
    ))
    
    # 2. User Satisfaction Histogram
    satisfaction_scores = [e['user_satisfaction'] for e in evaluations]
    print(create_histogram(
        "User Satisfaction Score Distribution",
        satisfaction_scores,
        bins=10
    ))
    
    # 3. Latency Histogram
    latencies = [e['avg_latency'] for e in evaluations]
    print(create_histogram(
        "Average Latency Distribution (ms)",
        latencies,
        bins=8
    ))
    
    # 4. Sentiment Distribution
    sentiment_counts = defaultdict(int)
    for e in evaluations:
        sentiment_counts[e['sentiment']] += 1
    
    print(create_bar_chart(
        "Sentiment Distribution",
        list(sentiment_counts.keys()),
        list(sentiment_counts.values())
    ))
    
    # 5. Cost vs Duration Scatter (text-based)
    print("\n" + "=" * 80)
    print("Cost vs Duration Analysis")
    print("=" * 80)
    
    total_cost = sum(e['total_cost'] for e in evaluations)
    total_duration = sum(e['duration'] for e in evaluations)
    avg_cost_per_min = (total_cost / total_duration) * 60 if total_duration > 0 else 0
    
    print(f"Total Cost: ${total_cost:.2f}")
    print(f"Total Duration: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
    print(f"Average Cost/Minute: ${avg_cost_per_min:.3f}")
    
    # 6. Quality vs Cost Analysis
    print("\n" + "=" * 80)
    print("Quality vs Cost Efficiency")
    print("=" * 80)
    
    # Categorize calls
    excellent = sum(1 for e in evaluations if e['user_satisfaction'] >= 80)
    good = sum(1 for e in evaluations if 60 <= e['user_satisfaction'] < 80)
    poor = sum(1 for e in evaluations if e['user_satisfaction'] < 60)
    
    print(f"Excellent Calls (>=80): {excellent} ({excellent/len(evaluations)*100:.1f}%)")
    print(f"Good Calls (60-79): {good} ({good/len(evaluations)*100:.1f}%)")
    print(f"Poor Calls (<60): {poor} ({poor/len(evaluations)*100:.1f}%)")
    
    # 7. Top Issues
    print("\n" + "=" * 80)
    print("Most Common Issues")
    print("=" * 80)
    
    issue_counts = defaultdict(int)
    for e in evaluations:
        if e['notes'] and e['notes'] != "No issues detected":
            # Split on semicolon for multiple issues
            issues = e['notes'].split(';')
            for issue in issues:
                issue = issue.strip()
                if issue:
                    # Extract issue type
                    if 'accuracy' in issue.lower():
                        issue_counts['Low Accuracy'] += 1
                    elif 'flow' in issue.lower():
                        issue_counts['Flow Problems'] += 1
                    elif 'latency' in issue.lower():
                        issue_counts['High Latency'] += 1
                    elif 'sentiment' in issue.lower() or 'negative' in issue.lower():
                        issue_counts['Negative Sentiment'] += 1
                    elif 'completion' in issue.lower():
                        issue_counts['Incomplete Tasks'] += 1
    
    if issue_counts:
        # Sort by frequency
        sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
        for issue, count in sorted_issues[:5]:  # Top 5
            pct = (count / len(evaluations)) * 100
            print(f"{issue:25s}: {count:3d} calls ({pct:.1f}%)")
    else:
        print("No major issues detected!")
    
    # 8. Escalation Analysis
    escalations = sum(1 for e in evaluations if e['escalation_needed'])
    print("\n" + "=" * 80)
    print("Escalation Analysis")
    print("=" * 80)
    print(f"Calls Requiring Escalation: {escalations} ({escalations/len(evaluations)*100:.1f}%)")
    
    # 9. Conversation Length Analysis
    print("\n" + "=" * 80)
    print("Conversation Length Analysis")
    print("=" * 80)
    
    avg_turns = sum(e['total_turns'] for e in evaluations) / len(evaluations)
    min_turns = min(e['total_turns'] for e in evaluations)
    max_turns = max(e['total_turns'] for e in evaluations)
    
    print(f"Average Turns per Call: {avg_turns:.1f}")
    print(f"Range: {min_turns} - {max_turns} turns")
    
    turns = [e['total_turns'] for e in evaluations]
    print(create_histogram(
        "Conversation Turns Distribution",
        turns,
        bins=8
    ))
    
    # 10. Time-based Analysis (if timestamps available)
    print("\n" + "=" * 80)
    print("Time-based Trends")
    print("=" * 80)
    
    try:
        # Group by date
        date_scores = defaultdict(list)
        for e in evaluations:
            date = e['timestamp'][:10]  # Extract date (YYYY-MM-DD)
            date_scores[date].append(e['user_satisfaction'])
        
        if len(date_scores) > 1:
            print("Average User Satisfaction by Date:")
            for date in sorted(date_scores.keys()):
                avg = sum(date_scores[date]) / len(date_scores[date])
                count = len(date_scores[date])
                print(f"  {date}: {avg:.1f} ({count} calls)")
        else:
            print("All evaluations from single date")
    
    except Exception as e:
        print(f"Time analysis not available: {e}")
    
    # 11. Recommendations
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    recommendations = []
    
    # Calculate average latency for recommendations
    avg_latency = sum(e['avg_latency'] for e in evaluations) / len(evaluations)
    
    if avg_accuracy < 70:
        recommendations.append("WARNING: Average accuracy is low - review response quality and prompts")
    
    if avg_flow < 70:
        recommendations.append("WARNING: Flow score is low - check for delays and improve response timing")
    
    if avg_task < 70:
        recommendations.append("WARNING: Task completion is low - users may not be achieving their goals")
    
    if avg_latency > 3000:
        recommendations.append("WARNING: High latency detected - investigate performance bottlenecks")
    
    if avg_cost_eff < 70:
        recommendations.append("WARNING: Cost efficiency is low - optimize resource usage")
    
    poor_pct = (poor / len(evaluations)) * 100
    if poor_pct > 20:
        recommendations.append(f"WARNING: {poor_pct:.0f}% of calls are rated poor - immediate attention needed")
    
    if escalations > len(evaluations) * 0.1:
        recommendations.append("WARNING: High escalation rate - consider improving agent capabilities")
    
    if not recommendations:
        recommendations.append("SUCCESS: Overall quality is good - continue monitoring for trends")
    
    for rec in recommendations:
        print(f"\n{rec}")
    
    print("\n" + "=" * 80)


def compare_evaluations(csv_file1: str, csv_file2: str, label1: str = "Set 1", 
                       label2: str = "Set 2"):
    """
    Compare two sets of evaluations.
    
    Args:
        csv_file1: First CSV file
        csv_file2: Second CSV file
        label1: Label for first set
        label2: Label for second set
    """
    evals1 = load_evaluations(csv_file1)
    evals2 = load_evaluations(csv_file2)
    
    if not evals1 or not evals2:
        print("Error: Could not load one or both evaluation sets")
        return
    
    print("\n" + "=" * 80)
    print(f"COMPARISON: {label1} vs {label2}")
    print("=" * 80)
    
    # Calculate metrics for both sets
    metrics = [
        'accuracy_score', 'flow_score', 'intent_accuracy', 
        'task_completion', 'cost_efficiency', 'user_satisfaction'
    ]
    
    for metric in metrics:
        avg1 = sum(e[metric] for e in evals1) / len(evals1)
        avg2 = sum(e[metric] for e in evals2) / len(evals2)
        diff = avg2 - avg1
        pct_change = (diff / avg1 * 100) if avg1 > 0 else 0
        
        arrow = "up" if diff > 0 else "down" if diff < 0 else "same"
        metric_name = metric.replace('_', ' ').title()
        
        print(f"{metric_name:20s}: {avg1:.1f} -> {avg2:.1f} ({arrow} {diff:+.1f}, {pct_change:+.1f}%)")
    
    print("=" * 80)


if __name__ == "__main__":
    import sys
    
    # Check for CSV file
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    else:
        # Default location
        csv_file = os.path.join(os.path.dirname(__file__), "evaluations", "call_evaluations.csv")
    
    if not os.path.exists(csv_file):
        print(f"Error: CSV file not found at {csv_file}")
        print("\nUsage: python visualize_evaluations.py [path/to/evaluations.csv]")
        sys.exit(1)
    
    visualize_evaluations(csv_file)
