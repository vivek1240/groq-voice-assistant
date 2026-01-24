# Cost Calculation and Latency Monitoring System

This system provides comprehensive cost tracking and latency monitoring for the Groq Voice Assistant.

## Features

### Cost Tracking
- **STT (Speech-to-Text)**: Cost per minute of audio processed
- **LLM (Large Language Model)**: Cost per input/output tokens
- **TTS (Text-to-Speech)**: Cost per character processed
- **VAPI (Voice Platform)**: Per-minute platform costs

### Latency Tracking
- **STT Latency**: Time from speech end to transcript available
- **LLM Latency**: Time from prompt sent to response received (TTFT - Time To First Token)
- **TTS Latency**: Time from text sent to audio ready
- **End-to-End Latency**: Total response time (user speaks → agent responds)

## Files

- `cost_tracker.py`: Core cost tracking implementation
- `advanced_cost_tracker.py`: Enhanced tracker with LiveKit integration
- `main.py`: Integrated agent with cost tracking enabled

## Usage

### Basic Usage

The cost tracker is automatically initialized when a call starts:

```python
from cost_tracker import CostTracker

# Initialize tracker
tracker = CostTracker(call_id="call_123")

# Track a response
tracker.start_response()

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

# End response
tracker.end_response()

# End call
tracker.end_call()

# Get summary
summary = tracker.get_call_summary()
print(f"Total cost: ${summary['total_cost']:.6f}")
```

### Output Format

#### Per-Response Summary (Logged During Call)

```
================================================================================
RESPONSE SUMMARY: call_room_abc_response_1
================================================================================
  STT: 3.50s audio, 823ms latency, $0.001167
  LLM: 245 in / 89 out tokens, 187ms latency, $0.000215
  TTS: 312 chars, 341ms latency, $0.003120
  End-to-End: 1351ms
  Total Cost: $0.004502
================================================================================
```

#### Per-Call Summary (Logged at Call End)

```
================================================================================
CALL SUMMARY: call_room_abc_12345678
================================================================================
Duration: 127.3s
Total Responses: 8

USAGE:
  STT: 45.23s audio
  LLM: 1847 input tokens, 634 output tokens
  TTS: 2145 characters

COSTS:
  STT:  $0.015077
  LLM:  $0.001589
  TTS:  $0.021450
  VAPI: $0.106083
  --------------
  TOTAL: $0.144199

AVERAGE LATENCIES:
  STT: 798ms
  LLM: 203ms
  TTS: 359ms
  End-to-End: 1360ms
================================================================================
```

#### JSON Export

Metrics are automatically exported to `metrics/{call_id}.json`:

```json
{
  "call_id": "call_room_abc_12345678",
  "start_timestamp": "2026-01-23T10:15:30.123456",
  "end_timestamp": "2026-01-23T10:17:37.456789",
  "duration_seconds": 127.3,
  "responses": [
    {
      "response_id": "call_room_abc_12345678_response_1",
      "timestamp": "2026-01-23T10:15:32.000000",
      "stt": {
        "model": "whisper-large-v3-turbo",
        "duration_seconds": 3.5,
        "cost": 0.001167,
        "latency_ms": 823,
        "transcript_length": 45,
        "timestamp": "2026-01-23T10:15:32.500000"
      },
      "llm": {
        "model": "llama-3.3-70b-versatile",
        "input_tokens": 245,
        "output_tokens": 89,
        "total_tokens": 334,
        "input_cost": 0.000145,
        "output_cost": 0.00007,
        "total_cost": 0.000215,
        "latency_ms": 187,
        "timestamp": "2026-01-23T10:15:33.000000"
      },
      "tts": {
        "model": "canopylabs/orpheus-v1-english",
        "characters_processed": 312,
        "cost": 0.00312,
        "latency_ms": 341,
        "audio_duration_seconds": 0.0,
        "timestamp": "2026-01-23T10:15:33.500000"
      },
      "end_to_end_latency_ms": 1351,
      "total_cost": 0.004502
    }
  ],
  "total_stt_cost": 0.015077,
  "total_llm_cost": 0.001589,
  "total_tts_cost": 0.02145,
  "total_vapi_cost": 0.106083,
  "total_cost": 0.144199,
  "total_stt_duration": 45.23,
  "total_llm_input_tokens": 1847,
  "total_llm_output_tokens": 634,
  "total_tts_characters": 2145,
  "avg_stt_latency_ms": 798,
  "avg_llm_latency_ms": 203,
  "avg_tts_latency_ms": 359,
  "avg_end_to_end_latency_ms": 1360
}
```

