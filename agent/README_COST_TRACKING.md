# Cost Tracking & Latency Monitoring System

> Comprehensive cost calculation and performance monitoring for Groq Voice Assistant

## 🎯 Quick Links

- **[Quick Start](QUICK_START_COST_TRACKING.md)** - Get started in 5 minutes
- **[Complete Documentation](COST_TRACKING_README.md)** - Full system documentation
- **[Pricing Guide](PRICING_UPDATE_GUIDE.md)** - Update pricing configuration
- **[Architecture](ARCHITECTURE.md)** - System design and technical details
- **[Implementation Summary](../IMPLEMENTATION_SUMMARY.md)** - Overview of what was built

## 📊 What It Tracks

### Costs
✅ **STT** - Speech-to-Text processing costs  
✅ **LLM** - Large Language Model inference costs  
✅ **TTS** - Text-to-Speech synthesis costs  
✅ **VAPI** - Voice platform/connection costs  
✅ **Total** - Aggregate costs per response and per call  

### Latencies
✅ **STT Latency** - Speech recognition time  
✅ **LLM Latency** - Response generation time (TTFT)  
✅ **TTS Latency** - Audio synthesis time  
✅ **End-to-End** - Complete response cycle time  

### Analytics
✅ **Real-time logging** - Per-response summaries  
✅ **Call summaries** - Complete call breakdowns  
✅ **JSON export** - Detailed metrics files  
✅ **Multi-call analysis** - Aggregate statistics  
✅ **Visualizations** - Charts and graphs  

## 🚀 Quick Start

### 1. Run the Agent

Cost tracking is **automatically enabled**:

```bash
cd agent
python main.py dev
```

### 2. Make Some Calls

Use the voice assistant normally. All metrics are tracked automatically.

### 3. View Real-Time Metrics

Watch the console for real-time summaries:

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

### 4. Analyze Multiple Calls

```bash
# Complete analysis
python analyze_metrics.py

# Visualizations
python visualize_metrics.py
```

## 📁 Files Overview

```
agent/
├── 📊 Core System
│   ├── cost_tracker.py              # Main tracking engine
│   ├── advanced_cost_tracker.py     # Enhanced features
│   ├── pricing_config.json          # Pricing configuration
│   └── main.py                      # Integrated agent
│
├── 🔧 Tools
│   ├── analyze_metrics.py           # Analysis tool
│   ├── visualize_metrics.py         # Visualization tool
│   └── test_cost_tracker.py         # Test suite
│
├── 📖 Documentation
│   ├── README_COST_TRACKING.md      # This file
│   ├── QUICK_START_COST_TRACKING.md # Quick start guide
│   ├── COST_TRACKING_README.md      # Complete docs
│   ├── PRICING_UPDATE_GUIDE.md      # Pricing guide
│   └── ARCHITECTURE.md              # Technical design
│
└── 📂 Data
    └── metrics/                     # Exported JSON metrics
        ├── call_001.json
        ├── call_002.json
        └── ...
```

## 💻 Usage Examples

### Basic Usage

The system runs automatically. No code changes needed:

```python
# Just run the agent
python main.py dev

# Metrics are tracked automatically:
# ✓ Every user speech → STT tracking
# ✓ Every LLM response → LLM tracking
# ✓ Every agent speech → TTS tracking
# ✓ Call ends → Summary + JSON export
```

### Analysis

```bash
# Analyze all calls
python analyze_metrics.py --directory metrics/

# Show only costs
python analyze_metrics.py --costs

# Show only latencies
python analyze_metrics.py --latencies

# Show only usage stats
python analyze_metrics.py --usage

# Analyze single file
python analyze_metrics.py --file metrics/call_123.json
```

### Visualization

```bash
# Generate dashboard
python visualize_metrics.py --directory metrics/
```

