# Groq voice assistant with LiveKit Agents

This example shows a voice agent running a pipeline of STT, LLM, and TTS entirely on Groq's low-latency inference.

You'll need a Groq Cloud API key in order to run the demo.

In our testing, we were able to achieve the following latencies:

- STT `whisper-large-v3-turbo`: 800ms
- LLM TTFT `llama-3.3-70b-versatile`: 200ms
- TTS `playai-tts`: 350ms


## Run agent in a console tab

1. `cd agent`
2. `python -m venv .venv`
3. `source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. `cp .env.example .env`
6. populate `.env` with valid values for keys:
   ```env
   LIVEKIT_URL=...
   LIVEKIT_API_KEY=...
   LIVEKIT_API_SECRET=...
   GROQ_API_KEY=...               # Required for both agent and LLM evaluation
   USE_LLM_EVALUATION=true        # Enable intelligent evaluation (recommended)
   LABS_EVAL_MODEL=llama-3.3-70b-versatile  # Optional, defaults to this
   ```
   
   
7. `python main.py dev`

**On Windows (PowerShell):**
1. `cd agent`
2. `python -m venv .venv`
3. `.venv\Scripts\Activate.ps1`
4. `pip install -r requirements.txt`
5. `copy .env.example .env`
6. populate `.env` with valid values for keys (see above)
7. `python main.py dev`

**On Windows (Command Prompt):**
1. `cd agent`
2. `python -m venv .venv`
3. `.venv\Scripts\activate.bat`
4. `pip install -r requirements.txt`
5. `copy .env.example .env`
6. populate `.env` with valid values for keys (see above)
7. `python main.py dev`

## Run web client in another console tab

**On Linux/macOS:**
1. `cd client/web`
2. `pnpm i`
3. `cp .env.example .env.local`
4. populate `.env` with valid values for keys
5. `pnpm dev`

**On Windows (PowerShell):**
1. `cd client/web`
2. `pnpm i`
3. `copy .env.example .env.local`
4. populate `.env` with valid values for keys
5. `pnpm dev`

**On Windows (Command Prompt):**
1. `cd client/web`
2. `pnpm i`
3. `copy .env.example .env.local`
4. populate `.env` with valid values for keys
5. `pnpm dev`

## Start the app

1. open a browser and navigate to `http://localhost:3000`

## Monitoring and Analysis

### View Labs Module Evaluations (Primary)

After calls complete, view Labs-specific evaluation results:

```bash
# View CSV in Excel/Google Sheets
open agent/labs_evaluations/labs_call_evaluations.csv

# Generate compliance report
python agent/labs_evaluator.py agent/metrics/

# Enable LLM evaluation for better accuracy
export GROQ_API_KEY=your_key
python agent/labs_evaluator.py agent/metrics/ --llm
```

### View General Evaluations (Alternative)

```bash
# View CSV
open agent/evaluations/call_evaluations.csv

# Visualize in terminal
python agent/visualize_evaluations.py
```

### View Cost Metrics

Analyze cost and performance metrics:

```bash
# Analyze specific call
python agent/analyze_metrics.py agent/metrics/call_001.json

# Batch analyze all calls
python agent/analyze_metrics.py agent/metrics/
```

### Run Tests

```bash
# Test cost tracker
python agent/test_cost_tracker.py

# Test evaluation framework
python agent/test_call_evaluator.py
```


