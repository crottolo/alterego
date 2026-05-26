# AlterEgo

> A pattern for personal AI memory that follows you across tools, learns from how you
> work, and stays under your control.

## What this is

AlterEgo is **a specification**, not an implementation. It describes a pattern for a
local, cross-vendor memory layer that captures events from AI tools (opencode, Claude
Code, Cursor, Gemini, Codex, and others), distills them into typed, time-aware memories,
and injects compact context back into new sessions.

Read the full spec: **[SPEC.md](./SPEC.md)** — also available as [Gist](https://gist.github.com/crottolo/a5d3e33573de373c4a3673985b3000cf) for easy sharing.

## Why

- Your AI tools forget you between sessions.
- Vendor memory is opaque, server-side, and locked to one vendor.
- Manual context files (`CLAUDE.md`, `AGENTS.md`) go stale.
- No one is building a cross-tool, observation-based, user-owned memory layer.

This document defines what that layer would look like.

## Documentation

- **[SPEC.md](./SPEC.md)** — the full specification (also available as [Gist](https://gist.github.com/crottolo/a5d3e33573de373c4a3673985b3000cf))
- **[ADAPTERS.md](./ADAPTERS.md)** — per-platform implementation reference (18 AI tools)
- **[MEMORY-TYPES.md](./MEMORY-TYPES.md)** — the eight base memory types, expanded
- **[CONSTITUTION-TEMPLATE.md](./CONSTITUTION-TEMPLATE.md)** — template for `~/.alterego/schema/manifest.md`

## Status

**Phase 0: specification.** No code yet. The document is intended to be shared with an
LLM agent and instantiated against your specific tools and domain.

If you build an implementation, an adapter, or a fork — open an issue (use the
[Adapter Proposal](./.github/ISSUE_TEMPLATE/adapter-proposal.md) template) or PR
linking to it. The pattern grows by accumulation.

## Inspiration

- [Karpathy's LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — observational knowledge maintained by an LLM
- [Spacebot](https://github.com/spacedriveapp/spacebot) — typed memory graph + cortex pattern
- [OpenClaw](https://github.com/openclaw/openclaw) — local-first personal AI assistant
- [graphify](https://github.com/safishamsi/graphify) — cross-platform install model
- [Andy Matuschak's evergreen notes](https://notes.andymatuschak.org) — atomic, densely linked, permanent

## License

[CC0 1.0 Universal](./LICENSE). Copy, fork, modify, redistribute without attribution.