Output example:
```
AVERAGE COST BREAKDOWN (per call)
================================================================================
STT                  ████████████████ 0.0151
LLM                  ██ 0.0016
TTS                  ██████████████████████ 0.0215
VAPI                 ████████████████████████████████████████████████ 0.1061
```

### Testing

```bash
# Run test suite
python test_cost_tracker.py

# Creates sample data for testing analysis tools
```

## 📊 Sample Output

### Real-Time Response Summary

```
================================================================================
RESPONSE SUMMARY: call_room_abc_12345678_response_1
================================================================================
  STT: 3.50s audio, 823ms latency, $0.001167
  LLM: 245 in / 89 out tokens, 187ms latency, $0.000215
  TTS: 312 chars, 341ms latency, $0.003120
  End-to-End: 1351ms
  Total Cost: $0.004502
================================================================================
```

### Call Summary (at end)

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

### Multi-Call Analysis

```
================================================================================
COST ANALYSIS
================================================================================

Total Calls: 15

AGGREGATE COSTS:
  Total across all calls: $2.1628
  Average per call: $0.1442
  Median per call: $0.1401
  Min per call: $0.0523
  Max per call: $0.2847

COST BREAKDOWN (Average per call):
  STT:  $0.0151 (10.5%)
  LLM:  $0.0016 (1.1%)
  TTS:  $0.0215 (14.9%)
  VAPI: $0.1061 (73.5%)
```

## 🔧 Configuration

### Update Pricing

Edit `pricing_config.json`:

```json
{
  "pricing": {
    "stt": {
      "whisper-large-v3-turbo": {
        "price_per_minute": 0.02
      }
    },
    "llm": {
      "llama-3.3-70b-versatile": {
        "input_price_per_1k": 0.00059,
        "output_price_per_1k": 0.00079
      }
    },
    "tts": {
      "canopylabs/orpheus-v1-english": {
        "price_per_character": 0.00001
      }
    },
    "vapi": {
      "platform_cost": {
        "price_per_minute": 0.05
      }
    }
  }
}
```

See [PRICING_UPDATE_GUIDE.md](PRICING_UPDATE_GUIDE.md) for details.

## 📈 Analytics

### Cost Analysis

```bash
python analyze_metrics.py --costs
```

Shows:
- Total costs across all calls
- Average, median, min, max per call
- Breakdown by component (STT, LLM, TTS, VAPI)
- Cost percentages
- Most expensive call

### Latency Analysis

```bash
python analyze_metrics.py --latencies
```

Shows:
- Average, median, min, max latencies
- Standard deviation
- Percentiles (P50, P95, P99)
- Distribution by component

### Usage Analysis

```bash
python analyze_metrics.py --usage
```

Shows:
- Total audio processed
- Total tokens used
- Total characters synthesized
- Averages per call and per response

## 🎨 Visualizations

```bash
python visualize_metrics.py
```

Generates:
- Cost breakdown bar charts
- Latency histograms
- Usage over time
- Token usage charts

## 🔍 Exported Data Format

Each call creates a JSON file in `metrics/`:

```json
{
  "call_id": "call_room_abc_12345678",
  "start_timestamp": "2026-01-23T10:15:30.123456",
  "end_timestamp": "2026-01-23T10:17:37.456789",
  "duration_seconds": 127.3,
  "total_cost": 0.144199,
  "total_stt_cost": 0.015077,
  "total_llm_cost": 0.001589,
  "total_tts_cost": 0.02145,
  "total_vapi_cost": 0.106083,
  "responses": [...],
  "avg_stt_latency_ms": 798,
  "avg_llm_latency_ms": 203,
  "avg_tts_latency_ms": 359,
  "avg_end_to_end_latency_ms": 1360
}
```

## 🧪 Testing

Comprehensive test suite included:

```bash
python test_cost_tracker.py
```

