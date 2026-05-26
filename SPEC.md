# AlterEgo

A pattern for personal AI memory that follows you across tools, learns from how you work,
and stays under your control.

## The idea

Most AI tools have short memory. Claude forgets you between sessions. ChatGPT remembers
some things but only inside its walled garden. Your coding agent doesn't know your
conventions. Your project assistant doesn't know the decision you made yesterday with a
different agent on a different machine.

The pattern proposed here is simple: instead of each AI tool maintaining its own opaque,
vendor-locked memory of you, you run a **local memory layer** that every AI tool you use
writes to and reads from. The layer observes — passively, while you work — and distills
events into typed, time-aware memories. New sessions start with the right context already
loaded. The memory lives on your machine (or a server you control), in a format you can
inspect, edit, export, and migrate.

This is not RAG. RAG retrieves chunks from documents at query time. This is observational:
events come _from_ your AI tools as you use them, get classified into structured memories,
and feed back into future sessions as compact context.

It is also not a single-tool feature. The same layer serves Claude Code, opencode, Cursor,
Gemini CLI, Codex, and any future agent that follows the same protocol. The memory is
yours, not the vendor's.

## Why this is needed

Current options fall into three categories, each with a structural limit:

- **Vendor memory** (Claude, ChatGPT, Gemini): opaque, server-side, account-bound, not
  portable between tools. You don't see what it knows. You can't move it. Every vendor
  has to rebuild your profile from scratch.

- **Manual context files** (`CLAUDE.md`, `AGENTS.md`, `MEMORY.md`): explicit, portable,
  but maintenance-heavy. You forget to update them. They go stale. They don't generalize
  across projects.

- **Document-driven memory** (mem0, Letta, NotebookLM): you ingest files; the system
  retrieves from them. Useful for knowledge bases. Not useful for learning _who you are_
  from _what you do_.

None of these answer the question: _what does the system know about me that it learned
from watching me work?_ Apple is the only large vendor positioned to build this on-device,
but Apple will not bridge to WhatsApp, opencode, or anything outside its ecosystem. The
cross-tool, observation-based, user-controlled memory layer is a gap.

## Architecture

Three layers plus a classifier.

```
┌──────────────────────────────────────────────────────────────────┐
│ PRODUCERS                                                        │
│ Each AI tool emits events as you use it: prompts, responses,     │
│ tool calls, errors, retries, web fetches, subagent spawns,       │
│ session boundaries. Async, fire-and-forget.                      │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (local HTTP or pipe)
┌──────────────────────────────────────────────────────────────────┐
│ STORE                                                            │
│  ┌────────────────┐    ┌──────────────┐    ┌─────────────────┐   │
│  │ Raw event log  │ →  │ Classifier   │ →  │ Memory graph    │   │
│  │ (append-only,  │    │ (LLM batch,  │    │ (typed nodes +  │   │
│  │  immutable)    │    │  periodic)   │    │  typed edges +  │   │
│  │                │    │              │    │  timestamps)    │   │
│  └────────────────┘    └──────────────┘    └─────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼ (HTTP / MCP)
┌──────────────────────────────────────────────────────────────────┐
│ CONSUMERS                                                        │
│ AI tools fetch compact, project-scoped, recency-weighted context │
│ at session start. Replaces or augments CLAUDE.md/AGENTS.md.      │
└──────────────────────────────────────────────────────────────────┘
```

Each layer is replaceable. SQLite for personal use, Postgres for multi-device. Local LLM
for the classifier, cloud LLM for harder cases. The contract between layers is the event
schema and the memory schema — both plain JSON, both versioned.

## What gets captured

Events are immutable JSON records emitted by AI tools and other adapters. Each event has
a timestamp, a type, a source tool, and a payload.

The base event types every adapter should emit:

- `prompt.user` — the user typed something at an AI tool
- `response.agent` — the AI responded
- `tool.invoke` / `tool.result` — a tool was called and returned
- `subagent.spawn` / `subagent.return` — a sub-agent was delegated to
- `web.fetch` — a URL was retrieved
- `file.access` — a file was read, written, or edited
- `error.encountered` — something failed
- `retry.attempt` / `success.after_failure` — a fix was tried; one worked
- `session.start` / `session.end` — a session opened or closed

Optional events from non-AI adapters (channels, calendar, mail, shell) can be added
without changing the schema: a `type`, a `ts`, a `payload`.

Two design rules: events are **immutable** (no edits, only invalidation through new
events) and **idempotent** (a stable `event_id` lets producers retry without duplicating).
This makes the raw log safe to replay, fork, and audit.

## What becomes memory

The classifier does not store events directly as memories. It distills batches of events
into typed nodes. The minimum viable schema:

- `Identity` — who the user is: roles, languages, locations, broad domain
- `Preference` — choices made repeatedly (`pnpm` over `npm`, async over sync)
- `Convention` — explicit rules followed (commit format, code style, file naming)
- `Fact` — discrete facts about the user's world (project structure, team members)
- `Decision` — choices made at a point in time, with the reasoning
- `AntiPattern` — things that fail when tried (deprecated APIs, broken approaches)
- `Solution` — the fix that actually worked, after one or more failed attempts
- `Workflow` — recurring execution patterns (how the user explores, decides, ships)

