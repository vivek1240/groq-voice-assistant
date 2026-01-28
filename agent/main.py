import logging
import sys
import asyncio
import time
import os
import uuid

from dotenv import load_dotenv
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
    metrics,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import silero, groq

# Import cost tracker and evaluators
from cost_tracker import CostTracker
from call_evaluator import CallEvaluator, evaluate_call_automatically
from labs_evaluator import LabsCallEvaluator, evaluate_labs_call_automatically

# Import DuplexClosed if available (for error handling on Windows)
try:
    from livekit.agents.utils.aio.duplex_unix import DuplexClosed
except ImportError:
    # If import fails, we'll catch by exception type name instead
    DuplexClosed = None

load_dotenv()

# Configure basic logging first (before using Config, in case Config has issues)
# This ensures we can see errors even if Config fails to load
logging.basicConfig(
    level=logging.INFO,  # Start with INFO level, will be updated after Config loads
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True  # Force reconfiguration if logging was already set up
)

# Now import and use Config
try:
    from config import Config
    
    # Update logging level from Config if available
    try:
        log_level = getattr(logging, Config.LOGGING.LOG_LEVEL.upper(), logging.INFO)
        logging.getLogger().setLevel(log_level)
        # Reconfigure with Config's format
        for handler in logging.getLogger().handlers:
            handler.setFormatter(logging.Formatter(Config.LOGGING.LOG_FORMAT))
    except Exception as e:
        logging.warning(f"Could not configure logging from Config: {e}, using defaults")

except ImportError as e:
    logging.error(f"Failed to import Config: {e}")
    logging.error("Please ensure config.py exists in the agent directory")
    raise
except Exception as e:
    logging.error(f"Error initializing Config: {e}")
    import traceback
    logging.error(traceback.format_exc())
    raise

logger = logging.getLogger("voice-agent")
logger.info("Voice agent logger initialized")

# Ensure output is visible immediately (for better log visibility)
try:
    if sys.stdout.isatty() and hasattr(sys.stdout, 'reconfigure'):  # Only if running in a terminal
        sys.stdout.reconfigure(line_buffering=True)
except:
    pass  # Ignore if not supported

# Suppress DuplexClosed errors from LiveKit agents watcher on Windows
try:
    suppress_duplex = Config.LOGGING.SUPPRESS_DUPLEX_CLOSED
except:
    suppress_duplex = True  # Default to True if Config not available

if sys.platform == "win32" and suppress_duplex:
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning, module="livekit.agents")
    
    # Filter out DuplexClosed errors from logs
    class DuplexClosedFilter(logging.Filter):
        def filter(self, record):
            return "DuplexClosed" not in str(record.getMessage())
    
    # Apply filter to livekit.agents loggers
    logging.getLogger("livekit.agents").addFilter(DuplexClosedFilter())

# Get call configuration from Config
try:
    END_CALL_CONFIG = Config.get_end_call_config()
    logger.debug("Call configuration loaded successfully")
except Exception as e:
    logger.error(f"Failed to load call configuration: {e}")
    # Fallback to default configuration
    END_CALL_CONFIG = {
        "inactivity_timeout_seconds": 15,
        "max_call_duration_minutes": 15,
        "farewell_intents": ["bye", "goodbye", "that's all", "i'm done"],
        "inactivity_message": "I haven't heard from you in a while. I'll disconnect for now.",
        "max_duration_warning_minutes": 1,
        "max_duration_warning_message": "Just a heads up, we're approaching the maximum call duration.",
        "max_duration_end_message": "We've reached the maximum call duration. Thank you!",
        "farewell_message": "Thank you for contacting Mercola Health Coach! Take care!",
    }
    logger.warning("Using fallback call configuration")


