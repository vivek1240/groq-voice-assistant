"""
Call Evaluation Framework

This module provides automatic evaluation of voice assistant calls upon completion.
It analyzes multiple dimensions including accuracy, conversation flow, intent recognition,
task completion, sentiment, latency, and cost efficiency.

The framework is designed for:
- Automatic triggering when calls end
- CSV storage (initial implementation)
- Extensibility for future enhancements
- Integration with existing cost tracking
"""

import csv
import json
import logging
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger("call-evaluator")


class SentimentType(Enum):
    """Sentiment classification"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class IntentCategory(Enum):
    """Common intent categories for health coaching"""
    INQUIRY = "inquiry"  # Asking about tests, processes
    ORDERING = "ordering"  # Purchasing or ordering
    REGISTRATION = "registration"  # Kit registration
    COLLECTION_HELP = "collection_help"  # Sample collection guidance
    RESULTS = "results"  # Understanding results
    TROUBLESHOOTING = "troubleshooting"  # Technical issues
    ESCALATION = "escalation"  # Need human support
    FAREWELL = "farewell"  # Ending conversation
    UNKNOWN = "unknown"


@dataclass
class EvaluationScores:
    """Container for all evaluation scores"""
    accuracy_score: float = 0.0  # 0-100, response correctness
    flow_score: float = 0.0  # 0-100, conversation naturalness
    intent_accuracy: float = 0.0  # 0-100, intent recognition success
    task_completion: float = 0.0  # 0-100, user goal achievement
    sentiment: SentimentType = SentimentType.UNKNOWN
    cost_efficiency: float = 0.0  # 0-100, cost vs value score
    
    # Additional metrics
    avg_latency: float = 0.0  # milliseconds
    interruption_count: int = 0
    escalation_needed: bool = False
    user_satisfaction_indicator: float = 0.0  # 0-100, derived metric


@dataclass
class ConversationTurn:
    """Represents a single turn in the conversation"""
    turn_id: int
    user_text: str
    agent_text: str
    intent: IntentCategory
    latency_ms: float
    timestamp: str


@dataclass
class CallEvaluation:
    """Complete evaluation for a single call"""
    call_id: str
    timestamp: str
    duration_seconds: float
    total_cost: float
    
    # Evaluation scores
    scores: EvaluationScores
    
    # Conversation analysis
    total_turns: int = 0
    intents_detected: List[str] = field(default_factory=list)
    
    # Notes and observations
    notes: str = ""
    evaluation_version: str = "1.0"
    
    # Raw data reference
    metrics_file: str = ""


class CallEvaluator:
    """
    Evaluates voice assistant calls across multiple dimensions.
    
    This class analyzes call metrics and conversation data to provide
    comprehensive evaluation scores for quality improvement.
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the evaluator.
        
        Args:
            output_dir: Directory for CSV output. Defaults to ./evaluations/
        """
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), "evaluations")
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        self.csv_file = self.output_dir / "call_evaluations.csv"
        self._ensure_csv_header()
    
    def _ensure_csv_header(self):
        """Ensure CSV file exists with proper header"""
        if not self.csv_file.exists():
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'call_id',
                    'timestamp',
                    'duration',
                    'total_cost',
                    'accuracy_score',
                    'flow_score',
                    'intent_accuracy',
                    'task_completion',
                    'sentiment',
                    'avg_latency',
                    'cost_efficiency',
                    'user_satisfaction',
                    'interruption_count',
                    'escalation_needed',
                    'total_turns',
                    'intents_detected',
                    'notes'
                ])
            logger.info(f"Created evaluation CSV at {self.csv_file}")
    
    def evaluate_call(self, call_metrics: Dict[str, Any], 
                     conversation_data: Optional[Dict[str, Any]] = None) -> CallEvaluation:
        """
        Evaluate a completed call.
        
        Args:
            call_metrics: Call metrics from cost tracker (JSON format)
            conversation_data: Optional additional conversation data
            
        Returns:
            CallEvaluation object with all scores
        """
        logger.info(f"Evaluating call: {call_metrics.get('call_id', 'unknown')}")
        
        # Extract basic info
        call_id = call_metrics.get('call_id', 'unknown')
        timestamp = call_metrics.get('end_timestamp', datetime.now().isoformat())
        duration = call_metrics.get('duration_seconds', 0.0)
        total_cost = call_metrics.get('total_cost', 0.0)
        
        # Initialize evaluation
        evaluation = CallEvaluation(
            call_id=call_id,
            timestamp=timestamp,
            duration_seconds=duration,
            total_cost=total_cost,
            scores=EvaluationScores(),
            metrics_file=f"{call_id}.json"
        )
        
        # Perform evaluations
        self._evaluate_accuracy(evaluation, call_metrics, conversation_data)
        self._evaluate_flow(evaluation, call_metrics, conversation_data)
        self._evaluate_intent_recognition(evaluation, call_metrics, conversation_data)
        self._evaluate_task_completion(evaluation, call_metrics, conversation_data)
        self._evaluate_sentiment(evaluation, call_metrics, conversation_data)
        self._evaluate_latency(evaluation, call_metrics)
        self._evaluate_cost_efficiency(evaluation, call_metrics)
        self._calculate_user_satisfaction(evaluation)
        
        # Add notes
        self._generate_notes(evaluation, call_metrics)
        
        logger.info(f"Evaluation complete for {call_id}")
        return evaluation
    
    def _evaluate_accuracy(self, evaluation: CallEvaluation, 
                          call_metrics: Dict, conversation_data: Optional[Dict]):
        """
        Evaluate response accuracy.
        
        Initial implementation uses heuristics:
        - Check for complete responses (has STT, LLM, TTS)
        - Verify reasonable response lengths
        - Check for error indicators
        
        Future: Use LLM-based accuracy scoring
        """
        responses = call_metrics.get('responses', [])
        if not responses:
            evaluation.scores.accuracy_score = 0.0
            return
        
        score = 100.0
        complete_responses = 0
        
        for response in responses:
            has_llm = response.get('llm') is not None
            has_tts = response.get('tts') is not None
            
            if has_llm and has_tts:
                complete_responses += 1
                
                # Check for reasonable output
                llm = response.get('llm', {})
                output_tokens = llm.get('output_tokens', 0)
                
                # Penalize very short responses (< 20 tokens, likely incomplete)
                if output_tokens > 0 and output_tokens < 20:
                    score -= 5
                
                # Reward substantial responses (> 50 tokens)
                elif output_tokens > 50:
                    score += 2
        
        # Adjust based on completion rate
        if len(responses) > 0:
            completion_rate = complete_responses / len(responses)
            score = score * completion_rate
        
        # Cap at 100
        evaluation.scores.accuracy_score = min(max(score, 0.0), 100.0)
        evaluation.total_turns = len(responses)
    
    def _evaluate_flow(self, evaluation: CallEvaluation,
                      call_metrics: Dict, conversation_data: Optional[Dict]):
        """
        Evaluate conversation flow quality.
        
        Measures:
        - Response timing consistency
        - Natural turn-taking
        - Absence of long pauses
        - Reasonable call duration
        """
        responses = call_metrics.get('responses', [])
        duration = call_metrics.get('duration_seconds', 0.0)
        
        if not responses or duration == 0:
            evaluation.scores.flow_score = 50.0  # Neutral
            return
        
        score = 100.0
        
        # Check call duration (ideal: 2-10 minutes for typical interactions)
        if duration < 30:  # Very short, may indicate issues
            score -= 20
        elif duration > 600:  # Very long, may indicate confusion
            score -= 15
        
        # Check response distribution
        avg_time_between = duration / len(responses) if len(responses) > 0 else 0
        
        # Ideal: 10-30 seconds between responses
        if avg_time_between < 5:  # Too rapid
            score -= 10
        elif avg_time_between > 60:  # Too slow
            score -= 15
        
        # Check for latency spikes
        latencies = [r.get('end_to_end_latency_ms', 0) for r in responses]
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            
            # Penalize if max latency is much higher than average (indicates issues)
            if avg_latency > 0 and max_latency > avg_latency * 3:
                score -= 10
        
        evaluation.scores.flow_score = min(max(score, 0.0), 100.0)
    
    def _evaluate_intent_recognition(self, evaluation: CallEvaluation,
                                    call_metrics: Dict, conversation_data: Optional[Dict]):
        """
        Evaluate intent recognition accuracy.
        
        Initial implementation uses keyword-based heuristics.
        Future: Use NLU models for intent classification.
        """
        # For now, we don't have explicit intent data in metrics
        # We'll infer from conversation patterns
        
        responses = call_metrics.get('responses', [])
        
        # Heuristic: If we have multiple complete responses, intent recognition likely worked
        complete_responses = sum(1 for r in responses if r.get('llm') and r.get('tts'))
        
        if len(responses) == 0:
            evaluation.scores.intent_accuracy = 0.0
            return
        
        # Base score on response completeness
        completion_rate = complete_responses / len(responses)
        base_score = completion_rate * 100
        
        # Add detected intents (simplified for now)
        evaluation.intents_detected = ["inquiry"]  # Default assumption
        
        evaluation.scores.intent_accuracy = min(max(base_score, 0.0), 100.0)
    
    def _evaluate_task_completion(self, evaluation: CallEvaluation,
                                 call_metrics: Dict, conversation_data: Optional[Dict]):
        """
        Evaluate task completion rate.
        
        Measures:
        - Did call reach natural conclusion?
        - Was farewell exchanged?
        - Reasonable number of turns?
        """
        duration = call_metrics.get('duration_seconds', 0.0)
        responses = call_metrics.get('responses', [])
        
        score = 50.0  # Start neutral
        
        # Calls that last 1-15 minutes likely had some completion
        if 60 <= duration <= 900:
            score += 20
        
        # Multiple responses indicate engagement
        if len(responses) >= 3:
            score += 15
        
        # Very short calls likely incomplete
        if duration < 30:
            score -= 30
        
        # Very long calls may indicate issues
        if duration > 900:
            score -= 10
        
        evaluation.scores.task_completion = min(max(score, 0.0), 100.0)
    
    def _evaluate_sentiment(self, evaluation: CallEvaluation,
                           call_metrics: Dict, conversation_data: Optional[Dict]):
        """
        Evaluate user sentiment.
        
        Initial implementation: Neutral default
        Future: Analyze conversation text for sentiment indicators
        """
        # For initial version, use call characteristics as proxy
        duration = call_metrics.get('duration_seconds', 0.0)
        responses = call_metrics.get('responses', [])
        
        # Heuristic: Longer engaged calls = positive, very short = negative
        if duration > 120 and len(responses) >= 5:
            evaluation.scores.sentiment = SentimentType.POSITIVE
        elif duration < 30 or len(responses) < 2:
            evaluation.scores.sentiment = SentimentType.NEGATIVE
        else:
            evaluation.scores.sentiment = SentimentType.NEUTRAL
    
    def _evaluate_latency(self, evaluation: CallEvaluation, call_metrics: Dict):
        """
        Evaluate latency metrics.
        
        Extracts and stores average latency for monitoring.
        """
        avg_latency = call_metrics.get('avg_end_to_end_latency_ms', 0.0)
        evaluation.scores.avg_latency = avg_latency
        
        # Store interruption count from metrics if available
        # For now, we don't have this data - future enhancement
        evaluation.scores.interruption_count = 0
    
    def _evaluate_cost_efficiency(self, evaluation: CallEvaluation, call_metrics: Dict):
        """
        Evaluate cost efficiency.
        
        Measures cost relative to value delivered:
        - Cost per minute
        - Cost per response
        - Reasonable spending patterns
        """
        total_cost = call_metrics.get('total_cost', 0.0)
        duration = call_metrics.get('duration_seconds', 0.0)
        responses = call_metrics.get('responses', [])
        
        if duration == 0 or len(responses) == 0:
            evaluation.scores.cost_efficiency = 50.0
            return
        
        # Calculate metrics
        cost_per_minute = (total_cost / duration) * 60 if duration > 0 else 0
        cost_per_response = total_cost / len(responses) if len(responses) > 0 else 0
        
        score = 100.0
        
        # Ideal cost per minute: $0.05 - $0.15
        if cost_per_minute > 0.20:  # Too expensive
            score -= 20
        elif cost_per_minute < 0.03:  # Suspiciously cheap
            score -= 10
        
        # Ideal cost per response: $0.01 - $0.05
        if cost_per_response > 0.10:
            score -= 15
        
        evaluation.scores.cost_efficiency = min(max(score, 0.0), 100.0)
    
    def _calculate_user_satisfaction(self, evaluation: CallEvaluation):
        """
        Calculate overall user satisfaction indicator.
        
        Weighted combination of all scores:
        - Task completion: 30%
        - Flow quality: 25%
        - Accuracy: 20%
        - Latency: 15%
        - Sentiment: 10%
        """
        scores = evaluation.scores
        
        # Sentiment to numeric (0-100)
        sentiment_score = {
            SentimentType.POSITIVE: 90.0,
            SentimentType.NEUTRAL: 60.0,
            SentimentType.NEGATIVE: 30.0,
            SentimentType.MIXED: 50.0,
            SentimentType.UNKNOWN: 50.0,
        }.get(scores.sentiment, 50.0)
        
        # Latency to score (inverse: lower is better)
        latency_score = 100.0
        if scores.avg_latency > 5000:  # > 5 seconds
            latency_score = 50.0
        elif scores.avg_latency > 3000:  # > 3 seconds
            latency_score = 70.0
        elif scores.avg_latency > 2000:  # > 2 seconds
            latency_score = 85.0
        
        # Weighted average
        satisfaction = (
            scores.task_completion * 0.30 +
            scores.flow_score * 0.25 +
            scores.accuracy_score * 0.20 +
            latency_score * 0.15 +
            sentiment_score * 0.10
        )
        
        evaluation.scores.user_satisfaction_indicator = min(max(satisfaction, 0.0), 100.0)
    
    def _generate_notes(self, evaluation: CallEvaluation, call_metrics: Dict):
        """Generate human-readable notes about the evaluation"""
        notes = []
        
        scores = evaluation.scores
        
        # Highlight concerns
        if scores.accuracy_score < 60:
            notes.append("Low accuracy score - review response quality")
        
        if scores.flow_score < 60:
            notes.append("Poor conversation flow - check for delays or issues")
        
        if scores.task_completion < 50:
            notes.append("Low task completion - user may not have achieved goal")
        
        if scores.avg_latency > 3000:
            notes.append(f"High latency ({scores.avg_latency:.0f}ms) - performance issue")
        
        if scores.sentiment == SentimentType.NEGATIVE:
            notes.append("Negative sentiment detected - review conversation")
        
        if scores.escalation_needed:
            notes.append("Escalation required - follow up needed")
        
        # Positive highlights
        if scores.user_satisfaction_indicator >= 80:
            notes.append("Excellent call quality")
        
        evaluation.notes = "; ".join(notes) if notes else "No issues detected"
    
    def save_evaluation(self, evaluation: CallEvaluation):
        """
        Save evaluation to CSV file.
        
        Args:
            evaluation: CallEvaluation object to save
        """
        try:
            with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    evaluation.call_id,
                    evaluation.timestamp,
                    f"{evaluation.duration_seconds:.2f}",
                    f"{evaluation.total_cost:.6f}",
                    f"{evaluation.scores.accuracy_score:.1f}",
                    f"{evaluation.scores.flow_score:.1f}",
                    f"{evaluation.scores.intent_accuracy:.1f}",
                    f"{evaluation.scores.task_completion:.1f}",
                    evaluation.scores.sentiment.value,
                    f"{evaluation.scores.avg_latency:.1f}",
                    f"{evaluation.scores.cost_efficiency:.1f}",
                    f"{evaluation.scores.user_satisfaction_indicator:.1f}",
                    evaluation.scores.interruption_count,
                    evaluation.scores.escalation_needed,
                    evaluation.total_turns,
                    ','.join(evaluation.intents_detected),
                    evaluation.notes
                ])
            
            logger.info(f"Evaluation saved to CSV: {evaluation.call_id}")
            
            # Also save detailed JSON
            json_file = self.output_dir / f"{evaluation.call_id}_eval.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                # Convert evaluation to dict
                eval_dict = {
                    'call_id': evaluation.call_id,
                    'timestamp': evaluation.timestamp,
                    'duration_seconds': evaluation.duration_seconds,
                    'total_cost': evaluation.total_cost,
                    'scores': {
                        'accuracy_score': evaluation.scores.accuracy_score,
                        'flow_score': evaluation.scores.flow_score,
                        'intent_accuracy': evaluation.scores.intent_accuracy,
                        'task_completion': evaluation.scores.task_completion,
                        'sentiment': evaluation.scores.sentiment.value,
                        'cost_efficiency': evaluation.scores.cost_efficiency,
                        'avg_latency': evaluation.scores.avg_latency,
                        'interruption_count': evaluation.scores.interruption_count,
                        'escalation_needed': evaluation.scores.escalation_needed,
                        'user_satisfaction_indicator': evaluation.scores.user_satisfaction_indicator,
                    },
                    'total_turns': evaluation.total_turns,
                    'intents_detected': evaluation.intents_detected,
                    'notes': evaluation.notes,
                    'evaluation_version': evaluation.evaluation_version,
                    'metrics_file': evaluation.metrics_file,
                }
                json.dump(eval_dict, f, indent=2)
            
            logger.info(f"Detailed evaluation saved to JSON: {json_file}")
            
        except Exception as e:
            logger.error(f"Error saving evaluation: {e}", exc_info=True)
            raise
    
    def evaluate_from_file(self, metrics_file: str) -> CallEvaluation:
        """
        Load metrics from file and evaluate.
        
        Args:
            metrics_file: Path to JSON metrics file
            
        Returns:
            CallEvaluation object
        """
        try:
            with open(metrics_file, 'r', encoding='utf-8') as f:
                call_metrics = json.load(f)
            
            evaluation = self.evaluate_call(call_metrics)
            self.save_evaluation(evaluation)
            
            return evaluation
            
        except Exception as e:
            logger.error(f"Error evaluating from file {metrics_file}: {e}")
            raise
    
    def batch_evaluate(self, metrics_dir: str):
        """
        Evaluate all metrics files in a directory.
        
        Args:
            metrics_dir: Directory containing JSON metrics files
        """
        metrics_path = Path(metrics_dir)
        json_files = list(metrics_path.glob("*.json"))
        
        logger.info(f"Found {len(json_files)} metrics files to evaluate")
        
        evaluations = []
        for json_file in json_files:
            try:
                # Skip evaluation files themselves
                if '_eval.json' in json_file.name:
                    continue
                
                logger.info(f"Evaluating {json_file.name}")
                evaluation = self.evaluate_from_file(str(json_file))
                evaluations.append(evaluation)
                
            except Exception as e:
                logger.error(f"Error evaluating {json_file}: {e}")
                continue
        
        logger.info(f"Batch evaluation complete: {len(evaluations)} calls evaluated")
        return evaluations
    
    def get_summary_statistics(self) -> Dict[str, Any]:
        """
        Calculate summary statistics from all evaluations.
        
        Returns:
            Dictionary with aggregate statistics
        """
        if not self.csv_file.exists():
            return {}
        
        stats = {
            'total_calls': 0,
            'avg_accuracy': 0.0,
            'avg_flow': 0.0,
            'avg_intent_accuracy': 0.0,
            'avg_task_completion': 0.0,
            'avg_cost_efficiency': 0.0,
            'avg_user_satisfaction': 0.0,
            'avg_latency': 0.0,
            'sentiment_distribution': {},
        }
        
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                if not rows:
                    return stats
                
                stats['total_calls'] = len(rows)
                
                # Calculate averages
                stats['avg_accuracy'] = sum(float(r['accuracy_score']) for r in rows) / len(rows)
                stats['avg_flow'] = sum(float(r['flow_score']) for r in rows) / len(rows)
                stats['avg_intent_accuracy'] = sum(float(r['intent_accuracy']) for r in rows) / len(rows)
                stats['avg_task_completion'] = sum(float(r['task_completion']) for r in rows) / len(rows)
                stats['avg_cost_efficiency'] = sum(float(r['cost_efficiency']) for r in rows) / len(rows)
                stats['avg_user_satisfaction'] = sum(float(r['user_satisfaction']) for r in rows) / len(rows)
                stats['avg_latency'] = sum(float(r['avg_latency']) for r in rows) / len(rows)
                
                # Sentiment distribution
                sentiments = [r['sentiment'] for r in rows]
                for sentiment in set(sentiments):
                    stats['sentiment_distribution'][sentiment] = sentiments.count(sentiment)
                
        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")
        
        return stats


def evaluate_call_automatically(call_metrics: Dict[str, Any], 
                               evaluator: Optional[CallEvaluator] = None) -> CallEvaluation:
    """
    Convenience function to evaluate a call automatically.
    
    This is the main entry point for automatic evaluation when a call ends.
    
    Args:
        call_metrics: Call metrics dictionary from cost tracker
        evaluator: Optional existing evaluator instance
        
    Returns:
        CallEvaluation object
    """
    if evaluator is None:
        evaluator = CallEvaluator()
    
    evaluation = evaluator.evaluate_call(call_metrics)
    evaluator.save_evaluation(evaluation)
    
    return evaluation


if __name__ == "__main__":
    # CLI for batch evaluation
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    if len(sys.argv) > 1:
        metrics_dir = sys.argv[1]
    else:
        metrics_dir = os.path.join(os.path.dirname(__file__), "metrics")
    
    print(f"Evaluating metrics from: {metrics_dir}")
    
    evaluator = CallEvaluator()
    evaluator.batch_evaluate(metrics_dir)
    
    # Print summary
    stats = evaluator.get_summary_statistics()
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Total Calls: {stats['total_calls']}")
    print(f"Average Accuracy: {stats['avg_accuracy']:.1f}")
    print(f"Average Flow Score: {stats['avg_flow']:.1f}")
    print(f"Average Intent Accuracy: {stats['avg_intent_accuracy']:.1f}")
    print(f"Average Task Completion: {stats['avg_task_completion']:.1f}")
    print(f"Average Cost Efficiency: {stats['avg_cost_efficiency']:.1f}")
    print(f"Average User Satisfaction: {stats['avg_user_satisfaction']:.1f}")
    print(f"Average Latency: {stats['avg_latency']:.0f}ms")
    print(f"\nSentiment Distribution: {stats['sentiment_distribution']}")
    print("=" * 60)
