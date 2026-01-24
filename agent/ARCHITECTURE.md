# Cost Tracking System Architecture

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Voice Assistant                              │
│                           (main.py)                                  │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ Events
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Cost Tracker                                   │
│                     (cost_tracker.py)                                │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │     STT      │  │     LLM      │  │     TTS      │             │
│  │   Tracking   │  │   Tracking   │  │   Tracking   │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                      │
│  ┌────────────────────────────────────────────────────┐            │
│  │          Latency Measurement System                 │            │
│  │  (Start/End timing for all operations)             │            │
│  └────────────────────────────────────────────────────┘            │
│                                                                      │
│  ┌────────────────────────────────────────────────────┐            │
│  │          Cost Calculation Engine                    │            │
│  │  (Uses pricing_config.json)                        │            │
│  └────────────────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ Export
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Metrics Storage                              │
│                     (metrics/*.json files)                          │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ Analysis
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Analysis & Visualization                        │
│  ┌──────────────────┐    ┌──────────────────┐                     │
│  │ analyze_metrics  │    │ visualize_metrics│                     │
│  │      .py         │    │      .py         │                     │
│  └──────────────────┘    └──────────────────┘                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Call Initialization
```
User initiates call
    ↓
Agent starts (main.py)
    ↓
CostTracker initialized
    ↓
Call ID generated
    ↓
Start timestamp recorded
```

### 2. Per-Response Tracking
```
User speaks
    ↓
[START STT] → Timer starts
    ↓
STT processes audio
    ↓
[END STT] → Timer stops, cost calculated
    ↓
Transcript available
    ↓
[START LLM] → Timer starts
    ↓
LLM generates response
    ↓
[END LLM] → Timer stops, cost calculated
    ↓
Response text available
    ↓
[START TTS] → Timer starts
    ↓
TTS synthesizes audio
    ↓
[END TTS] → Timer stops, cost calculated
    ↓
Audio plays to user
    ↓
[END RESPONSE] → Total latency calculated
    ↓
Response metrics logged
```

### 3. Call Finalization
```
Call ends (user disconnects/timeout)
    ↓
End timestamp recorded
    ↓
VAPI cost calculated
    ↓
Aggregate metrics computed
    ↓
Call summary logged
    ↓
Metrics exported to JSON
```

## Component Details

### Cost Tracker Core (cost_tracker.py)

**Key Classes:**
- `CostTracker`: Main tracking coordinator
- `STTMetrics`: Speech-to-text metrics
- `LLMMetrics`: Language model metrics
- `TTSMetrics`: Text-to-speech metrics
- `VAPIMetrics`: Platform metrics
- `ResponseMetrics`: Per-response container
- `CallMetrics`: Per-call container

**Key Methods:**
```python
# Response tracking
start_response() → str           # Returns response_id
end_response() → None

# Component tracking
start_stt() → None
end_stt(duration, transcript, model) → None

start_llm() → None
end_llm(input_tokens, output_tokens, model) → None

start_tts() → None
end_tts(characters, model) → None

# Call tracking
end_call() → None
get_call_summary() → Dict
export_to_file(filepath) → None
```

### Event Integration (main.py)

**Events Tracked:**
```python
@agent.on("user_started_speaking")
    → start_response()
    → start_stt()

@agent.on("user_speech_committed")
    → end_stt()
    → start_llm()

@agent.on("agent_started_speaking")
    → end_llm()
    → start_tts()

@agent.on("agent_stopped_speaking")
    → end_tts()
    → end_response()

# On disconnect
    → end_call()
    → export_to_file()
```

### Pricing System (pricing_config.json)

**Structure:**
```json
{
  "pricing": {
    "stt": {
      "model_name": {
        "price_per_minute": float
      }
    },
    "llm": {
      "model_name": {
        "input_price_per_1k": float,
        "output_price_per_1k": float
      }
    },
    "tts": {
      "model_name": {
        "price_per_character": float
      }
    },
    "vapi": {
      "platform_cost": {
        "price_per_minute": float
      }
    }
  }
}
```

**Loading:**
```python
PRICING = load_pricing_config()
    ↓
Try loading pricing_config.json
    ↓
If success: Use config values
If fail: Use default values
```

### Analysis Tools

**analyze_metrics.py:**
```
Load JSON files
    ↓
Aggregate data
    ↓
Calculate statistics
    ↓
Display reports:
    - Cost analysis
    - Latency analysis
    - Usage analysis
```

**visualize_metrics.py:**
```
Load JSON files
    ↓
Process data
    ↓
Generate ASCII visualizations:
    - Bar charts
    - Histograms
    - Time series
```

## Metrics Schema

### Response Metrics
```json
{
  "response_id": "string",
  "timestamp": "ISO8601",
  "stt": {
    "model": "string",
    "duration_seconds": float,
    "cost": float,
    "latency_ms": float,
    "transcript_length": int
  },
  "llm": {
    "model": "string",
    "input_tokens": int,
    "output_tokens": int,
    "total_tokens": int,
    "input_cost": float,
    "output_cost": float,
    "total_cost": float,
    "latency_ms": float
  },
  "tts": {
    "model": "string",
    "characters_processed": int,
    "cost": float,
    "latency_ms": float
  },
  "end_to_end_latency_ms": float,
  "total_cost": float
}
```

### Call Metrics
```json
{
  "call_id": "string",
  "start_timestamp": "ISO8601",
  "end_timestamp": "ISO8601",
  "duration_seconds": float,
  "responses": [ResponseMetrics],
  "total_stt_cost": float,
  "total_llm_cost": float,
  "total_tts_cost": float,
  "total_vapi_cost": float,
  "total_cost": float,
  "total_stt_duration": float,
  "total_llm_input_tokens": int,
  "total_llm_output_tokens": int,
  "total_tts_characters": int,
  "avg_stt_latency_ms": float,
  "avg_llm_latency_ms": float,
  "avg_tts_latency_ms": float,
  "avg_end_to_end_latency_ms": float,
  "vapi": VAPIMetrics
}
```

## Cost Calculation Formulas

### STT (Speech-to-Text)
```
cost = (duration_seconds / 60) × price_per_minute

Example:
  30 seconds audio at $0.02/min
  = (30 / 60) × 0.02
  = 0.5 × 0.02
  = $0.01
```

### LLM (Large Language Model)
```
input_cost = (input_tokens / 1000) × input_price_per_1k
output_cost = (output_tokens / 1000) × output_price_per_1k
total_cost = input_cost + output_cost

Example:
  1500 input tokens at $0.00059/1K
  500 output tokens at $0.00079/1K
  = (1500/1000 × 0.00059) + (500/1000 × 0.00079)
  = (1.5 × 0.00059) + (0.5 × 0.00079)
  = 0.000885 + 0.000395
  = $0.00128
```

### TTS (Text-to-Speech)
```
cost = characters × price_per_character

Example:
  1000 characters at $0.00001/char
  = 1000 × 0.00001
  = $0.01
```

### VAPI (Voice Platform)
```
cost = (connection_seconds / 60) × price_per_minute

Example:
  120 seconds connection at $0.05/min
  = (120 / 60) × 0.05
  = 2 × 0.05
  = $0.10
```

## Latency Measurement

### Precision
```python
import time

start = time.time()      # High-precision timestamp
# ... operation ...
end = time.time()        # High-precision timestamp
latency_ms = (end - start) * 1000  # Convert to milliseconds
```

### Components Measured

**STT Latency:**
```
Time from: user_started_speaking
Time to:   user_speech_committed
Measures:  Speech recognition processing time
```

**LLM Latency (TTFT - Time To First Token):**
```
Time from: user_speech_committed (LLM start)
Time to:   agent_started_speaking
Measures:  Language model response generation time
```

**TTS Latency:**
```
Time from: agent_started_speaking (TTS start)
Time to:   agent_stopped_speaking
Measures:  Speech synthesis processing time
```

**End-to-End Latency:**
```
Time from: start_response()
Time to:   end_response()
Measures:  Complete user query to agent response cycle
```

## File Organization

```
groq-voice-assistant/
├── IMPLEMENTATION_SUMMARY.md      # Implementation overview
├── agent/
│   ├── main.py                    # Agent with cost tracking
│   ├── cost_tracker.py            # Core tracking system
│   ├── advanced_cost_tracker.py   # Enhanced tracking
│   ├── pricing_config.json        # Pricing configuration
│   ├── analyze_metrics.py         # Analysis tool
│   ├── visualize_metrics.py       # Visualization tool
│   ├── test_cost_tracker.py       # Test suite
│   ├── COST_TRACKING_README.md    # Complete documentation
│   ├── PRICING_UPDATE_GUIDE.md    # Pricing guide
│   ├── QUICK_START_COST_TRACKING.md  # Quick start
│   ├── ARCHITECTURE.md            # This file
│   └── metrics/                   # Exported metrics
│       ├── call_001.json
│       ├── call_002.json
│       └── ...
└── client/web/
    └── ... (unchanged)
```

## Extension Points

### Adding New Components

To track a new component (e.g., embedding model):

1. **Create metrics class:**
```python
@dataclass
class EmbeddingMetrics:
    model: str = ""
    input_tokens: int = 0
    cost: float = 0.0
    latency_ms: float = 0.0
    
    def calculate_cost(self):
        pricing = PRICING["embedding"][self.model]
        self.cost = (self.input_tokens / 1000) × pricing
```

2. **Add to ResponseMetrics:**
```python
@dataclass
class ResponseMetrics:
    # ... existing fields ...
    embedding: Optional[EmbeddingMetrics] = None
```

3. **Add tracking methods:**
```python
def start_embedding(self):
    self.embedding_latency.start()

def end_embedding(self, tokens, model):
    latency = self.embedding_latency.end()
    # ... create EmbeddingMetrics ...
```

4. **Update pricing config:**
```json
{
  "embedding": {
    "model-name": {
      "price_per_1k": 0.0001
    }
  }
}
```

### Custom Analysis

Create custom analysis scripts:

```python
import json
from pathlib import Path

# Load all metrics
metrics_dir = Path("metrics")
calls = []
for file in metrics_dir.glob("*.json"):
    with open(file) as f:
        calls.append(json.load(f))

# Custom analysis
total_cost = sum(call["total_cost"] for call in calls)
avg_latency = sum(call["avg_end_to_end_latency_ms"] 
                  for call in calls) / len(calls)

print(f"Total cost across all calls: ${total_cost:.2f}")
print(f"Average latency: {avg_latency:.0f}ms")
```

## Performance Considerations

### Overhead
- **Per-call overhead:** ~1-2ms for initialization
- **Per-response overhead:** ~0.1-0.5ms for tracking
- **Export overhead:** ~10-50ms (depends on call length)

### Memory Usage
- **Active tracking:** ~1-5KB per response
- **Call metrics:** ~10-100KB per call (depends on responses)
- **JSON export:** Similar to in-memory size

### Optimization Tips
1. Metrics are only exported at call end (no I/O during call)
2. Use async/await for non-blocking operations
3. Batch analysis for multiple calls
4. Consider database storage for very large datasets

## Security Considerations

### Data Privacy
- All metrics stored locally
- No PII in default tracking
- Transcript text can be excluded if needed

### File Permissions
- Metrics directory should be read-protected
- JSON files may contain conversation metadata
- Consider encryption for sensitive environments

### Configuration Security
- pricing_config.json is plain text
- Version control: Consider .gitignore for custom pricing
- No secrets or API keys stored in metrics