Tests:
- ✅ Basic tracking functionality
- ✅ Edge cases (empty responses)
- ✅ JSON export/import
- ✅ Cost calculations
- ✅ Latency measurements
- ✅ Sample data generation

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [QUICK_START_COST_TRACKING.md](QUICK_START_COST_TRACKING.md) | 5-minute quick start |
| [COST_TRACKING_README.md](COST_TRACKING_README.md) | Complete documentation |
| [PRICING_UPDATE_GUIDE.md](PRICING_UPDATE_GUIDE.md) | How to update pricing |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design details |
| [../IMPLEMENTATION_SUMMARY.md](../IMPLEMENTATION_SUMMARY.md) | Implementation overview |

## 🎯 Key Features

✅ **Zero Configuration** - Works out of the box  
✅ **Automatic Tracking** - No manual intervention  
✅ **Real-Time Logging** - See costs as they happen  
✅ **Detailed Analytics** - Deep insights into usage  
✅ **Flexible Pricing** - Easy to update via JSON  
✅ **Multiple Models** - Support for all Groq models  
✅ **Export to JSON** - Easy integration  
✅ **Analysis Tools** - Built-in reporting  
✅ **Visualizations** - Charts and graphs  
✅ **Production Ready** - Tested and reliable  

## 🚦 Status

✅ **Production Ready**  
✅ **All Tests Passing**  
✅ **Fully Documented**  
✅ **Integrated into Agent**  

## 💡 Tips

### For Cost Optimization

1. **Monitor your most expensive calls**
   ```bash
   python analyze_metrics.py --costs | grep "MOST EXPENSIVE"
   ```

2. **Track token usage trends**
   ```bash
   python analyze_metrics.py --usage
   ```

3. **Identify high-latency responses**
   ```bash
   python analyze_metrics.py --latencies | grep "Max:"
   ```

### For Performance Optimization

1. **Check P95/P99 latencies** to identify outliers
2. **Compare STT vs LLM vs TTS** to find bottlenecks
3. **Monitor end-to-end latency trends** over time

### For Budget Management

1. **Set up daily analysis** of costs
2. **Track cost per call** to stay within budget
3. **Export metrics** to billing system

## 🔗 Integration

### With Analytics Platforms

```python
import json
from pathlib import Path

# Load metrics
metrics_dir = Path("metrics")
for file in metrics_dir.glob("*.json"):
    with open(file) as f:
        data = json.load(f)
        # Send to your analytics platform
        send_to_analytics(data)
```

### With Billing Systems

```python
# Calculate daily costs
from datetime import date
import json

daily_cost = 0
for file in Path("metrics").glob("*.json"):
    with open(file) as f:
        data = json.load(f)
        if data["start_timestamp"].startswith(str(date.today())):
            daily_cost += data["total_cost"]

print(f"Today's cost: ${daily_cost:.2f}")
```

### With Monitoring Systems

```python
# Send alerts for high costs
if call_cost > THRESHOLD:
    send_alert(f"High cost call: ${call_cost:.2f}")
```

## 🛠️ Troubleshooting

### Metrics not being saved

1. Check that `metrics/` directory exists
2. Verify write permissions
3. Look for errors in logs

### Incorrect costs

1. Verify `pricing_config.json` has correct values
2. Check units (per minute vs per second, per 1K vs per 1M)
3. Run test suite: `python test_cost_tracker.py`

### Missing data

1. Ensure agent ran completely
2. Check for exceptions in logs
3. Verify all event handlers are registered

## 📝 Support

- **Documentation**: See linked guides above
- **Testing**: Run `python test_cost_tracker.py`
- **Logs**: Check console output for errors
- **Issues**: Review logs for error messages

## 🎉 Getting Started

Ready to use? Just 3 steps:

1. **Run the agent**: `python main.py dev`
2. **Make calls**: Use normally, metrics tracked automatically
3. **Analyze**: `python analyze_metrics.py`

That's it! 🚀

---

**Built for [Groq Voice Assistant](../README.md)**  
**Cost tracking system v1.0**
