"""
Configuration Management for Groq Voice Assistant

This module provides centralized configuration management for the voice assistant.
All settings can be easily modified here or overridden via environment variables.

Usage:
    from config import Config
    
    # Access configuration
    stt_model = Config.MODELS.STT_MODEL
    max_duration = Config.CALL.MAX_DURATION_MINUTES
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger("config")


@dataclass
class ModelConfig:
    """AI Model Configuration"""
    # Speech-to-Text (STT) Configuration
    STT_MODEL: str = os.getenv("STT_MODEL", "whisper-large-v3-turbo")
    STT_ALTERNATIVE_MODELS: List[str] = field(default_factory=lambda: [
        "whisper-large-v3",
        "whisper-large-v3-turbo"
    ])
    
    # Large Language Model (LLM) Configuration
    LLM_MODEL: str = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
    LLM_ALTERNATIVE_MODELS: List[str] = field(default_factory=lambda: [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768"
    ])
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS: Optional[int] = None  # None = use model default
    
    # Text-to-Speech (TTS) Configuration
    TTS_MODEL: str = os.getenv("TTS_MODEL", "canopylabs/orpheus-v1-english")
    TTS_VOICE: str = os.getenv("TTS_VOICE", "autumn")
    TTS_ALTERNATIVE_MODELS: List[str] = field(default_factory=lambda: [
        "canopylabs/orpheus-v1-english",
        "tts-1",
        "tts-1-hd",
        "playai-tts"
    ])
    TTS_AVAILABLE_VOICES: List[str] = field(default_factory=lambda: [
        "autumn", "diana", "hannah", "austin", "daniel", "troy"
    ])


@dataclass
class CallConfig:
    """Call Management Configuration"""
    # Timeout Settings
    INACTIVITY_TIMEOUT_SECONDS: int = int(os.getenv("INACTIVITY_TIMEOUT_SECONDS", "15"))
    MAX_CALL_DURATION_MINUTES: int = int(os.getenv("MAX_CALL_DURATION_MINUTES", "15"))
    MAX_DURATION_WARNING_MINUTES: int = int(os.getenv("MAX_DURATION_WARNING_MINUTES", "1"))
    
    # Farewell Detection
    FAREWELL_INTENTS: List[str] = field(default_factory=lambda: [
        # Direct farewells
        "bye", "goodbye", "good bye", "bye bye", "byebye",
        # Ending phrases
        "that's all", "thats all", "that is all", "nothing else",
        "i'm done", "im done", "i am done", "all done",
        "no more questions", "no questions", "that's it", "thats it",
        # Explicit endings
        "end call", "hang up", "disconnect", "end the call",
        # Casual farewells
        "see you", "see ya", "talk to you later", "ttyl",
        "have a good day", "have a nice day",
        # Combined with bye
        "okay bye", "ok bye", "thanks bye", "thank you bye",
        "thanks goodbye", "thank you goodbye",
        "okay thank you bye", "ok thank you bye",
        "take care bye", "take care goodbye"
    ])
    
    # Messages
    INACTIVITY_MESSAGE: str = os.getenv(
        "INACTIVITY_MESSAGE",
        "I haven't heard from you in a while. "
        "I'll disconnect for now, but feel free to call back if you have any questions. Take care!"
    )
    MAX_DURATION_WARNING_MESSAGE: str = os.getenv(
        "MAX_DURATION_WARNING_MESSAGE",
        "Just a heads up, we're approaching the maximum call duration. "
        "Is there anything else I can quickly help you with?"
    )
    MAX_DURATION_END_MESSAGE: str = os.getenv(
        "MAX_DURATION_END_MESSAGE",
        "We've reached the maximum call duration. "
        "Thank you for using Mercola Health Coach. Feel free to call back anytime!"
    )
    FAREWELL_MESSAGE: str = os.getenv(
        "FAREWELL_MESSAGE",
        "Thank you for contacting Mercola Health Coach! "
        "Feel free to reach out anytime you need help. Take care!"
    )
    GREETING_MESSAGE: str = os.getenv(
        "GREETING_MESSAGE",
        "Hey there! I'm Pax, your Mercola Health Coach. "
        "How can I help you today?"
    )


@dataclass
class AgentConfig:
    """Agent Identity and Behavior Configuration"""
    AGENT_NAME: str = os.getenv("AGENT_NAME", "mercola-health-coach")  # LiveKit agent identifier
    AGENT_IDENTITY: str = os.getenv("AGENT_IDENTITY", "Pax")  # Display name for the assistant
    AGENT_ROLE: str = os.getenv("AGENT_ROLE", "Mercola Health Coach voice assistant")
    
    # System prompt can be loaded from file or environment variable
    # Default to "system_prompt" file in the agent directory
    SYSTEM_PROMPT_FILE: Optional[str] = os.getenv(
        "SYSTEM_PROMPT_FILE", 
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "system_prompt")
    )
    SYSTEM_PROMPT: Optional[str] = None  # Will be loaded from file or use default


@dataclass
class PathConfig:
    """Directory and File Path Configuration"""
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    AGENT_DIR: str = os.path.dirname(os.path.abspath(__file__))
    
    # Output directories
    METRICS_DIR: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "metrics")
    LABS_EVALUATIONS_DIR: str = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "labs_evaluations"
    )
    TRANSCRIPTS_DIR: str = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "labs_evaluations", "transcripts"
    )
    
    # Configuration files
    PRICING_CONFIG_FILE: str = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "pricing_config.json"
    )
    
    # Ensure directories exist
    def __post_init__(self):
        """Create directories if they don't exist"""
        for dir_path in [
            self.METRICS_DIR,
            self.LABS_EVALUATIONS_DIR,
            self.TRANSCRIPTS_DIR
        ]:
            os.makedirs(dir_path, exist_ok=True)


