import logging

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


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "You are a voice assistant powered by Groq. Your interface with users will be voice. "
            "You should use short and concise responses, avoiding usage of unpronounceable punctuation."
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

    @agent.on("metrics_collected")
    def _on_metrics_collected(mtrcs: metrics.AgentMetrics):
        metrics.log_metrics(mtrcs)

    agent.start(ctx.room, participant)
    
    # The agent should be polite and greet the user when it joins
    await agent.say("Hey, how can I help you today?", allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )
