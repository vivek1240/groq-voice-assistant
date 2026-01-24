# Pricing Configuration Guide

This guide explains how to update pricing information for cost tracking.

## Overview

The cost tracking system uses pricing data to calculate costs for:
- **STT (Speech-to-Text)**: Charged per minute of audio
- **LLM (Large Language Model)**: Charged per input/output tokens
- **TTS (Text-to-Speech)**: Charged per character
- **VAPI (Voice Platform)**: Charged per minute of connection

## Configuration File

Pricing is configured in `pricing_config.json`. The system automatically loads this file on startup.

## Updating Pricing

### Method 1: Edit pricing_config.json (Recommended)

1. Open `pricing_config.json` in a text editor
2. Update the pricing values
3. Save the file
4. Restart the agent

**Example: Updating STT pricing**

```json
{
  "pricing": {
    "stt": {
      "whisper-large-v3-turbo": {
        "price_per_minute": 0.02,  // ← Change this value
        "description": "Groq Whisper Large v3 Turbo"
      }
    }
  }
}
```

**Example: Updating LLM pricing**

```json
{
  "pricing": {
    "llm": {
      "llama-3.3-70b-versatile": {
        "input_price_per_1k": 0.00059,   // ← Price per 1K input tokens
        "output_price_per_1k": 0.00079,  // ← Price per 1K output tokens
        "description": "Llama 3.3 70B"
      }
    }
  }
}
```

**Example: Adding a new model**

```json
{
  "pricing": {
    "llm": {
      "new-model-name": {
        "input_price_per_1k": 0.0010,
        "output_price_per_1k": 0.0015,
        "description": "New Model Description"
      }
    }
  }
}
```

### Method 2: Edit cost_tracker.py (Alternative)

If you prefer to hardcode pricing, you can modify the default values in `cost_tracker.py`:

1. Open `agent/cost_tracker.py`
2. Find the `load_pricing_config()` function
3. Update the `default_pricing` dictionary
4. Save and restart

## Pricing Sources

### Groq Pricing

Visit [https://groq.com/pricing](https://groq.com/pricing) for official Groq pricing.

**Common Groq Models:**

| Model | Input Price | Output Price |
|-------|-------------|--------------|
| llama-3.3-70b-versatile | $0.59/1M tokens | $0.79/1M tokens |
| llama-3.1-8b-instant | $0.05/1M tokens | $0.08/1M tokens |
| mixtral-8x7b-32768 | $0.24/1M tokens | $0.24/1M tokens |
| whisper-large-v3-turbo | ~$0.02/minute | N/A |

**Converting Groq pricing to config format:**

If Groq lists: "$0.59 per 1 million input tokens"
- Divide by 1000: $0.59 / 1000 = $0.00059
- Use this value for `input_price_per_1k`

### LiveKit Pricing

Visit [https://livekit.io/pricing](https://livekit.io/pricing) for official LiveKit pricing.

Platform costs typically include:
- Connection time
- Bandwidth usage
- Infrastructure costs

Update the `vapi.platform_cost.price_per_minute` value accordingly.

## Pricing Units

### STT (Speech-to-Text)
- **Unit**: Per minute of audio
- **Formula**: `cost = (audio_duration_seconds / 60) × price_per_minute`
- **Example**: 30 seconds at $0.02/min = (30/60) × $0.02 = $0.01

### LLM (Large Language Model)
- **Unit**: Per 1,000 tokens (separate for input/output)
- **Formula**: 
  - Input: `cost = (input_tokens / 1000) × input_price_per_1k`
  - Output: `cost = (output_tokens / 1000) × output_price_per_1k`
- **Example**: 
  - 1,500 input tokens at $0.00059/1K = 1.5 × $0.00059 = $0.000885
  - 500 output tokens at $0.00079/1K = 0.5 × $0.00079 = $0.000395
  - Total: $0.00128

### TTS (Text-to-Speech)
- **Unit**: Per character
- **Formula**: `cost = characters × price_per_character`
- **Example**: 1,000 chars at $0.00001/char = $0.01

### VAPI (Voice Platform)
- **Unit**: Per minute of connection
- **Formula**: `cost = (connection_duration_seconds / 60) × price_per_minute`
- **Example**: 2 minutes at $0.05/min = $0.10

## Token Estimation

For estimating token counts from text:
- **Rule of thumb**: 1 token ≈ 0.75 words or 4 characters
- **Example**: "Hello world" (2 words) ≈ 3 tokens

For more accurate token counting, consider using a tokenizer library like `tiktoken`.

## Verification

After updating pricing, verify the changes:

1. Run the test script:
```bash
python test_cost_tracker.py
```

2. Check that costs are calculated correctly:
```bash
python analyze_metrics.py --directory metrics/
```

3. Review the logs for any pricing-related warnings

## Pricing Change Log

Keep track of pricing updates:

| Date | Model | Old Price | New Price | Notes |
|------|-------|-----------|-----------|-------|
| 2026-01-23 | llama-3.3-70b | $0.59/1M | $0.59/1M | Initial config |
| | | | | |

## Troubleshooting

### Pricing not updating
- **Issue**: Changes to `pricing_config.json` not reflected
- **Solution**: Restart the agent process

### Missing model pricing
- **Issue**: Warning about missing pricing for a model
- **Solution**: Add the model to `pricing_config.json` with appropriate pricing

### Incorrect cost calculations
- **Issue**: Costs seem too high or too low
- **Solution**: 
  1. Verify pricing units (per minute vs per second, per 1K tokens vs per 1M tokens)
  2. Check the formula in the corresponding metrics class
  3. Test with known values using `test_cost_tracker.py`

## Best Practices

1. **Update regularly**: Check for pricing changes monthly
2. **Document changes**: Add entries to the pricing change log
3. **Test after updates**: Run test scripts to verify calculations
4. **Backup config**: Keep a backup of `pricing_config.json` before making changes
5. **Monitor costs**: Use analysis scripts to track actual vs expected costs

## Support

For issues with pricing configuration:
1. Check the logs for error messages
2. Verify JSON syntax in `pricing_config.json`
3. Compare with the example format in this guide
4. Test with default pricing by temporarily renaming the config file
