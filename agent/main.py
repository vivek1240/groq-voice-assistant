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

# Import cost tracker
from cost_tracker import CostTracker

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
    proc.userdata["vad"] = silero.VAD.load()


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

        agent = VoicePipelineAgent(
            vad=ctx.proc.userdata["vad"],
            stt=groq.STT(model="whisper-large-v3-turbo"),
            llm=groq.LLM(model="llama-3.3-70b-versatile"),
            tts=groq.TTS(model="canopylabs/orpheus-v1-english", voice="autumn"),
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

        # Event handler for metrics collection
        @agent.on("metrics_collected")
        def _on_metrics_collected(mtrcs: metrics.AgentMetrics):
            metrics.log_metrics(mtrcs)
        
        # Cost tracking state
        tracking_state = {
            'current_user_text': '',
            'current_agent_text': '',
            'stt_start_time': 0,
            'llm_start_time': 0,
            'tts_start_time': 0,
        }
        
        # Cost tracking event handlers
        @agent.on("user_started_speaking")
        def _on_user_started_speaking():
            """User started speaking - start tracking response"""
            logger.debug("User started speaking - starting response tracking")
            cost_tracker.start_response()
            cost_tracker.start_stt()
            tracking_state['stt_start_time'] = time.time()
        
        @agent.on("user_speech_committed")
        def _on_user_speech_committed_for_cost(msg):
            """STT completed - track STT metrics"""
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
                logger.error(f"Error tracking STT metrics: {e}")
        
        @agent.on("agent_started_speaking")
        def _on_agent_started_speaking_for_cost():
            """Agent started speaking - this means LLM has responded"""
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
                    model="llama-3.3-70b-versatile"
                )
                
                # Start TTS tracking
                cost_tracker.start_tts()
                tracking_state['tts_start_time'] = time.time()
                
            except Exception as e:
                logger.error(f"Error tracking LLM metrics: {e}")
        
        @agent.on("agent_stopped_speaking")
        def _on_agent_stopped_speaking_for_cost():
            """Agent stopped speaking - TTS completed"""
            try:
                # Get the agent's response text if available
                agent_text = tracking_state.get('current_agent_text', '')
                
                # Estimate characters
                # If we don't have the exact text, estimate based on typical response length
                estimated_characters = len(agent_text) if agent_text else 200
                
                cost_tracker.end_tts(
                    characters=estimated_characters,
                    model="canopylabs/orpheus-v1-english"
                )
                
                # End response tracking
                cost_tracker.end_response()
                
                # Reset tracking state
                tracking_state['current_user_text'] = ''
                tracking_state['current_agent_text'] = ''
                
            except Exception as e:
                logger.error(f"Error tracking TTS metrics: {e}")
        
        # Try to capture agent's text responses
        @agent.on("agent_speech_committed")
        def _on_agent_speech_committed(msg):
            """Capture agent's speech text for metrics"""
            try:
                agent_text = ""
                if hasattr(msg, 'text'):
                    agent_text = msg.text
                elif hasattr(msg, 'content'):
                    agent_text = msg.content
                elif isinstance(msg, str):
                    agent_text = msg
                
                tracking_state['current_agent_text'] = agent_text
                
                # Update LLM output token estimate if we haven't ended the response yet
                if agent_text and cost_tracker.current_response:
                    output_tokens = int(len(agent_text.split()) / 0.75)
                    # Update the LLM metrics with better estimate
                    if cost_tracker.current_response.llm:
                        cost_tracker.current_response.llm.output_tokens = output_tokens
                        cost_tracker.current_response.llm.calculate_cost()
                
            except Exception as e:
                logger.error(f"Error capturing agent speech: {e}")
        
        # Event handler for user speech to track activity and detect farewells
        @agent.on("user_speech_committed")
        def _on_user_speech(msg):
            nonlocal last_activity_time, farewell_detected
            
            # If farewell already detected and we're in the process of ending, ignore new speech
            # This prevents user speech during farewell from restarting conversation
            if farewell_detected:
                logger.info("Ignoring user speech - farewell already detected, ending call")
                return
            
            last_activity_time = time.time()
            
            # Try to get text from different possible attributes
            user_text = None
            if hasattr(msg, 'text'):
                user_text = msg.text
            elif hasattr(msg, 'content'):
                user_text = msg.content
            elif isinstance(msg, str):
                user_text = msg
            
            logger.info(f"USER SPOKE: {user_text[:80] if user_text else 'N/A'}...")
            
            # Check for farewell intent in user's message
            # Note: We only set farewell_detected flag, NOT call_ended
            # The monitor loop will handle ending the call after farewell message
            if user_text and detect_farewell_intent(user_text):
                farewell_detected = True
                logger.info(f"FAREWELL DETECTED in: '{user_text}' - will end call after farewell message")
        
        # Track when agent starts speaking
        @agent.on("agent_started_speaking")
        def _on_agent_started():
            nonlocal agent_is_speaking
            agent_is_speaking = True
            logger.info("AGENT STARTED SPEAKING")
        
        # Track when agent stops speaking and reset timer
        @agent.on("agent_stopped_speaking")
        def _on_agent_stopped():
            nonlocal agent_is_speaking, last_activity_time
            agent_is_speaking = False
            # Don't reset timer if farewell was detected - we want to end the call
            if not farewell_detected:
                last_activity_time = time.time()
                logger.info("AGENT STOPPED SPEAKING - timer reset")
            else:
                logger.info("AGENT STOPPED SPEAKING - farewell mode, not resetting timer")

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
                    
                    # Play inactivity message (don't allow interruptions to ensure it completes)
                    await agent.say(END_CALL_CONFIG["inactivity_message"], allow_interruptions=True)
                    
                    # Wait for inactivity message to finish speaking first
                    logger.info("Waiting for inactivity message to complete...")
                    await asyncio.sleep(10)  # Wait for message to be spoken
                    
                    # Now check if user spoke DURING the message (their speech would update last_activity_time)
                    if last_activity_time > time_before_goodbye:
                        logger.info("User responded during inactivity message, cancelling disconnect")
                        # Reset the timer since conversation is continuing
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
        # The agent_speech_committed event will reset the timer after this completes
        await agent.say(
            "Hey there! I'm Pax, your guide to Mercola's at-home lab testing. "
            "I can help you with ordering test kits, collecting your sample, or understanding your results. "
            "What can I help you with today?",
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
        
        # Disconnect from the room - this should trigger onDisconnected on client
        logger.info("Disconnecting from room NOW")
        try:
            await ctx.room.disconnect()
            logger.info("Room disconnected successfully")
        except Exception as disconnect_error:
            logger.warning(f"Disconnect error (may be expected): {disconnect_error}")
        
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
            logger.info(f"  - VAPI: ${summary['total_vapi_cost']:.6f}")
            logger.info(f"Metrics saved to: {metrics_file}")
            logger.info("=" * 80 + "\n")
            
        except Exception as tracking_error:
            logger.error(f"Error finalizing cost tracking: {tracking_error}")


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
