---
name: Adapter proposal
about: Propose an adapter for a new AI tool, platform, or channel
title: "[Adapter] "
labels: adapter
---

## Target platform

<!-- Name, version (if relevant), link to homepage/docs -->

## Tier classification

<!-- Pick one based on what the platform exposes -->

- [ ] **Tier 1** — Native hooks + skill + state config (full bidirectional)
- [ ] **Tier 2** — On-disk logs available + skill (pull + tail-based push)
- [ ] **Tier 3** — MCP server only (full pull, MCP-call push only)
- [ ] **Tier 4** — Skill file only (pull only, no push)

See [ADAPTERS.md](../../ADAPTERS.md) for tier definitions.

## Surfaces

### Skill location

<!-- Where would the skill file live? e.g. ~/.<tool>/skills/alterego/SKILL.md -->

### State config

<!-- What always-on config file does the tool read? e.g. CLAUDE.md, AGENTS.md -->

### Hook / plugin surface

<!-- Does the tool support hooks? If yes, what event types are exposed? -->

### MCP support

<!-- Does the tool support MCP? Link to the config file location if known. -->

### On-disk logs

<!-- Are there persistent logs that could be tailed? Path + format. -->

## Push capability

<!-- Which event types can be captured from this platform? -->

## Pull capability

<!-- Can context be injected at session start? How? -->

## Prior art

<!-- Has graphify or another tool built integrations? Link them. -->

## Notes

<!-- TOS concerns, gotchas, alternatives considered. -->
