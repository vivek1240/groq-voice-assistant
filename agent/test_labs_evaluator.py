"""
Test suite for Labs Module Call Evaluation Framework

Tests compliance with Labs_Call_Evaluation_System_Design v1.0
"""

import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from labs_evaluator import (
    LabsCallEvaluator,
    LabsCallEvaluation,
    UserSentiment,
    QueryCategory,
    TestingPhase,
    evaluate_labs_call_automatically,
)


class TestLabsCallEvaluator(unittest.TestCase):
    """Test suite for Labs Module evaluator"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary directory for test outputs
        self.test_dir = tempfile.mkdtemp()
        self.evaluator = LabsCallEvaluator(output_dir=self.test_dir, use_llm=False)
        
        # Sample call metrics
        self.sample_metrics = {
            "call_id": "labs_test_call_001",
            "start_timestamp": "2026-01-24T10:00:00.000000",
            "end_timestamp": "2026-01-24T10:05:30.000000",
            "duration_seconds": 330.0,
            "responses": [
                {
                    "response_id": "labs_test_call_001_response_1",
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
                },
            ],
            "total_cost": 0.0059,
            "avg_end_to_end_latency_ms": 2500.0,
        }
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_evaluator_initialization(self):
        """Test evaluator initializes correctly"""
        self.assertIsNotNone(self.evaluator)
        self.assertTrue(os.path.exists(self.test_dir))
        self.assertTrue(self.evaluator.csv_file.exists())
    
    def test_csv_header_labs_compliant(self):
        """Test CSV file has Labs Module compliant header"""
        with open(self.evaluator.csv_file, 'r') as f:
            header = f.readline().strip()
            
            # Check for all 8 required dimensions
            required_fields = [
                'user_sentiment', 'call_summary', 'query_resolved', 'escalation_required',
                'query_category', 'testing_phase',
                'medical_boundary_maintained', 'proper_disclaimer_given'
            ]
            
            for field in required_fields:
                self.assertIn(field, header, f"Missing required field: {field}")
    
    def test_user_sentiment_enum(self):
        """Test UserSentiment enum matches specification"""
        # Specification requires: positive, neutral, confused, anxious, frustrated
        self.assertEqual(UserSentiment.POSITIVE.value, "positive")
        self.assertEqual(UserSentiment.NEUTRAL.value, "neutral")
        self.assertEqual(UserSentiment.CONFUSED.value, "confused")
        self.assertEqual(UserSentiment.ANXIOUS.value, "anxious")
        self.assertEqual(UserSentiment.FRUSTRATED.value, "frustrated")
    
    def test_query_category_enum_16_types(self):
        """Test QueryCategory has all 16 required categories"""
        expected_categories = [
            'test_kit_info',
            'ordering_purchase', 'delivery_shipping',
            'kit_registration',
            'sample_collection', 'fasting_requirements', 'sample_shipping',
            'results_general', 'biomarker_explanation', 'results_interpretation', 'results_concern',
            'sample_rejection', 'technical_issue',
            'medical_advice_request', 'billing_refund', 'general_inquiry'
        ]
        
        actual_values = [cat.value for cat in QueryCategory]
        for expected in expected_categories:
            self.assertIn(expected, actual_values, f"Missing category: {expected}")
        
        self.assertEqual(len(actual_values), 16, "Should have exactly 16 categories")
    
    def test_testing_phase_enum_8_phases(self):
        """Test TestingPhase has all 8 required phases"""
        expected_phases = [
            'pre_purchase', 'post_order', 'kit_received',
            'pre_collection', 'during_collection', 'post_collection',
            'results_received', 'unknown'
        ]
        
        actual_values = [phase.value for phase in TestingPhase]
        for expected in expected_phases:
            self.assertIn(expected, actual_values, f"Missing phase: {expected}")
        
        self.assertEqual(len(actual_values), 8, "Should have exactly 8 phases")
    
    def test_evaluate_call_basic(self):
        """Test basic Labs call evaluation"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        
        self.assertIsNotNone(evaluation)
        self.assertEqual(evaluation.call_id, "labs_test_call_001")
        
        # Check all 8 dimensions exist
        self.assertIsInstance(evaluation.user_sentiment, UserSentiment)
        self.assertIsInstance(evaluation.call_summary, str)
        self.assertIsInstance(evaluation.query_resolved, bool)
        self.assertIsInstance(evaluation.escalation_required, bool)
        self.assertIsInstance(evaluation.query_category, QueryCategory)
        self.assertIsInstance(evaluation.testing_phase, TestingPhase)
        self.assertIsInstance(evaluation.medical_boundary_maintained, bool)
        # proper_disclaimer_given can be None
    
    def test_evaluation_8_dimensions(self):
        """Test evaluation has all 8 required dimensions"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        
        # Core Metrics (4)
        self.assertIsNotNone(evaluation.user_sentiment)
        self.assertIsNotNone(evaluation.call_summary)
        self.assertIsNotNone(evaluation.query_resolved)
        self.assertIsNotNone(evaluation.escalation_required)
        
        # Domain Metrics (2)
        self.assertIsNotNone(evaluation.query_category)
        self.assertIsNotNone(evaluation.testing_phase)
        
        # Compliance Metrics (2)
        self.assertIsNotNone(evaluation.medical_boundary_maintained)
        # proper_disclaimer_given can be None (not applicable)
    
    def test_call_summary_generation(self):
        """Test call summary is generated (2-3 sentences)"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        
        summary = evaluation.call_summary
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 0, "Summary should not be empty")
        
        # Check it's a reasonable length (roughly 2-3 sentences)
        sentences = summary.split('.')
        self.assertGreaterEqual(len([s for s in sentences if s.strip()]), 1)
    
    def test_medical_boundary_maintained_tracked(self):
        """Test medical boundary compliance is tracked"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        
        # Should be boolean
        self.assertIsInstance(evaluation.medical_boundary_maintained, bool)
        
        # Heuristic should default to True (conservative)
        self.assertTrue(evaluation.medical_boundary_maintained)
    
    def test_proper_disclaimer_given_tracked(self):
        """Test disclaimer tracking (can be None if not applicable)"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        
        # Can be True, False, or None
        self.assertIn(
            evaluation.proper_disclaimer_given,
            [True, False, None]
        )
    
    def test_compliance_flags_generation(self):
        """Test compliance flags are generated"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        
        # Flags should be a list
        self.assertIsInstance(evaluation.flags, list)
    
    def test_save_evaluation_csv_format(self):
        """Test evaluation saves to CSV correctly"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        self.evaluator.save_evaluation(evaluation)
        
        # Check CSV file has content
        with open(self.evaluator.csv_file, 'r') as f:
            lines = f.readlines()
            self.assertGreater(len(lines), 1, "Should have header + data")
            self.assertIn("labs_test_call_001", lines[1])
    
    def test_save_evaluation_json_format(self):
        """Test evaluation saves to JSON correctly"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        self.evaluator.save_evaluation(evaluation)
        
        # Check JSON file exists
        json_file = Path(self.test_dir) / "labs_test_call_001_labs_eval.json"
        self.assertTrue(json_file.exists())
        
        # Check JSON structure
        with open(json_file, 'r') as f:
            data = json.load(f)
            self.assertIn('core_metrics', data)
            self.assertIn('domain_metrics', data)
            self.assertIn('compliance_metrics', data)
    
    def test_sentiment_detection_frustrated(self):
        """Test frustrated sentiment detection for short calls"""
        short_metrics = self.sample_metrics.copy()
        short_metrics["duration_seconds"] = 20.0
        short_metrics["responses"] = short_metrics["responses"][:1]
        
        evaluation = self.evaluator.evaluate_call(short_metrics)
        
        # Short calls should be detected as frustrated
        self.assertEqual(evaluation.user_sentiment, UserSentiment.FRUSTRATED)
    
    def test_sentiment_detection_confused(self):
        """Test confused sentiment for high latency calls"""
        high_latency_metrics = self.sample_metrics.copy()
        high_latency_metrics["avg_end_to_end_latency_ms"] = 7000.0
        
        evaluation = self.evaluator.evaluate_call(high_latency_metrics)
        
        # High latency should suggest confusion
        self.assertEqual(evaluation.user_sentiment, UserSentiment.CONFUSED)
    
    def test_escalation_detection_frustrated(self):
        """Test escalation needed for frustrated users"""
        frustrated_metrics = self.sample_metrics.copy()
        frustrated_metrics["duration_seconds"] = 15.0
        
        evaluation = self.evaluator.evaluate_call(frustrated_metrics)
        
        # Frustrated calls should escalate
        self.assertTrue(evaluation.escalation_required)
    
    def test_evaluate_from_file(self):
        """Test evaluating from a metrics file"""
        # Save sample metrics to file
        metrics_file = Path(self.test_dir) / "test_metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(self.sample_metrics, f)
        
        # Evaluate from file
        evaluation = self.evaluator.evaluate_from_file(str(metrics_file))
        
        self.assertIsNotNone(evaluation)
        self.assertEqual(evaluation.call_id, "labs_test_call_001")
    
    def test_batch_evaluate(self):
        """Test batch evaluation of multiple files"""
        # Create multiple metrics files
        for i in range(3):
            metrics = self.sample_metrics.copy()
            metrics["call_id"] = f"labs_test_call_00{i+1}"
            
            metrics_file = Path(self.test_dir) / f"call_00{i+1}.json"
            with open(metrics_file, 'w') as f:
                json.dump(metrics, f)
        
        # Batch evaluate
        evaluations = self.evaluator.batch_evaluate(self.test_dir)
        
        # Should evaluate all 3 files
        self.assertEqual(len(evaluations), 3)
    
    def test_compliance_report_generation(self):
        """Test compliance report generation"""
        # Create and save some evaluations
        for i in range(5):
            metrics = self.sample_metrics.copy()
            metrics["call_id"] = f"labs_call_00{i+1}"
            
            evaluation = self.evaluator.evaluate_call(metrics)
            self.evaluator.save_evaluation(evaluation)
        
        # Generate compliance report
        report = self.evaluator.get_compliance_report()
        
        self.assertIsNotNone(report)
        self.assertIn('total_calls', report)
        self.assertIn('compliance', report)
        self.assertIn('kpis', report)
        self.assertIn('alerts', report)
    
    def test_compliance_report_kpis(self):
        """Test compliance report includes all required KPIs"""
        # Create evaluation
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        self.evaluator.save_evaluation(evaluation)
        
        report = self.evaluator.get_compliance_report()
        
        # Check required KPIs
        kpis = report['kpis']
        self.assertIn('resolution_rate', kpis)
        self.assertIn('escalation_rate', kpis)
        self.assertIn('anxiety_detection_rate', kpis)
    
    def test_compliance_report_targets(self):
        """Test compliance report includes target thresholds"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        self.evaluator.save_evaluation(evaluation)
        
        report = self.evaluator.get_compliance_report()
        
        # Check targets specified in document
        targets = report['targets']
        self.assertEqual(targets['resolution_rate_target'], 80)  # >80%
        self.assertEqual(targets['escalation_rate_target'], 15)  # <15%
        self.assertEqual(targets['medical_compliance_target'], 100)  # 100%
    
    def test_medical_boundary_violation_alert(self):
        """Test alert generated for medical boundary violations"""
        # Create evaluation with violation
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        evaluation.medical_boundary_maintained = False  # Violation
        
        self.evaluator.save_evaluation(evaluation)
        
        report = self.evaluator.get_compliance_report()
        
        # Should have critical alert
        alerts = report['alerts']
        self.assertTrue(any('CRITICAL' in alert for alert in alerts))
        self.assertTrue(any('medical boundary' in alert.lower() for alert in alerts))
    
    def test_evaluate_labs_call_automatically(self):
        """Test automatic evaluation convenience function"""
        evaluation = evaluate_labs_call_automatically(
            self.sample_metrics,
            evaluator=self.evaluator
        )
        
        self.assertIsNotNone(evaluation)
        self.assertEqual(evaluation.call_id, "labs_test_call_001")
        
        # Should be saved to CSV
        with open(self.evaluator.csv_file, 'r') as f:
            content = f.read()
            self.assertIn("labs_test_call_001", content)
    
    def test_evaluation_version_tracking(self):
        """Test evaluation version is tracked"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        
        self.assertIsNotNone(evaluation.evaluation_version)
        self.assertEqual(evaluation.evaluation_version, "1.0")
    
    def test_evaluation_method_tracking(self):
        """Test evaluation method is tracked (heuristic vs llm)"""
        evaluation = self.evaluator.evaluate_call(self.sample_metrics)
        
        self.assertIn(evaluation.evaluation_method, ["heuristic", "llm"])
    
    def test_heuristic_evaluation_method(self):
        """Test heuristic evaluation is used when LLM disabled"""
        evaluator = LabsCallEvaluator(output_dir=self.test_dir, use_llm=False)
        evaluation = evaluator.evaluate_call(self.sample_metrics)
        
        self.assertEqual(evaluation.evaluation_method, "heuristic")
    
    def test_empty_call_handling(self):
        """Test handling of calls with no responses"""
        empty_metrics = self.sample_metrics.copy()
        empty_metrics["responses"] = []
        empty_metrics["duration_seconds"] = 5.0
        
        evaluation = self.evaluator.evaluate_call(empty_metrics)
        
        # Should not crash
        self.assertIsNotNone(evaluation)
        self.assertEqual(evaluation.total_turns, 0)


class TestUserSentiment(unittest.TestCase):
    """Test UserSentiment enum"""
    
    def test_all_required_sentiments(self):
        """Test all 5 required sentiment types exist"""
        required = ['positive', 'neutral', 'confused', 'anxious', 'frustrated']
        actual = [s.value for s in UserSentiment]
        
        for req in required:
            self.assertIn(req, actual, f"Missing sentiment: {req}")


class TestQueryCategory(unittest.TestCase):
    """Test QueryCategory enum"""
    
    def test_16_categories_exact(self):
        """Test exactly 16 categories as specified"""
        categories = list(QueryCategory)
        self.assertEqual(len(categories), 16, "Should have exactly 16 categories")
    
    def test_test_kit_info_category(self):
        """Test test kit info category exists"""
        self.assertEqual(QueryCategory.TEST_KIT_INFO.value, "test_kit_info")
    
    def test_ordering_categories(self):
        """Test ordering related categories"""
        self.assertEqual(QueryCategory.ORDERING_PURCHASE.value, "ordering_purchase")
        self.assertEqual(QueryCategory.DELIVERY_SHIPPING.value, "delivery_shipping")
    
    def test_collection_categories(self):
        """Test sample collection categories"""
        self.assertEqual(QueryCategory.SAMPLE_COLLECTION.value, "sample_collection")
        self.assertEqual(QueryCategory.FASTING_REQUIREMENTS.value, "fasting_requirements")
        self.assertEqual(QueryCategory.SAMPLE_SHIPPING.value, "sample_shipping")
    
    def test_results_categories(self):
        """Test results-related categories"""
        self.assertEqual(QueryCategory.RESULTS_GENERAL.value, "results_general")
        self.assertEqual(QueryCategory.BIOMARKER_EXPLANATION.value, "biomarker_explanation")
        self.assertEqual(QueryCategory.RESULTS_INTERPRETATION.value, "results_interpretation")
        self.assertEqual(QueryCategory.RESULTS_CONCERN.value, "results_concern")
    
    def test_out_of_scope_categories(self):
        """Test out-of-scope categories"""
        self.assertEqual(QueryCategory.MEDICAL_ADVICE_REQUEST.value, "medical_advice_request")
        self.assertEqual(QueryCategory.BILLING_REFUND.value, "billing_refund")


class TestTestingPhase(unittest.TestCase):
    """Test TestingPhase enum"""
    
    def test_8_phases_exact(self):
        """Test exactly 8 phases as specified"""
        phases = list(TestingPhase)
        self.assertEqual(len(phases), 8, "Should have exactly 8 phases")
    
    def test_journey_phases(self):
        """Test all journey phases exist"""
        self.assertEqual(TestingPhase.PRE_PURCHASE.value, "pre_purchase")
        self.assertEqual(TestingPhase.POST_ORDER.value, "post_order")
        self.assertEqual(TestingPhase.KIT_RECEIVED.value, "kit_received")
        self.assertEqual(TestingPhase.PRE_COLLECTION.value, "pre_collection")
        self.assertEqual(TestingPhase.DURING_COLLECTION.value, "during_collection")
        self.assertEqual(TestingPhase.POST_COLLECTION.value, "post_collection")
        self.assertEqual(TestingPhase.RESULTS_RECEIVED.value, "results_received")
        self.assertEqual(TestingPhase.UNKNOWN.value, "unknown")


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