def prewarm(proc: JobProcess):
    """Prewarm models to reduce cold start latency."""
    import time
    prewarm_start = time.time()
    logger.info("Prewarming models...")
    
    # Load VAD model
    vad_start = time.time()
    proc.userdata["vad"] = silero.VAD.load()
    logger.info(f"VAD model loaded in {(time.time() - vad_start)*1000:.0f}ms")
    
    # Pre-initialize Groq clients to establish connections early
    # This reduces first-request latency
    
    # STT: Groq Whisper Large V3 Turbo (fastest, best quality)
    stt_start = time.time()
    proc.userdata["stt"] = groq.STT(model=Config.MODELS.STT_MODEL)
    logger.info(f"STT client initialized in {(time.time() - stt_start)*1000:.0f}ms")
    
    # LLM: Llama 3.3 70B (best quality, Groq makes it fast)
    # Groq's inference is so fast that 70B has negligible latency cost vs 8B
    llm_start = time.time()
    proc.userdata["llm"] = groq.LLM(model=Config.MODELS.LLM_MODEL)
    logger.info(f"LLM client initialized in {(time.time() - llm_start)*1000:.0f}ms")
    
    # TTS: Groq Orpheus
    # Available voices: autumn, diana, hannah, austin, daniel, troy
    tts_start = time.time()
    proc.userdata["tts"] = groq.TTS(
        model=Config.MODELS.TTS_MODEL,
        voice=Config.MODELS.TTS_VOICE
    )
    logger.info(f"TTS client initialized in {(time.time() - tts_start)*1000:.0f}ms")
    
    total_prewarm_time = (time.time() - prewarm_start) * 1000
    logger.info(f"Models prewarmed successfully in {total_prewarm_time:.0f}ms total")


