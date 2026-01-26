import { NextResponse } from "next/server";
import { readdir } from "fs/promises";
import { join, resolve } from "path";
import { accessSync as accessSyncSync } from "fs";

export const revalidate = 0; // Don't cache

// Path to agent directory - use absolute path resolution
function getAgentDir() {
  const cwd = process.cwd();
  console.log("getAgentDir: Current working directory:", cwd);
  
  // Try to resolve from common locations
  // If we're in client/web, go up 2 levels
  // If we're in client, go up 1 level
  // If we're in root, use agent directly
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
  
  // Last resort: try to find workspace root by looking for agent directory
  const fallback = resolve(cwd, "..", "..", "agent");
  console.log(`getAgentDir: Using fallback path: ${fallback}`);
  return fallback;
}

// Don't resolve paths at module load - do it at request time
function getMetricsDir() {
  const agentDir = getAgentDir();
  return join(agentDir, "metrics");
}

export async function GET(request: Request) {
  try {
    const METRICS_DIR = getMetricsDir();
    const { searchParams } = new URL(request.url);
    const prefix = searchParams.get("prefix");
    
    console.log("Search API: Looking for call with prefix:", prefix);
    console.log("Search API: Current working directory:", process.cwd());
    console.log("Search API: Metrics directory:", METRICS_DIR);
    
    if (!prefix) {
      return NextResponse.json(
        { error: "prefix parameter is required" },
        { status: 400 }
      );
    }

    // Read labs evaluations files (source of CSV data)
    const agentDir = getAgentDir();
    const LABS_EVAL_DIR = join(agentDir, "labs_evaluations");
    console.log("Search API: Labs evaluations directory:", LABS_EVAL_DIR);
    let evalFiles: string[] = [];
    try {
      evalFiles = await readdir(LABS_EVAL_DIR);
      console.log(`Search API: Found ${evalFiles.length} files in labs_evaluations directory`);
      console.log("Search API: Sample files:", evalFiles.slice(0, 5));
    } catch (error: any) {
      console.error("Error reading labs_evaluations directory:", error);
      console.error("Error details:", error.message, error.code, error.path);
      return NextResponse.json(
        { error: `Labs evaluations directory not found: ${LABS_EVAL_DIR}` },
        { status: 500 }
      );
    }

    // Find file that starts with the prefix and ends with _labs_eval.json
    // Format: call_{room_name}_{uuid}_labs_eval.json
    const matchingFile = evalFiles.find((file) => 
      file.startsWith(prefix) && file.endsWith("_labs_eval.json")
    );

    console.log("Search API: Matching file:", matchingFile);

    if (!matchingFile) {
      console.log("Search API: No matching file found. Available files starting with 'call_':", 
        evalFiles.filter(f => f.startsWith("call_")).slice(0, 10));
      return NextResponse.json(
        { error: "Call not found", prefix, availableFiles: evalFiles.filter(f => f.startsWith("call_")).slice(0, 10) },
        { status: 404 }
      );
    }

    // Extract call_id from filename (remove _labs_eval.json extension)
    // Format: call_{room_name}_{uuid}_labs_eval.json -> call_{room_name}_{uuid}
    const callId = matchingFile.replace("_labs_eval.json", "");
    console.log("Search API: Found call ID:", callId);

    return NextResponse.json({ call_id: callId });
  } catch (error) {
    console.error("Error searching for call:", error);
    return NextResponse.json(
      { error: "Failed to search for call" },
      { status: 500 }
    );
  }
}
