"""
Test suite for the Call Evaluation Framework

This module tests all aspects of the evaluation system including:
- Accuracy scoring
- Flow evaluation
- Intent recognition
- Task completion assessment
- Sentiment analysis
- Cost efficiency calculation
- CSV storage
- Batch processing
"""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from call_evaluator import (
    CallEvaluator,
    CallEvaluation,
    EvaluationScores,
    SentimentType,
    IntentCategory,
    evaluate_call_automatically,
)


class TestCallEvaluator(unittest.TestCase):
    """Test suite for CallEvaluator"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directory for test outputs
        self.test_dir = tempfile.mkdtemp()
        self.evaluator = CallEvaluator(output_dir=self.test_dir)
        
        # Sample call metrics (realistic structure)
        self.sample_metrics = {
            "call_id": "test_call_001",
            "start_timestamp": "2026-01-24T10:00:00.000000",
            "end_timestamp": "2026-01-24T10:05:30.000000",
            "duration_seconds": 330.0,
            "responses": [
                {
                    "response_id": "test_call_001_response_1",
                    "timestamp": "2026-01-24T10:00:05.000000",
                    "stt": {
                        "model": "whisper-large-v3-turbo",
                        "duration_seconds": 3.0,
                        "cost": 0.001,
                        "latency_ms": 500.0,
                    },
                    "llm": {
                        "model": "llama-3.3-70b-versatile",
                        "input_tokens": 2000,
                        "output_tokens": 150,
                        "total_tokens": 2150,
                        "input_cost": 0.00118,
                        "output_cost": 0.0001185,
                        "total_cost": 0.0012985,
                        "latency_ms": 1200.0,
                    },
                    "tts": {
                        "model": "canopylabs/orpheus-v1-english",
                        "characters_processed": 350,
                        "cost": 0.0035,
                        "latency_ms": 800.0,
                    },
                    "end_to_end_latency_ms": 2500.0,
                    "total_cost": 0.0059,
                },
                {
                    "response_id": "test_call_001_response_2",
                    "timestamp": "2026-01-24T10:01:20.000000",
                    "stt": {
                        "model": "whisper-large-v3-turbo",
                        "duration_seconds": 2.5,
                        "cost": 0.0008,
                        "latency_ms": 450.0,
                    },
                    "llm": {
                        "model": "llama-3.3-70b-versatile",
                        "input_tokens": 2100,
                        "output_tokens": 120,
                        "total_tokens": 2220,
                        "input_cost": 0.001239,
                        "output_cost": 0.0000948,
                        "total_cost": 0.0013338,
                        "latency_ms": 1100.0,
                    },
                    "tts": {
                        "model": "canopylabs/orpheus-v1-english",
                        "characters_processed": 280,
                        "cost": 0.0028,
                        "latency_ms": 700.0,
                    },
                    "end_to_end_latency_ms": 2250.0,
                    "total_cost": 0.0050,
                },
            ],
            "total_stt_cost": 0.0018,
            "total_llm_cost": 0.0026323,
            "total_tts_cost": 0.0063,
            "total_livekit_cost": 0.055,
            "total_cost": 0.0657323,
            "total_stt_duration": 5.5,
            "total_llm_input_tokens": 4100,
            "total_llm_output_tokens": 270,
            "total_tts_characters": 630,
            "avg_stt_latency_ms": 475.0,
            "avg_llm_latency_ms": 1150.0,
            "avg_tts_latency_ms": 750.0,
            "avg_end_to_end_latency_ms": 2375.0,
            "livekit": {
                "connection_duration_seconds": 330.0,
                "cost": 0.055,
                "timestamp": "2026-01-24T10:05:30.000000",
            }
        }
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Remove temporary directory
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_evaluator_initialization(self):
        """Test evaluator initializes correctly"""
        self.assertIsNotNone(self.evaluator)
        self.assertTrue(os.path.exists(self.test_dir))
        self.assertTrue(self.evaluator.csv_file.exists())
    
    def test_csv_header_creation(self):
        """Test CSV file has correct header"""
        with open(self.evaluator.csv_file, 'r') as f:
            header = f.readline().strip()
            expected_fields = [
                'call_id', 'timestamp', 'duration', 'total_cost',
                'accuracy_score', 'flow_score', 'intent_accuracy',
                'task_completion', 'sentiment', 'avg_latency',
                'cost_efficiency', 'user_satisfaction'
            ]
            for field in expected_fields:
                self.assertIn(field, header)
    
    def test_evaluate_call_basic(self):
        """Test basic call evaluation"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        
        self.assertIsNotNone(evaluation)
        self.assertEqual(evaluation.call_id, "test_call_001")
        self.assertEqual(evaluation.duration_seconds, 330.0)
        self.assertGreater(evaluation.total_cost, 0)
        self.assertIsNotNone(evaluation.scores)
    
    def test_accuracy_scoring(self):
        """Test accuracy score calculation"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        
        # Should have good accuracy with complete responses
        self.assertGreater(evaluation.scores.accuracy_score, 70.0)
        self.assertLessEqual(evaluation.scores.accuracy_score, 100.0)
    
    def test_accuracy_scoring_incomplete_responses(self):
        """Test accuracy with incomplete responses"""
        incomplete_metrics = self.sample_metrics.copy()
        incomplete_metrics["responses"] = [
            {
                "response_id": "incomplete_1",
                "timestamp": "2026-01-24T10:00:05.000000",
                "llm": None,  # Missing LLM
                "tts": {
                    "model": "canopylabs/orpheus-v1-english",
                    "characters_processed": 50,
                    "cost": 0.0005,
                    "latency_ms": 300.0,
                },
                "end_to_end_latency_ms": 300.0,
                "total_cost": 0.0005,
            }
        ]
        
        evaluation = self.evaluator.evaluate_call(incomplete_metrics)
        
        # Should have lower accuracy
        self.assertLess(evaluation.scores.accuracy_score, 70.0)
    
    def test_flow_scoring(self):
        """Test conversation flow scoring"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        
        # Should have decent flow with reasonable duration and responses
        self.assertGreater(evaluation.scores.flow_score, 60.0)
        self.assertLessEqual(evaluation.scores.flow_score, 100.0)
    
    def test_flow_scoring_short_call(self):
        """Test flow scoring for very short calls"""
        short_metrics = self.sample_metrics.copy()
        short_metrics["duration_seconds"] = 15.0
        short_metrics["responses"] = short_metrics["responses"][:1]
        
        evaluation = self.evaluator.evaluate_call(short_metrics)
        
        # Short calls should get lower flow scores
        self.assertLess(evaluation.scores.flow_score, 85.0)
    
    def test_flow_scoring_long_call(self):
        """Test flow scoring for very long calls"""
        long_metrics = self.sample_metrics.copy()
        long_metrics["duration_seconds"] = 1200.0  # 20 minutes
        
        evaluation = self.evaluator.evaluate_call(long_metrics)
        
        # Very long calls should get lower flow scores
        self.assertLess(evaluation.scores.flow_score, 90.0)
    
    def test_intent_recognition_scoring(self):
        """Test intent recognition scoring"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        
        # Should have some intent accuracy
        self.assertGreater(evaluation.scores.intent_accuracy, 0.0)
        self.assertLessEqual(evaluation.scores.intent_accuracy, 100.0)
        self.assertTrue(len(evaluation.intents_detected) > 0)
    
    def test_task_completion_scoring(self):
        """Test task completion scoring"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        
        # Good call should have decent task completion
        self.assertGreater(evaluation.scores.task_completion, 60.0)
        self.assertLessEqual(evaluation.scores.task_completion, 100.0)
    
    def test_sentiment_evaluation(self):
        """Test sentiment evaluation"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        
        # Should have a valid sentiment
        self.assertIsInstance(evaluation.scores.sentiment, SentimentType)
        self.assertIn(evaluation.scores.sentiment, list(SentimentType))
    
    def test_sentiment_negative_short_call(self):
        """Test negative sentiment for very short calls"""
        short_metrics = self.sample_metrics.copy()
        short_metrics["duration_seconds"] = 20.0
        short_metrics["responses"] = short_metrics["responses"][:1]
        
        evaluation = self.evaluator.evaluate_call(short_metrics)
        
        # Very short calls likely negative
        self.assertEqual(evaluation.scores.sentiment, SentimentType.NEGATIVE)
    
    def test_latency_evaluation(self):
        """Test latency metric extraction"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        
        # Should extract average latency
        self.assertGreater(evaluation.scores.avg_latency, 0.0)
        self.assertEqual(evaluation.scores.avg_latency, 2375.0)
    
    def test_cost_efficiency_scoring(self):
        """Test cost efficiency calculation"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        
        # Should have a cost efficiency score
        self.assertGreater(evaluation.scores.cost_efficiency, 0.0)
        self.assertLessEqual(evaluation.scores.cost_efficiency, 100.0)
    
    def test_cost_efficiency_expensive_call(self):
        """Test cost efficiency for expensive calls"""
        expensive_metrics = self.sample_metrics.copy()
        expensive_metrics["total_cost"] = 5.0  # Very expensive
        expensive_metrics["duration_seconds"] = 60.0  # Short duration
        
        evaluation = self.evaluator.evaluate_call(expensive_metrics)
        
        # Should have lower cost efficiency
        self.assertLess(evaluation.scores.cost_efficiency, 85.0)
    
    def test_user_satisfaction_calculation(self):
        """Test overall user satisfaction indicator"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        
        # Should calculate satisfaction
        self.assertGreater(evaluation.scores.user_satisfaction_indicator, 0.0)
        self.assertLessEqual(evaluation.scores.user_satisfaction_indicator, 100.0)
    
    def test_notes_generation(self):
        """Test that notes are generated"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        
        # Should have notes
        self.assertIsNotNone(evaluation.notes)
        self.assertIsInstance(evaluation.notes, str)
    
    def test_notes_for_problematic_call(self):
        """Test notes for calls with issues"""
        problematic_metrics = self.sample_metrics.copy()
        problematic_metrics["avg_end_to_end_latency_ms"] = 8000.0  # High latency
        problematic_metrics["duration_seconds"] = 15.0  # Short
        
        evaluation = self.evaluator.evaluate_call(problematic_metrics)
        
        # Should have issue notes
        self.assertIn("latency", evaluation.notes.lower())
    
    def test_save_evaluation(self):
        """Test saving evaluation to CSV"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        self.evaluator.save_evaluation(evaluation)
        
        # Check CSV file has content
        with open(self.evaluator.csv_file, 'r') as f:
            lines = f.readlines()
            self.assertGreater(len(lines), 1)  # Header + data
            self.assertIn("test_call_001", lines[1])
    
    def test_save_evaluation_json(self):
        """Test that detailed JSON is also saved"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        self.evaluator.save_evaluation(evaluation)
        
        # Check JSON file exists
        json_file = Path(self.test_dir) / "test_call_001_eval.json"
        self.assertTrue(json_file.exists())
        
        # Check JSON content
        with open(json_file, 'r') as f:
            data = json.load(f)
            self.assertEqual(data['call_id'], "test_call_001")
            self.assertIn('scores', data)
    
    def test_evaluate_from_file(self):
        """Test evaluating from a metrics file"""
        # Save sample metrics to file
        metrics_file = Path(self.test_dir) / "test_metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(self.sample_metrics, f)
        
        # Evaluate from file
        evaluation = self.evaluator.evaluate_from_file(str(metrics_file))
        
        self.assertIsNotNone(evaluation)
        self.assertEqual(evaluation.call_id, "test_call_001")
    
    def test_batch_evaluate(self):
        """Test batch evaluation of multiple files"""
        # Create multiple metrics files
        for i in range(3):
            metrics = self.sample_metrics.copy()
            metrics["call_id"] = f"test_call_00{i+1}"
            
            metrics_file = Path(self.test_dir) / f"call_00{i+1}.json"
            with open(metrics_file, 'w') as f:
                json.dump(metrics, f)
        
        # Batch evaluate
        evaluations = self.evaluator.batch_evaluate(self.test_dir)
        
        # Should evaluate all 3 files
        self.assertEqual(len(evaluations), 3)
    
    def test_summary_statistics(self):
        """Test summary statistics calculation"""
        # Create and save some evaluations
        for i in range(5):
            metrics = self.sample_metrics.copy()
            metrics["call_id"] = f"test_call_00{i+1}"
            
            evaluation = self.evaluator.evaluate_call(metrics)
            self.evaluator.save_evaluation(evaluation)
        
        # Get summary statistics
        stats = self.evaluator.get_summary_statistics()
        
        self.assertEqual(stats['total_calls'], 5)
        self.assertIn('avg_accuracy', stats)
        self.assertIn('avg_flow', stats)
        self.assertIn('avg_user_satisfaction', stats)
        self.assertIn('sentiment_distribution', stats)
    
    def test_evaluate_call_automatically(self):
        """Test automatic evaluation convenience function"""
        evaluation = evaluate_call_automatically(
            self.sample_metrics,
            evaluator=self.evaluator
        )
        
        self.assertIsNotNone(evaluation)
        self.assertEqual(evaluation.call_id, "test_call_001")
        
        # Should be saved to CSV
        with open(self.evaluator.csv_file, 'r') as f:
            content = f.read()
            self.assertIn("test_call_001", content)
    
    def test_empty_responses_handling(self):
        """Test handling of calls with no responses"""
        empty_metrics = self.sample_metrics.copy()
        empty_metrics["responses"] = []
        
        evaluation = self.evaluator.evaluate_call(empty_metrics)
        
        # Should handle gracefully
        self.assertEqual(evaluation.scores.accuracy_score, 0.0)
        self.assertEqual(evaluation.total_turns, 0)
    
    def test_missing_data_handling(self):
        """Test handling of missing optional data"""
        minimal_metrics = {
            "call_id": "minimal_call",
            "duration_seconds": 60.0,
            "total_cost": 0.05,
            "responses": [],
        }
        
        # Should not crash
        evaluation = self.evaluator.evaluate_call(minimal_metrics)
        self.assertIsNotNone(evaluation)
    
    def test_evaluation_versioning(self):
        """Test that evaluation version is tracked"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        
        self.assertIsNotNone(evaluation.evaluation_version)
        self.assertEqual(evaluation.evaluation_version, "1.0")
    
    def test_total_turns_tracking(self):
        """Test that total turns are tracked correctly"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        
        self.assertEqual(evaluation.total_turns, len(self.sample_metrics["responses"]))
        self.assertEqual(evaluation.total_turns, 2)


class TestEvaluationScores(unittest.TestCase):
    """Test EvaluationScores dataclass"""
    
    def test_default_scores(self):
        """Test default score values"""
        scores = EvaluationScores()
        
        self.assertEqual(scores.accuracy_score, 0.0)
        self.assertEqual(scores.flow_score, 0.0)
        self.assertEqual(scores.intent_accuracy, 0.0)
        self.assertEqual(scores.task_completion, 0.0)
        self.assertEqual(scores.sentiment, SentimentType.UNKNOWN)
        self.assertEqual(scores.cost_efficiency, 0.0)
    
    def test_score_assignment(self):
        """Test assigning scores"""
        scores = EvaluationScores(
            accuracy_score=85.0,
            flow_score=90.0,
            sentiment=SentimentType.POSITIVE
        )
        
        self.assertEqual(scores.accuracy_score, 85.0)
        self.assertEqual(scores.flow_score, 90.0)
        self.assertEqual(scores.sentiment, SentimentType.POSITIVE)


class TestSentimentType(unittest.TestCase):
    """Test SentimentType enum"""
    
    def test_sentiment_values(self):
        """Test sentiment type values"""
        self.assertEqual(SentimentType.POSITIVE.value, "positive")
        self.assertEqual(SentimentType.NEUTRAL.value, "neutral")
        self.assertEqual(SentimentType.NEGATIVE.value, "negative")
        self.assertEqual(SentimentType.MIXED.value, "mixed")
        self.assertEqual(SentimentType.UNKNOWN.value, "unknown")


class TestIntentCategory(unittest.TestCase):
    """Test IntentCategory enum"""
    
    def test_intent_categories(self):
        """Test intent category values"""
        self.assertEqual(IntentCategory.INQUIRY.value, "inquiry")
        self.assertEqual(IntentCategory.ORDERING.value, "ordering")
        self.assertEqual(IntentCategory.RESULTS.value, "results")
        self.assertEqual(IntentCategory.UNKNOWN.value, "unknown")


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