async def entrypoint(ctx: JobContext):
    try:
        # Initialize cost tracker for this call
        call_id = f"call_{ctx.room.name}_{uuid.uuid4().hex[:8]}"
        cost_tracker_start = time.time()
        cost_tracker = CostTracker(call_id=call_id)
        logger.info(f"CostTracker initialized in {(time.time() - cost_tracker_start)*1000:.0f}ms")
        
        # Load system prompt from config
        prompt_start = time.time()
        system_prompt = Config.load_system_prompt()
        logger.info(f"System prompt loaded in {(time.time() - prompt_start)*1000:.0f}ms")
        
        initial_ctx = llm.ChatContext().append(
            role="system",
            text=system_prompt,
        )

        logger.info(f"connecting to room {ctx.room.name}")
        connect_start = time.time()
        await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
        logger.info(f"Connected to room in {(time.time() - connect_start)*1000:.0f}ms")

        # Wait for the first participant to connect
        participant_start = time.time()
        participant = await ctx.wait_for_participant()
        logger.info(f"Participant connected in {(time.time() - participant_start)*1000:.0f}ms")
        logger.info(f"starting voice assistant for participant {participant.identity}")

        # Use prewarmed models for faster startup
        agent_start = time.time()
        agent = VoicePipelineAgent(
            vad=ctx.proc.userdata["vad"],
            stt=ctx.proc.userdata.get("stt") or groq.STT(model=Config.MODELS.STT_MODEL),
            llm=ctx.proc.userdata.get("llm") or groq.LLM(model=Config.MODELS.LLM_MODEL),
            tts=ctx.proc.userdata.get("tts") or groq.TTS(
                model=Config.MODELS.TTS_MODEL, 
                voice=Config.MODELS.TTS_VOICE
            ),
            chat_ctx=initial_ctx,
        )
        logger.info(f"VoicePipelineAgent created in {(time.time() - agent_start)*1000:.0f}ms")

        # Initialize call tracking variables
        call_start_time = time.time()
        last_activity_time = time.time()
        call_ended = False
        max_duration_warning_sent = False
        farewell_detected = False
        inactivity_ended = False  # Track if call ended due to inactivity
        agent_is_speaking = False
        inactivity_disconnect_in_progress = False  # Track if we're in the middle of disconnecting due to inactivity
        
        # Function to check for farewell intents
        def detect_farewell_intent(text: str) -> bool:
            """Detect if user is saying goodbye or ending the conversation."""
            if not text:
                return False
            text_lower = text.lower().strip()
            for intent in END_CALL_CONFIG["farewell_intents"]:
                if intent in text_lower:
                    return True
            return False
        
        # Function to filter out false-positive transcriptions
        def is_valid_transcript(text: str) -> bool:
            """
            Filter out false-positive transcriptions from background noise or silence.
            Returns False if transcript should be ignored.
            """
            if not text:
                return False
            
            text_stripped = text.strip()
            
            # Reject empty or whitespace-only transcripts
            if not text_stripped:
                return False
            
            # Count meaningful words (excluding very short words that might be noise)
            words = [w for w in text_stripped.split() if len(w) > 1]
            word_count = len(words)
            
            # Reject transcripts that are too short in character length
            # Very short transcripts (less than 5 characters) are likely noise
            if len(text_stripped) < 5:
                logger.warning(f"REJECTING VERY SHORT TRANSCRIPT ({len(text_stripped)} chars): '{text_stripped}'")
                return False
            
            # Reject transcripts with less than 2 meaningful words
            # This filters out single words, filler sounds, or very short phrases
            if word_count < 2:
                logger.warning(f"REJECTING SHORT TRANSCRIPT (only {word_count} word(s)): '{text_stripped}'")
                return False
            
            # Reject transcripts that are just punctuation or very short phrases
            # Remove punctuation and check if there's meaningful content
            import re
            text_no_punct = re.sub(r'[^\w\s]', '', text_stripped)
            meaningful_words = [w for w in text_no_punct.split() if len(w) > 1]
            
            if len(meaningful_words) < 2:
                logger.warning(f"REJECTING LOW-QUALITY TRANSCRIPT (mostly punctuation/noise): '{text_stripped}'")
                return False
            
            # Reject transcripts that are just single-word filler sounds (not legitimate responses)
            # Note: We allow 2-word phrases even if they're common, as they might be legitimate
            single_word_fillers = [
                "uh", "um", "ah", "eh", "oh", "hmm", "mm", "mmm",
                "so", "well", "like", "actually"
            ]
            text_lower = text_stripped.lower()
            
            # Only reject if it's a single word AND it's a known filler sound
            if word_count == 1:
                if text_lower.strip() in single_word_fillers:
                    logger.warning(f"REJECTING SINGLE-WORD FILLER: '{text_stripped}'")
                    return False
            
            return True

        # Cost tracking state
        tracking_state = {
            'current_user_text': '',
            'current_agent_text': '',
            'stt_start_time': 0,
            'llm_start_time': 0,
            'tts_start_time': 0,
            'eou_delay_ms': 0,  # End-of-Utterance delay (VAD + transcription)
            'llm_ttft_ms': 0,  # LLM Time to First Token
            'tts_ttfb_ms': 0,  # TTS Time to First Byte
        }
        
        # Event handler for metrics collection - capture EOU, TTFT, TTFB
        @agent.on("metrics_collected")
        def _on_metrics_collected(mtrcs):
            """Capture pipeline metrics including EOU delay, TTFT and TTFB"""
            # mtrcs is the metrics object directly (e.g., PipelineLLMMetrics, PipelineTTSMetrics, PipelineEOUMetrics)
            # Log the metrics using the built-in logger
            metrics.log_metrics(mtrcs)
            
            # Check for EOU (End-of-Utterance) metrics - this is the VAD + transcription delay
            if hasattr(mtrcs, 'end_of_utterance_delay') and mtrcs.end_of_utterance_delay is not None:
                tracking_state['eou_delay_ms'] = mtrcs.end_of_utterance_delay * 1000  # Convert to ms
                logger.info(f"Captured EOU Delay: {tracking_state['eou_delay_ms']:.0f}ms")
            
            # Check for LLM metrics (has ttft attribute)
            if hasattr(mtrcs, 'ttft') and mtrcs.ttft is not None and mtrcs.ttft > 0:
                tracking_state['llm_ttft_ms'] = mtrcs.ttft * 1000  # Convert to ms
                logger.info(f"Captured LLM TTFT: {tracking_state['llm_ttft_ms']:.0f}ms")
            
            # Check for TTS metrics (has ttfb attribute)
            if hasattr(mtrcs, 'ttfb') and mtrcs.ttfb is not None and mtrcs.ttfb > 0:
                tracking_state['tts_ttfb_ms'] = mtrcs.ttfb * 1000  # Convert to ms
                logger.info(f"Captured TTS TTFB: {tracking_state['tts_ttfb_ms']:.0f}ms")
        
        # Event handlers (consolidated for cost tracking + call logic)
        @agent.on("user_started_speaking")
        def _on_user_started_speaking():
            """User started speaking - start tracking response and reset activity timer"""
            nonlocal last_activity_time, inactivity_disconnect_in_progress
            
            # CRITICAL: Reset activity timer immediately when user starts speaking
            # This prevents premature disconnection if user_speech_committed fails to fire
            last_activity_time = time.time()
            
            # Cancel any pending inactivity disconnect
            if inactivity_disconnect_in_progress:
                inactivity_disconnect_in_progress = False
                logger.info("USER STARTED SPEAKING - CANCELLING inactivity disconnect")
            else:
                logger.info("USER STARTED SPEAKING - activity timer reset")
            
            logger.debug("Starting response tracking")
            cost_tracker.start_response()
            cost_tracker.start_stt()
            tracking_state['stt_start_time'] = time.time()
        
        @agent.on("user_speech_committed")
        def _on_user_speech_committed(msg):
            """STT completed - track metrics and check for farewell intent"""
            nonlocal last_activity_time, farewell_detected
            
            # If farewell already detected and we're in the process of ending, ignore new speech
            if farewell_detected:
                logger.info("Ignoring user speech - farewell already detected, ending call")
                return
            
            # Update activity time (also done in user_started_speaking for redundancy)
            last_activity_time = time.time()
            logger.info("USER SPEECH COMMITTED - activity timer refreshed")
            
            try:
                # Extract transcript text
                user_text = ""
                if hasattr(msg, 'text'):
                    user_text = msg.text
                elif hasattr(msg, 'content'):
                    user_text = msg.content
                elif isinstance(msg, str):
                    user_text = msg
                
                # Filter out false-positive transcriptions (background noise, silence, etc.)
                if not is_valid_transcript(user_text):
                    logger.info(f"IGNORING INVALID TRANSCRIPT: '{user_text}' - likely false positive from noise/silence")
                    # Don't process this transcript - return early
                    # But still reset activity timer since VAD detected something
                    return
                
                tracking_state['current_user_text'] = user_text
                logger.info(f"USER SPOKE: {user_text[:80] if user_text else 'N/A'}...")
                
                # Check for farewell intent in user's message
                if user_text and detect_farewell_intent(user_text):
                    farewell_detected = True
                    logger.info(f"FAREWELL DETECTED in: '{user_text}' - will end call after farewell message")
                
                # Estimate audio duration based on text length
                # Average speaking rate: ~150 words per minute, ~2.5 words per second
                word_count = len(user_text.split())
                estimated_duration = max(word_count / 2.5, 0.5)  # At least 0.5s
                
                # Track STT completion
                cost_tracker.end_stt(
                    duration=estimated_duration,
                    transcript=user_text,
                    model="whisper-large-v3-turbo"
                )
                
                # Start LLM tracking
                cost_tracker.start_llm()
                tracking_state['llm_start_time'] = time.time()
                
            except Exception as e:
                logger.error(f"Error in user_speech_committed handler: {e}")
        
        @agent.on("agent_started_speaking")
        def _on_agent_started_speaking():
            """Agent started speaking - track LLM completion and start TTS tracking"""
            nonlocal agent_is_speaking
            agent_is_speaking = True
            logger.info("AGENT STARTED SPEAKING")
            
            try:
                # Estimate token usage based on text length
                # Rough approximation: 1 token ≈ 0.75 words (4 characters)
                user_text = tracking_state.get('current_user_text', '')
                
                # Input tokens: system prompt + conversation history + user message
                # System prompt is ~1500 words, user message varies
                system_prompt_tokens = int(1500 / 0.75)  # ~2000 tokens
                user_tokens = int(len(user_text.split()) / 0.75)
                estimated_input_tokens = system_prompt_tokens + user_tokens
                
                # Output tokens will be estimated after we capture the agent's response
                # For now, use a placeholder that will be updated
                estimated_output_tokens = 100  # Will be refined
                
                cost_tracker.end_llm(
                    input_tokens=estimated_input_tokens,
                    output_tokens=estimated_output_tokens,
                    model=Config.MODELS.LLM_MODEL,
                    ttft_ms=tracking_state.get('llm_ttft_ms', 0)
                )
                
                # Start TTS tracking
                cost_tracker.start_tts()
                tracking_state['tts_start_time'] = time.time()
                
            except Exception as e:
                logger.error(f"Error in agent_started_speaking handler: {e}")
        
        @agent.on("agent_stopped_speaking")
        def _on_agent_stopped_speaking():
            """Agent stopped speaking - TTS completed"""
            nonlocal agent_is_speaking, last_activity_time
            agent_is_speaking = False
            
            # CRITICAL: Reset inactivity timer when agent finishes speaking
            # The time while agent was speaking should NOT count as user inactivity.
            # User needs time to process the response and formulate their reply.
            last_activity_time = time.time()
            logger.info("AGENT STOPPED SPEAKING - inactivity timer reset (user now has time to respond)")
            
            try:
                # Get the agent's response text if available
                agent_text = tracking_state.get('current_agent_text', '')
                
                # Estimate characters
                # If we don't have the exact text, estimate based on typical response length
                estimated_characters = len(agent_text) if agent_text else 200
                
                cost_tracker.end_tts(
                    characters=estimated_characters,
                    model=Config.MODELS.TTS_MODEL,
                    ttfb_ms=tracking_state.get('tts_ttfb_ms', 0)
                )
                
                # End response tracking with EOU delay
                cost_tracker.end_response(
                    eou_delay_ms=tracking_state.get('eou_delay_ms', 0)
                )
                
                # Reset tracking state for next response
                tracking_state['current_user_text'] = ''
                tracking_state['current_agent_text'] = ''
                tracking_state['eou_delay_ms'] = 0
                tracking_state['llm_ttft_ms'] = 0
                tracking_state['tts_ttfb_ms'] = 0
                
            except Exception as e:
                logger.error(f"Error in agent_stopped_speaking handler: {e}")
        
        # Try to capture agent's text responses
        @agent.on("agent_speech_committed")
        def _on_agent_speech_committed(msg):
            """Capture agent's speech text for metrics"""
            try:
                # Debug: Log the message structure
                logger.debug(f"agent_speech_committed event: type={type(msg)}, dir={[attr for attr in dir(msg) if not attr.startswith('_')]}")
                
                agent_text = ""
                if hasattr(msg, 'text'):
                    agent_text = msg.text
                    logger.debug(f"Got agent text from 'text' attribute: {len(agent_text)} chars")
                elif hasattr(msg, 'content'):
                    agent_text = msg.content
                    logger.debug(f"Got agent text from 'content' attribute: {len(agent_text)} chars")
                elif hasattr(msg, 'message'):
                    agent_text = msg.message
                    logger.debug(f"Got agent text from 'message' attribute: {len(agent_text)} chars")
                elif isinstance(msg, str):
                    agent_text = msg
                    logger.debug(f"Got agent text from string: {len(agent_text)} chars")
                else:
                    logger.warning(f"Could not extract agent text from message: {type(msg)}")
                
                tracking_state['current_agent_text'] = agent_text
                
                # The response has already ended by the time this event fires
                # So we need to update the LAST response in the call metrics
                if agent_text and cost_tracker.call_metrics.responses:
                    last_response = cost_tracker.call_metrics.responses[-1]
                    
                    # Update LLM metrics with actual response text
                    if last_response.llm:
                        last_response.llm.response_text = agent_text
                        
                        # Update output tokens based on actual text
                        output_tokens = int(len(agent_text.split()) / 0.75)
                        last_response.llm.output_tokens = output_tokens
                        last_response.llm.calculate_cost()
                        
                        # Recalculate total cost for this response
                        last_response.calculate_total_cost()
                        
                        # Add assistant message to conversation transcript
                        if agent_text.strip():
                            cost_tracker.call_metrics.conversation_transcript.append({
                                "role": "assistant",
                                "content": agent_text
                            })
                            logger.info(f"Added assistant response to transcript: {len(agent_text)} chars")
                else:
                    if not agent_text:
                        logger.warning(f"No agent text to update")
                    if not cost_tracker.call_metrics.responses:
                        logger.warning(f"No responses in call metrics yet")
                
            except Exception as e:
                logger.error(f"Error capturing agent speech: {e}", exc_info=True)

        # Start the agent and measure startup time
        agent_start_time = time.time()
        logger.info("Starting agent pipeline...")
        agent.start(ctx.room, participant)
        agent_startup_time = (time.time() - agent_start_time) * 1000
        logger.info(f"Agent pipeline started in {agent_startup_time:.0f}ms")
        
        # Background task to monitor call duration and inactivity




