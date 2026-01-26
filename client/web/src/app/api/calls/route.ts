import { NextResponse } from "next/server";
import { readdir, readFile } from "fs/promises";
import { accessSync as accessSyncSync } from "fs";
import { join } from "path";

export const revalidate = 0; // Don't cache

// Path to agent directory - try multiple possible locations
function getAgentDir() {
  const cwd = process.cwd();
  console.log("Current working directory:", cwd);
  
  const possiblePaths = [
    join(cwd, "..", "..", "agent"), // If running from client/web -> go up twice
    join(cwd, "..", "agent"), // If running from client/web -> go up once (wrong but try)
    join(cwd, "agent"), // If running from root
  ];
  
  for (const path of possiblePaths) {
    try {
      const metricsPath = join(path, "metrics");
      accessSyncSync(metricsPath);
      console.log("Found agent directory at:", path);
      return path;
    } catch (err) {
      console.log("Path not found:", path);
      continue;
    }
  }
  
  // Fallback - try to construct from cwd
  const fallback = join(cwd, "..", "..", "agent");
  console.log("Using fallback path:", fallback);
  return fallback;
}

const AGENT_DIR = getAgentDir();
const METRICS_DIR = join(AGENT_DIR, "metrics");
const EVALUATIONS_DIR = join(AGENT_DIR, "labs_evaluations");
const EVALUATIONS_CSV = join(EVALUATIONS_DIR, "labs_call_evaluations.csv");

interface CallSummary {
  call_id: string;
  timestamp: string;
  duration_seconds: number;
  duration_minutes: number;
  total_cost: number;
  cost_per_minute: number;
  total_responses: number;
}

export async function GET() {
  try {
    console.log("API: Fetching calls from:", METRICS_DIR);
    console.log("API: Evaluations CSV:", EVALUATIONS_CSV);
    
    // Read evaluation CSV to get call summaries
    let evaluations: any[] = [];
    try {
      const csvContent = await readFile(EVALUATIONS_CSV, "utf-8");
      console.log("API: Successfully read evaluations CSV");
      const lines = csvContent.split("\n").filter((line) => line.trim());
      if (lines.length > 1) {
        const headers = lines[0].split(",").map((h) => h.trim());
        
        // Simple CSV parser that handles quoted fields
        const parseCSVLine = (line: string): string[] => {
          const result: string[] = [];
          let current = "";
          let inQuotes = false;
          
          for (let i = 0; i < line.length; i++) {
            const char = line[i];
            if (char === '"') {
              inQuotes = !inQuotes;
            } else if (char === "," && !inQuotes) {
              result.push(current.trim());
              current = "";
            } else {
              current += char;
            }
          }
          result.push(current.trim());
          return result;
        };
        
        for (let i = 1; i < lines.length; i++) {
          const values = parseCSVLine(lines[i]);
          const record: any = {};
          headers.forEach((header, idx) => {
            record[header] = values[idx]?.replace(/^"|"$/g, "") || "";
          });
          evaluations.push(record);
        }
      }
    } catch (error) {
      console.error("Error reading evaluations CSV:", error);
      console.error("CSV Path attempted:", EVALUATIONS_CSV);
    }

    // Read metrics files
    let metricsFiles: string[] = [];
    try {
      metricsFiles = await readdir(METRICS_DIR);
      console.log(`API: Found ${metricsFiles.length} files in metrics directory`);
    } catch (error) {
      console.error("Error reading metrics directory:", error);
      console.error("Metrics Path attempted:", METRICS_DIR);
      return NextResponse.json({ calls: [], error: `Metrics directory not found: ${METRICS_DIR}` }, { status: 200 });
    }

    const calls: CallSummary[] = [];

    for (const file of metricsFiles) {
      if (!file.endsWith(".json")) continue;

      try {
        const filePath = join(METRICS_DIR, file);
        const content = await readFile(filePath, "utf-8");
        const metrics = JSON.parse(content);

        const duration_minutes = metrics.duration_seconds / 60;
        const cost_per_minute = duration_minutes > 0 
          ? metrics.total_cost / duration_minutes 
          : 0;

        // Find matching evaluation
        const evaluation = evaluations.find(
          (e) => e.call_id === metrics.call_id
        );

        calls.push({
          call_id: metrics.call_id,
          timestamp: metrics.start_timestamp || metrics.end_timestamp || "",
          duration_seconds: metrics.duration_seconds || 0,
          duration_minutes,
          total_cost: metrics.total_cost || 0,
          cost_per_minute,
          total_responses: metrics.responses?.length || 0,
          ...(evaluation && {
            user_sentiment: evaluation.user_sentiment,
            query_resolved: evaluation.query_resolved === "True",
            escalation_required: evaluation.escalation_required === "True",
            query_category: evaluation.query_category,
            testing_phase: evaluation.testing_phase,
            medical_boundary_maintained: evaluation.medical_boundary_maintained === "True",
            proper_disclaimer_given: evaluation.proper_disclaimer_given === "True" || evaluation.proper_disclaimer_given === "",
            call_summary: evaluation.call_summary,
          }),
        });
      } catch (error) {
        console.error(`Error processing ${file}:`, error);
      }
    }

    // Sort by timestamp (newest first)
    calls.sort((a, b) => 
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );

    console.log(`API: Returning ${calls.length} calls`);
    return NextResponse.json({ calls });
  } catch (error) {
    console.error("Error fetching calls:", error);
    return NextResponse.json(
      { error: "Failed to fetch calls" },
      { status: 500 }
    );
  }
}