@dataclass
class EvaluationConfig:
    """Call Evaluation Configuration"""
    USE_LLM_EVALUATION: bool = os.getenv("USE_LLM_EVALUATION", "true").lower() == "true"
    LABS_EVAL_MODEL: str = os.getenv("LABS_EVAL_MODEL", "llama-3.3-70b-versatile")
    LLM_EVAL_TEMPERATURE: float = float(os.getenv("LLM_EVAL_TEMPERATURE", "0.1"))
    LLM_EVAL_MAX_TOKENS: int = int(os.getenv("LLM_EVAL_MAX_TOKENS", "1000"))


@dataclass
class LiveKitConfig:
    """LiveKit Platform Configuration"""
    LIVEKIT_URL: str = os.getenv("LIVEKIT_URL", "")
    LIVEKIT_API_KEY: str = os.getenv("LIVEKIT_API_KEY", "")
    LIVEKIT_API_SECRET: str = os.getenv("LIVEKIT_API_SECRET", "")
    
    def validate(self) -> bool:
        """Validate that required LiveKit credentials are set"""
        if not self.LIVEKIT_URL:
            logger.warning("LIVEKIT_URL not set")
            return False
        if not self.LIVEKIT_API_KEY:
            logger.warning("LIVEKIT_API_KEY not set")
            return False
        if not self.LIVEKIT_API_SECRET:
            logger.warning("LIVEKIT_API_SECRET not set")
            return False
        return True


@dataclass
class GroqConfig:
    """Groq API Configuration"""
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    
    def validate(self) -> bool:
        """Validate that Groq API key is set"""
        if not self.GROQ_API_KEY:
            logger.warning("GROQ_API_KEY not set")
            return False
        return True


@dataclass
class LoggingConfig:
    """Logging Configuration"""
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    SUPPRESS_DUPLEX_CLOSED: bool = os.getenv("SUPPRESS_DUPLEX_CLOSED", "true").lower() == "true"


