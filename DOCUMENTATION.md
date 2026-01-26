# 🎙️ Groq Voice Assistant - Complete Documentation

## 📋 Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Core Features](#core-features)
4. [Evaluation Framework](#evaluation-framework)
5. [Cost Tracking System](#cost-tracking-system)
6. [Testing & Performance](#testing--performance)
7. [Configuration Management](#configuration-management)
8. [Web Client Interface](#web-client-interface)
9. [Deployment Guide](#deployment-guide)
10. [API Reference](#api-reference)
11. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

The **Groq Voice Assistant** is a production-ready, enterprise-grade voice AI system built on Groq's ultra-low-latency inference platform. It provides real-time voice conversations with advanced capabilities including intelligent evaluation, comprehensive cost tracking, and robust call management.

### Key Highlights

- ⚡ **Ultra-Low Latency**: STT (800ms), LLM TTFT (200ms), TTS (350ms)
- 🧠 **LLM-Based Intelligent Evaluation**: Automated call quality assessment using Groq's Llama 3.3 70B with 8-dimension analysis
- 💰 **Comprehensive Cost Tracking**: Real-time cost monitoring for all components
- 🔄 **Concurrent User Support**: Successfully tested with 10+ concurrent users
- 🎨 **Modern Web Interface**: Beautiful, responsive React/Next.js client
- 🛡️ **Production Ready**: Robust error handling, call management, and monitoring

### Technology Stack

- **Backend**: Python 3.9+, LiveKit Agents Framework
- **AI Models**: Groq (STT: Whisper Large V3 Turbo, LLM: Llama 3.3 70B, TTS: Orpheus V1)
- **Frontend**: Next.js 14, React, TypeScript, Tailwind CSS
- **Platform**: LiveKit Cloud for real-time communication
- **Evaluation**: LLM-Based Labs Module Evaluation Framework (Groq Llama 3.3 70B)

---

## 🏗️ System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Client (Next.js)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  React Components │ LiveKit SDK │ Audio Processing   │  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │ WebRTC
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              LiveKit Cloud Platform                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Room Management │ Audio Routing │ Agent Orchestration│  │
│  └──────────────────────────────────────────────────────┘  │
└───────────────────────┬─────────────────────────────────────┘
                        │ Agent Connection
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Voice Agent (Python)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │     STT      │→ │     LLM      │→ │     TTS      │      │
│  │  (Whisper)   │  │ (Llama 3.3)  │  │  (Orpheus)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Cost Tracker │ Call Evaluator │ Metrics Collector   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Groq Inference Platform                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Ultra-Fast Inference │ Model Serving │ API Gateway   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Component Flow

1. **User Interaction**: User speaks through web browser → WebRTC → LiveKit
2. **Speech Recognition**: LiveKit → Agent → Groq STT (Whisper)
3. **Intent Understanding**: STT transcript → Groq LLM (Llama 3.3 70B)
4. **Response Generation**: LLM response → Groq TTS (Orpheus)
5. **Audio Playback**: TTS audio → LiveKit → WebRTC → User's browser
6. **Metrics Collection**: All components → Cost Tracker → JSON metrics files
7. **Post-Call Evaluation**: Metrics → Labs Evaluator → CSV/JSON reports

---

## ✨ Core Features

### 1. Real-Time Voice Conversation

- **Natural Dialogue**: Bidirectional voice conversation with minimal latency
- **Interruption Handling**: Users can interrupt the agent mid-speech
- **Voice Activity Detection**: Automatic detection of user speech using Silero VAD
- **Echo Cancellation**: Built-in echo cancellation for clear audio
- **Noise Filtering**: Optional Krisp noise filtering support

### 2. Intelligent Call Management

#### Automatic Call Termination

- **Maximum Duration**: Configurable call duration limit (default: 15 minutes)
- **Inactivity Timeout**: Automatic disconnect after silence (default: 15 seconds)
- **Farewell Detection**: Recognizes goodbye phrases and gracefully ends calls
- **Warning System**: Pre-warning users before call limits are reached



### 3. Advanced Metrics Collection

#### Per-Response Metrics

- **STT Metrics**: Duration, latency, transcript length, cost
- **LLM Metrics**: Input/output tokens, TTFT (Time to First Token), latency, cost
- **TTS Metrics**: Characters processed, TTFB (Time to First Byte), latency, cost
- **End-to-End Metrics**: Total response time, EOU (End of Utterance) delay

#### Per-Call Metrics

- **Call Duration**: Total call time in seconds
- **Total Costs**: Breakdown by component (STT, LLM, TTS, LiveKit)
- **Token Usage**: Total input/output tokens
- **Average Latencies**: Mean latencies across all responses
- **Conversation Transcript**: Complete conversation history

### 4. Model Prewarming

- **Cold Start Optimization**: Models are prewarmed on agent startup
- **Connection Pooling**: Pre-established connections to Groq API
- **Reduced Latency**: First response is as fast as subsequent ones

### 5. Error Handling & Resilience

- **Graceful Degradation**: System continues operating even if one component fails
- **Automatic Retries**: Built-in retry logic for transient failures
- **Error Logging**: Comprehensive error tracking and logging
- **User Feedback**: Clear error messages to users when issues occur

---

## 📊 Evaluation Framework

### Labs Module Evaluation System

The system includes a sophisticated **8-dimension evaluation framework** specifically designed for healthcare/medical voice assistants, compliant with Labs_Call_Evaluation_System_Design v1.0.

#### Evaluation Dimensions

**Category 1: Core Metrics (4 dimensions)**

1. **User Sentiment**
   - Positive, Neutral, Confused, Anxious, Frustrated
   - Analyzed from conversation tone and language

2. **Call Summary**
   - 2-3 sentence summary of the conversation
   - Captures main topics and outcomes

3. **Query Resolution**
   - Boolean: Whether the AI fully addressed the user's question
   - Tracks if user's needs were met

4. **Escalation Required**
   - Boolean: Whether human follow-up is needed
   - Flags complex issues requiring human intervention

**Category 2: Domain-Specific Metrics (2 dimensions)**

5. **Query Category** (16 categories)
   - Test Kit Information
   - Ordering & Purchase
   - Delivery & Shipping
   - Kit Registration
   - Sample Collection
   - Fasting Requirements
   - Sample Shipping
   - Results General
   - Biomarker Explanation
   - Results Interpretation
   - Results Concern
   - Sample Rejection
   - Technical Issues
   - Medical Advice Request
   - Billing & Refund
   - General Inquiry

6. **Testing Phase** (8 phases)
   - Pre-Purchase
   - Post-Order
   - Kit Received
   - Pre-Collection
   - During Collection
   - Post-Collection
   - Results Received
   - Unknown

**Category 3: Compliance & Safety Metrics (2 dimensions)**

7. **Medical Boundary Maintenance**
   - Boolean: Agent avoided medical diagnosis/advice
   - Critical for healthcare compliance

8. **Proper Disclaimer Given**
   - Boolean/Null: Disclaimers when discussing results
   - Null if not applicable to the conversation

#### Evaluation Methods

**1. LLM-Based Evaluation (Primary Method)**
- **Uses Groq's Llama 3.3 70B** for intelligent, context-aware analysis
- **Highly Accurate**: Superior sentiment and context understanding
- **Nuanced Detection**: Better at identifying compliance issues and medical boundary violations
- **Intelligent Classification**: Accurate categorization of query types and testing phases
- **Production Ready**: Used in all production evaluations
- Requires `GROQ_API_KEY` and `USE_LLM_EVALUATION=true` (enabled by default)

**2. Heuristic Evaluation (Fallback/Alternative)**
- Fast, rule-based analysis
- Keyword matching and pattern recognition
- No API costs
- Suitable for high-volume evaluation when LLM is unavailable
- Less accurate than LLM-based evaluation

#### Evaluation Output

**CSV Reports** (`labs_evaluations/labs_call_evaluations.csv`)
- Comprehensive spreadsheet with all evaluation dimensions
- Easy to import into Excel/Google Sheets
- Suitable for batch analysis and reporting

**JSON Reports** (`labs_evaluations/call_*_labs_eval.json`)
- Detailed per-call evaluation results
- Includes full conversation transcripts
- Machine-readable format for automation

**Cost Metrics** (`labs_evaluations/call_cost_metrics.csv`)
- Aggregated cost analysis across all calls
- Cost breakdown by component
- Average costs per call type



**Note**: The system uses **LLM-based evaluation** as the primary method for all production evaluations, providing superior accuracy and context understanding compared to heuristic methods.

---

## 💰 Cost Tracking System

### Comprehensive Cost Monitoring

The system tracks costs for **every component** in real-time:

#### 1. Speech-to-Text (STT) Costs

- **Model**: Whisper Large V3 Turbo
- **Pricing**: $0.02 per minute of audio
- **Tracking**: Duration-based calculation
- **Metrics**: Audio duration, transcript length, cost per call

#### 2. Large Language Model (LLM) Costs

- **Model**: Llama 3.3 70B Versatile
- **Pricing**: 
  - Input: $0.59 per 1M tokens
  - Output: $0.79 per 1M tokens
- **Tracking**: Token-based calculation (input + output)
- **Metrics**: Input tokens, output tokens, total tokens, cost per call

#### 3. Text-to-Speech (TTS) Costs

- **Model**: Orpheus V1 English
- **Pricing**: $0.022 per 1K characters
- **Tracking**: Character-based calculation
- **Metrics**: Characters processed, audio duration, cost per call

#### 4. LiveKit Platform Costs

- **Service**: LiveKit Cloud Agent Sessions
- **Pricing**: $0.01 per minute of agent connection
- **Tracking**: Duration-based calculation
- **Metrics**: Connection duration, cost per call

### Cost Calculation

**Per-Response Cost**:
```
Response Cost = STT Cost + LLM Cost + TTS Cost
```

**Per-Call Cost**:
```
Total Cost = Σ(Response Costs) + LiveKit Cost
```

### Cost Tracking Features

- **Real-Time Calculation**: Costs calculated as components are used
- **Per-Response Breakdown**: See costs for each interaction
- **Per-Call Summary**: Total costs with component breakdown
- **Batch Analysis**: Analyze costs across multiple calls
- **Export Capabilities**: JSON and CSV export formats



**Output Includes**:
- Total costs across all calls
- Average cost per call
- Cost breakdown by component
- Most expensive calls
- Cost trends over time

---

## 🧪 Testing & Performance

### Load Testing Results

**✅ Successfully Tested with 10 Concurrent Users**

The system has been thoroughly tested with **10 concurrent users** connecting simultaneously, demonstrating:

- **Stability**: No crashes or failures under load
- **Performance**: Maintained low latency even with multiple users
- **Scalability**: System handles concurrent connections efficiently
- **Resource Management**: Proper resource allocation across users
- **Error Handling**: Graceful handling of edge cases under load

### Performance Benchmarks

#### Latency Metrics (Achieved in Production)

- **STT Latency**: ~800ms (Whisper Large V3 Turbo)
- **LLM TTFT**: ~200ms (Llama 3.3 70B)
- **TTS Latency**: ~350ms (Orpheus V1)
- **End-to-End Response**: ~1.5-2 seconds (from user speech to agent response)

#### Throughput Metrics

- **Concurrent Users**: 10+ (tested and verified)
- **Calls per Hour**: System can handle hundreds of calls per hour
- **Average Call Duration**: 2-15 minutes (configurable)
- **Response Rate**: 100% (all user inputs receive responses)

### Test Coverage

#### Unit Tests

- Cost tracker functionality
- Evaluation framework logic
- Configuration management
- Metrics collection

#### Integration Tests

- End-to-end call flow
- Multi-user concurrent connections
- Error scenarios
- Call termination logic

#### Load Tests

- 10 concurrent users (✅ Passed)
- Sustained load over extended periods
- Resource usage monitoring
- Performance degradation analysis

### Performance Monitoring

The system includes built-in performance monitoring:

- **Real-Time Metrics**: Latency tracking for all components
- **Historical Analysis**: Metrics stored for trend analysis
- **Alerting**: Configurable alerts for performance degradation
- **Dashboards**: CSV/JSON exports for visualization

---



## 🖥️ Web Client Interface

### Modern React/Next.js Application

The web client provides a beautiful, responsive interface for voice interactions.

#### Features

- **Real-Time Connection**: WebRTC-based audio streaming
- **Visual Feedback**: Connection state indicators
- **Responsive Design**: Works on desktop and mobile
- **Dark Theme**: Modern, professional appearance

#### Components

1. **Connection Manager**: Handles LiveKit room connections
2. **Voice Assistant Control Bar**: Main interaction interface
3. **Audio Renderer**: Processes and plays audio
4. **State Management**: Tracks connection and agent states

#### Connection Flow

1. User clicks "Connect" button
2. Client fetches connection details from API
3. LiveKit room is created/joined
4. Agent connects automatically
5. Voice conversation begins
6. Real-time audio streaming (bidirectional)





