"""
Advanced Cost Tracker with LiveKit Integration

This module provides deeper integration with LiveKit agents to capture
actual metrics from STT, LLM, and TTS operations.
"""

import logging
from typing import Optional, Dict, Any
from livekit.agents import metrics as lk_metrics
from cost_tracker import CostTracker

logger = logging.getLogger("advanced-cost-tracker")


class AdvancedCostTracker:
    """
    Enhanced cost tracker that integrates with LiveKit metrics.
    
    This class wraps the basic CostTracker and adds LiveKit-specific
    metric extraction capabilities.
    """
    
    def __init__(self, call_id: str):
        self.tracker = CostTracker(call_id=call_id)
        self.current_llm_metrics: Optional[Dict[str, Any]] = None
        self.current_stt_metrics: Optional[Dict[str, Any]] = None
        self.current_tts_metrics: Optional[Dict[str, Any]] = None
        self.last_spoken_text: str = ""
        
    def process_metrics(self, metrics: lk_metrics.AgentMetrics):
        """
        Process LiveKit metrics and extract relevant information.
        
        Args:
            metrics: LiveKit AgentMetrics object
        """
        try:
            # Extract STT metrics
            if hasattr(metrics, 'stt') and metrics.stt:
                self._extract_stt_metrics(metrics.stt)
            
            # Extract LLM metrics
            if hasattr(metrics, 'llm') and metrics.llm:
                self._extract_llm_metrics(metrics.llm)
            
            # Extract TTS metrics
            if hasattr(metrics, 'tts') and metrics.tts:
                self._extract_tts_metrics(metrics.tts)
                
        except Exception as e:
            logger.error(f"Error processing LiveKit metrics: {e}")
    
    def _extract_stt_metrics(self, stt_metrics):
        """Extract STT metrics from LiveKit"""
        try:
            self.current_stt_metrics = {
                'duration': getattr(stt_metrics, 'duration', 0.0),
                'model': getattr(stt_metrics, 'model', 'whisper-large-v3-turbo'),
            }
            logger.debug(f"Extracted STT metrics: {self.current_stt_metrics}")
        except Exception as e:
            logger.error(f"Error extracting STT metrics: {e}")
    
    def _extract_llm_metrics(self, llm_metrics):
        """Extract LLM metrics from LiveKit"""
        try:
            # Try to get token usage
            input_tokens = 0
            output_tokens = 0
            
            if hasattr(llm_metrics, 'completion_tokens'):
                output_tokens = llm_metrics.completion_tokens
            if hasattr(llm_metrics, 'prompt_tokens'):
                input_tokens = llm_metrics.prompt_tokens
            
            # Alternative attribute names
            if hasattr(llm_metrics, 'tokens_used'):
                tokens_used = llm_metrics.tokens_used
                if isinstance(tokens_used, dict):
                    input_tokens = tokens_used.get('prompt_tokens', input_tokens)
                    output_tokens = tokens_used.get('completion_tokens', output_tokens)
            
            self.current_llm_metrics = {
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'model': getattr(llm_metrics, 'model', 'llama-3.3-70b-versatile'),
            }
            logger.debug(f"Extracted LLM metrics: {self.current_llm_metrics}")
        except Exception as e:
            logger.error(f"Error extracting LLM metrics: {e}")
    
    def _extract_tts_metrics(self, tts_metrics):
        """Extract TTS metrics from LiveKit"""
        try:
            self.current_tts_metrics = {
                'characters': getattr(tts_metrics, 'characters_count', 0),
                'audio_duration': getattr(tts_metrics, 'audio_duration', 0.0),
                'model': getattr(tts_metrics, 'model', 'canopylabs/orpheus-v1-english'),
            }
            logger.debug(f"Extracted TTS metrics: {self.current_tts_metrics}")
        except Exception as e:
            logger.error(f"Error extracting TTS metrics: {e}")
    
    def capture_spoken_text(self, text: str):
        """Capture text that will be spoken by TTS"""
        self.last_spoken_text = text
    
    def start_response(self):
        """Start tracking a new response"""
        self.tracker.start_response()
        # Reset metrics
        self.current_stt_metrics = None
        self.current_llm_metrics = None
        self.current_tts_metrics = None
        self.last_spoken_text = ""
    
    def track_stt_complete(self, transcript: str, duration: Optional[float] = None, model: Optional[str] = None):
        """Track STT completion with optional override values"""
        # Use captured metrics if available, otherwise use provided values
        if self.current_stt_metrics:
            duration = self.current_stt_metrics.get('duration', duration or 1.0)
            model = self.current_stt_metrics.get('model', model or 'whisper-large-v3-turbo')
        else:
            duration = duration or 1.0
            model = model or 'whisper-large-v3-turbo'
        
        self.tracker.end_stt(
            duration=duration,
            transcript=transcript,
            model=model
        )
    
    def track_llm_complete(self, input_tokens: Optional[int] = None, 
                          output_tokens: Optional[int] = None,
                          model: Optional[str] = None):
        """Track LLM completion with optional override values"""
        # Use captured metrics if available, otherwise use provided values
        if self.current_llm_metrics:
            input_tokens = self.current_llm_metrics.get('input_tokens', input_tokens or 100)
            output_tokens = self.current_llm_metrics.get('output_tokens', output_tokens or 50)
            model = self.current_llm_metrics.get('model', model or 'llama-3.3-70b-versatile')
        else:
            input_tokens = input_tokens or 100
            output_tokens = output_tokens or 50
            model = model or 'llama-3.3-70b-versatile'
        
        self.tracker.end_llm(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model
        )
    
    def track_tts_complete(self, characters: Optional[int] = None,
                          model: Optional[str] = None,
                          audio_duration: Optional[float] = None):
        """Track TTS completion with optional override values"""
        # Use captured metrics if available, otherwise use provided values
        if self.current_tts_metrics:
            characters = self.current_tts_metrics.get('characters', characters or len(self.last_spoken_text))
            model = self.current_tts_metrics.get('model', model or 'canopylabs/orpheus-v1-english')
            audio_duration = self.current_tts_metrics.get('audio_duration', audio_duration or 0.0)
        else:
            characters = characters or len(self.last_spoken_text)
            model = model or 'canopylabs/orpheus-v1-english'
            audio_duration = audio_duration or 0.0
        
        self.tracker.end_tts(
            characters=characters,
            model=model,
            audio_duration=audio_duration
        )
    
    def end_response(self):
        """End response tracking"""
        self.tracker.end_response()
    
    def end_call(self):
        """End call tracking"""
        self.tracker.end_call()
    
    def get_call_summary(self):
        """Get call summary"""
        return self.tracker.get_call_summary()
    
    def export_to_file(self, filepath: str):
        """Export metrics to file"""
        self.tracker.export_to_file(filepath)
    
    # Delegate attribute access to underlying tracker
    def __getattr__(self, name):
        return getattr(self.tracker, name)
