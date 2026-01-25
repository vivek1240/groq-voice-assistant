"""
Labs Module Call Evaluation Framework

Compliant with Labs_Call_Evaluation_System_Design v1.0 (January 2026)

This module provides automated call quality evaluation specifically designed for
the Mercola Health Coach Labs Module voice assistant.

Evaluates 8 dimensions across 3 categories:
- Core Metrics: sentiment, summary, resolved, escalation
- Domain Metrics: query category (16 types), testing phase (8 phases)
- Compliance Metrics: medical boundary maintenance, disclaimer detection
"""

import csv
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("labs-evaluator")


# ============================================================================
# ENUMS - As per specification
# ============================================================================

class UserSentiment(Enum):
    """User's emotional state during the call"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    CONFUSED = "confused"
    ANXIOUS = "anxious"          # Health-related anxiety
    FRUSTRATED = "frustrated"


class QueryCategory(Enum):
    """Primary topic classification (16 labs-specific categories)"""
    # Test Kit Information
    TEST_KIT_INFO = "test_kit_info"
    
    # Ordering & Delivery
    ORDERING_PURCHASE = "ordering_purchase"
    DELIVERY_SHIPPING = "delivery_shipping"
    
    # Registration
    KIT_REGISTRATION = "kit_registration"
    
    # Sample Collection
    SAMPLE_COLLECTION = "sample_collection"
    FASTING_REQUIREMENTS = "fasting_requirements"
    SAMPLE_SHIPPING = "sample_shipping"
    
    # Results & Understanding
    RESULTS_GENERAL = "results_general"
    BIOMARKER_EXPLANATION = "biomarker_explanation"
    RESULTS_INTERPRETATION = "results_interpretation"
    RESULTS_CONCERN = "results_concern"
    
    # Troubleshooting
    SAMPLE_REJECTION = "sample_rejection"
    TECHNICAL_ISSUE = "technical_issue"
    
    # Out of Scope
    MEDICAL_ADVICE_REQUEST = "medical_advice_request"
    BILLING_REFUND = "billing_refund"
    GENERAL_INQUIRY = "general_inquiry"


class TestingPhase(Enum):
    """Which phase of the lab testing journey the user is in"""
    PRE_PURCHASE = "pre_purchase"           # Browsing, not bought yet
    POST_ORDER = "post_order"               # Kit ordered, waiting delivery
    KIT_RECEIVED = "kit_received"           # Kit delivered, needs registration
    PRE_COLLECTION = "pre_collection"       # Registered, preparing for collection
    DURING_COLLECTION = "during_collection" # Actively collecting sample
    POST_COLLECTION = "post_collection"     # Sample collected, waiting results
    RESULTS_RECEIVED = "results_received"   # Has results, viewing them
    UNKNOWN = "unknown"                     # Cannot determine from conversation


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class LabsCallEvaluation:
    """
    Complete Labs Module evaluation result.
    
    Complies with 8-dimension specification:
    - Core Metrics (4): sentiment, summary, resolved, escalation
    - Domain Metrics (2): query category, testing phase
    - Compliance Metrics (2): medical boundary, disclaimer
    """
    # Call identification
    call_id: str
    timestamp: str
    duration_seconds: float
    total_cost: float
    
    # CATEGORY 1: Core Metrics (Standard)
    user_sentiment: UserSentiment
    call_summary: str  # 2-3 sentence summary
    query_resolved: bool  # Whether AI fully addressed the question
    escalation_required: bool  # Whether human follow-up is needed
    
    # CATEGORY 2: Domain-Specific Metrics
    query_category: QueryCategory  # Primary topic (16 categories)
    testing_phase: TestingPhase  # Journey phase (8 phases)
    
    # CATEGORY 3: Compliance & Safety Metrics
    medical_boundary_maintained: bool  # Agent avoided medical diagnosis/advice
    proper_disclaimer_given: Optional[bool]  # Disclaimers when discussing results (null if N/A)
    
    # Conversation transcript
    conversation_transcript: List[Dict[str, str]] = field(default_factory=list)  # Full conversation history
    
    # Additional metadata
    total_turns: int = 0
    avg_latency_ms: float = 0.0
    evaluation_version: str = "1.0"
    evaluation_method: str = "heuristic"  # or "llm"
    
    # Notes for review
    notes: str = ""
    flags: List[str] = field(default_factory=list)  # Compliance flags


class LabsCallEvaluator:
    """
    Labs Module Call Evaluator.
    
    Evaluates voice assistant calls according to Labs Module specification.
    Uses heuristic analysis and optional LLM-based evaluation.
    """
    
    def __init__(self, output_dir: Optional[str] = None, use_llm: bool = False):
        """
        Initialize the Labs evaluator.
        
        Args:
            output_dir: Directory for CSV output. Defaults to ./labs_evaluations/
            use_llm: Whether to use LLM for evaluation (requires GROQ_API_KEY)
        """
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), "labs_evaluations")
        
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        self.csv_file = self.output_dir / "labs_call_evaluations.csv"
        self.cost_csv_file = self.output_dir / "call_cost_metrics.csv"
        self.use_llm = use_llm
        
        # Initialize LLM if requested
        if self.use_llm:
            self._initialize_llm()
        
        self._ensure_csv_header()
        self._ensure_cost_csv_header()
    
    def _initialize_llm(self):
        """Initialize Groq LLM for intelligent evaluation"""
        try:
            from groq import Groq
            from dotenv import load_dotenv
            
            # Load environment variables from .env file
            load_dotenv()
            
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                logger.warning("=" * 60)
                logger.warning("GROQ_API_KEY not found in environment")
                logger.warning("Falling back to heuristic evaluation")
                logger.warning("To enable LLM evaluation, add GROQ_API_KEY to .env")
                logger.warning("=" * 60)
                self.use_llm = False
                return
            
            self.llm_client = Groq(api_key=api_key)
            self.llm_model = os.getenv("LABS_EVAL_MODEL", "llama-3.3-70b-versatile")
            
            logger.info("=" * 60)
            logger.info("LLM EVALUATION ENABLED")
            logger.info(f"Model: {self.llm_model}")
            logger.info("This provides accurate sentiment, intent, and compliance analysis")
            logger.info("=" * 60)
            
        except ImportError:
            logger.warning("=" * 60)
            logger.warning("Groq package not installed")
            logger.warning("Install with: pip install groq")
            logger.warning("Falling back to heuristic evaluation")
            logger.warning("=" * 60)
            self.use_llm = False
        except Exception as e:
            logger.error(f"Error initializing LLM: {e}")
            logger.warning("Falling back to heuristic evaluation")
            self.use_llm = False
    
    def _ensure_csv_header(self):
        """Ensure CSV file exists with proper Labs Module header"""
        if not self.csv_file.exists():
            with open(self.csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'call_id',
                    'timestamp',
                    'duration_seconds',
                    'total_cost',
                    # Core Metrics
                    'user_sentiment',
                    'call_summary',
                    'query_resolved',
                    'escalation_required',
                    # Domain Metrics
                    'query_category',
                    'testing_phase',
                    # Compliance Metrics
                    'medical_boundary_maintained',
                    'proper_disclaimer_given',
                    # Additional
                    'total_turns',
                    'avg_latency_ms',
                    'evaluation_method',
                    'notes',
                    'flags',
                    # Conversation transcript
                    'conversation_transcript'
                ])
            logger.info(f"Created Labs evaluation CSV at {self.csv_file}")
    
    def _ensure_cost_csv_header(self):
        """Ensure cost metrics CSV file exists with proper header"""
        if not self.cost_csv_file.exists():
            with open(self.cost_csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'call_id',
                    'timestamp',
                    'duration_seconds',
                    # Cost breakdown
                    'total_cost',
                    'total_stt_cost',
                    'total_llm_cost',
                    'total_tts_cost',
                    'total_livekit_cost',
                    # Usage metrics
                    'total_stt_duration',
                    'total_llm_input_tokens',
                    'total_llm_output_tokens',
                    'total_tts_characters',
                    # Latency metrics (Time to First Token)
                    'avg_eou_delay_ms',
                    'avg_llm_ttft_ms',
                    'avg_tts_ttfb_ms',
                    'avg_ttft_ms'
                ])
            logger.info(f"Created cost metrics CSV at {self.cost_csv_file}")
    
    def evaluate_call(self, call_metrics: Dict[str, Any],
                     conversation_data: Optional[Dict[str, Any]] = None) -> LabsCallEvaluation:
        """
        Evaluate a completed call according to Labs Module specification.
        
        Args:
            call_metrics: Call metrics from cost tracker
            conversation_data: Optional conversation transcripts and details
            
        Returns:
            LabsCallEvaluation object with all 8 dimensions
        """
        logger.info(f"Evaluating Labs call: {call_metrics.get('call_id', 'unknown')}")
        
        # Extract basic info
        call_id = call_metrics.get('call_id', 'unknown')
        timestamp = call_metrics.get('end_timestamp', datetime.now().isoformat())
        duration = call_metrics.get('duration_seconds', 0.0)
        total_cost = call_metrics.get('total_cost', 0.0)
        
        # Choose evaluation method
        if self.use_llm and conversation_data:
            evaluation = self._evaluate_with_llm(
                call_id, timestamp, duration, total_cost,
                call_metrics, conversation_data
            )
        else:
            evaluation = self._evaluate_heuristic(
                call_id, timestamp, duration, total_cost,
                call_metrics, conversation_data
            )
        
        logger.info(f"Labs evaluation complete for {call_id}")
        return evaluation
    
    def _evaluate_with_llm(self, call_id: str, timestamp: str, duration: float,
                          total_cost: float, call_metrics: Dict, 
                          conversation_data: Dict) -> LabsCallEvaluation:
        """
        Use LLM to intelligently evaluate the call.
        
        This provides more accurate evaluation by analyzing actual conversation content.
        If transcript is not available, falls back to heuristic with metadata analysis.
        """
        logger.info("Using LLM-based evaluation")
        
        # Build evaluation prompt
        system_prompt = self._get_llm_system_prompt()
        
        # Extract conversation for analysis
        transcript = self._extract_transcript(conversation_data or call_metrics)
        
        # If we don't have a meaningful transcript, fall back to heuristic
        if "not available" in transcript.lower() or "not implemented" in transcript.lower():
            logger.warning("Transcript not available, using LLM with metadata only")
            # Use enhanced heuristic-based evaluation
            return self._evaluate_heuristic(call_id, timestamp, duration, total_cost,
                                           call_metrics, conversation_data)
        
        user_prompt = f"""Analyze this call and provide evaluation:

