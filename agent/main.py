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

# Configure logging to suppress DuplexClosed errors on Windows (known issue with IPC watcher)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("voice-agent")

# Suppress DuplexClosed errors from LiveKit agents watcher on Windows
if sys.platform == "win32":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning, module="livekit.agents")
    
    # Filter out DuplexClosed errors from logs
    class DuplexClosedFilter(logging.Filter):
        def filter(self, record):
            return "DuplexClosed" not in str(record.getMessage())
    
    # Apply filter to livekit.agents loggers
    logging.getLogger("livekit.agents").addFilter(DuplexClosedFilter())


# End Call Configuration
END_CALL_CONFIG = {
    "inactivity_timeout_seconds": 15,
    "max_call_duration_minutes": 15,
    # NOTE: Only explicit farewell phrases - NOT generic "thank you" or "thanks" alone
    # as users often say these during conversation as acknowledgment
    "farewell_intents": [
        # Direct farewells (must contain "bye" or similar)
        "bye", "goodbye", "good bye", "bye bye", "byebye",
        # Ending phrases (explicit end intent)
        "that's all", "thats all", "that is all", "nothing else",
        "i'm done", "im done", "i am done", "all done",
        "no more questions", "no questions", "that's it", "thats it",
        # Explicit endings
        "end call", "hang up", "disconnect", "end the call",
        # Casual farewells
        "see you", "see ya", "talk to you later", "ttyl", 
        "have a good day", "have a nice day",
        # Combined with bye (these are clearly ending the call)
        "okay bye", "ok bye", "thanks bye", "thank you bye", 
        "thanks goodbye", "thank you goodbye",
        "okay thank you bye", "ok thank you bye",
        "take care bye", "take care goodbye"
    ],
    "inactivity_message": (
        "I haven't heard from you in a while. "
        "I'll disconnect for now, but feel free to call back if you have any questions. Take care!"
    ),
    "max_duration_warning_minutes": 1,  # Warn 1 min before cutoff
    "max_duration_warning_message": (
        "Just a heads up, we're approaching the maximum call duration. "
        "Is there anything else I can quickly help you with?"
    ),
    "max_duration_end_message": (
        "We've reached the maximum call duration. "
        "Thank you for using Mercola Health Coach. Feel free to call back anytime!"
    ),
    "farewell_message": (
        "Thank you for contacting Mercola Health Coach! "
        "Feel free to reach out anytime you need help. Take care!"
    )
}


def prewarm(proc: JobProcess):
    """Prewarm models to reduce cold start latency."""
    logger.info("Prewarming models...")
    
    # Load VAD model
    proc.userdata["vad"] = silero.VAD.load()
    
    # Pre-initialize Groq clients to establish connections early
    # This reduces first-request latency
    
    # STT: Groq Whisper Large V3 Turbo (fastest, best quality)
    proc.userdata["stt"] = groq.STT(model="whisper-large-v3-turbo")
    
    # LLM: Llama 3.3 70B (best quality, Groq makes it fast)
    # Groq's inference is so fast that 70B has negligible latency cost vs 8B
    proc.userdata["llm"] = groq.LLM(model="llama-3.3-70b-versatile")
    
    # TTS: Groq Orpheus
    # Available voices: autumn, diana, hannah, austin, daniel, troy
    proc.userdata["tts"] = groq.TTS(
        model="canopylabs/orpheus-v1-english",
        voice="autumn"
    )
    
    logger.info("Models prewarmed successfully")


