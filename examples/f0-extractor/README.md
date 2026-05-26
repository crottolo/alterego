# F0 Extractor — Deterministic-First Reference Implementation

A minimal, dependency-free Python reference implementation of the
**deterministic-first pass** described in [SPEC.md](../../SPEC.md) §Five operations.

It reads a JSONL file of canonical AlterEgo events and produces a `me.md`
memory profile using only regex, counters, and statistical patterns.
No LLM call. No external dependencies. Python 3.10+ stdlib only.

This is what AlterEgo would run _before_ invoking the LLM classifier:
extract everything that can be extracted deterministically, then let the
LLM handle only what's left.

## What it extracts

| Section                 | Source signal                                                               |
| ----------------------- | --------------------------------------------------------------------------- |
| **Identity**            | language detection on prompts, active-hour histogram, source tool diversity |
| **Conventions**         | regex on `git commit` invocations → format detection                        |
| **Tool preferences**    | tool invocation counters, package manager detection from Bash args          |
| **Delegation patterns** | `subagent.spawn` counters, parallelism bursts                               |
| **Anti-patterns**       | `error.encountered` events grouped by `kind` with N≥2 threshold             |
| **Solutions**           | `success.after_failure` events, paired with attempt counts                  |
| **Workflow**            | session duration, events/session, retries, parallel-spawn bursts            |

## Quick run

```bash
python3 extract.py --input events-sample.jsonl --output me.md
cat me.md
```

The repo includes `events-sample.jsonl` (93 synthetic events across 9 sessions,
covering all event types) and `sample-me.md` (the output of running `extract.py`
on the sample).

## The canonical event schema

Every event is one JSON line:

```json
{
  "id":          "evt_<id>",
  "ts":          "2026-04-15T09:23:14Z",
  "type":        "prompt.user | response.agent | tool.invoke | ...",
  "source_tool": "opencode | claude-code | cursor | ...",
  "session_id":  "ses_<id>",
  "payload":     { ... type-specific fields ... }
}
```

Full list of recognized `type` values:

- `session.start`, `session.end`
- `prompt.user`, `response.agent`
- `tool.invoke`, `tool.result`
- `subagent.spawn`, `subagent.return`
- `web.fetch`
- `file.access`
- `error.encountered`
- `retry.attempt`, `success.after_failure`

Adapters for each AI tool convert that tool's native events into this format.
See [ADAPTERS.md](../../ADAPTERS.md) for per-platform integration notes.

## Bring your own data

To run this on your own AI tool sessions, write a small adapter that emits
the canonical event format. The structure is intentionally minimal — any
producer can write a tail script that converts its events to JSONL.

The reference adapters described in [ADAPTERS.md](../../ADAPTERS.md) are
not yet implemented here. Contributions welcome via the
[Adapter Proposal](../../.github/ISSUE_TEMPLATE/adapter-proposal.md) issue
template.

## What this is not

- It is **not** the full AlterEgo system. It is the deterministic pre-pass.
- It does **not** classify natural-language intent or preferences inferred
  from conversation. That is the LLM classifier's job (next phase).
- It does **not** maintain a persistent memory graph. It produces a
  one-shot snapshot from a batch of events.
- It does **not** read any tool's database, log, or chat history directly.
  It reads only the canonical events.jsonl produced by adapters.

## Why this is enough as a starting point

The deterministic pre-pass is responsible for the majority of high-confidence
memories. Tool counts, package-manager preference, commit format, recurring
errors, parallel-delegation patterns — none of these need an LLM to detect.
They are cheap, fast, and exact.

The LLM classifier is reserved for what only an LLM can do: read natural
language, infer intent, detect contradictions, summarize workflows in prose.
Stacking the LLM on top of deterministic extraction is what makes the
pipeline economical at scale.

## Sample output

See [`sample-me.md`](./sample-me.md) for the full extracted profile from the
synthetic `events-sample.jsonl`. Highlights:

- 93 events / 9 sessions / 9-day span
- Italian / English language mix detected from prompts
- `pnpm` preferred package manager (10 invocations)
- `[MODULE] - message` commit format detected (8 commits)
- 2 recurring anti-patterns (`odoo_view_tree_deprecated`, `jwt_expired_unhandled`)
- 3 solutions recovered after failure attempts
- 2 research-heavy sessions (3+ parallel subagent spawns within 30s)

## License

CC0 1.0 Universal — same as the parent spec.
