# Quick Start: Cost Tracking

Get started with cost tracking in under 5 minutes!

## 1. Test the System

First, verify the cost tracking system works:

```bash
cd agent
python test_cost_tracker.py
```

This will:
- ✓ Run basic tracking tests
- ✓ Generate sample metrics
- ✓ Export test data to JSON

## 2. Run the Agent with Cost Tracking

Cost tracking is **automatically enabled** when you run the agent:

```bash
python main.py dev
```

The agent will:
- Track costs for every interaction
- Log real-time metrics to the console
- Save detailed metrics to `metrics/{call_id}.json`

## 3. View Cost Summary

After a call ends, you'll see a summary like this:

```
================================================================================
FINAL CALL METRICS
================================================================================
Call ID: call_room_abc_12345678
Duration: 127.3s
Total Responses: 8
Total Cost: $0.144199
  - STT:  $0.015077
  - LLM:  $0.001589
  - TTS:  $0.021450
  - VAPI: $0.106083
Metrics saved to: metrics/call_room_abc_12345678.json
================================================================================
```

## 4. Analyze Multiple Calls

After you have metrics from several calls:

```bash
# Complete analysis
python analyze_metrics.py --directory metrics/

# Just costs
python analyze_metrics.py --costs

# Just latencies
python analyze_metrics.py --latencies

# Visualizations
python visualize_metrics.py --directory metrics/
```

## 5. Update Pricing (Optional)

To update pricing for your specific plan:

1. Edit `pricing_config.json`
2. Update the prices for your models
3. Save and restart the agent

See `PRICING_UPDATE_GUIDE.md` for detailed instructions.

## What Gets Tracked?

### Costs
- **STT**: $0.02/minute (whisper-large-v3-turbo)
- **LLM**: $0.59/1M input + $0.79/1M output tokens (llama-3.3-70b)
- **TTS**: $0.01/1K characters (orpheus-v1-english)
- **VAPI**: $0.05/minute (platform cost)

### Latencies
- **STT Latency**: Time to transcribe speech
- **LLM Latency**: Time to generate response (TTFT)
- **TTS Latency**: Time to synthesize speech
- **End-to-End**: Total response time

## Real-Time Monitoring

Watch costs in real-time while the agent runs:

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

## Exported Data

Each call creates a JSON file in `metrics/` with complete details:

```json
{
  "call_id": "call_...",
  "duration_seconds": 127.3,
  "total_cost": 0.144199,
  "responses": [...],
  "avg_stt_latency_ms": 798,
  "avg_llm_latency_ms": 203,
  "avg_tts_latency_ms": 359
}
```

## Quick Commands

```bash
# Test the system
python test_cost_tracker.py

# Run agent with tracking
python main.py dev

# Analyze all calls
python analyze_metrics.py

# Show visualizations
python visualize_metrics.py

# Analyze specific file
python analyze_metrics.py --file metrics/call_123.json

# Show only costs
python analyze_metrics.py --costs
```

## Troubleshooting

### Metrics folder doesn't exist
The folder is created automatically on first run. If missing:
```bash
mkdir metrics
```

### No data showing up
- Check that the agent ran completely
- Look for error messages in the console
- Verify `cost_tracker.py` is in the same directory as `main.py`

### Costs seem wrong
- Update pricing in `pricing_config.json` to match your plan
- See `PRICING_UPDATE_GUIDE.md` for details

## Next Steps

- Read `COST_TRACKING_README.md` for full documentation
- Review `PRICING_UPDATE_GUIDE.md` to customize pricing
- Integrate metrics with your analytics platform
- Set up alerts for high costs

## Files Overview

```
agent/
├── main.py                          # Agent with cost tracking integrated
├── cost_tracker.py                  # Core tracking system
├── advanced_cost_tracker.py         # Enhanced tracking
├── pricing_config.json              # Pricing configuration
├── analyze_metrics.py               # Analysis tool
├── visualize_metrics.py             # Visualization tool
├── test_cost_tracker.py             # Testing script
├── COST_TRACKING_README.md          # Full documentation
├── PRICING_UPDATE_GUIDE.md          # Pricing guide
└── metrics/                         # Exported metrics
    ├── call_001.json
    ├── call_002.json
    └── ...
```

## Support

Need help?
1. Check the logs for error messages
2. Review the full documentation in `COST_TRACKING_README.md`
3. Run the test script to verify functionality
4. Check pricing configuration in `pricing_config.json`

---

**That's it!** Cost tracking is now running. Just use your voice assistant normally and metrics will be collected automatically. 🎉
