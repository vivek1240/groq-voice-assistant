"""
Cost and Latency Tracking System for Groq Voice Assistant

This module tracks:
1. Cost metrics for STT, LLM, TTS, and VAPI platform usage
2. Latency metrics for end-to-end performance monitoring
3. Per-response and per-call summaries
"""

import time
import json
import logging
import os
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

logger = logging.getLogger("cost-tracker")


class ComponentType(Enum):
    """Types of components being tracked"""
    STT = "speech_to_text"
    LLM = "large_language_model"
    TTS = "text_to_speech"
    VAPI = "voice_platform"


# ============================================================================
# PRICING CONFIGURATION
# ============================================================================
# Update these values based on actual Groq pricing

def load_pricing_config():
    """Load pricing from config file if available, otherwise use defaults"""
    config_file = os.path.join(os.path.dirname(__file__), "pricing_config.json")
    
    # Default pricing
    default_pricing = {
        "stt": {
            "whisper-large-v3-turbo": 0.02,
            "whisper-large-v3": 0.025,
        },
        "llm": {
            "llama-3.3-70b-versatile": {
                "input": 0.00059,
                "output": 0.00079,
            },
            "llama-3.1-8b-instant": {
                "input": 0.00005,
                "output": 0.00008,
            },
            "mixtral-8x7b-32768": {
                "input": 0.00024,
                "output": 0.00024,
            },
        },
        "tts": {
            "canopylabs/orpheus-v1-english": 0.000010,
            "playai-tts": 0.000010,
        },
        "vapi": {
            "platform_per_minute": 0.05,
        }
    }
    
    # Try to load from config file
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                pricing_data = config.get("pricing", {})
                
                # Convert config format to internal format
                pricing = {
                    "stt": {},
                    "llm": {},
                    "tts": {},
                    "vapi": {}
                }
                
                # STT pricing
                for model, data in pricing_data.get("stt", {}).items():
                    pricing["stt"][model] = data.get("price_per_minute", default_pricing["stt"].get(model, 0.02))
                
                # LLM pricing
                for model, data in pricing_data.get("llm", {}).items():
                    pricing["llm"][model] = {
                        "input": data.get("input_price_per_1k", 0.0),
                        "output": data.get("output_price_per_1k", 0.0),
                    }
                
                # TTS pricing
                for model, data in pricing_data.get("tts", {}).items():
                    pricing["tts"][model] = data.get("price_per_character", default_pricing["tts"].get(model, 0.00001))
                
                # VAPI pricing
                vapi_data = pricing_data.get("vapi", {}).get("platform_cost", {})
                pricing["vapi"]["platform_per_minute"] = vapi_data.get("price_per_minute", 0.05)
                
                logger.info(f"Loaded pricing config from {config_file}")
                return pricing
    except Exception as e:
        logger.warning(f"Could not load pricing config: {e}, using defaults")
    
    return default_pricing