class Config:
    """
    Main Configuration Class
    
    Centralized configuration management for the voice assistant.
    All settings can be accessed via Config.CATEGORY.SETTING
    
    Example:
        from config import Config
        
        # Access model settings
        stt_model = Config.MODELS.STT_MODEL
        
        # Access call settings
        timeout = Config.CALL.INACTIVITY_TIMEOUT_SECONDS
        
        # Validate credentials
        if not Config.LIVEKIT.validate():
            raise ValueError("Missing LiveKit credentials")
    """
    
    # Initialize all configuration categories
    MODELS = ModelConfig()
    CALL = CallConfig()
    AGENT = AgentConfig()
    PATHS = PathConfig()
    EVALUATION = EvaluationConfig()
    LIVEKIT = LiveKitConfig()
    GROQ = GroqConfig()
    LOGGING = LoggingConfig()
    
    @classmethod
    def load_system_prompt(cls) -> str:
        """
        Load system prompt from file or use default.
        If the system_prompt file doesn't exist, create it with the default prompt.
        
        Returns:
            System prompt string
        """
        # Try to load from file first
        if cls.AGENT.SYSTEM_PROMPT_FILE:
            if os.path.exists(cls.AGENT.SYSTEM_PROMPT_FILE):
                try:
                    with open(cls.AGENT.SYSTEM_PROMPT_FILE, 'r', encoding='utf-8') as f:
                        prompt = f.read().strip()
                    logger.info(f"Loaded system prompt from {cls.AGENT.SYSTEM_PROMPT_FILE}")
                    return prompt
                except Exception as e:
                    logger.warning(f"Failed to load system prompt from file: {e}")
            else:
                # File doesn't exist - create it with default prompt
                try:
                    default_prompt = cls._get_default_system_prompt()
                    with open(cls.AGENT.SYSTEM_PROMPT_FILE, 'w', encoding='utf-8') as f:
                        f.write(default_prompt)
                    logger.info(f"Created system_prompt file at {cls.AGENT.SYSTEM_PROMPT_FILE} with default prompt")
                    return default_prompt
                except Exception as e:
                    logger.warning(f"Failed to create system_prompt file: {e}, using default prompt")
        
        # Use default system prompt (fallback)
        return cls._get_default_system_prompt()
    
    @staticmethod
    def _get_default_system_prompt() -> str:
        """Get the default system prompt"""
        return """default system prompt"""
    
    @classmethod
    def get_end_call_config(cls) -> dict:
        """
        Get call ending configuration as a dictionary (for backward compatibility).
        
        Returns:
            Dictionary with call ending settings
        """
        return {
            "inactivity_timeout_seconds": cls.CALL.INACTIVITY_TIMEOUT_SECONDS,
            "max_call_duration_minutes": cls.CALL.MAX_CALL_DURATION_MINUTES,
            "farewell_intents": cls.CALL.FAREWELL_INTENTS,
            "inactivity_message": cls.CALL.INACTIVITY_MESSAGE,
            "max_duration_warning_minutes": cls.CALL.MAX_DURATION_WARNING_MINUTES,
            "max_duration_warning_message": cls.CALL.MAX_DURATION_WARNING_MESSAGE,
            "max_duration_end_message": cls.CALL.MAX_DURATION_END_MESSAGE,
            "farewell_message": cls.CALL.FAREWELL_MESSAGE,
        }
    
    @classmethod
    def validate_all(cls) -> bool:
        """
        Validate all required configurations.
        
        Returns:
            True if all required configs are valid, False otherwise
        """
        all_valid = True
        
        if not cls.LIVEKIT.validate():
            logger.error("LiveKit configuration is invalid")
            all_valid = False
        
        if not cls.GROQ.validate():
            logger.warning("Groq API key not set (some features may not work)")
        
        return all_valid
    
    @classmethod
    def print_config(cls):
        """Print current configuration (excluding sensitive data)"""
        print("=" * 80)
        print("VOICE ASSISTANT CONFIGURATION")
        print("=" * 80)
        print(f"\nMODELS:")
        print(f"  STT: {cls.MODELS.STT_MODEL}")
        print(f"  LLM: {cls.MODELS.LLM_MODEL}")
        print(f"  TTS: {cls.MODELS.TTS_MODEL} (voice: {cls.MODELS.TTS_VOICE})")
        print(f"\nCALL SETTINGS:")
        print(f"  Inactivity Timeout: {cls.CALL.INACTIVITY_TIMEOUT_SECONDS}s")
        print(f"  Max Duration: {cls.CALL.MAX_CALL_DURATION_MINUTES} minutes")
        print(f"  Farewell Intents: {len(cls.CALL.FAREWELL_INTENTS)} phrases")
        print(f"\nAGENT:")
        print(f"  Name: {cls.AGENT.AGENT_NAME}")
        print(f"  Identity: {cls.AGENT.AGENT_IDENTITY}")
        print(f"\nPATHS:")
        print(f"  Metrics: {cls.PATHS.METRICS_DIR}")
        print(f"  Evaluations: {cls.PATHS.LABS_EVALUATIONS_DIR}")
        print(f"\nEVALUATION:")
        print(f"  Use LLM: {cls.EVALUATION.USE_LLM_EVALUATION}")
        print(f"  Model: {cls.EVALUATION.LABS_EVAL_MODEL}")
        print(f"\nCREDENTIALS:")
        print(f"  LiveKit URL: {'[SET]' if cls.LIVEKIT.LIVEKIT_URL else '[NOT SET]'}")
        print(f"  LiveKit API Key: {'[SET]' if cls.LIVEKIT.LIVEKIT_API_KEY else '[NOT SET]'}")
        print(f"  Groq API Key: {'[SET]' if cls.GROQ.GROQ_API_KEY else '[NOT SET]'}")
        print("=" * 80)


# Initialize paths (creates directories)
_ = Config.PATHS