CALL INFO:
- Call ID: {call_id}
- Duration: {duration:.1f} seconds
- Total turns: {len(call_metrics.get('responses', []))}
- Total cost: ${total_cost:.6f}

TRANSCRIPT:
{transcript}

Provide your evaluation in JSON format with these exact fields:
{{
  "user_sentiment": "positive|neutral|confused|anxious|frustrated",
  "call_summary": "2-3 sentence summary of what happened",
  "query_resolved": true or false,
  "escalation_required": true or false,
  "query_category": "one of: test_kit_info, ordering_purchase, delivery_shipping, kit_registration, sample_collection, fasting_requirements, sample_shipping, results_general, biomarker_explanation, results_interpretation, results_concern, sample_rejection, technical_issue, medical_advice_request, billing_refund, general_inquiry",
  "testing_phase": "one of: pre_purchase, post_order, kit_received, pre_collection, during_collection, post_collection, results_received, unknown",
  "medical_boundary_maintained": true or false,
  "proper_disclaimer_given": true or false or null,
  "notes": "any concerns or observations"
}}
"""
        
        try:
            # Call LLM
            logger.info(f"Sending evaluation request to {self.llm_model}...")
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for consistent evaluation
                max_tokens=1000
            )
            
            # Parse LLM response
            llm_result = self._parse_llm_response(response.choices[0].message.content)
            
            if not llm_result:
                logger.error("Failed to parse LLM response, falling back to heuristic")
                return self._evaluate_heuristic(call_id, timestamp, duration, total_cost,
                                               call_metrics, conversation_data)
            
            logger.info("LLM evaluation successful")
            
            # Extract conversation transcript from call_metrics or conversation_data
            conversation_transcript = self._extract_conversation_transcript(call_metrics, conversation_data)
            
            # Create evaluation from LLM results
            evaluation = LabsCallEvaluation(
                call_id=call_id,
                timestamp=timestamp,
                duration_seconds=duration,
                total_cost=total_cost,
                user_sentiment=UserSentiment(llm_result.get('user_sentiment', 'neutral')),
                call_summary=llm_result.get('call_summary', ''),
                query_resolved=llm_result.get('query_resolved', False),
                escalation_required=llm_result.get('escalation_required', False),
                query_category=QueryCategory(llm_result.get('query_category', 'general_inquiry')),
                testing_phase=TestingPhase(llm_result.get('testing_phase', 'unknown')),
                medical_boundary_maintained=llm_result.get('medical_boundary_maintained', True),
                proper_disclaimer_given=llm_result.get('proper_disclaimer_given'),
                conversation_transcript=conversation_transcript,
                total_turns=len(call_metrics.get('responses', [])),
                avg_latency_ms=call_metrics.get('avg_end_to_end_latency_ms', 0.0),
                evaluation_method="llm",
                notes=llm_result.get('notes', '')
            )
            
            # Check for compliance issues
            self._check_compliance_flags(evaluation)
            
            return evaluation
            
        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}", exc_info=True)
            logger.warning("Falling back to heuristic evaluation")
            return self._evaluate_heuristic(call_id, timestamp, duration, total_cost,
                                           call_metrics, conversation_data)
    
    def _evaluate_heuristic(self, call_id: str, timestamp: str, duration: float,
                           total_cost: float, call_metrics: Dict,
                           conversation_data: Optional[Dict]) -> LabsCallEvaluation:
        """
        Heuristic-based evaluation using call patterns and metrics.
        
        Less accurate than LLM but doesn't require API calls.
        """
        logger.info("Using heuristic-based evaluation")
        
        responses = call_metrics.get('responses', [])
        total_turns = len(responses)
        avg_latency = call_metrics.get('avg_end_to_end_latency_ms', 0.0)
        
        # DIMENSION 1: User Sentiment (heuristic)
        sentiment = self._detect_sentiment_heuristic(duration, total_turns, avg_latency)
        
        # DIMENSION 2: Call Summary
        summary = self._generate_summary_heuristic(duration, total_turns, sentiment)
        
        # DIMENSION 3: Query Resolved
        query_resolved = self._is_query_resolved_heuristic(duration, total_turns)
        
        # DIMENSION 4: Escalation Required
        escalation_required = self._needs_escalation_heuristic(duration, total_turns, sentiment)
        
        # DIMENSION 5: Query Category (heuristic - limited without transcript)
        query_category = self._detect_query_category_heuristic(duration, total_turns)
        
        # DIMENSION 6: Testing Phase (heuristic - limited without transcript)
        testing_phase = self._detect_testing_phase_heuristic(duration, total_turns)
        
        # DIMENSION 7 & 8: Compliance (assume maintained without transcript)
        medical_boundary_maintained = True  # Conservative assumption
        proper_disclaimer_given = None  # Cannot determine without transcript
        
        # Extract conversation transcript
        conversation_transcript = self._extract_conversation_transcript(call_metrics, conversation_data)
        
        evaluation = LabsCallEvaluation(
            call_id=call_id,
            timestamp=timestamp,
            duration_seconds=duration,
            total_cost=total_cost,
            user_sentiment=sentiment,
            call_summary=summary,
            query_resolved=query_resolved,
            escalation_required=escalation_required,
            query_category=query_category,
            testing_phase=testing_phase,
            medical_boundary_maintained=medical_boundary_maintained,
            proper_disclaimer_given=proper_disclaimer_given,
            conversation_transcript=conversation_transcript,
            total_turns=total_turns,
            avg_latency_ms=avg_latency,
            evaluation_method="heuristic",
            notes="Heuristic evaluation - limited accuracy without transcript analysis"
        )
        
        return evaluation
    
    def _detect_sentiment_heuristic(self, duration: float, turns: int,
                                   latency: float) -> UserSentiment:
        """Detect sentiment from call patterns"""
        # High latency may cause confusion (check first before short call check)
        if latency > 5000:
            return UserSentiment.CONFUSED
        
        # Very short calls likely frustrated
        if duration < 30 or turns < 2:
            return UserSentiment.FRUSTRATED
        
        # Long engaged calls likely positive
        if duration > 120 and turns >= 5:
            return UserSentiment.POSITIVE
        
        # Medium-length results-related calls may be anxious
        if 60 <= duration <= 180 and turns >= 3:
            return UserSentiment.ANXIOUS
        
        return UserSentiment.NEUTRAL
    
    def _generate_summary_heuristic(self, duration: float, turns: int,
                                   sentiment: UserSentiment) -> str:
        """Generate call summary from metrics"""
        if turns == 0:
            return "Call ended immediately with no interaction."
        
        if turns < 3:
            return f"Brief {duration:.0f}-second call with {turns} turn(s). User {sentiment.value}. Limited interaction suggests potential issue or quick question."
        
        return f"Call lasted {duration:.0f} seconds with {turns} conversation turns. User appeared {sentiment.value}. {'Engaged discussion indicating active problem-solving.' if turns >= 5 else 'Standard interaction.'}"
    
    def _is_query_resolved_heuristic(self, duration: float, turns: int) -> bool:
        """Determine if query was resolved based on patterns"""
        # Very short calls unlikely resolved
        if duration < 30 or turns < 2:
            return False
        
        # Reasonable engagement suggests resolution
        if duration >= 60 and turns >= 3:
            return True
        
        return False
    
    def _needs_escalation_heuristic(self, duration: float, turns: int,
                                   sentiment: UserSentiment) -> bool:
        """Detect if escalation is needed"""
        # Frustrated users may need escalation
        if sentiment == UserSentiment.FRUSTRATED:
            return True
        
        # Very short calls may indicate unresolved issues
        if duration < 20:
            return True
        
        return False
    
    def _detect_query_category_heuristic(self, duration: float, turns: int) -> QueryCategory:
        """Detect query category from patterns (limited without transcript)"""
        # Without transcript, we can only make educated guesses
        # Default to general inquiry
        return QueryCategory.GENERAL_INQUIRY
    
    def _detect_testing_phase_heuristic(self, duration: float, turns: int) -> TestingPhase:
        """Detect testing phase from patterns (limited without transcript)"""
        # Without transcript, cannot accurately determine phase
        return TestingPhase.UNKNOWN
    
    def _check_compliance_flags(self, evaluation: LabsCallEvaluation):
        """Check for compliance issues and add flags"""
        flags = []
        
        # CRITICAL: Medical boundary violation
        if not evaluation.medical_boundary_maintained:
            flags.append("CRITICAL: Medical boundary violated - agent may have provided diagnosis/advice")
        
        # IMPORTANT: Missing disclaimer
        if evaluation.proper_disclaimer_given is False:
            if evaluation.query_category in [QueryCategory.RESULTS_CONCERN, 
                                            QueryCategory.RESULTS_INTERPRETATION,
                                            QueryCategory.MEDICAL_ADVICE_REQUEST]:
                flags.append("IMPORTANT: Required disclaimer missing for health-related query")
        
        # Escalation should have happened
        if evaluation.query_category == QueryCategory.BILLING_REFUND and not evaluation.escalation_required:
            flags.append("WARNING: Billing issue should always escalate")
        
        if evaluation.query_category == QueryCategory.MEDICAL_ADVICE_REQUEST and not evaluation.escalation_required:
            flags.append("WARNING: Medical advice request should escalate")
        
        evaluation.flags = flags
    
    def _get_llm_system_prompt(self) -> str:
        """Get system prompt for LLM evaluator"""
        return """You are a call quality analyst for Mercola Health Coach's Labs Module voice assistant ("Coach").

