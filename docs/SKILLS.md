# Skills System (Upstream Format)

Hodor uses the upstream `@mariozechner/pi-coding-agent` skills system (`agentskills.io` style).

Skills are:
- Discovered from the reviewed repository at `.pi/skills` or `.hodor/skills`
- Advertised to the model as metadata
- Loaded lazily by the agent with the `read` tool when relevant

## Quick Start

Create a skill in the repository you want Hodor to review:

```bash
mkdir -p .pi/skills/security-review
```

```markdown
<!-- .pi/skills/security-review/SKILL.md -->
---
name: security-review
description: Security checklist for API and auth related pull requests.
---

## Authentication
- All protected endpoints must enforce auth middleware.
- Session and token checks must happen server-side.

## Input Validation
- Reject invalid payloads at API boundaries.
- Use parameterized queries for all DB access.
```

Run Hodor with verbose logs:

```bash
bun run dist/cli.js <PR_URL> --workspace . --verbose
```

## Supported Layouts

Hodor discovers skills from both `.pi/skills` and `.hodor/skills` (if either exists):

1. Flat markdown files: `.pi/skills/*.md` (or `.hodor/skills/*.md`)
2. Subdirectory skills: `.pi/skills/<skill-name>/SKILL.md` (recommended)

Use the subdirectory `SKILL.md` format when possible because it keeps one skill per folder and avoids name collisions.

## Frontmatter Requirements

Skills should include YAML frontmatter:

```yaml
---
name: security-review
description: Security checklist for API and auth related pull requests.
---
```

- `description` is required for the SDK to activate the skill.
- `name` is strongly recommended and should match the parent directory for `SKILL.md` skills.

## Behavior in Hodor

When Hodor starts a review:

1. It initializes the SDK resource loader with the review system prompt.
2. It discovers skills from `.pi/skills` and `.hodor/skills` in the reviewed repository.
3. It passes skill metadata to the agent.
4. The agent reads matching skill files on demand during review.

Hodor no longer inlines skill markdown into the system prompt and no longer uses `.cursorrules` or `AGENTS.md` as repository skills.

## Troubleshooting

If skills are not used:

1. Verify files are under `.pi/skills` or `.hodor/skills` in the repository being reviewed.
2. Ensure each skill has valid frontmatter with `description`.
3. Prefer `.pi/skills/<name>/SKILL.md` with `name: <name>`.
4. Run with `--verbose` and check skill discovery logs.
