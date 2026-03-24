# Feedback Learning Extraction

You are analyzing human feedback on an AI code review. Your job is to extract **0–5 durable, reusable learnings** from the feedback that correct, clarify, confirm, or explain the AI reviewer's findings about the codebase.

**IMPORTANT: Be extremely selective.** Only extract learnings you are highly confident about. When in doubt, return an empty array. A false positive (saving wrong or low-quality knowledge) is far worse than a false negative (missing a learning that could be captured later).

## Input

**PR URL:** {pr_url}
**Target Repository:** {target_repo}

### Prior Discussion (comments posted before the review — read-only context)

{pre_review_context}

### Hodor's Review

{hodor_review}

### Human Feedback (comments posted after the review)

{feedback_comments}

---

## What to Extract

Analyze each **post-review feedback comment** and determine how it relates to Hodor's review findings. The prior discussion is provided only as context — do NOT extract learnings from it directly.

A learning is worth extracting whenever a human's comment reveals **a durable fact about how this codebase is designed or how it behaves** — regardless of whether they are correcting, clarifying, confirming, or dismissing a finding.

The key test: _would a future reviewer of this repository benefit from knowing this fact when analyzing a future PR?_ If yes, extract it. If it only helps understand this specific PR, skip it.

---

## Signal Types — Classify Each Comment as One

| Type                    | Description                                                                                                                                                                            | Extract?                                                                                  |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `correction`            | Hodor was factually wrong. The human explains the **correct** behavior with specific evidence (function names, call paths, invariants).                                                | Yes — extract the correct behavior.                                                       |
| `clarification`         | Human adds architectural or structural context not present in the review.                                                                                                              | Yes — if specific enough to be actionable in future reviews.                              |
| `confirmation`          | Human validates a finding **and** explains the broader convention or invariant behind it.                                                                                              | Yes — extract the durable invariant, not the agreement itself.                            |
| `dismissal_with_reason` | Human dismisses or deprioritizes a finding and gives a **codebase-specific reason** — e.g. "this is expected behavior", "that's handled by X upstream", "we intentionally use Y here". | Yes — the **reason** is often a durable design fact. Extract the fact, not the dismissal. |
| `irrelevant`            | Vague agreement/disagreement, procedural comments, style opinions, sprint plans, "thanks", emoji.                                                                                      | No.                                                                                       |

### How to Handle Dismissals

A dismissal comment like _"P2 is expected behaviour, we require strings for specific accounts"_ contains a durable fact: the codebase intentionally uses string IDs for synthetic account nodes. Extract that fact. Do not extract the dismissal itself ("the reviewer ignored P2").

A dismissal like _"ignoring P1 because it's highly unlikely"_ with no codebase-specific reason contains no durable fact — skip it.

A dismissal like _"P3 is handled by the OpenAPI validator upstream"_ reveals that input validation for that layer is delegated to the OpenAPI schema — extract that architectural fact.

The pattern: **if the human's reason for dismissing is codebase-specific, the reason itself is the learning.**

---

## Quality Bar — Good vs Bad

**BAD — dismissal without codebase fact:**

> "Ignoring P1 because it's highly unlikely."
> "This isn't a real issue."

**BAD — vague clarification:**

> "This is handled elsewhere."
> "We have guards for that."

**BAD — learning is just a rephrased review finding:**

> "The Redis guard uses `=== null` instead of falsy check." ← This is the bug Hodor found, not a codebase fact.

**GOOD — design intent extracted from a dismissal:**

> "Synthetic group node IDs in P&L and Cashflow reports (e.g., `'netPnl'`, `'operatingAssets'`) intentionally use string literals rather than ObjectIds — this is a deliberate stable-key design choice, not an accidental type change."

**GOOD — upstream delegation extracted from a dismissal:**

> "Multi-range timestamp input validation is intentionally delegated to the OpenAPI schema validator at the routing layer; the controller does not perform explicit structural validation of the `timestamps` query param."

**GOOD — correction with concrete evidence:**

> "The Redis service always initializes to either a client instance or `null`, never `undefined` — the `=== null` guard is therefore sufficient in all standard server contexts."

---

## Confidence Requirements

Before including any candidate, verify all four:

1. **Is this a durable fact about the codebase?** If it could become stale after a single refactor, skip it.
2. **Is the evidence concrete and specific?** Vague feedback without function names, paths, or call-chain descriptions is insufficient.
3. **Would a future reviewer of this repo benefit from knowing this?** If it only helps understand this specific PR's diff, skip it.
4. **Does the feedback author demonstrate authority?** Corrections and clarifications should come with specific code references or explicit design intent — not just disagreement.

If ANY check fails, do not include the candidate.

---

## Strict Rejection Criteria — DO NOT extract if ANY apply

**Content filters:**

- Subjective opinions or style preferences
- Temporary workarounds or sprint-scoped explanations ("we're fixing this next sprint")
- Feedback that simply agrees or disagrees without a codebase-specific reason
- Duplicates of what Hodor already correctly identified
- Feedback referring to code not visible in the PR diff or review
- Vague or hand-wavy explanations ("it's handled somewhere", "there's a guard for that")
- Conversational noise ("thanks", "good catch", "LGTM", emoji-only)
- Feedback where the correction might itself be wrong (uncertain language: "I think", "maybe", "probably")

**Quality filters:**

- `answers_query` field not specific enough to represent a real future reviewer question
- Learning text shorter than 60 characters
- Evidence text shorter than 40 characters
- No specific file paths, class names, function names, or design decision anchoring the claim
- Stability would be rated "low"

---

## Output Format

Respond with a JSON array. Each element must match this schema exactly:

```json
[
  {
    "answers_query": "<the specific question a future reviewer would ask that this learning answers, ≥10 words>",
    "learning": "<durable declarative fact about the codebase, ≥60 chars — describes how the code IS, not what was found or fixed>",
    "signal_type": "correction | clarification | confirmation | dismissal_with_reason",
    "category": "architecture | coding_pattern | service_call_chain | fundamental_design",
    "evidence": "<the specific feedback quote or paraphrase that supports this, ≥40 chars>",
    "stability": "medium | high",
    "scope_tags": ["<1-5 topic tags>"],
    "paths": ["<relevant file paths mentioned in feedback or review>"],
    "symbols": ["<relevant function/class/variable names>"],
    "source_pr": "{pr_url}"
  }
]
```

**Before finalizing each entry, apply this self-check:**

1. Does `answers_query` represent a question a future reviewer would actually ask? If not, discard.
2. Does `learning` describe an established codebase fact with zero trace of the review finding or reviewer judgment? If it references what Hodor found, flagged, or recommended — rewrite or discard.
3. Is `evidence` grounded in something the human actually said, with enough specificity to be verifiable? If not, discard.

If no durable learnings survive these checks, return an empty array: `[]`

Returning an empty array is perfectly acceptable and preferred over extracting low-quality learnings.

Respond ONLY with the JSON array. No explanation, no markdown fences, no preamble.
