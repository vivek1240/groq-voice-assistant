# Groq voice assistant with LiveKit Agents

This example shows a voice agent running a pipeline of STT, LLM, and TTS entirely on Groq's low-latency inference.

You'll need a Groq Cloud API key in order to run the demo.

In our testing, we were able to achieve the following latencies:

- STT `whisper-large-v3-turbo`: 800ms
- LLM TTFT `llama-3.3-70b-versatile`: 200ms
- TTS `playai-tts`: 350ms

## Features

### 🎯 Voice Assistant
- Real-time voice conversation with AI assistant
- Specialized in Mercola Health Coach lab testing
- Natural language understanding and responses

### 💰 Cost Tracking
- Automatic cost tracking for all API calls (STT, LLM, TTS, VAPI)
- Per-response and per-call cost analysis
- Detailed latency metrics
- JSON export for analysis
- See [agent/COST_TRACKING_README.md](agent/COST_TRACKING_README.md) for details

### 📊 Call Evaluation Framework

**Two Evaluation Systems:**

1. **Labs Module Evaluator** (Primary) - Healthcare-Specific
   - **🤖 LLM-Powered Evaluation** (Default) - Uses Groq LLM for intelligent analysis
   - **100% compliant** with Labs Module specification
   - **8 evaluation dimensions**: Core, Domain, Compliance metrics
   - **16 Labs-specific categories**: Test kit info, ordering, collection, results
   - **Medical compliance tracking**: Boundary violations, disclaimers (CRITICAL)
   - **Testing journey phases**: 8 phases from pre-purchase to results
   - **Regulatory ready**: HIPAA-aware, audit trail, compliance alerts
   - **Accurate sentiment & intent detection** via LLM analysis
   - See [agent/LABS_EVALUATION_README.md](agent/LABS_EVALUATION_README.md) for details
   - See [agent/LLM_EVALUATION_GUIDE.md](agent/LLM_EVALUATION_GUIDE.md) for LLM setup

2. **General Evaluator** (Available) - General-Purpose
   - **7 evaluation dimensions**: Accuracy, Flow, Intent, Task Completion, Sentiment, Latency, Cost
   - **User Satisfaction Score** (0-100) combining all dimensions
   - See [agent/EVALUATION_README.md](agent/EVALUATION_README.md) for details

**Features:**
- **🤖 LLM-based evaluation** for accurate sentiment, intent, and compliance analysis
- **Automatic evaluation** of every call upon completion
- **Multi-dimensional analysis**: Comprehensive quality metrics
- **CSV storage** for easy analysis in Excel/Google Sheets
- **Visualization tools** with charts and recommendations
- **Compliance monitoring** with KPIs and alerts (Labs Module)
- **Heuristic fallback** when LLM is unavailable
- **Dual evaluation modes**: Heuristic (fast) or LLM-based (accurate)

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

## Documentation

- **[Labs Module Evaluation](agent/LABS_EVALUATION_README.md)**: Healthcare-specific evaluation framework (PRIMARY)
- **[Labs Implementation](agent/LABS_IMPLEMENTATION_SUMMARY.md)**: Labs Module deployment status
- **[General Evaluation](agent/EVALUATION_README.md)**: General-purpose evaluation framework  
- **[Cost Tracking](agent/COST_TRACKING_README.md)**: Complete guide to cost tracking system
- **[Architecture](agent/ARCHITECTURE.md)**: System architecture and design

## Labs Module Evaluation Metrics

Every call is automatically evaluated across **8 dimensions** in **3 categories**:

**Category 1: Core Metrics**
1. **User Sentiment**: positive, neutral, confused, anxious, frustrated
2. **Call Summary**: 2-3 sentence interaction summary
3. **Query Resolved**: Whether AI fully addressed the question
4. **Escalation Required**: Whether human follow-up is needed

**Category 2: Domain Metrics**  
5. **Query Category**: 16 Labs-specific types (test_kit_info, ordering, registration, sample_collection, results, troubleshooting, etc.)
6. **Testing Phase**: 8 journey phases (pre_purchase → results_received)

**Category 3: Compliance Metrics** (CRITICAL for Healthcare)
7. **Medical Boundary Maintained**: Agent avoided diagnosis/medical advice
8. **Proper Disclaimer Given**: Appropriate disclaimers for health queries

**Compliance Dashboard KPIs:**
- Resolution Rate (Target: >80%)
- Escalation Rate (Target: <15%)
- Medical Compliance Rate (Target: 100%) ✅
- Anxiety Detection Rate (Monitor)

Results stored in CSV format for regulatory audit and continuous improvement.