## Pricing Configuration

Pricing is configured in `cost_tracker.py` in the `PRICING` dictionary. Update these values based on your actual Groq pricing:

```python
PRICING = {
    "stt": {
        "whisper-large-v3-turbo": 0.02,  # $0.02 per minute
    },
    "llm": {
        "llama-3.3-70b-versatile": {
            "input": 0.00059,   # $0.59 per 1M input tokens
            "output": 0.00079,  # $0.79 per 1M output tokens
        },
    },
    "tts": {
        "canopylabs/orpheus-v1-english": 0.000010,  # $0.01 per 1K chars
    },
    "vapi": {
        "platform_per_minute": 0.05,  # $0.05 per minute
    }
}
```

## Metrics Directory

All call metrics are saved to the `metrics/` directory as JSON files:

```
agent/
├── main.py
├── cost_tracker.py
├── advanced_cost_tracker.py
└── metrics/
    ├── call_room_abc_12345678.json
    ├── call_room_def_87654321.json
    └── ...
```

## Integration with Main Agent

The cost tracker is integrated into `main.py` and automatically:

1. Initializes when a call starts
2. Tracks each user-agent interaction
3. Logs per-response summaries in real-time
4. Generates a comprehensive call summary when the call ends
5. Exports metrics to a JSON file

## Viewing Metrics

### Real-time Monitoring

Metrics are logged in real-time to the console with INFO level logging. You'll see:
- Individual response summaries after each interaction
- Final call summary when the call ends

### Post-Call Analysis

After a call ends, you can analyze the exported JSON file:

```python
import json

# Load metrics
with open('metrics/call_room_abc_12345678.json') as f:
    metrics = json.load(f)

# Analyze costs
print(f"Total cost: ${metrics['total_cost']:.4f}")
print(f"Cost per response: ${metrics['total_cost'] / len(metrics['responses']):.4f}")

# Analyze latencies
print(f"Average end-to-end latency: {metrics['avg_end_to_end_latency_ms']:.0f}ms")

# Find slowest response
slowest = max(metrics['responses'], key=lambda r: r['end_to_end_latency_ms'])
print(f"Slowest response: {slowest['end_to_end_latency_ms']:.0f}ms")
```

## Advanced Features

### Custom Analysis Scripts

You can create custom analysis scripts to:
- Aggregate metrics across multiple calls
- Track cost trends over time
- Identify performance bottlenecks
- Generate usage reports

### API Integration

The JSON export format can be easily integrated with:
- Analytics platforms
- Monitoring dashboards
- Billing systems
- Performance monitoring tools

## Troubleshooting

### Metrics Not Being Tracked

1. Check that `cost_tracker.py` is in the same directory as `main.py`
2. Verify the `metrics/` directory was created
3. Check logs for any error messages

### Inaccurate Token Counts

Token counts are estimated based on LiveKit callbacks. For more accurate tracking:
1. Enable detailed LLM logging
2. Capture actual token usage from Groq API responses
3. Update the tracking code to use real values

### Missing Latency Data

Latency tracking requires proper event sequencing:
1. Ensure `start_*` methods are called before operations
2. Ensure `end_*` methods are called after operations complete
3. Check that events are being triggered in the correct order

## Future Enhancements

Potential improvements:
- Real-time dashboard visualization
- Alert system for high costs or latencies
- Integration with Groq billing API for exact costs
- Historical trend analysis
- Cost optimization recommendations
- A/B testing support for different models

## Support

For issues or questions about cost tracking:
1. Check the logs for error messages
2. Verify pricing configuration matches your Groq plan
3. Review the exported JSON files for data accuracy
4. Consult LiveKit documentation for event details