The schema is intentionally open. Add types as your domain demands. The categories above
are a starting point, not a constraint.

Every memory carries:

- a stable `id`
- `created_at`, `last_seen_at`, `valid_from`, optional `valid_to`
- a `confidence` score that increases with repeated observation and decays with time
- a `sources` array pointing to the events that produced it (provenance is non-negotiable)
- a vector embedding for semantic recall

Memories connect through typed edges:

- `RelatedTo` — generic association
- `Updates` — supersedes an older memory
- `Contradicts` — conflict detected, awaiting resolution
- `CausedBy` — causal link (a solution caused by a specific failure)
- `PartOf` — hierarchy
- `SupportedBy` — links to the events that constitute the evidence

Three things make this a memory and not a knowledge base. Time is a first-class
dimension: every memory has temporal validity and decays. Provenance is mandatory: every
claim points to its evidence. Contradictions are not silently overwritten: they create
`Updates` or `Contradicts` edges, preserving the history of what was true when.

## Five operations

**Capture** is passive and continuous. Producers emit events as the user works. No
intervention required.

**Classify** is periodic and batched. Every few minutes, or at session end, a job reads
unclassified events and distills them into memories. Two passes:

1. _Deterministic first._ Regex extractors for known patterns (file paths, commit hashes,
   tool output formats). AST tools like `graphify` for code symbols. Output parsers for
   `git`, `pnpm`, `pytest`. These are free, fast, and deterministic. They produce
   high-confidence memories without an LLM call.

2. _LLM classifier next._ Only on what remains: natural language, intent, preferences
   inferred from behavior. The LLM is invoked on batches of 50–100 events with the schema
   as a function-calling target. Deduplication is via embedding similarity; contradiction
   detection is via semantic comparison with existing memories of the same type.

**Recall** is on-demand and fast. A single endpoint takes a project path, a tool name,
a recency window, and a token budget. It returns compact markdown ready for system prompt
injection: identity, active conventions, tool preferences, recent decisions,
project-relevant anti-patterns. Retrieval is hybrid: vector similarity + full-text +
temporal decay, fused via Reciprocal Rank Fusion. Memories below a minimum weight are
filtered out.

**Decay** runs in the background. Every memory's effective weight is
`confidence * exp(-λ * age_days)`. Recent observations matter more than old ones. Pinned
memories are exempt. The schema lets the user tune `λ` per memory type: identities decay
slowly, todos decay fast.

**Reconcile** is periodic maintenance. Near-duplicate memories merge. Unresolved
contradictions surface for review. Orphaned nodes (no edges in or out) are flagged. The
graph stays clean without manual curation.

## The schema (constitution)

Like Karpathy's `CLAUDE.md` for the LLM Wiki, AlterEgo has a constitution file: a
markdown document that tells the classifier how to operate. It is not code. It is
configuration in prose, edited by the user.

The constitution defines:

- which memory types exist and when to create each
- extraction rules for known patterns (`when output contains 'fatal: not a git repo',
emit AntiPattern{git_outside_repo}`)
- redaction rules (`never capture content from paths matching ~/secrets/`)
- decay parameters per type
- entity identifiers (how to recognize that "Marco" in WhatsApp and "marco@..." in email
  are the same person)
- naming conventions for the user's domain

The constitution co-evolves with the user. When the classifier mis-categorizes, the user
edits the constitution. The classifier reads it on every batch. It is the programming
interface for the system, without writing code.

## Distribution

The pattern is replicable across many AI tools because most of them already expose the
necessary surfaces. The model to follow is `graphify` (`safishamsi/graphify`), which
ships a single CLI that installs itself into eighteen different AI platforms by writing
the right files in the right places.

The mechanism has three layers:

1. **A skill file** (`SKILL.md` or platform equivalent) placed in the tool's skill or
   plugin directory. It teaches the AI what AlterEgo is and how to invoke it.

2. **A state injection** (1–3 lines added to `CLAUDE.md`/`AGENTS.md`/`GEMINI.md` or the
   equivalent always-on config) that instructs the AI to fetch AlterEgo context at
   session start.

3. **A hook or plugin** (where the tool supports it: Claude Code, opencode, Gemini CLI,
   Codex) that pushes events to the local AlterEgo daemon as the user works.

For tools without native hooks (Cursor, Claude Desktop, Aider), AlterEgo registers as an
MCP server. Pull-side works fully. Push-side captures only MCP tool calls and explicit
`alterego_remember` invocations — lossy, but functional.

For tools with persistent on-disk logs (opencode's SQLite, Claude Code's JSONL
transcripts), a tail-based adapter reads events from existing files. No invasive
installation needed.

The `alterego install --platform <name>` command handles all three layers. Adding a new
platform means writing one adapter (typically 100–300 lines), not building a new product.

## Privacy and portability

The default deployment is local: a daemon on the user's machine, an embedded database, no
network egress except optional cloud LLM calls. A user who wants multi-device sync runs
the same daemon on a VPS they control.

