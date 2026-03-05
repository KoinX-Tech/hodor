/**
 * Render structured JSON review output into clean markdown for PR/MR comments.
 */

import type { ReviewFinding, ReviewOutput } from "./types.js";

/**
 * Parse the raw agent text to extract JSON review output.
 * Handles cases where the agent includes reasoning text before the JSON.
 */
export function parseReviewJson(rawText: string): ReviewOutput {
  // Try parsing the whole text first (ideal case)
  const trimmed = rawText.trim();
  try {
    return JSON.parse(trimmed) as ReviewOutput;
  } catch {
    // Not pure JSON — try to extract the outermost JSON object
  }

  // Find the outermost balanced {} block using brace counting.
  // Simple indexOf/lastIndexOf fails when finding bodies contain JSON or code with braces.
  const start = trimmed.indexOf("{");
  if (start >= 0) {
    let depth = 0;
    let inString = false;
    let escape = false;
    for (let i = start; i < trimmed.length; i++) {
      const ch = trimmed[i];
      if (escape) {
        escape = false;
        continue;
      }
      if (ch === "\\") {
        escape = true;
        continue;
      }
      if (ch === '"') {
        inString = !inString;
        continue;
      }
      if (inString) continue;
      if (ch === "{") depth++;
      else if (ch === "}") {
        depth--;
        if (depth === 0) {
          try {
            return JSON.parse(trimmed.slice(start, i + 1)) as ReviewOutput;
          } catch {
            // Matched braces but invalid JSON — keep scanning
            break;
          }
        }
      }
    }
  }

  throw new Error(
    "Failed to parse review JSON from agent output. " +
      `Raw text (first 200 chars): ${trimmed.slice(0, 200)}`,
  );
}

/**
 * Render a parsed ReviewOutput into clean markdown for posting as a PR/MR comment.
 */
export function renderMarkdown(review: ReviewOutput): string {
  const lines: string[] = [];

  // Group findings by priority
  const critical: ReviewFinding[] = []; // P0, P1
  const important: ReviewFinding[] = []; // P2
  const minor: ReviewFinding[] = []; // P3

  for (const f of review.findings) {
    const p = f.priority ?? inferPriority(f.title);
    if (p <= 1) critical.push(f);
    else if (p === 2) important.push(f);
    else minor.push(f);
  }

  lines.push("### Issues Found");
  lines.push("");

  if (review.findings.length === 0) {
    lines.push("No issues found.");
    lines.push("");
  }

  if (critical.length > 0) {
    lines.push("**Critical (P0/P1)**");
    for (const f of critical) {
      lines.push(formatFinding(f));
    }
    lines.push("");
  }

  if (important.length > 0) {
    lines.push("**Important (P2)**");
    for (const f of important) {
      lines.push(formatFinding(f));
    }
    lines.push("");
  }

  if (minor.length > 0) {
    lines.push("**Minor (P3)**");
    for (const f of minor) {
      lines.push(formatFinding(f));
    }
    lines.push("");
  }

  // Summary
  lines.push("### Summary");
  lines.push(
    `Total issues: ${critical.length} critical, ${important.length} important, ${minor.length} minor.`,
  );
  lines.push("");

  // Overall verdict
  lines.push("### Overall Verdict");
  const isCorrect = review.overall_correctness === "patch is correct";
  lines.push(
    `**Status**: ${isCorrect ? "Patch is correct" : "Patch has blocking issues"}`,
  );
  lines.push("");
  if (review.overall_explanation) {
    lines.push(`**Explanation**: ${review.overall_explanation}`);
  }

  return lines.join("\n").trimEnd() + "\n";
}

function formatFinding(f: ReviewFinding): string {
  const loc = f.code_location
    ? ` (\`${formatLocation(f.code_location)}\`)`
    : "";
  const title = `- **${f.title}**${loc}`;
  const body = `  - ${f.body}`;
  return `${title}\n${body}`;
}

function formatLocation(loc: {
  absolute_file_path: string;
  line_range: { start: number; end: number };
}): string {
  // Strip common workspace prefixes to get a clean relative path
  let filePath = loc.absolute_file_path;

  // GitLab CI: /builds/owner/repo/src/file.ts → src/file.ts
  const buildsMatch = filePath.match(/\/builds\/[^/]+\/[^/]+\/(.+)/);
  if (buildsMatch) {
    filePath = buildsMatch[1];
  }
  // GitHub Actions / generic workspace
  else if (filePath.includes("/workspace/")) {
    filePath = filePath.slice(filePath.indexOf("/workspace/") + "/workspace/".length);
  }
  // Temp review dirs: /tmp/hodor-review-<id>/src/file.ts → src/file.ts
  else {
    filePath = filePath.replace(/^.*\/hodor-review-[^/]+\//, "");
  }

  const { start, end } = loc.line_range;
  return start === end ? `${filePath}:${start}` : `${filePath}:${start}-${end}`;
}

function inferPriority(title: string): number {
  const match = title.match(/\[P(\d)]/);
  return match ? parseInt(match[1], 10) : 2;
}
