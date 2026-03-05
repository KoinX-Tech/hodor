import { describe, test, expect } from "bun:test";
import { parseReviewJson, renderMarkdown } from "../src/render.js";
import type { ReviewOutput } from "../src/types.js";

describe("parseReviewJson", () => {
  test("parses clean JSON", () => {
    const json = JSON.stringify({
      findings: [],
      overall_correctness: "patch is correct",
      overall_explanation: "No issues found.",
      overall_confidence_score: 0.95,
    });
    const result = parseReviewJson(json);
    expect(result.findings).toEqual([]);
    expect(result.overall_correctness).toBe("patch is correct");
  });

  test("extracts JSON from text with reasoning preamble", () => {
    const raw = `I analyzed the code changes and found one issue.\n\n${JSON.stringify({
      findings: [
        {
          title: "[P1] Missing null check",
          body: "The function does not check for null input.",
          priority: 1,
          confidence_score: 0.9,
          code_location: {
            absolute_file_path: "/builds/group/repo/src/auth.ts",
            line_range: { start: 45, end: 48 },
          },
        },
      ],
      overall_correctness: "patch is incorrect",
      overall_explanation: "Missing null check will cause crash.",
    })}`;
    const result = parseReviewJson(raw);
    expect(result.findings).toHaveLength(1);
    expect(result.findings[0].title).toBe("[P1] Missing null check");
    expect(result.overall_correctness).toBe("patch is incorrect");
  });

  test("handles nested braces in finding body", () => {
    const json = JSON.stringify({
      findings: [
        {
          title: "[P2] Config object malformed",
          body: 'The config `{"key": "value"}` is missing required fields.',
          priority: 2,
          code_location: {
            absolute_file_path: "/workspace/src/config.ts",
            line_range: { start: 10, end: 10 },
          },
        },
      ],
      overall_correctness: "patch is incorrect",
      overall_explanation: "Config bug.",
    });
    const raw = `Here is my analysis of the code:\n\n${json}`;
    const result = parseReviewJson(raw);
    expect(result.findings).toHaveLength(1);
    expect(result.findings[0].body).toContain('{"key": "value"}');
  });

  test("throws on non-JSON text", () => {
    expect(() => parseReviewJson("Just some text without JSON")).toThrow(
      "Failed to parse review JSON",
    );
  });
});

describe("renderMarkdown", () => {
  test("renders empty findings", () => {
    const review: ReviewOutput = {
      findings: [],
      overall_correctness: "patch is correct",
      overall_explanation: "No issues found in the changes.",
    };
    const md = renderMarkdown(review);
    expect(md).toContain("### Issues Found");
    expect(md).toContain("No issues found.");
    expect(md).toContain("### Summary");
    expect(md).toContain("Total issues: 0 critical, 0 important, 0 minor.");
    expect(md).toContain("**Status**: Patch is correct");
  });

  test("renders findings grouped by priority", () => {
    const review: ReviewOutput = {
      findings: [
        {
          title: "[P0] SQL injection in login",
          body: "User input concatenated into query.",
          priority: 0,
          code_location: {
            absolute_file_path: "/builds/acme/app/src/db.ts",
            line_range: { start: 12, end: 15 },
          },
        },
        {
          title: "[P2] Missing index on user_id",
          body: "Full table scan on every request.",
          priority: 2,
          code_location: {
            absolute_file_path: "/builds/acme/app/src/models.ts",
            line_range: { start: 89, end: 89 },
          },
        },
        {
          title: "[P3] Magic number 42",
          body: "Should be a named constant.",
          priority: 3,
          code_location: {
            absolute_file_path: "/builds/acme/app/src/util.ts",
            line_range: { start: 7, end: 7 },
          },
        },
      ],
      overall_correctness: "patch is incorrect",
      overall_explanation: "SQL injection is a blocker.",
    };
    const md = renderMarkdown(review);
    expect(md).toContain("**Critical (P0/P1)**");
    expect(md).toContain("**Important (P2)**");
    expect(md).toContain("**Minor (P3)**");
    expect(md).toContain("Total issues: 1 critical, 1 important, 1 minor.");
    expect(md).toContain("**Status**: Patch has blocking issues");
    // Check path stripping: /builds/acme/app/src/db.ts → src/db.ts
    expect(md).toContain("`src/db.ts:12-15`");
    expect(md).toContain("`src/models.ts:89`");
  });

  test("infers priority from title when priority field is missing", () => {
    const review: ReviewOutput = {
      findings: [
        {
          title: "[P1] Resource leak",
          body: "File handle not closed.",
        },
      ],
      overall_correctness: "patch is incorrect",
      overall_explanation: "Leak found.",
    };
    const md = renderMarkdown(review);
    expect(md).toContain("**Critical (P0/P1)**");
    expect(md).toContain("[P1] Resource leak");
  });
});