PRICING = load_pricing_config()


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class LatencyMetrics:
    """Latency tracking for a single operation"""
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    
    def start(self):
        """Mark the start of an operation"""
        self.start_time = time.time()
    
    def end(self):
        """Mark the end of an operation and calculate duration"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        return self.duration_ms


@dataclass
class STTMetrics:
    """Speech-to-Text metrics"""
    model: str = ""
    duration_seconds: float = 0.0
    cost: float = 0.0
    latency_ms: float = 0.0
    transcript_length: int = 0
    timestamp: str = ""
    
    def calculate_cost(self):
        """Calculate cost based on duration"""
        duration_minutes = self.duration_seconds / 60.0
        price_per_minute = PRICING["stt"].get(self.model, 0.02)
        self.cost = duration_minutes * price_per_minute
        return self.cost


@dataclass
class LLMMetrics:
    """Large Language Model metrics"""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    input_cost: float = 0.0
    output_cost: float = 0.0
    total_cost: float = 0.0
    latency_ms: float = 0.0  # Time to first token
    total_generation_time_ms: float = 0.0
    timestamp: str = ""
    
    def calculate_cost(self):
        """Calculate cost based on token usage"""
        pricing = PRICING["llm"].get(self.model, {"input": 0.0, "output": 0.0})
        self.input_cost = (self.input_tokens / 1000.0) * pricing["input"]
        self.output_cost = (self.output_tokens / 1000.0) * pricing["output"]
        self.total_cost = self.input_cost + self.output_cost
        self.total_tokens = self.input_tokens + self.output_tokens
        return self.total_cost


@dataclass
class TTSMetrics:
    """Text-to-Speech metrics"""
    model: str = ""
    characters_processed: int = 0
    cost: float = 0.0
    latency_ms: float = 0.0
    audio_duration_seconds: float = 0.0
    timestamp: str = ""
    
    def calculate_cost(self):
        """Calculate cost based on character count"""
        price_per_char = PRICING["tts"].get(self.model, 0.000010)
        self.cost = self.characters_processed * price_per_char
        return self.cost


@dataclass
class VAPIMetrics:
    """Voice Platform (VAPI/LiveKit) metrics"""
    connection_duration_seconds: float = 0.0
    cost: float = 0.0
    timestamp: str = ""
    
    def calculate_cost(self):
        """Calculate cost based on connection duration"""
        duration_minutes = self.connection_duration_seconds / 60.0
        price_per_minute = PRICING["vapi"]["platform_per_minute"]
        self.cost = duration_minutes * price_per_minute
        return self.cost


@dataclass
class ResponseMetrics:
    """Metrics for a single response (user speaks -> agent responds)"""
    response_id: str = ""
    timestamp: str = ""
    
    # Component metrics
    stt: Optional[STTMetrics] = None
    llm: Optional[LLMMetrics] = None
    tts: Optional[TTSMetrics] = None
    
    # End-to-end latency
    end_to_end_latency_ms: float = 0.0
    
    # Costs
    total_cost: float = 0.0
    
    def calculate_total_cost(self):
        """Calculate total cost for this response"""
        self.total_cost = 0.0
        if self.stt:
            self.total_cost += self.stt.cost
        if self.llm:
            self.total_cost += self.llm.total_cost
        if self.tts:
            self.total_cost += self.tts.cost
        return self.total_cost


@dataclass
class CallMetrics:
    """Metrics for an entire call session"""
    call_id: str = ""
    start_timestamp: str = ""
    end_timestamp: str = ""
    duration_seconds: float = 0.0
    
    # Response tracking
    responses: List[ResponseMetrics] = field(default_factory=list)
    
    # Aggregated metrics
    total_stt_cost: float = 0.0
    total_llm_cost: float = 0.0
    total_tts_cost: float = 0.0
    total_vapi_cost: float = 0.0
    total_cost: float = 0.0
    
    # Aggregated usage
    total_stt_duration: float = 0.0
    total_llm_input_tokens: int = 0
    total_llm_output_tokens: int = 0
    total_tts_characters: int = 0
    
    # Latency statistics
    avg_stt_latency_ms: float = 0.0
    avg_llm_latency_ms: float = 0.0
    avg_tts_latency_ms: float = 0.0
    avg_end_to_end_latency_ms: float = 0.0
    
    # VAPI metrics
    vapi: Optional[VAPIMetrics] = None
    
    def add_response(self, response: ResponseMetrics):
        """Add a response to this call"""
        self.responses.append(response)
    
    def calculate_totals(self):
        """Calculate all aggregate metrics"""
        # Reset totals
        self.total_stt_cost = 0.0
        self.total_llm_cost = 0.0
        self.total_tts_cost = 0.0
        self.total_vapi_cost = 0.0
        
        self.total_stt_duration = 0.0
        self.total_llm_input_tokens = 0
        self.total_llm_output_tokens = 0
        self.total_tts_characters = 0
        
        stt_latencies = []
        llm_latencies = []
        tts_latencies = []
        e2e_latencies = []
        
        # Aggregate from all responses
        for response in self.responses:
            if response.stt:
                self.total_stt_cost += response.stt.cost
                self.total_stt_duration += response.stt.duration_seconds
                stt_latencies.append(response.stt.latency_ms)
            
            if response.llm:
                self.total_llm_cost += response.llm.total_cost
                self.total_llm_input_tokens += response.llm.input_tokens
                self.total_llm_output_tokens += response.llm.output_tokens
                llm_latencies.append(response.llm.latency_ms)
            
            if response.tts:
                self.total_tts_cost += response.tts.cost
                self.total_tts_characters += response.tts.characters_processed
                tts_latencies.append(response.tts.latency_ms)
            
            if response.end_to_end_latency_ms > 0:
                e2e_latencies.append(response.end_to_end_latency_ms)
        
        # Calculate VAPI cost
        if self.vapi:
            self.total_vapi_cost = self.vapi.cost
        
        # Calculate total cost
        self.total_cost = (
            self.total_stt_cost +
            self.total_llm_cost +
            self.total_tts_cost +
            self.total_vapi_cost
        )
        
        # Calculate average latencies
        self.avg_stt_latency_ms = sum(stt_latencies) / len(stt_latencies) if stt_latencies else 0.0
        self.avg_llm_latency_ms = sum(llm_latencies) / len(llm_latencies) if llm_latencies else 0.0
        self.avg_tts_latency_ms = sum(tts_latencies) / len(tts_latencies) if tts_latencies else 0.0
        self.avg_end_to_end_latency_ms = sum(e2e_latencies) / len(e2e_latencies) if e2e_latencies else 0.0


# ============================================================================
# COST TRACKER CLASS
# ============================================================================

class CostTracker:
    """
    Main cost and latency tracking system.
    
    Usage:
        tracker = CostTracker(call_id="call_123")
        
        # Track a complete response
        response_id = tracker.start_response()
        
        # Track STT
        tracker.start_stt()
        # ... STT processing ...
        tracker.end_stt(duration=5.2, transcript="Hello", model="whisper-large-v3-turbo")
        
        # Track LLM
        tracker.start_llm()
        # ... LLM processing ...
        tracker.end_llm(input_tokens=100, output_tokens=50, model="llama-3.3-70b-versatile")
        
        # Track TTS
        tracker.start_tts()
        # ... TTS processing ...
        tracker.end_tts(characters=200, model="canopylabs/orpheus-v1-english")
        
        tracker.end_response()
        
        # At end of call
        tracker.end_call()
        summary = tracker.get_call_summary()
    """
    
    def __init__(self, call_id: str):
        self.call_id = call_id
        self.call_metrics = CallMetrics(
            call_id=call_id,
            start_timestamp=datetime.now().isoformat()
        )
        self.call_start_time = time.time()
        
        # Current response tracking
        self.current_response: Optional[ResponseMetrics] = None
        self.current_response_start_time: float = 0.0
        
        # Component latency trackers
        self.stt_latency = LatencyMetrics()
        self.llm_latency = LatencyMetrics()
        self.tts_latency = LatencyMetrics()
        
        self.response_counter = 0
        
        logger.info(f"CostTracker initialized for call: {call_id}")
    
    # ========================================================================
    # RESPONSE TRACKING
    # ========================================================================
    
    def start_response(self) -> str:
        """Start tracking a new response"""
        self.response_counter += 1
        response_id = f"{self.call_id}_response_{self.response_counter}"
        
        self.current_response = ResponseMetrics(
            response_id=response_id,
            timestamp=datetime.now().isoformat()
        )
        self.current_response_start_time = time.time()
        
        logger.debug(f"Started tracking response: {response_id}")
        return response_id
    
    def end_response(self):
        """End tracking current response and calculate metrics"""
        if not self.current_response:
            logger.warning("end_response called but no response in progress")
            return
        
        # Calculate end-to-end latency
        if self.current_response_start_time > 0:
            end_time = time.time()
            self.current_response.end_to_end_latency_ms = (
                (end_time - self.current_response_start_time) * 1000
            )
        
        # Calculate total cost for this response
        self.current_response.calculate_total_cost()
        
        # Add to call metrics
        self.call_metrics.add_response(self.current_response)
        
        # Log response summary
        self._log_response_summary(self.current_response)
        
        # Reset current response
        self.current_response = None
        self.current_response_start_time = 0.0
    
    # ========================================================================
    # STT TRACKING
    # ========================================================================
    
    def start_stt(self):
        """Start tracking STT latency"""
        self.stt_latency.start()
        logger.debug("STT tracking started")
    
    def end_stt(self, duration: float, transcript: str, model: str):
        """
        End STT tracking and record metrics
        
        Args:
            duration: Duration of audio in seconds
            transcript: Transcribed text
            model: STT model used
        """
        latency = self.stt_latency.end()
        
        if not self.current_response:
            self.start_response()
        
        stt_metrics = STTMetrics(
            model=model,
            duration_seconds=duration,
            latency_ms=latency,
            transcript_length=len(transcript),
            timestamp=datetime.now().isoformat()
        )
        stt_metrics.calculate_cost()
        
        self.current_response.stt = stt_metrics
        
        logger.debug(
            f"STT completed: duration={duration:.2f}s, latency={latency:.0f}ms, "
            f"cost=${stt_metrics.cost:.6f}, model={model}"
        )
    
    # ========================================================================
    # LLM TRACKING
    # ========================================================================
    
    def start_llm(self):
        """Start tracking LLM latency"""
        self.llm_latency.start()
        logger.debug("LLM tracking started")
    
    def end_llm(self, input_tokens: int, output_tokens: int, model: str):
        """
        End LLM tracking and record metrics
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: LLM model used
        """
        latency = self.llm_latency.end()
        
        if not self.current_response:
            self.start_response()
        
        llm_metrics = LLMMetrics(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency,
            timestamp=datetime.now().isoformat()
        )
        llm_metrics.calculate_cost()
        
        self.current_response.llm = llm_metrics
        
        logger.debug(
            f"LLM completed: in={input_tokens} out={output_tokens} tokens, "
            f"latency={latency:.0f}ms, cost=${llm_metrics.total_cost:.6f}, model={model}"
        )
    
    # ========================================================================
    # TTS TRACKING
    # ========================================================================
    
    def start_tts(self):
        """Start tracking TTS latency"""
        self.tts_latency.start()
        logger.debug("TTS tracking started")
    
    def end_tts(self, characters: int, model: str, audio_duration: float = 0.0):
        """
        End TTS tracking and record metrics
        
        Args:
            characters: Number of characters processed
            model: TTS model used
            audio_duration: Duration of generated audio in seconds
        """
        latency = self.tts_latency.end()
        
        if not self.current_response:
            self.start_response()
        
        tts_metrics = TTSMetrics(
            model=model,
            characters_processed=characters,
            latency_ms=latency,
            audio_duration_seconds=audio_duration,
            timestamp=datetime.now().isoformat()
        )
        tts_metrics.calculate_cost()
        
        self.current_response.tts = tts_metrics
        
        logger.debug(
            f"TTS completed: chars={characters}, latency={latency:.0f}ms, "
            f"cost=${tts_metrics.cost:.6f}, model={model}"
        )
    
    # ========================================================================
    # CALL TRACKING
    # ========================================================================
    
    def end_call(self):
        """End call tracking and calculate final metrics"""
        call_end_time = time.time()
        self.call_metrics.duration_seconds = call_end_time - self.call_start_time
        self.call_metrics.end_timestamp = datetime.now().isoformat()
        
        # Calculate VAPI cost
        vapi_metrics = VAPIMetrics(
            connection_duration_seconds=self.call_metrics.duration_seconds,
            timestamp=datetime.now().isoformat()
        )
        vapi_metrics.calculate_cost()
        self.call_metrics.vapi = vapi_metrics
        
        # Calculate all totals
        self.call_metrics.calculate_totals()
        
        # Log call summary
        self._log_call_summary()
        
        logger.info(f"Call ended: {self.call_id}, total cost: ${self.call_metrics.total_cost:.6f}")
    
    # ========================================================================
    # SUMMARY METHODS
    # ========================================================================
    
    def get_call_summary(self) -> Dict[str, Any]:
        """Get complete call summary as dictionary"""
        return asdict(self.call_metrics)
    
    def get_call_summary_json(self) -> str:
        """Get complete call summary as JSON string"""
        return json.dumps(self.get_call_summary(), indent=2)
    
    def _log_response_summary(self, response: ResponseMetrics):
        """Log a formatted response summary"""
        logger.info("=" * 80)
        logger.info(f"RESPONSE SUMMARY: {response.response_id}")
        logger.info("=" * 80)
        
        if response.stt:
            logger.info(
                f"  STT: {response.stt.duration_seconds:.2f}s audio, "
                f"{response.stt.latency_ms:.0f}ms latency, "
                f"${response.stt.cost:.6f}"
            )
        
        if response.llm:
            logger.info(
                f"  LLM: {response.llm.input_tokens} in / {response.llm.output_tokens} out tokens, "
                f"{response.llm.latency_ms:.0f}ms latency, "
                f"${response.llm.total_cost:.6f}"
            )
        
        if response.tts:
            logger.info(
                f"  TTS: {response.tts.characters_processed} chars, "
                f"{response.tts.latency_ms:.0f}ms latency, "
                f"${response.tts.cost:.6f}"
            )
        
        logger.info(f"  End-to-End: {response.end_to_end_latency_ms:.0f}ms")
        logger.info(f"  Total Cost: ${response.total_cost:.6f}")
        logger.info("=" * 80)
    
    def _log_call_summary(self):
        """Log a formatted call summary"""
        logger.info("\n" + "=" * 80)
        logger.info(f"CALL SUMMARY: {self.call_id}")
        logger.info("=" * 80)
        
        logger.info(f"Duration: {self.call_metrics.duration_seconds:.1f}s")
        logger.info(f"Total Responses: {len(self.call_metrics.responses)}")
        logger.info("")
        
        logger.info("USAGE:")
        logger.info(f"  STT: {self.call_metrics.total_stt_duration:.2f}s audio")
        logger.info(
            f"  LLM: {self.call_metrics.total_llm_input_tokens} input tokens, "
            f"{self.call_metrics.total_llm_output_tokens} output tokens"
        )
        logger.info(f"  TTS: {self.call_metrics.total_tts_characters} characters")
        logger.info("")
        
        logger.info("COSTS:")
        logger.info(f"  STT:  ${self.call_metrics.total_stt_cost:.6f}")
        logger.info(f"  LLM:  ${self.call_metrics.total_llm_cost:.6f}")
        logger.info(f"  TTS:  ${self.call_metrics.total_tts_cost:.6f}")
        logger.info(f"  VAPI: ${self.call_metrics.total_vapi_cost:.6f}")
        logger.info(f"  --------------")
        logger.info(f"  TOTAL: ${self.call_metrics.total_cost:.6f}")
        logger.info("")
        
        logger.info("AVERAGE LATENCIES:")
        logger.info(f"  STT: {self.call_metrics.avg_stt_latency_ms:.0f}ms")
        logger.info(f"  LLM: {self.call_metrics.avg_llm_latency_ms:.0f}ms")
        logger.info(f"  TTS: {self.call_metrics.avg_tts_latency_ms:.0f}ms")
        logger.info(f"  End-to-End: {self.call_metrics.avg_end_to_end_latency_ms:.0f}ms")
        logger.info("=" * 80 + "\n")
    
    # ========================================================================
    # EXPORT METHODS
    # ========================================================================
    
    def export_to_file(self, filepath: str):
        """Export call metrics to JSON file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.get_call_summary(), f, indent=2)
            logger.info(f"Call metrics exported to: {filepath}")
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