Your role is to analyze call transcripts and evaluate 8 dimensions:

CATEGORY 1: Core Metrics
1. user_sentiment: Assess emotional state (positive, neutral, confused, anxious, frustrated)
2. call_summary: Write 2-3 sentences covering what was asked, how AI responded, and outcome
3. query_resolved: TRUE if AI fully answered the question
4. escalation_required: TRUE if human follow-up needed

CATEGORY 2: Domain Metrics
5. query_category: Classify PRIMARY topic from these 16 categories:
   - test_kit_info, ordering_purchase, delivery_shipping
   - kit_registration, sample_collection, fasting_requirements, sample_shipping
   - results_general, biomarker_explanation, results_interpretation, results_concern
   - sample_rejection, technical_issue
   - medical_advice_request, billing_refund, general_inquiry

6. testing_phase: Identify journey phase:
   - pre_purchase (browsing), post_order (waiting delivery), kit_received (needs registration)
   - pre_collection (preparing), during_collection (actively collecting), post_collection (waiting results)
   - results_received (viewing results), unknown

CATEGORY 3: Compliance Metrics
7. medical_boundary_maintained: TRUE if AI avoided medical diagnosis/advice
   ❌ VIOLATIONS: Suggesting conditions, recommending treatments, making health predictions
   ✅ MAINTAINED: Explaining biomarkers, recommending doctor consultation, general wellness info