# 2. FIXED inactivity check - simpler and more reliable
        async def monitor_call():
            nonlocal call_ended, max_duration_warning_sent, inactivity_ended, last_activity_time, farewell_detected, agent_is_speaking
            
            while not call_ended:
                await asyncio.sleep(1)  # Check every second
                
                current_time = time.time()
                call_duration_seconds = current_time - call_start_time
                call_duration_minutes = call_duration_seconds / 60
                time_since_last_activity = current_time - last_activity_time
                
                # Check for farewell detection
                if farewell_detected and not agent_is_speaking:
                    logger.info("Farewell detected, agent response finished - proceeding to farewell message")
                    call_ended = True
                    break
                
                # Skip all checks while agent is speaking
                if agent_is_speaking:
                    continue
                
                # Check for maximum call duration warning
                max_duration_minutes = END_CALL_CONFIG["max_call_duration_minutes"]
                warning_threshold = max_duration_minutes - END_CALL_CONFIG["max_duration_warning_minutes"]
                
                if (not max_duration_warning_sent and 
                    call_duration_minutes >= warning_threshold and 
                    call_duration_minutes < max_duration_minutes):
                    max_duration_warning_sent = True
                    logger.info(f"Sending maximum duration warning at {call_duration_minutes:.1f} minutes")
                    await agent.say(END_CALL_CONFIG["max_duration_warning_message"], allow_interruptions=True)
                
                # Check for maximum call duration reached
                if call_duration_minutes >= max_duration_minutes:
                    logger.info(f"Maximum call duration reached: {call_duration_minutes:.1f} minutes")
                    await agent.say(END_CALL_CONFIG["max_duration_end_message"], allow_interruptions=False)
                    await asyncio.sleep(8)
                    call_ended = True
                    break
                
                # Check for inactivity timeout
                inactivity_timeout = END_CALL_CONFIG["inactivity_timeout_seconds"]
                
                if time_since_last_activity >= inactivity_timeout:
                    logger.info(f"Inactivity timeout: {time_since_last_activity:.1f}s of silence")
                    
                    # Capture the current activity time BEFORE saying anything
                    activity_time_before_message = last_activity_time
                    
                    # Say inactivity message (allow interruptions)
                    logger.info("Playing inactivity message to user")
                    await agent.say(END_CALL_CONFIG["inactivity_message"], allow_interruptions=True)
                    
                    # Check if user spoke during the message
                    if last_activity_time > activity_time_before_message:
                        logger.info("User interrupted inactivity message - continuing conversation")
                        continue  # Go back to monitoring
                    
                    # Wait additional time for user to respond after hearing the message
                    logger.info("Waiting 10 seconds for user response...")
                    for i in range(10):
                        await asyncio.sleep(1)
                        
                        # Check if user spoke during wait
                        if last_activity_time > activity_time_before_message:
                            logger.info(f"User responded after {i+1}s - continuing conversation")
                            break  # Exit the wait loop and continue monitoring
                    else:
                        # Loop completed without break = user never responded
                        # Check one final time
                        if last_activity_time > activity_time_before_message:
                            logger.info("User responded at last moment - continuing conversation")
                            continue
                        
                        # No response - disconnect
                        logger.info("No response detected after inactivity message, disconnecting NOW")
                        inactivity_ended = True
                        call_ended = True
                        break  # Exit the while loop immediately
                
        # CRITICAL: Send greeting IMMEDIATELY after agent starts
        # Start TTS generation as fast as possible - don't wait for monitor task
        greeting_start = time.time()
        greeting_message = Config.CALL.GREETING_MESSAGE
        logger.info(f"Starting greeting TTS generation immediately: {greeting_message[:50]}...")
        
        # Send greeting immediately - this queues TTS generation
        # The await here is necessary but TTS generation happens asynchronously
        await agent.say(greeting_message, allow_interruptions=True)
        
        greeting_time = (time.time() - greeting_start) * 1000
        logger.info(f"Greeting queued and TTS generation started in {greeting_time:.0f}ms")
        
        # Start the monitoring task AFTER greeting is queued (non-blocking)
        monitor_task = asyncio.create_task(monitor_call())
        
        # Wait for the call to end
        await monitor_task
        
        # If farewell intent was detected, send farewell message before disconnecting
        if farewell_detected:
            logger.info("Playing farewell message to user")
            # Use allow_interruptions=False to prevent user speech from interfering
            await agent.say(END_CALL_CONFIG["farewell_message"], allow_interruptions=True)
            # Wait for the farewell message to be fully spoken
            logger.info("Waiting for farewell message to complete")
            await asyncio.sleep(12)
            logger.info("Farewell message complete, initiating disconnect")
        elif inactivity_ended:
            # Inactivity message was already played in the monitor loop
            # Just wait a moment to ensure it completes, then disconnect
            logger.info("Inactivity timeout - message already played, proceeding to disconnect")
            await asyncio.sleep(2)
        
        # IMPORTANT: Finalize tracking and evaluation BEFORE disconnect
        # The disconnect causes the job to shut down, so we must do this first
        
        # End call tracking and generate summary
        try:
            cost_tracker.end_call()
            
            # Export to file using configured metrics directory
            metrics_file = os.path.join(Config.PATHS.METRICS_DIR, f"{call_id}.json")
            cost_tracker.export_to_file(metrics_file)
            
            # Print summary to console
            logger.info("\n" + "=" * 80)
            logger.info("FINAL CALL METRICS")
            logger.info("=" * 80)
            summary = cost_tracker.get_call_summary()
            logger.info(f"Call ID: {summary['call_id']}")
            logger.info(f"Duration: {summary['duration_seconds']:.1f}s")
            logger.info(f"Total Responses: {len(summary['responses'])}")
            logger.info(f"Total Cost: ${summary['total_cost']:.6f}")
            logger.info(f"  - STT:  ${summary['total_stt_cost']:.6f}")
            logger.info(f"  - LLM:  ${summary['total_llm_cost']:.6f}")
            logger.info(f"  - TTS:  ${summary['total_tts_cost']:.6f}")
            logger.info(f"  - LiveKit: ${summary['total_livekit_cost']:.6f}")
            logger.info(f"Metrics saved to: {metrics_file}")
            logger.info("=" * 80 + "\n")
            
            # AUTOMATIC EVALUATION - Trigger evaluation immediately after call ends
            try:
                logger.info("Starting automatic call evaluation...")
                
                # Use Labs-specific evaluator for comprehensive compliance tracking
                # LLM evaluation provides accurate sentiment, intent, and compliance analysis
                # Heuristic evaluation is faster but less accurate
                use_llm = Config.EVALUATION.USE_LLM_EVALUATION
                eval_method = "LLM-based (intelligent)" if use_llm else "Heuristic-based (pattern matching)"
                logger.info(f"Evaluation method: {eval_method}")
                
                # Prepare conversation data for LLM evaluation
                conversation_data = None
                if 'conversation_transcript' in summary and summary['conversation_transcript']:
                    conversation_data = {
                        'messages': summary['conversation_transcript']
                    }
                    logger.info(f"Captured {len(summary['conversation_transcript'])} conversation turns for evaluation")
                
                # Evaluate with conversation data for LLM-based analysis
                labs_evaluation = evaluate_labs_call_automatically(
                    summary, 
                    conversation_data=conversation_data,
                    use_llm=use_llm
                )
                
                logger.info("\n" + "=" * 80)
                logger.info("LABS MODULE CALL EVALUATION RESULTS")
                logger.info("=" * 80)
                logger.info("CORE METRICS:")
                logger.info(f"  User Sentiment: {labs_evaluation.user_sentiment.value}")
                logger.info(f"  Query Resolved: {labs_evaluation.query_resolved}")
                logger.info(f"  Escalation Required: {labs_evaluation.escalation_required}")
                logger.info(f"\nDOMAIN METRICS:")
                logger.info(f"  Query Category: {labs_evaluation.query_category.value}")
                logger.info(f"  Testing Phase: {labs_evaluation.testing_phase.value}")
                logger.info(f"\nCOMPLIANCE METRICS:")
                logger.info(f"  Medical Boundary Maintained: {labs_evaluation.medical_boundary_maintained}")
                logger.info(f"  Proper Disclaimer Given: {labs_evaluation.proper_disclaimer_given}")
                logger.info(f"\nCALL SUMMARY:")
                logger.info(f"  {labs_evaluation.call_summary}")
                
                if labs_evaluation.flags:
                    logger.warning(f"\nCOMPLIANCE FLAGS:")
                    for flag in labs_evaluation.flags:
                        logger.warning(f"  {flag}")
                
                logger.info(f"\nNotes: {labs_evaluation.notes}")
                logger.info("=" * 80 + "\n")
                
            except Exception as eval_error:
                logger.error(f"Error during automatic evaluation: {eval_error}", exc_info=True)
            
        except Exception as tracking_error:
            logger.error(f"Error finalizing cost tracking: {tracking_error}")
        
        # Disconnect from the room AFTER finalization - this triggers job shutdown
        logger.info("Disconnecting from room NOW")
        try:
            await ctx.room.disconnect()
            logger.info("Room disconnected successfully")
        except Exception as disconnect_error:
            logger.warning(f"Disconnect error (may be expected): {disconnect_error}")


    except Exception as e:
        # Handle DuplexClosed errors on Windows (known IPC watcher issue)
        is_duplex_closed = (
            (DuplexClosed and isinstance(e, DuplexClosed)) or
            "DuplexClosed" in type(e).__name__ or
            "duplex_unix" in str(type(e).__module__)
        )
        if sys.platform == "win32" and is_duplex_closed:
            logger.debug("DuplexClosed error caught (non-fatal on Windows)", exc_info=True)
            return
        logger.error(f"Error in entrypoint: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # Force unbuffered output immediately
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')
        except:
            pass
    
    # Check if this is a download-files command (used during Docker build)
    # Skip credential validation for this command since env vars aren't available at build time
    is_download_files = len(sys.argv) > 1 and sys.argv[1] == "download-files"
    
    try:
        # CRITICAL: Print to stderr first (usually not buffered) to ensure visibility
        import sys
        sys.stderr.write("\n" + "=" * 80 + "\n")
        sys.stderr.write("STARTING GROQ VOICE ASSISTANT\n")
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.flush()
        
        # Also print to stdout
        print("\n" + "=" * 80, file=sys.stdout, flush=True)
        print("STARTING GROQ VOICE ASSISTANT", file=sys.stdout, flush=True)
        print("=" * 80, file=sys.stdout, flush=True)
        
        # Log startup information
        logger.info("=" * 80)
        logger.info("STARTING GROQ VOICE ASSISTANT")
        logger.info("=" * 80)
        logger.info(f"Agent Name: {Config.AGENT.AGENT_NAME}")
        logger.info(f"STT Model: {Config.MODELS.STT_MODEL}")
        logger.info(f"LLM Model: {Config.MODELS.LLM_MODEL}")
        logger.info(f"TTS Model: {Config.MODELS.TTS_MODEL} (voice: {Config.MODELS.TTS_VOICE})")
        
        # Print config to both stdout and stderr for maximum visibility
        config_info = f"""
Configuration:
  Agent Name: {Config.AGENT.AGENT_NAME}
  STT Model: {Config.MODELS.STT_MODEL}
  LLM Model: {Config.MODELS.LLM_MODEL}
  TTS Model: {Config.MODELS.TTS_MODEL} (voice: {Config.MODELS.TTS_VOICE})
"""
        sys.stderr.write(config_info)
        sys.stderr.flush()
        print(config_info, file=sys.stdout, flush=True)
        
        # Validate credentials (skip for download-files command during Docker build)
        if not is_download_files:
            if not Config.LIVEKIT.validate():
                error_msg = "LiveKit credentials are missing or invalid!"
                sys.stderr.write(f"ERROR: {error_msg}\n")
                sys.stderr.flush()
                print(f"ERROR: {error_msg}", file=sys.stdout, flush=True)
                logger.error(error_msg)
                logger.error("Please set LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET in .env")
                sys.exit(1)
            
            if not Config.GROQ.validate():
                warning_msg = "Groq API key is missing - some features may not work"
                sys.stderr.write(f"WARNING: {warning_msg}\n")
                sys.stderr.flush()
                print(f"WARNING: {warning_msg}", file=sys.stdout, flush=True)
                logger.warning(warning_msg)
                logger.warning("Please set GROQ_API_KEY in .env for full functionality")
        else:
            logger.info("Running download-files command - skipping credential validation")
        
        logger.info("=" * 80)
        logger.info("Starting agent...")
        logger.info("=" * 80)
        
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.write("Starting agent and connecting to LiveKit...\n")
        sys.stderr.write("=" * 80 + "\n")
        sys.stderr.flush()
        print("=" * 80, file=sys.stdout, flush=True)
        print("Starting agent and connecting to LiveKit...", file=sys.stdout, flush=True)
        print("=" * 80, file=sys.stdout, flush=True)
        
        cli.run_app(
            WorkerOptions(
                entrypoint_fnc=entrypoint,
                prewarm_fnc=prewarm,
                agent_name=Config.AGENT.AGENT_NAME,  # Unique name to identify this agent
            )
        )
    except KeyboardInterrupt:
        # KeyboardInterrupt is normal when stopping the agent
        logger.info("Agent stopped by user")
    except Exception as e:
        # Handle DuplexClosed errors gracefully on Windows
        is_duplex_closed = (
            (DuplexClosed and isinstance(e, DuplexClosed)) or
            "DuplexClosed" in type(e).__name__ or
            "duplex_unix" in str(type(e).__module__)
        )
        if sys.platform == "win32" and is_duplex_closed:
            logger.info("Agent stopped (DuplexClosed error is non-fatal on Windows)")
        else:
            logger.error(f"Agent failed to start: {e}", exc_info=True)
            raise
