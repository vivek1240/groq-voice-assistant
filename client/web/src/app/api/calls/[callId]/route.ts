import { NextResponse } from "next/server";
import { readFile } from "fs/promises";
import { accessSync as accessSyncSync } from "fs";
import { join, resolve } from "path";

export const revalidate = 0; // Don't cache

// Path to agent directory - use absolute path resolution
function getAgentDir() {
  const cwd = process.cwd();
  console.log("getAgentDir: Current working directory:", cwd);
  
  const possiblePaths = [
    resolve(cwd, "..", "..", "agent"), // client/web -> root/agent
    resolve(cwd, "..", "agent"), // client -> root/agent
    resolve(cwd, "agent"), // root -> root/agent
    resolve(cwd, "..", "..", "..", "agent"), // nested -> root/agent
  ];
  
  for (const agentPath of possiblePaths) {
    try {
      const metricsPath = join(agentPath, "metrics");
      console.log(`getAgentDir: Trying: ${agentPath} -> ${metricsPath}`);
      accessSyncSync(metricsPath);
      console.log(`getAgentDir: SUCCESS - Found metrics at: ${metricsPath}`);
      return agentPath;
    } catch (err: any) {
      console.log(`getAgentDir: FAILED - ${err.message}`);
      continue;
    }
  }
  
  const fallback = resolve(cwd, "..", "..", "agent");
  console.log(`getAgentDir: Using fallback path: ${fallback}`);
  return fallback;
}

// Get labs evaluations directory (where evaluation JSON files are stored)
function getLabsEvaluationsDir() {
  const agentDir = getAgentDir();
  return join(agentDir, "labs_evaluations");
}

// Get metrics directory (for cost breakdown if needed)
function getMetricsDir() {
  const agentDir = getAgentDir();
  return join(agentDir, "metrics");
}

export async function GET(
  request: Request,
  { params }: { params: { callId: string } }
) {
  try {
    const LABS_EVAL_DIR = getLabsEvaluationsDir();
    const METRICS_DIR = getMetricsDir();
    const callId = params.callId;

    console.log("Call details API: Current working directory:", process.cwd());
    console.log("Call details API: Labs evaluations directory:", LABS_EVAL_DIR);
    console.log("Call details API: Metrics directory:", METRICS_DIR);
    console.log("Call details API: Looking for call ID:", callId);

    // Read evaluation JSON file (source of CSV data)
    const evalFile = join(LABS_EVAL_DIR, `${callId}_labs_eval.json`);
    console.log("Call details API: Evaluation file path:", evalFile);
    
    let evaluation: any = null;
    try {
      const evalContent = await readFile(evalFile, "utf-8");
      evaluation = JSON.parse(evalContent);
      console.log("Call details API: Successfully loaded evaluation data");
    } catch (error: any) {
      console.log(`Call details API: Evaluation file not found: ${error.message}`);
      // Continue - we'll try metrics file for cost data
    }

    // Read metrics JSON file (source of cost CSV data)
    const metricsFile = join(METRICS_DIR, `${callId}.json`);
    console.log("Call details API: Metrics file path:", metricsFile);
    
    let metrics: any = null;
    try {
      const metricsContent = await readFile(metricsFile, "utf-8");
      metrics = JSON.parse(metricsContent);
      console.log("Call details API: Successfully loaded metrics data");
    } catch (error: any) {
      console.log(`Call details API: Metrics file not found: ${error.message}`);
    }

    // If neither file exists, return error with details
    if (!evaluation && !metrics) {
      console.error("Call details API: Neither evaluation nor metrics file found");
      console.error(`  Tried evaluation file: ${evalFile}`);
      console.error(`  Tried metrics file: ${metricsFile}`);
      return NextResponse.json(
        { 
          error: "Call not found",
          details: {
            evaluation_file: evalFile,
            metrics_file: metricsFile,
            call_id: callId
          }
        },
        { status: 404 }
      );
    }

    // Prefer evaluation data for transcript and basic info, fallback to metrics
    const callData = evaluation || metrics;
    const duration_seconds = callData.duration_seconds || 0;
    const duration_minutes = duration_seconds / 60;
    
    // Extract transcript from evaluation (preferred) or metrics
    const transcript = evaluation?.conversation_transcript || metrics?.conversation_transcript || [];

    // Get cost data from metrics (has breakdown) or evaluation (has total only)
    const total_cost = metrics?.total_cost || evaluation?.total_cost || 0;
    const stt_cost = metrics?.total_stt_cost || 0;
    const llm_cost = metrics?.total_llm_cost || 0;
    const tts_cost = metrics?.total_tts_cost || 0;
    
    const cost_per_minute = duration_minutes > 0 ? total_cost / duration_minutes : 0;

    const result = {
      call_id: callData.call_id,
      timestamp: callData.timestamp || callData.start_timestamp,
      duration_seconds,
      duration_minutes,
      total_cost,
      cost_per_minute,
      total_responses: metrics?.responses?.length || 0,
      transcript,
      costs: {
        stt: stt_cost,
        llm: llm_cost,
        tts: tts_cost,
        total: total_cost,
        stt_per_minute: duration_minutes > 0 ? stt_cost / duration_minutes : 0,
        llm_per_minute: duration_minutes > 0 ? llm_cost / duration_minutes : 0,
        tts_per_minute: duration_minutes > 0 ? tts_cost / duration_minutes : 0,
      },
    };

    console.log("Call details API: Returning result:", {
      call_id: result.call_id,
      has_transcript: !!result.transcript && result.transcript.length > 0,
      transcript_length: result.transcript?.length || 0,
      has_costs: !!result.costs,
      total_cost: result.total_cost,
    });

    return NextResponse.json(result);
  } catch (error) {
    console.error("Error fetching call details:", error);
    return NextResponse.json(
      { error: "Failed to fetch call details" },
      { status: 500 }
    );
  }
}