8. proper_disclaimer_given: TRUE if appropriate disclaimers provided (null if not applicable)
   REQUIRED FOR: Results concerns, red markers, health anxiety, condition questions
   EXPECTED: "I can help understand results, but not provide medical advice", "Consult your healthcare provider"

ESCALATION RULES (Always set escalation_required=TRUE for):
- Billing/refund requests
- "Speak to human" phrases
- Health emergencies ("urgent", "emergency")
- Lost shipments
- Strong frustration

Respond in JSON format with all fields."""
    
    def _extract_transcript(self, conversation_data: Dict) -> str:
        """
        Extract conversation transcript from data.
        
        Builds a formatted transcript from conversation messages.
        """
        if not conversation_data:
            return "No conversation data available. Evaluation based on call metrics only."
        
        # Check if we have actual conversation text
        if 'transcript' in conversation_data:
            return conversation_data['transcript']
        
        if 'messages' in conversation_data:
            transcript_lines = []
            for msg in conversation_data['messages']:
                role = msg.get('role', 'unknown').upper()
                content = msg.get('content', '')
                if content.strip():  # Only include non-empty messages
                    transcript_lines.append(f"{role}: {content}")
            
            if transcript_lines:
                return "\n".join(transcript_lines)
            else:
                return "No conversation messages found."
        
        # Check if conversation_transcript is directly in the data
        if 'conversation_transcript' in conversation_data:
            messages = conversation_data['conversation_transcript']
            if messages and isinstance(messages, list):
                transcript_lines = []
                for msg in messages:
                    role = msg.get('role', 'unknown').upper()
                    content = msg.get('content', '')
                    if content.strip():
                        transcript_lines.append(f"{role}: {content}")
                
                if transcript_lines:
                    return "\n".join(transcript_lines)
        
        # Fallback: construct basic info from responses metadata
        responses = conversation_data.get('responses', [])
        if responses:
            transcript_parts = [
                "Note: Full conversation transcript not available.",
                f"Call had {len(responses)} interactions.",
                "Analysis based on call patterns and metadata only."
            ]
            return "\n".join(transcript_parts)
        
        return "Transcript extraction not available - using heuristic analysis"
    
    def _extract_conversation_transcript(self, call_metrics: Dict, 
                                         conversation_data: Optional[Dict]) -> List[Dict[str, str]]:
        """
        Extract the raw conversation transcript as a list of message objects.
        
        Returns a list of dicts with 'role' and 'content' keys.
        """
        # First check conversation_data (passed explicitly)
        if conversation_data:
            if 'messages' in conversation_data and conversation_data['messages']:
                return conversation_data['messages']
            if 'conversation_transcript' in conversation_data and conversation_data['conversation_transcript']:
                return conversation_data['conversation_transcript']
        
        # Then check call_metrics directly
        if call_metrics:
            if 'conversation_transcript' in call_metrics and call_metrics['conversation_transcript']:
                return call_metrics['conversation_transcript']
        
        # No transcript available
        return []
    
    def _parse_llm_response(self, response_text: str) -> Dict:
        """Parse LLM JSON response"""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {}
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return {}
    
    def save_evaluation(self, evaluation: LabsCallEvaluation, call_metrics: Optional[Dict[str, Any]] = None):
        """
        Save evaluation to CSV and JSON.
        
        Args:
            evaluation: LabsCallEvaluation object to save
            call_metrics: Optional call metrics dict for cost data
        """
        try:
            # Format conversation transcript as JSON string for CSV storage
            transcript_json = json.dumps(evaluation.conversation_transcript) if evaluation.conversation_transcript else ''
            
            # Save to CSV
            with open(self.csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    evaluation.call_id,
                    evaluation.timestamp,
                    f"{evaluation.duration_seconds:.2f}",
                    f"{evaluation.total_cost:.6f}",
                    # Core Metrics
                    evaluation.user_sentiment.value,
                    evaluation.call_summary,
                    evaluation.query_resolved,
                    evaluation.escalation_required,
                    # Domain Metrics
                    evaluation.query_category.value,
                    evaluation.testing_phase.value,
                    # Compliance Metrics
                    evaluation.medical_boundary_maintained,
                    evaluation.proper_disclaimer_given if evaluation.proper_disclaimer_given is not None else '',
                    # Additional
                    evaluation.total_turns,
                    f"{evaluation.avg_latency_ms:.1f}",
                    evaluation.evaluation_method,
                    evaluation.notes,
                    ';'.join(evaluation.flags) if evaluation.flags else '',
                    # Conversation transcript as JSON
                    transcript_json
                ])
            
            logger.info(f"Labs evaluation saved to CSV: {evaluation.call_id}")
            
            # Save detailed JSON
            json_file = self.output_dir / f"{evaluation.call_id}_labs_eval.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                eval_dict = {
                    'call_id': evaluation.call_id,
                    'timestamp': evaluation.timestamp,
                    'duration_seconds': evaluation.duration_seconds,
                    'total_cost': evaluation.total_cost,
                    'core_metrics': {
                        'user_sentiment': evaluation.user_sentiment.value,
                        'call_summary': evaluation.call_summary,
                        'query_resolved': evaluation.query_resolved,
                        'escalation_required': evaluation.escalation_required,
                    },
                    'domain_metrics': {
                        'query_category': evaluation.query_category.value,
                        'testing_phase': evaluation.testing_phase.value,
                    },
                    'compliance_metrics': {
                        'medical_boundary_maintained': evaluation.medical_boundary_maintained,
                        'proper_disclaimer_given': evaluation.proper_disclaimer_given,
                    },
                    'conversation_transcript': evaluation.conversation_transcript,
                    'additional_info': {
                        'total_turns': evaluation.total_turns,
                        'avg_latency_ms': evaluation.avg_latency_ms,
                        'evaluation_method': evaluation.evaluation_method,
                        'evaluation_version': evaluation.evaluation_version,
                    },
                    'notes': evaluation.notes,
                    'flags': evaluation.flags,
                }
                json.dump(eval_dict, f, indent=2)
            
            logger.info(f"Detailed Labs evaluation saved to JSON: {json_file}")
            
            # Save cost metrics to separate CSV (if call_metrics provided)
            if call_metrics:
                self._save_cost_metrics(evaluation.call_id, evaluation.timestamp, call_metrics)
            
            # Log compliance flags if any
            if evaluation.flags:
                logger.warning(f"COMPLIANCE FLAGS for {evaluation.call_id}:")
                for flag in evaluation.flags:
                    logger.warning(f"  - {flag}")
            
        except Exception as e:
            logger.error(f"Error saving Labs evaluation: {e}", exc_info=True)
            raise
    
    def _save_cost_metrics(self, call_id: str, timestamp: str, call_metrics: Dict[str, Any]):
        """
        Save cost metrics to separate CSV file.
        
        Args:
            call_id: Call identifier
            timestamp: Call timestamp
            call_metrics: Call metrics dictionary with cost data
        """
        try:
            with open(self.cost_csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    call_id,
                    timestamp,
                    f"{call_metrics.get('duration_seconds', 0.0):.2f}",
                    # Cost breakdown
                    f"{call_metrics.get('total_cost', 0.0):.6f}",
                    f"{call_metrics.get('total_stt_cost', 0.0):.6f}",
                    f"{call_metrics.get('total_llm_cost', 0.0):.6f}",
                    f"{call_metrics.get('total_tts_cost', 0.0):.6f}",
                    f"{call_metrics.get('total_livekit_cost', 0.0):.6f}",
                    # Usage metrics
                    f"{call_metrics.get('total_stt_duration', 0.0):.2f}",
                    call_metrics.get('total_llm_input_tokens', 0),
                    call_metrics.get('total_llm_output_tokens', 0),
                    call_metrics.get('total_tts_characters', 0),
                    # Latency metrics (Time to First Token)
                    f"{call_metrics.get('avg_eou_delay_ms', 0.0):.2f}",
                    f"{call_metrics.get('avg_llm_ttft_ms', 0.0):.2f}",
                    f"{call_metrics.get('avg_tts_ttfb_ms', 0.0):.2f}",
                    f"{call_metrics.get('avg_ttft_ms', 0.0):.2f}"
                ])
            logger.info(f"Cost metrics saved to CSV: {call_id}")
        except Exception as e:
            logger.error(f"Error saving cost metrics: {e}", exc_info=True)
    
    def evaluate_from_file(self, metrics_file: str) -> LabsCallEvaluation:
        """
        Load metrics from file and evaluate.
        
        Args:
            metrics_file: Path to JSON metrics file
            
        Returns:
            LabsCallEvaluation object
        """
        try:
            with open(metrics_file, 'r', encoding='utf-8') as f:
                call_metrics = json.load(f)
            
            evaluation = self.evaluate_call(call_metrics)
            self.save_evaluation(evaluation, call_metrics)
            
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
        
        logger.info(f"Found {len(json_files)} metrics files for Labs evaluation")
        
        evaluations = []
        for json_file in json_files:
            try:
                # Skip evaluation files themselves
                if '_eval.json' in json_file.name or '_labs_eval.json' in json_file.name:
                    continue
                
                logger.info(f"Evaluating {json_file.name}")
                evaluation = self.evaluate_from_file(str(json_file))
                evaluations.append(evaluation)
                
            except Exception as e:
                logger.error(f"Error evaluating {json_file}: {e}")
                continue
        
        logger.info(f"Labs batch evaluation complete: {len(evaluations)} calls evaluated")
        return evaluations
    
    def get_compliance_report(self) -> Dict[str, Any]:
        """
        Generate compliance report from all evaluations.
        
        Returns critical metrics for regulatory monitoring.
        """
        if not self.csv_file.exists():
            return {}
        
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            if not rows:
                return {}
            
            total_calls = len(rows)
            
            # Medical boundary violations (CRITICAL)
            boundary_violations = sum(
                1 for r in rows 
                if r['medical_boundary_maintained'].lower() == 'false'
            )
            
            # Missing disclaimers on results calls
            results_calls = [
                r for r in rows 
                if r['query_category'] in [
                    'results_concern', 'results_interpretation', 
                    'biomarker_explanation', 'medical_advice_request'
                ]
            ]
            missing_disclaimers = sum(
                1 for r in results_calls
                if r['proper_disclaimer_given'].lower() == 'false'
            )
            
            # Escalation metrics
            escalated = sum(1 for r in rows if r['escalation_required'].lower() == 'true')
            billing_issues = sum(1 for r in rows if r['query_category'] == 'billing_refund')
            billing_escalated = sum(
                1 for r in rows 
                if r['query_category'] == 'billing_refund' 
                and r['escalation_required'].lower() == 'true'
            )
            
            # Resolution rate
            resolved = sum(1 for r in rows if r['query_resolved'].lower() == 'true')
            
            # Sentiment distribution
            sentiment_counts = {}
            for r in rows:
                sentiment = r['user_sentiment']
                sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
            
            # Anxious calls (health-related anxiety)
            anxious_calls = sentiment_counts.get('anxious', 0)
            
            report = {
                'total_calls': total_calls,
                'compliance': {
                    'medical_boundary_violations': boundary_violations,
                    'boundary_violation_rate': (boundary_violations / total_calls * 100) if total_calls > 0 else 0,
                    'missing_disclaimers': missing_disclaimers,
                    'missing_disclaimer_rate': (missing_disclaimers / len(results_calls) * 100) if results_calls else 0,
                    'compliance_rate': ((total_calls - boundary_violations) / total_calls * 100) if total_calls > 0 else 0,
                },
                'kpis': {
                    'resolution_rate': (resolved / total_calls * 100) if total_calls > 0 else 0,
                    'escalation_rate': (escalated / total_calls * 100) if total_calls > 0 else 0,
                    'billing_escalation_rate': (billing_escalated / billing_issues * 100) if billing_issues > 0 else 100,
                    'anxiety_detection_rate': (anxious_calls / total_calls * 100) if total_calls > 0 else 0,
                },
                'sentiment_distribution': sentiment_counts,
                'targets': {
                    'resolution_rate_target': 80,  # >80%
                    'escalation_rate_target': 15,  # <15%
                    'medical_compliance_target': 100,  # 100%
                    'user_satisfaction_target': 70,  # >70%
                },
                'alerts': self._generate_alerts(
                    boundary_violations, missing_disclaimers,
                    len(results_calls), escalated, total_calls
                )
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating compliance report: {e}")
            return {}
    
    def _generate_alerts(self, violations: int, missing_disclaimers: int,
                        results_calls: int, escalated: int, total: int) -> List[str]:
        """Generate compliance alerts"""
        alerts = []
        
        # CRITICAL: Medical boundary violations
        if violations > 0:
            alerts.append(f"CRITICAL: {violations} medical boundary violation(s) detected - IMMEDIATE REVIEW REQUIRED")
        
        # Missing disclaimers
        if missing_disclaimers > 0:
            rate = (missing_disclaimers / results_calls * 100) if results_calls > 0 else 0
            if rate > 5:
                alerts.append(f"WARNING: {missing_disclaimers} missing disclaimers ({rate:.1f}%) exceeds 5% threshold")
        
        # Escalation rate
        escalation_rate = (escalated / total * 100) if total > 0 else 0
        if escalation_rate > 15:
            alerts.append(f"WARNING: Escalation rate ({escalation_rate:.1f}%) exceeds 15% target")
        
        if not alerts:
            alerts.append("SUCCESS: All compliance metrics within acceptable ranges")
        
        return alerts


def evaluate_labs_call_automatically(call_metrics: Dict[str, Any],
                                    conversation_data: Optional[Dict] = None,
                                    evaluator: Optional[LabsCallEvaluator] = None,
                                    use_llm: bool = False) -> LabsCallEvaluation:
    """
    Convenience function to evaluate a Labs call automatically.
    
    This is the main entry point for automatic evaluation when a call ends.
    
    Args:
        call_metrics: Call metrics dictionary from cost tracker
        conversation_data: Optional conversation transcripts
        evaluator: Optional existing evaluator instance
        use_llm: Whether to use LLM evaluation
        
    Returns:
        LabsCallEvaluation object
    """
    if evaluator is None:
        evaluator = LabsCallEvaluator(use_llm=use_llm)
    
    evaluation = evaluator.evaluate_call(call_metrics, conversation_data)
    evaluator.save_evaluation(evaluation, call_metrics)
    
    return evaluation


if __name__ == "__main__":
    # CLI for batch evaluation
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    use_llm = "--llm" in sys.argv
    
    if len(sys.argv) > 1 and sys.argv[1] != "--llm":
        metrics_dir = sys.argv[1]
    else:
        metrics_dir = os.path.join(os.path.dirname(__file__), "metrics")
    
    print(f"Evaluating Labs metrics from: {metrics_dir}")
    if use_llm:
        print("Using LLM-based evaluation (requires GROQ_API_KEY)")
    else:
        print("Using heuristic evaluation")
    
    evaluator = LabsCallEvaluator(use_llm=use_llm)
    evaluator.batch_evaluate(metrics_dir)
    
    # Generate compliance report
    print("\n" + "=" * 80)
    print("LABS MODULE COMPLIANCE REPORT")
    print("=" * 80)
    
    report = evaluator.get_compliance_report()
    
    if report:
        print(f"\nTotal Calls Evaluated: {report['total_calls']}")
        
        print("\nCOMPLIANCE METRICS:")
        comp = report['compliance']
        print(f"  Medical Boundary Violations: {comp['medical_boundary_violations']}")
        print(f"  Compliance Rate: {comp['compliance_rate']:.1f}% (Target: 100%)")
        print(f"  Missing Disclaimers: {comp['missing_disclaimers']}")
        print(f"  Disclaimer Rate: {100 - comp['missing_disclaimer_rate']:.1f}%")
        
        print("\nKEY PERFORMANCE INDICATORS:")
        kpis = report['kpis']
        print(f"  Resolution Rate: {kpis['resolution_rate']:.1f}% (Target: >80%)")
        print(f"  Escalation Rate: {kpis['escalation_rate']:.1f}% (Target: <15%)")
        print(f"  Anxiety Detection: {kpis['anxiety_detection_rate']:.1f}%")
        
        print("\nSENTIMENT DISTRIBUTION:")
        for sentiment, count in report['sentiment_distribution'].items():
            pct = (count / report['total_calls'] * 100)
            print(f"  {sentiment}: {count} ({pct:.1f}%)")
        
        print("\nALERTS:")
        for alert in report['alerts']:
            print(f"  {alert}")
        
        print("=" * 80)