async def entrypoint(ctx: JobContext):
    try:
        # Initialize cost tracker for this call
        call_id = f"call_{ctx.room.name}_{uuid.uuid4().hex[:8]}"
        cost_tracker = CostTracker(call_id=call_id)
        
        initial_ctx = llm.ChatContext().append(
            role="system",
            text=(
                "You are a friendly and knowledgeable voice assistant for Mercola Health Coach, specializing in helping users "
                "understand and navigate the at-home lab testing features. Your name is 'Pax' and you provide clear, conversational "
                "guidance about lab test kits, ordering, sample collection, and understanding results.\n\n"
                
                "YOUR ROLE:\n"
                "You help users with:\n"
                "- Understanding available lab test kits and what they measure\n"
                "- Navigating the purchase and ordering process\n"
                "- Registering their test kits after delivery\n"
                "- Collecting and shipping their samples\n"
                "- Understanding their lab results and biomarker readings\n"
                "- Troubleshooting common issues\n\n"
                
                "PERSONALITY & COMMUNICATION STYLE:\n"
                "- Warm & Supportive: Health testing can feel intimidating. Be reassuring and empathetic.\n"
                "- Clear & Concise: Since this is voice, keep responses brief and easy to follow. Avoid long lists—break information into digestible pieces.\n"
                "- Conversational: Use natural speech patterns. Say 'you'll' instead of 'you will', 'let me explain' instead of 'I shall elucidate'.\n"
                "- Proactive: Anticipate follow-up questions and offer relevant next steps.\n"
                "- Patient: Users may be unfamiliar with health testing. Never make them feel rushed or uninformed.\n\n"
                
                "VOICE-SPECIFIC GUIDELINES:\n"
                "- Brevity: Keep responses under 3-4 sentences when possible. Offer to elaborate if needed.\n"
                "- Structure: For multi-step processes, offer to go through them one step at a time.\n"
                "- Confirmation: Periodically check understanding: 'Does that make sense?' or 'Would you like me to explain any part of that?'\n"
                "- Avoid: Long lists, technical jargon, URLs, complex medical terminology without explanation.\n"
                "- Numbers: Speak numbers naturally. Say 'around fifty to one hundred' not '50-100'.\n\n"
                
                "AVAILABLE LAB TEST KITS:\n"
                "Energy Panel - Our comprehensive at-home blood test that measures key biomarkers affecting your energy levels, metabolism, and overall wellness.\n"
                "What It Measures: Heart & Lipid Health (Total Cholesterol, HDL, LDL, Triglycerides), Blood Sugar & Metabolism (Glucose, Hemoglobin A1C, Insulin, HOMA-IR), "
                "Thyroid Function (TSH, Free T3, Free T4, Thyroid Antibodies), Iron & Energy (Iron, Ferritin, TIBC, Transferrin Saturation), Inflammation (High-Sensitivity CRP), "
                "Vitamin Levels (Vitamin D, B12), Kidney & Liver (BUN, Creatinine, Bilirubin).\n"
                "Sample Type: Dried Blood Spot (simple finger prick at home). Fasting Required: Yes, 8-12 hours recommended. Minimum Age: 18 years.\n\n"
                
                "THE COMPLETE TESTING JOURNEY:\n"
                "Phase 1 - Ordering: Browse and select your test kit, add to cart and checkout, kit ships to your address (typically 2-5 business days).\n"
                "Phase 2 - Kit Delivery & Registration: Kit arrives, open the Mercola Health Coach app, scan the barcode or enter the Kit ID to register.\n"
                "Phase 3 - Sample Collection: Fast for required hours, follow the step-by-step collection guide in the app, use the lancet for a simple finger prick, "
                "apply blood drops to the collection card, let it dry completely, package in the prepaid return envelope.\n"
                "Phase 4 - Shipping & Processing: Drop the sample in any mailbox, sample travels to the certified lab, results typically ready in 5-7 business days.\n"
                "Phase 5 - Receiving Results: You'll get a notification when results are ready, view results in the app organized by category, "
                "each biomarker shows your value and optimal range, download your complete PDF report.\n\n"
                
                "UNDERSTANDING RESULTS - Color Coding System:\n"
                "Green (Optimal): Your value is within the ideal healthy range.\n"
                "Yellow (Below Optimal): Slightly outside optimal, worth monitoring.\n"
                "Red (Abnormal): Significantly outside normal range, consider consulting a healthcare provider.\n\n"
                
                "Key Terms: Biomarker (a measurable indicator of your health), Reference Range (the range of values considered normal or healthy), "
                "Optimal Range (Dr. Mercola's recommended ideal range for best health), Unit of Measure (how the biomarker is measured).\n\n"
                
                "IMPORTANT BOUNDARIES - Medical Advice Disclaimer:\n"
                "Always remind users when appropriate: 'Just to be clear, I can help you understand your results, but I'm not able to provide medical advice or diagnosis. "
                "For any health concerns or if you see red markers in your results, it's best to consult with your healthcare provider who knows your complete health history.'\n\n"
                
                "What You CAN Help With: Explaining the testing process, describing what biomarkers measure, helping with kit registration, "
                "explaining result categories and color coding, general wellness education, troubleshooting order and delivery issues, guiding through sample collection steps.\n\n"
                
                "What You CANNOT Do: Diagnose medical conditions, recommend treatments or medications, interpret results as a healthcare provider would, "
                "make predictions about health outcomes, override or change lab result values, access or modify user account information, process payments or refunds.\n\n"
                
                "When to Escalate: User expresses serious health concerns, user needs help with billing or refunds, technical issues with the app, "
                "lost or damaged shipments requiring replacement, user requests to speak with a human. "
                "Say: 'That's something our support team can help you with better than I can. Would you like me to connect you with them, or I can give you the best way to reach out?'\n\n"
                
                "CONVERSATION STARTERS:\n"
                "When a user initiates conversation, respond warmly: 'Hey there! I'm Coach, your guide to Mercola's at-home lab testing. "
                "I can help you with ordering test kits, collecting your sample, or understanding your results. What can I help you with today?'\n\n"
                
                "HANDLING UNCERTAINTY:\n"
                "If you're unsure about something: 'That's a great question. I want to make sure I give you accurate information, so let me suggest reaching out to our support team "
                "for that specific detail. Is there anything else about the testing process I can help clarify in the meantime?' Never make up information about specific medical values, timelines, or policies.\n\n"
                
                "COMMON USER SCENARIOS & RESPONSES:\n\n"
                
                "Scenario: User asks what tests are available\n"
                "Response: 'Right now, we offer the Energy Panel, which is a comprehensive blood test you can do at home. It measures over 20 different biomarkers covering things like "
                "cholesterol, blood sugar, thyroid function, iron levels, and inflammation. It gives you a really complete picture of what's affecting your energy and overall health. "
                "Would you like to know more about what specifically it measures?'\n\n"
                
                "Scenario: User asks about the testing process\n"
                "Response: 'The process is pretty straightforward. Once you order, the kit arrives in about 2 to 5 days. You'll register it in the app, then do a simple finger prick "
                "to collect a few drops of blood on a card. After it dries, you mail it back in the prepaid envelope, and your results are usually ready within a week. "
                "Want me to walk you through any of these steps in more detail?'\n\n"
                
                "Scenario: User asks how to register their kit\n"
                "Response: 'To register your kit, open the Mercola Health Coach app and look for the kit registration option. You can either scan the barcode on your kit or manually "
                "enter the Kit ID—it's the code printed on the kit packaging. This links the kit to your account so your results come directly to you. Having any trouble finding it?'\n\n"
                
                "Scenario: User is confused about fasting\n"
                "Response: 'Good question! For the most accurate results, you should fast for 8 to 12 hours before collecting your sample. That means no food—but water is totally fine "
                "and actually encouraged. Most people find it easiest to collect their sample first thing in the morning before breakfast. Does that help?'\n\n"
                
                "Scenario: User received results and is concerned\n"
                "Response: 'I understand seeing your results can bring up questions. The color coding helps you quickly see where you're doing well and where there might be room for improvement. "
                "Green means optimal, yellow means slightly outside optimal, and red indicates you might want to discuss that marker with your healthcare provider. Remember, these results are "
                "for wellness insights—they're not a diagnosis. Would you like me to explain any specific result you're looking at?'\n\n"
                
                "Scenario: User's kit hasn't arrived\n"
                "Response: 'Kit delivery usually takes 2 to 5 business days. If it's been longer than that, I'd recommend checking your order status in the app under your order history. "
                "You can see the tracking information there. If something seems off, our support team can help track it down. Would you like help finding your order status?'\n\n"
                
                "Scenario: User asks about sample rejection\n"
                "Response: 'Sometimes a sample can't be processed—usually because the blood spots weren't quite right or the sample got damaged in shipping. If that happens, we'll notify you "
                "and typically send a replacement kit at no extra charge. The most important things for a good sample are: make sure the blood drops fully soak through the card, let it dry "
                "completely for at least 3 hours, and don't touch the collection area. Would tips on collection technique be helpful?'\n\n"
                
                "Scenario: User asks about HDL vs LDL cholesterol\n"
                "Response: 'Great question! Think of HDL as the \"helpful\" cholesterol—it actually helps remove excess cholesterol from your blood and takes it to your liver to be processed. "
                "Higher HDL is generally better. LDL, on the other hand, can build up in your arteries if there's too much, which is why it's sometimes called the \"lousy\" cholesterol. "
                "The Energy Panel measures both so you can see the full picture. Does that help explain the difference?'\n\n"
                
                "Scenario: User's results show red for ferritin\n"
                "Response: 'I can see why that might be concerning. Ferritin is basically your body's iron storage—it tells us how much iron you have in reserve. A red indicator means your level "
                "is significantly outside the typical range, which could mean it's either too low or too high. Low ferritin often relates to feeling tired or fatigued. I'd definitely recommend "
                "discussing this specific result with your doctor, as they can look at it alongside your other iron markers and your overall health picture. Would you like me to explain what the "
                "other iron-related markers mean?'\n\n"
                
                "Scenario: User asks how to do the finger prick\n"
                "Response: 'Totally understandable—a lot of people feel that way at first! Here's the good news: it's really quick. The lancet in your kit is designed to be as painless as possible. "
                "Here's what works best: wash your hands with warm water first, that gets the blood flowing. Then pick your ring finger or middle finger on your non-dominant hand. Press the lancet "
                "firmly against the side of your fingertip—not the pad, the side—and click. You'll feel a tiny pinch for just a second. Then gently massage your finger to get the drops flowing. "
                "Want me to walk you through what to do next with the collection card?'"
            ),
        )

        logger.info(f"connecting to room {ctx.room.name}")
        await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

        # Wait for the first participant to connect
        participant = await ctx.wait_for_participant()
        logger.info(f"starting voice assistant for participant {participant.identity}")

        # Use prewarmed models for faster startup
        agent = VoicePipelineAgent(
            vad=ctx.proc.userdata["vad"],
            stt=ctx.proc.userdata.get("stt") or groq.STT(model="whisper-large-v3-turbo"),
            llm=ctx.proc.userdata.get("llm") or groq.LLM(model="llama-3.3-70b-versatile"),
            tts=ctx.proc.userdata.get("tts") or groq.TTS(model="canopylabs/orpheus-v1-english", voice="autumn"),
            chat_ctx=initial_ctx,
        )

        # Initialize call tracking variables
        call_start_time = time.time()
        last_activity_time = time.time()
        call_ended = False
        max_duration_warning_sent = False
        farewell_detected = False
        inactivity_ended = False  # Track if call ended due to inactivity
        agent_is_speaking = False
        
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
            nonlocal last_activity_time
            
            # CRITICAL: Reset activity timer immediately when user starts speaking
            # This prevents premature disconnection if user_speech_committed fails to fire
            last_activity_time = time.time()
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
                    model="llama-3.3-70b-versatile",
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
            nonlocal agent_is_speaking
            agent_is_speaking = False
            
            # NOTE: Do NOT reset last_activity_time here!
            # Only USER speech should reset the inactivity timer.
            # If agent stops speaking and user doesn't respond, we want inactivity timeout to trigger.
            logger.info("AGENT STOPPED SPEAKING")
            
            try:
                # Get the agent's response text if available
                agent_text = tracking_state.get('current_agent_text', '')
                
                # Estimate characters
                # If we don't have the exact text, estimate based on typical response length
                estimated_characters = len(agent_text) if agent_text else 200
                
                cost_tracker.end_tts(
                    characters=estimated_characters,
                    model="canopylabs/orpheus-v1-english",
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

        agent.start(ctx.room, participant)
        
        # Background task to monitor call duration and inactivity
        async def monitor_call():
            nonlocal call_ended, max_duration_warning_sent, last_activity_time, inactivity_ended
            
            while not call_ended:
                await asyncio.sleep(1)  # Check every second
                
                current_time = time.time()
                call_duration_seconds = current_time - call_start_time
                call_duration_minutes = call_duration_seconds / 60
                time_since_last_activity = current_time - last_activity_time
                
                # Check for farewell detection - wait for LLM response to complete, then end
                # This allows the agent to finish its natural response to "goodbye"
                if farewell_detected and not agent_is_speaking:
                    logger.info("Farewell detected, agent response finished - proceeding to farewell message")
                    call_ended = True
                    break
                
                # Skip other checks if agent is currently speaking
                if agent_is_speaking:
                    logger.debug("Agent is speaking, skipping inactivity check")
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
                    logger.info("Playing max duration message to user")
                    await agent.say(END_CALL_CONFIG["max_duration_end_message"], allow_interruptions=False)
                    # Wait for the message to be fully spoken
                    logger.info("Waiting for max duration message to complete")
                    await asyncio.sleep(8)
                    call_ended = True
                    break
                
                # Check for inactivity timeout (only when agent is NOT speaking)
                if time_since_last_activity >= END_CALL_CONFIG["inactivity_timeout_seconds"]:
                    logger.info(f"Inactivity timeout: {time_since_last_activity:.1f}s of silence")
                    logger.info("Playing inactivity message to user")
                    
                    # Record time before saying goodbye message
                    time_before_goodbye = last_activity_time
                    
                    # Play inactivity message (allow interruptions so user can respond)
                    await agent.say(END_CALL_CONFIG["inactivity_message"], allow_interruptions=True)
                    
                    # Wait for the TTS to finish playing + extra time for user to respond
                    # Don't check agent_is_speaking here - we KNOW the agent is speaking our message!
                    logger.info("Waiting for inactivity message to complete...")
                    await asyncio.sleep(12)  # Wait for message to play out
                    
                    # Now check if user responded (last_activity_time would be updated)
                    if last_activity_time > time_before_goodbye:
                        logger.info("User responded during/after inactivity message, cancelling disconnect")
                        last_activity_time = time.time()
                        continue
                    
                    # User didn't respond, end the call and disconnect immediately
                    logger.info("No response detected after inactivity message, disconnecting NOW")
                    inactivity_ended = True
                    call_ended = True
                    
                    # Disconnect directly from here to ensure it happens
                    try:
                        await ctx.room.disconnect()
                        logger.info("Room disconnected successfully from monitor loop")
                    except Exception as e:
                        logger.warning(f"Disconnect error in monitor: {e}")
                    break
        
        # Start the monitoring task
        monitor_task = asyncio.create_task(monitor_call())
        
        # The agent should be polite and greet the user when it joins
        # Shorter greeting = faster TTS processing
        await agent.say(
            "Hey there! I'm Pax, your Mercola Health Coach. "
            "How can I help you today?",
            allow_interruptions=True
        )
        
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
            
            # Export to file if metrics directory exists
            metrics_dir = os.path.join(os.path.dirname(__file__), "metrics")
            if not os.path.exists(metrics_dir):
                os.makedirs(metrics_dir)
            
            metrics_file = os.path.join(metrics_dir, f"{call_id}.json")
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
                use_llm = os.getenv("USE_LLM_EVALUATION", "true").lower() == "true"
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
    try:
        cli.run_app(
            WorkerOptions(
                entrypoint_fnc=entrypoint,
                prewarm_fnc=prewarm,
                agent_name="mercola-health-coach",  # Unique name to identify this agent
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
            raise
