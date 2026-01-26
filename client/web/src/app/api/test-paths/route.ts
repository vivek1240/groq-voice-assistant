import { NextResponse } from "next/server";
import { join } from "path";
import { accessSync } from "fs";

export const revalidate = 0;

export async function GET() {
  const possiblePaths = [
    { name: "client/web -> ../agent", path: join(process.cwd(), "..", "agent") },
    { name: "root -> agent", path: join(process.cwd(), "agent") },
    { name: "process.cwd()", path: process.cwd() },
  ];

  const results = possiblePaths.map(({ name, path }) => {
    try {
      const metricsPath = join(path, "metrics");
      accessSync(metricsPath);
      return { name, path, metricsPath, exists: true };
    } catch {
      return { name, path, metricsPath: join(path, "metrics"), exists: false };
    }
  });

  return NextResponse.json({
    currentWorkingDir: process.cwd(),
    paths: results,
  });
}
