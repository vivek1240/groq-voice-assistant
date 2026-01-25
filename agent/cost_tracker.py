"""
Cost and Latency Tracking System for Groq Voice Assistant

This module tracks:
1. Cost metrics for STT, LLM, TTS, and LiveKit platform usage
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
    LIVEKIT = "livekit_platform"


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
        "livekit": {
            "platform_per_minute": 0.01,  # LiveKit Cloud: $0.01 per agent session minute
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
                    "livekit": {}
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
                
                # LiveKit pricing
                livekit_data = pricing_data.get("livekit", {}).get("platform_cost", {})
                pricing["livekit"]["platform_per_minute"] = livekit_data.get("price_per_minute", 0.05)
                
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
        if self.start_time <= 0:
            # Guard against missing start() calls to avoid epoch-scale latencies
            logger.warning("LatencyMetrics.end called without start(); returning 0ms")
            self.duration_ms = 0.0
            return self.duration_ms

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
    transcript: str = ""  # Actual transcribed text
    
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
    latency_ms: float = 0.0  # Total latency (legacy)
    ttft_ms: float = 0.0  # Time to First Token - key metric!
    total_generation_time_ms: float = 0.0
    timestamp: str = ""
    response_text: str = ""  # Actual LLM response text
    
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
    ttfb_ms: float = 0.0  # Time to First Byte - key metric!
    latency_ms: float = 0.0
    audio_duration_seconds: float = 0.0
    timestamp: str = ""
    
    def calculate_cost(self):
        """Calculate cost based on character count"""
        price_per_char = PRICING["tts"].get(self.model, 0.000010)
        self.cost = self.characters_processed * price_per_char
        return self.cost


@dataclass
class LiveKitMetrics:
    """Voice Platform (LiveKit) metrics"""
    connection_duration_seconds: float = 0.0
    cost: float = 0.0
    timestamp: str = ""
    
    def calculate_cost(self):
        """Calculate cost based on connection duration"""
        duration_minutes = self.connection_duration_seconds / 60.0
        price_per_minute = PRICING["livekit"]["platform_per_minute"]
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
    
    # Key latency metrics
    eou_delay_ms: float = 0.0  # End-of-Utterance delay (VAD + transcription)
    ttft_ms: float = 0.0  # Time to First Token = EOU + LLM TTFT + TTS TTFB
    
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
    
    # Conversation transcript (for LLM evaluation)
    conversation_transcript: List[Dict[str, str]] = field(default_factory=list)
    
    # Aggregated metrics
    total_stt_cost: float = 0.0
    total_llm_cost: float = 0.0
    total_tts_cost: float = 0.0
    total_livekit_cost: float = 0.0
    total_cost: float = 0.0
    
    # Aggregated usage
    total_stt_duration: float = 0.0
    total_llm_input_tokens: int = 0
    total_llm_output_tokens: int = 0
    total_tts_characters: int = 0
    
    # Latency statistics (Time to First Token metrics)
    avg_eou_delay_ms: float = 0.0  # Average End-of-Utterance delay (VAD + transcription)
    avg_llm_ttft_ms: float = 0.0  # Average LLM Time to First Token
    avg_tts_ttfb_ms: float = 0.0  # Average TTS Time to First Byte
    avg_ttft_ms: float = 0.0  # Average overall TTFT = EOU + LLM TTFT + TTS TTFB
    
    # LiveKit metrics
    livekit: Optional[LiveKitMetrics] = None
    
    def add_response(self, response: ResponseMetrics):
        """Add a response to this call"""
        self.responses.append(response)
    
    def calculate_totals(self):
        """Calculate all aggregate metrics"""
        # Reset totals
        self.total_stt_cost = 0.0
        self.total_llm_cost = 0.0
        self.total_tts_cost = 0.0
        self.total_livekit_cost = 0.0
        
        self.total_stt_duration = 0.0
        self.total_llm_input_tokens = 0
        self.total_llm_output_tokens = 0
        self.total_tts_characters = 0
        
        eou_delay_list = []
        llm_ttft_list = []
        tts_ttfb_list = []
        ttft_list = []
        
        # Aggregate from all responses
        for response in self.responses:
            if response.stt:
                self.total_stt_cost += response.stt.cost
                self.total_stt_duration += response.stt.duration_seconds
            
            if response.llm:
                self.total_llm_cost += response.llm.total_cost
                self.total_llm_input_tokens += response.llm.input_tokens
                self.total_llm_output_tokens += response.llm.output_tokens
                if response.llm.ttft_ms > 0:
                    llm_ttft_list.append(response.llm.ttft_ms)
            
            if response.tts:
                self.total_tts_cost += response.tts.cost
                self.total_tts_characters += response.tts.characters_processed
                if response.tts.ttfb_ms > 0:
                    tts_ttfb_list.append(response.tts.ttfb_ms)
            
            if response.eou_delay_ms > 0:
                eou_delay_list.append(response.eou_delay_ms)
            
            if response.ttft_ms > 0:
                ttft_list.append(response.ttft_ms)
        
        # Calculate LiveKit cost
        if self.livekit:
            self.total_livekit_cost = self.livekit.cost
        
        # Calculate total cost
        self.total_cost = (
            self.total_stt_cost +
            self.total_llm_cost +
            self.total_tts_cost +
            self.total_livekit_cost
        )
        
        # Calculate average latencies (Time to First Token metrics)
        self.avg_eou_delay_ms = sum(eou_delay_list) / len(eou_delay_list) if eou_delay_list else 0.0
        self.avg_llm_ttft_ms = sum(llm_ttft_list) / len(llm_ttft_list) if llm_ttft_list else 0.0
        self.avg_tts_ttfb_ms = sum(tts_ttfb_list) / len(tts_ttfb_list) if tts_ttfb_list else 0.0
        self.avg_ttft_ms = sum(ttft_list) / len(ttft_list) if ttft_list else 0.0


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
    
    def end_response(self, eou_delay_ms: float = 0.0):
        """End tracking current response and calculate metrics"""
        if not self.current_response:
            logger.warning("end_response called but no response in progress")
            return
        
        # Store EOU delay
        self.current_response.eou_delay_ms = eou_delay_ms
        
        # Calculate TTFT (Time to First Token/Byte)
        # TTFT = EOU Delay + LLM TTFT + TTS TTFB (full user-perceived latency)
        eou = self.current_response.eou_delay_ms
        llm_ttft = self.current_response.llm.ttft_ms if self.current_response.llm else 0
        tts_ttfb = self.current_response.tts.ttfb_ms if self.current_response.tts else 0
        self.current_response.ttft_ms = eou + llm_ttft + tts_ttfb
        
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
            transcript=transcript,  # Store actual transcript
            timestamp=datetime.now().isoformat()
        )
        stt_metrics.calculate_cost()
        
        self.current_response.stt = stt_metrics
        
        # Add user message to conversation transcript
        if transcript.strip():
            self.call_metrics.conversation_transcript.append({
                "role": "user",
                "content": transcript
            })
        
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
    
    def end_llm(self, input_tokens: int, output_tokens: int, model: str, response_text: str = "", ttft_ms: float = 0.0):
        """
        End LLM tracking and record metrics
        
        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: LLM model used
            response_text: Actual LLM response text (optional)
            ttft_ms: Time to First Token in milliseconds (from pipeline metrics)
        """
        latency = self.llm_latency.end()
        
        if not self.current_response:
            self.start_response()
        
        llm_metrics = LLMMetrics(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency,
            ttft_ms=ttft_ms,  # Time to First Token - key metric!
            response_text=response_text,  # Store actual response
            timestamp=datetime.now().isoformat()
        )
        llm_metrics.calculate_cost()
        
        self.current_response.llm = llm_metrics
        
        # Note: Assistant message is added to conversation transcript later
        # when the actual response text is available (in agent_speech_committed handler)
        
        logger.debug(
            f"LLM completed: in={input_tokens} out={output_tokens} tokens, "
            f"ttft={ttft_ms:.0f}ms, cost=${llm_metrics.total_cost:.6f}, model={model}"
        )
    
    # ========================================================================
    # TTS TRACKING
    # ========================================================================
    
    def start_tts(self):
        """Start tracking TTS latency"""
        self.tts_latency.start()
        logger.debug("TTS tracking started")
    
    def end_tts(self, characters: int, model: str, audio_duration: float = 0.0, ttfb_ms: float = 0.0):
        """
        End TTS tracking and record metrics
        
        Args:
            characters: Number of characters processed
            model: TTS model used
            audio_duration: Duration of generated audio in seconds
            ttfb_ms: Time to First Byte in milliseconds (from pipeline metrics)
        """
        latency = self.tts_latency.end()
        
        if not self.current_response:
            self.start_response()
        
        tts_metrics = TTSMetrics(
            model=model,
            characters_processed=characters,
            latency_ms=latency,
            ttfb_ms=ttfb_ms,  # Time to First Byte - key metric!
            audio_duration_seconds=audio_duration,
            timestamp=datetime.now().isoformat()
        )
        tts_metrics.calculate_cost()
        
        self.current_response.tts = tts_metrics
        
        logger.debug(
            f"TTS completed: chars={characters}, ttfb={ttfb_ms:.0f}ms, "
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
        
        # Calculate LiveKit cost
        livekit_metrics = LiveKitMetrics(
            connection_duration_seconds=self.call_metrics.duration_seconds,
            timestamp=datetime.now().isoformat()
        )
        livekit_metrics.calculate_cost()
        self.call_metrics.livekit = livekit_metrics
        
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
                f"TTFT={response.llm.ttft_ms:.0f}ms, "
                f"${response.llm.total_cost:.6f}"
            )
        
        if response.tts:
            logger.info(
                f"  TTS: {response.tts.characters_processed} chars, "
                f"TTFB={response.tts.ttfb_ms:.0f}ms, "
                f"${response.tts.cost:.6f}"
            )
        
        if response.eou_delay_ms > 0:
            logger.info(f"  EOU Delay: {response.eou_delay_ms:.0f}ms (VAD + transcription)")
        logger.info(f"  TTFT: {response.ttft_ms:.0f}ms  <-- User-perceived latency")
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
        logger.info(f"  LiveKit: ${self.call_metrics.total_livekit_cost:.6f}")
        logger.info(f"  --------------")
        logger.info(f"  TOTAL: ${self.call_metrics.total_cost:.6f}")
        logger.info("")
        
        logger.info("AVERAGE LATENCIES (Time to First Token):")
        logger.info(f"  EOU Delay: {self.call_metrics.avg_eou_delay_ms:.0f}ms (VAD + transcription)")
        logger.info(f"  LLM TTFT: {self.call_metrics.avg_llm_ttft_ms:.0f}ms")
        logger.info(f"  TTS TTFB: {self.call_metrics.avg_tts_ttfb_ms:.0f}ms")
        logger.info(f"  TTFT (Total): {self.call_metrics.avg_ttft_ms:.0f}ms  <-- User wait time")
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