Encryption at rest is non-negotiable. The database uses SQLCipher; secrets live in the OS
keychain. Redaction rules are explicit and editable: API keys, credentials, paths matching
sensitive patterns are filtered before any data reaches the classifier.

Portability is built in. `alterego export` produces JSONL of all events, memories, and
edges. `alterego import` reads the same format, plus converters from Claude memory export,
ChatGPT memory export, OpenClaw `MEMORY.md`, and Obsidian vaults. No data is held hostage.

When extended to non-AI channels (mail, messaging, calendar), the privacy stakes increase:
the system begins capturing data about third parties who did not consent. The
recommendation is firm: third-party data flows through a local-only classifier, not a
cloud LLM. Sensitive entities can be opt-out per-person. This is design from day one, not
a future patch.

## Why this works

Karpathy's LLM Wiki observed that the burden of maintaining a knowledge base is not the
reading or the thinking — it is the bookkeeping. LLMs are good at bookkeeping.

AlterEgo applies the same observation to the user's profile rather than to a domain. The
user works. The system watches. Events become typed memories. Sessions inherit context
they didn't have to build. The bookkeeping happens in the background.

Three properties make the result a memory, not a knowledge base, and not a CLAUDE.md
that goes stale:

- _Observational input._ The user does not curate. The system reads what the user does.
- _Temporal validity._ Facts have a `valid_at` and decay. Yesterday's preference can be
  superseded by today's behavior without losing the history.
- _Cross-tool by design._ The memory does not belong to a vendor. It belongs to the user
  and is consulted by whichever AI tool is in use.

The result is that a user's AI tools begin to behave consistently with the user's
patterns — not just their stated preferences, but their actual cadence, their recurring
failure modes, the fixes they have found before. The longer the system runs, the more
the AI feels like it knows the user. Not because the user told it. Because it watched.

## From memory to twin

A single instrumented tool gives AlterEgo facts about you. A few tools give it
preferences. The full ecosystem — your AI coding tools, your messaging channels, your
mail, your calendar, your project management — gives it something different in kind: an
operative signature.

```
INSTRUMENTATION GRADIENT

  Tools connected      Captured signal               Result
  ────────────────     ──────────────────────────    ──────────────────────

  1 tool               what you decided               Knowledge twin
  ────────────         preferences                    (a smarter CLAUDE.md)
  [▓░░░░░░░░░] 10%     anti-patterns

  3–5 tools            + how you decide               Behavioral twin
  ────────────         + when you decide              (works like you)
  [▓▓▓▓░░░░░░] 40%     + which tools, in what order
                       + your retry patterns

  10+ tools            + words you use                Operative clone
  ────────────         + cadence of your day          (sounds like you)
  [▓▓▓▓▓▓▓▓▓▓] 100%    + who you talk to, about what  + trainable dataset
                       + rhythm of your thought       for a fine-tuned model
                       + topics you keep returning to

  AI tools:    opencode · Claude Code · Cursor · Gemini · Codex · Copilot
  Messaging:   Slack · iMessage · Telegram · WhatsApp · Signal · Outlook · Gmail
  Work:        ClickUp · Asana · Notion · Linear · Jira · n8n · GitHub
  Ambient:     calendar · shell history · git log · browser
```

What gets captured at full coverage is not a profile in the traditional sense. It is a
working representation of your operational style: how you frame problems, how long you
explore before deciding, the words you reach for, the people you bring in for which
topics, the time of day you ship versus debug, the failure patterns that recur, the
fixes that actually work. The signature is unmistakable because the signal is dense
enough to encode it.

At this density, two things become possible that were not possible with a sparse profile:

- **Style-preserving response.** An AI tool reading the full context responds in your
  cadence, with your vocabulary, prioritizing what you prioritize. Not because it was
  told to. Because the context shows what you actually do.

- **A trainable dataset.** The same data that drives recall is, structurally, a corpus.
  Events with labels (memory types), timestamps, outcomes (failed vs worked),
  conversational structure. With enough volume, this is exactly the kind of data used to
  fine-tune a small model. The fine-tuned model is, by construction, a functional copy
  of your operational behavior. It does not need to be told who you are. It was trained
  to be a working model of you.

This is the difference between AlterEgo as memory and AlterEgo as twin. The pattern does
not change. The signal density does. The dataset that powers daily context injection at
small scale becomes, at large scale, the training set for a clone.

## Note on instantiation

This document is intentionally abstract. It describes a pattern, not an implementation.
The exact database choice, the classifier model, the format of the skill files, the
constitution conventions, the visualization — all depend on the implementer's preferences
and the platforms they care about. Everything here is modular: pick what is useful,
ignore what is not.

The right way to use this document is to share it with an LLM agent and work together to
instantiate a version that fits your tools and your domain. The categories of memory will
shift. The set of adapters will be narrower at first. The constitution will grow with use.

What stays constant is the pattern: observe, distill, decay, recall, refine.

---

License: [CC0 1.0 Universal](./LICENSE). Copy, fork, modify, redistribute without attribution.
