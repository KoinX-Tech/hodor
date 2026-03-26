# Feedback Learning Extraction

You are analyzing the full discussion on a pull request. Your job is to extract **0–5 durable, reusable learnings** from the conversation that reveal how this codebase is designed or behaves.

**IMPORTANT: Be extremely selective.** Only extract learnings you are highly confident about. When in doubt, return an empty array. A false positive is far worse than a false negative.

## Input

**PR URL:** {pr_url}
**Target Repository:** {target_repo}

### Full PR Conversation

{pr_conversation}

---

## Your Goal

Extract durable facts about how this codebase is structured or behaves, as revealed by engineers discussing this PR. These may come from any part of the conversation: design debates, dismissals of approaches, explanations of intent, implementation decisions, or corrections to any automated review comments present.

A future reviewer querying the knowledge base should be able to apply these facts to an unrelated PR in the same repository.

---

## What to Extract

Each learning must be:

- A durable fact about **how the code is structured or behaves**, not an observation about this specific PR's changes
- Grounded in concrete evidence from the conversation (file paths, function names, design decisions stated by engineers)
- Specific enough that a reviewer could apply it to unrelated future PRs in the same repo
- Phrased as a **declarative statement of established behavior**, not a recommendation or criticism
- Something that could **not** have been derived solely from reading the repository's documentation files — the knowledge base captures runtime behaviors, edge cases, and call-chain constraints that static docs do not describe

---

## Signal Types — Classify Each Learning as One

| Type                    | Description                                                                                                                                                                              | Extract?                                                                                  |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `correction`            | An engineer explains that a stated or implied fact about the codebase was wrong, and provides the correct behavior with specific evidence.                                               | Yes — extract the correct behavior.                                                       |
| `clarification`         | An engineer adds architectural or structural context not previously stated anywhere in the conversation.                                                                                 | Yes — if specific enough to be actionable in future reviews.                              |
| `confirmation`          | An engineer validates a claim **and** explains the broader convention or invariant behind it, adding specificity beyond what was already said.                                           | Yes — extract the durable invariant, not the agreement itself.                            |
| `dismissal_with_reason` | An engineer dismisses an approach or concern and gives a **codebase-specific reason** — e.g. "this is expected behavior", "that's handled by X upstream", "we intentionally use Y here". | Yes — the **reason** is often a durable design fact. Extract the fact, not the dismissal. |
| `irrelevant`            | Vague agreement/disagreement, procedural comments, style opinions, sprint plans, "thanks", emoji.                                                                                        | No.                                                                                       |

### How to Handle Dismissals

A dismissal like _"P2 is expected behaviour, we require strings for specific accounts"_ contains a durable fact: the codebase intentionally uses string IDs for synthetic account nodes. Extract that fact.

A dismissal like _"ignoring P1 because it's highly unlikely"_ with no codebase-specific reason contains no durable fact — skip it.

A dismissal like _"P3 is handled by the OpenAPI validator upstream"_ reveals that input validation for that layer is delegated to the OpenAPI schema — extract that architectural fact.

**The pattern: if the reason for dismissing is codebase-specific, the reason itself is the learning.**

---

## Quality Bar

**BAD — dismissal without codebase fact:**

> "Ignoring P1 because it's highly unlikely."

**BAD — vague clarification:**

> "This is handled elsewhere."

**BAD — restates what is already in static documentation:**

> "All service classes must export a singleton via `export default new ClassName()`"

**BAD — learning is just a rephrased PR-specific observation:**

> "The Redis guard uses `=== null` instead of falsy check."

**GOOD — design intent extracted from a dismissal:**

> "Synthetic group node IDs in P&L and Cashflow reports (e.g., `'netPnl'`, `'operatingAssets'`) intentionally use string literals rather than ObjectIds — this is a deliberate stable-key design choice."

**GOOD — upstream delegation extracted from a dismissal:**

> "Multi-range timestamp input validation is intentionally delegated to the OpenAPI schema validator at the routing layer; the controller does not perform explicit structural validation."

**GOOD — correction with concrete evidence:**

> "The Redis service always initializes to either a client instance or `null`, never `undefined` — the `=== null` guard is therefore sufficient in all standard server contexts."

---

## Confidence Requirements

Before including any candidate, verify all four:

1. **Is this a durable fact about the codebase?** If it could become stale after a single refactor, skip it.
2. **Is the evidence concrete and specific?** Vague feedback without function names, paths, or call-chain descriptions is insufficient.
3. **Would a future reviewer of this repo benefit from knowing this?** If it only helps understand this specific PR's diff, skip it.
4. **Does the speaker demonstrate authority or provide verifiable specifics?** Corrections and clarifications must come with specific code references or explicit design intent — not just disagreement.

---

## Strict Rejection Criteria — DO NOT extract if ANY apply

**Content filters:**

- Subjective opinions or style preferences
- Temporary workarounds or sprint-scoped explanations ("we're fixing this next sprint")
- Feedback that simply agrees or disagrees without a codebase-specific reason
- Vague or hand-wavy explanations ("it's handled somewhere", "there's a guard for that")
- Conversational noise ("thanks", "good catch", "LGTM", emoji-only)
- Feedback where the correction might itself be wrong (uncertain language: "I think", "maybe", "probably")

**Static documentation contamination:**

- The learning is already captured in `AGENTS.md` or any of its linked docs
- The learning restates a convention explicitly documented in the repository
- The learning could have been written by someone who only read the repository documentation without examining the conversation

**Quality filters:**

- `answers_query` not specific enough to represent a real future reviewer question
- Learning text shorter than 60 characters
- Evidence text shorter than 40 characters
- No specific file paths, class names, function names, or design decisions anchoring the claim
- Stability would be rated "low"

---

## Output Format

```json
[
  {
    "answers_query": "<the specific question a future reviewer would ask, ≥10 words>",
    "learning": "<durable declarative fact, ≥60 chars>",
    "signal_type": "correction | clarification | confirmation | dismissal_with_reason",
    "category": "architecture | coding_pattern | service_call_chain | fundamental_design",
    "evidence": "<specific quote or paraphrase from the conversation, ≥40 chars>",
    "stability": "medium | high",
    "scope_tags": ["<1-5 topic tags>"],
    "paths": ["<relevant file paths>"],
    "symbols": ["<relevant function/class/variable names>"],
    "source_pr": "{pr_url}"
  }
]
```

**Self-check before finalizing each entry:**

1. Does `answers_query` represent a question a future reviewer would actually ask? If not, discard.
2. Does `learning` describe an established codebase fact with zero trace of PR-specific observations? If not, discard.
3. Is `evidence` grounded in something an engineer actually said, with enough specificity to be verifiable? If not, discard.
4. Could this learning have been written by someone who only read `AGENTS.md` without reading the conversation? If yes, discard.

Return an empty array `[]` if no candidates survive. This is preferred over extracting low-quality learnings.

Respond ONLY with the JSON array. No explanation, no markdown fences, no preamble.
