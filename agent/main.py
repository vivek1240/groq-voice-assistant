import logging
import httpx
import asyncio
from datetime import datetime
from typing import Annotated

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

load_dotenv()
logger = logging.getLogger("voice-agent")


# Global reference to agent for end call functionality
_current_agent: VoicePipelineAgent | None = None
_current_ctx: JobContext | None = None


# Define function context for tool calling
class AssistantFnc(llm.FunctionContext):
    """
    Tool functions that the voice assistant can call.
    Based on official Groq documentation for tool use.
    """

    @llm.ai_callable()
    async def get_weather(
        self,
        location: Annotated[str, llm.TypeInfo(description="City and state/country, e.g., 'San Francisco, CA' or 'London, UK'")],
    ):
        """Get the current weather for a given location. Use this when user asks about weather."""
        logger.info(f"Getting weather for {location}")
        
        # Using Open-Meteo API (free, no API key needed)
        try:
            async with httpx.AsyncClient() as client:
                # First, geocode the location
                geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1"
                geo_response = await client.get(geo_url, timeout=10.0)
                geo_data = geo_response.json()
                
                if not geo_data.get("results"):
                    return f"Sorry, I couldn't find the location '{location}'. Please try a different city name."
                
                lat = geo_data["results"][0]["latitude"]
                lon = geo_data["results"][0]["longitude"]
                city_name = geo_data["results"][0]["name"]
                country = geo_data["results"][0].get("country", "")
                
                # Now get weather
                weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&temperature_unit=celsius"
                weather_response = await client.get(weather_url, timeout=10.0)
                weather_data = weather_response.json()
                
                current = weather_data["current"]
                temp_c = current["temperature_2m"]
                temp_f = (temp_c * 9/5) + 32
                humidity = current["relative_humidity_2m"]
                wind_speed = current["wind_speed_10m"]
                
                # Weather code mapping
                weather_codes = {
                    0: "clear sky",
                    1: "mainly clear", 2: "partly cloudy", 3: "overcast",
                    45: "foggy", 48: "foggy",
                    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
                    61: "light rain", 63: "rain", 65: "heavy rain",
                    71: "light snow", 73: "snow", 75: "heavy snow",
                    80: "light showers", 81: "showers", 82: "heavy showers",
                    95: "thunderstorm"
                }
                condition = weather_codes.get(current["weather_code"], "unknown conditions")
                
                return f"The weather in {city_name}, {country} is currently {condition} with a temperature of {temp_c:.1f}°C ({temp_f:.1f}°F), humidity at {humidity}%, and wind speed of {wind_speed} km/h."
                
        except Exception as e:
            logger.error(f"Weather API error: {e}")
            return f"Sorry, I couldn't fetch the weather right now. Please try again later."

    @llm.ai_callable()
    async def get_current_time(
        self,
        timezone: Annotated[str, llm.TypeInfo(description="Timezone like 'America/New_York', 'Europe/London', or 'Asia/Tokyo'. Use 'local' for current timezone.")] = "local",
    ):
        """Get the current date and time. Use this when user asks what time or date it is."""
        logger.info(f"Getting current time for timezone: {timezone}")
        
        try:
            from zoneinfo import ZoneInfo
            
            if timezone == "local":
                now = datetime.now()
                return f"The current date and time is {now.strftime('%A, %B %d, %Y at %I:%M %p')}."
            else:
                now = datetime.now(ZoneInfo(timezone))
                return f"The current date and time in {timezone} is {now.strftime('%A, %B %d, %Y at %I:%M %p')}."
        except Exception as e:
            logger.error(f"Time error: {e}")
            now = datetime.now()
            return f"The current date and time is {now.strftime('%A, %B %d, %Y at %I:%M %p')}."

    @llm.ai_callable()
    async def calculate(
        self,
        expression: Annotated[str, llm.TypeInfo(description="A mathematical expression to evaluate, e.g., '2 + 2', '15 * 7', 'sqrt(16)', '100 / 4'")],
    ):
        """Perform mathematical calculations. Use this when user asks to calculate something."""
        logger.info(f"Calculating: {expression}")
        
        try:
            import math
            # Safe evaluation with limited operations
            allowed_names = {
                'abs': abs, 'round': round, 'min': min, 'max': max,
                'sqrt': math.sqrt, 'pow': pow, 'sin': math.sin, 
                'cos': math.cos, 'tan': math.tan, 'pi': math.pi,
                'log': math.log, 'log10': math.log10, 'exp': math.exp
            }
            
            # Clean and evaluate expression
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            
            if isinstance(result, float):
                if result.is_integer():
                    return f"The result of {expression} is {int(result)}."
                else:
                    return f"The result of {expression} is {result:.4f}."
            return f"The result of {expression} is {result}."
            
        except Exception as e:
            logger.error(f"Calculation error: {e}")
            return f"Sorry, I couldn't calculate that expression. Please try a simpler format like '2 + 2' or 'sqrt(16)'."

    @llm.ai_callable()
    async def set_reminder(
        self,
        reminder_text: Annotated[str, llm.TypeInfo(description="What to remind the user about")],
        minutes: Annotated[int, llm.TypeInfo(description="Number of minutes from now for the reminder")] = 5,
    ):
        """Set a reminder for the user. Note: This is a demo - reminders won't persist after session ends."""
        logger.info(f"Setting reminder: '{reminder_text}' in {minutes} minutes")
        
        reminder_time = datetime.now()
        from datetime import timedelta
        reminder_time += timedelta(minutes=minutes)
        
        return f"I've noted your reminder: '{reminder_text}' for {reminder_time.strftime('%I:%M %p')}. Note: This is a demo, so the reminder won't persist after our conversation ends."

    @llm.ai_callable()
    async def end_conversation(
        self,
        farewell_reason: Annotated[str, llm.TypeInfo(description="Brief reason for ending: 'user_goodbye' if user said bye/goodbye/see you, 'task_complete' if user's request is fully resolved, 'user_request' if user explicitly asked to end")] = "user_goodbye",
    ):
        """
        End the voice conversation gracefully. Call this tool when:
        - User says goodbye, bye, see you, take care, have a good day, etc.
        - User says they're done, that's all, nothing else, I'm finished
        - User explicitly asks to end or hang up the call
        - User thanks you and indicates they're leaving (thanks, bye!)
        
        Do NOT call this just because you answered a question - only when the user signals they want to end.
        """
        global _current_agent, _current_ctx
        
        logger.info(f"End conversation triggered - reason: {farewell_reason}")
        
        # Schedule the disconnection after the farewell message is spoken
        async def delayed_disconnect():
            await asyncio.sleep(3)  # Wait for farewell to be spoken
            if _current_ctx:
                logger.info("Disconnecting from room...")
                await _current_ctx.room.disconnect()
        
        # Start the delayed disconnect task
        asyncio.create_task(delayed_disconnect())
        
        # Return farewell message based on reason
        farewells = {
            "user_goodbye": "Goodbye! It was nice chatting with you. Take care!",
            "task_complete": "Great, I'm glad I could help! Goodbye and have a wonderful day!",
            "user_request": "Alright, ending the call now. Goodbye!",
        }
        
        return farewells.get(farewell_reason, "Goodbye! Have a great day!")


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    global _current_agent, _current_ctx
    
    # Initialize function context for tool calling
    fnc_ctx = AssistantFnc()
    
    # Store context globally for end_conversation tool
    _current_ctx = ctx
    
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "Your name is Sylvia and you are a helpful voice assistant powered by Groq. "
            "You have access to tools that let you: get weather information, check the current time, "
            "perform calculations, set reminders, and end the conversation. "
            "\n\n"
            "IMPORTANT: Use the end_conversation tool when the user wants to end the call. "
            "Watch for signals like: 'goodbye', 'bye', 'see you', 'take care', 'that's all', "
            "'I'm done', 'thanks bye', 'have a good day', or any farewell. "
            "When you detect a farewell, call end_conversation BEFORE saying goodbye. "
            "\n\n"
            "Keep responses short and conversational since you're speaking, not writing. "
            "Avoid using punctuation that can't be spoken aloud."
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
        fnc_ctx=fnc_ctx,  # Enable tool calling
    )
    
    # Store agent globally
    _current_agent = agent

    @agent.on("metrics_collected")
    def _on_metrics_collected(mtrcs: metrics.AgentMetrics):
        metrics.log_metrics(mtrcs)

    agent.start(ctx.room, participant)
    
    # Greet the user with info about capabilities
    await agent.say(
        "Hey! I'm Sylvia, your voice assistant. I can help you with weather info, "
        "the current time, calculations, and reminders. Just say goodbye when you're done. "
        "What would you like to know?",
        allow_interruptions=True
    )


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            agent_name="groq-agent",  # Must match client's agentName dispatch
        )
    )
