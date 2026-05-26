# Memory Types

The eight base memory types in AlterEgo's open schema. Each captures a
different kind of signal distilled from raw events.

The schema is intentionally open: adapters and users can declare new types
in the [constitution](./CONSTITUTION-TEMPLATE.md). The eight below are the
recommended starting point — enough to model most observed behavior without
premature specialization.

## Common fields

Every memory, regardless of type, carries the same envelope:

```json
{
  "id": "mem_8f3a2b1c",
  "type": "Preference",
  "content": "uses pnpm over npm for JavaScript projects",
  "created_at": "2026-05-22T18:30:00Z",
  "last_seen_at": "2026-05-24T09:15:00Z",
  "valid_from": "2024-09-01T00:00:00Z",
  "valid_to": null,
  "confidence": 0.94,
  "sources": ["evt_a1b2", "evt_c3d4", "evt_e5f6"],
  "embedding": [...],
  "tags": ["dev-tooling", "javascript"],
  "scope": { "project": null, "tool": null }
}
```

`confidence` rises with repeated observation and decays with time.
`valid_to` is set when an `Updates` or `Contradicts` edge invalidates the memory.
`sources` is mandatory — every claim must point to its events.

## The eight types

### Identity

Who the user is. Stable across contexts. Used as high-priority context at
session start.

| Field           | Value                                                              |
| --------------- | ------------------------------------------------------------------ |
| When created    | First sessions, or when consistent role/language/location detected |
| Decay (λ)       | 0.0001 day⁻¹ (≈ 19-year half-life)                                 |
| Typical sources | Many events with consistent locale, signature, domain              |

```json
{
  "type": "Identity",
  "content": "Odoo 18 developer based in Italy; prefers Italian for chat, English for code",
  "confidence": 0.99
}
```

### Preference

A choice made repeatedly when alternatives exist.

| Field           | Value                                                 |
| --------------- | ----------------------------------------------------- |
| When created    | Same choice observed N≥3 times with no contradictions |
| Decay (λ)       | 0.01 day⁻¹ (≈ 70-day half-life)                       |
| Typical sources | `tool.invoke` events, command history                 |

```json
{
  "type": "Preference",
  "content": "uses pnpm over npm",
  "confidence": 0.94,
  "sources": [
    /* 12 events */
  ]
}
```

### Convention

A rule the user follows or has stated explicitly.

| Field           | Value                                                              |
| --------------- | ------------------------------------------------------------------ |
| When created    | Explicit declaration (CLAUDE.md, conversation) or heavy repetition |
| Decay (λ)       | 0.001 day⁻¹ (≈ 2-year half-life)                                   |
| Typical sources | Repository files, conversational statements                        |

```json
{
  "type": "Convention",
  "content": "Commit format: [MODULE_NAME] - descrizione in italiano",
  "confidence": 0.99
}
```

### Fact

A discrete fact about the user's world. Not behavioral.

| Field           | Value                                                                     |
| --------------- | ------------------------------------------------------------------------- |
| When created    | Deterministic extractors (paths, git, project structure) or LLM detection |
| Decay (λ)       | Type-dependent (project facts decay slowly; PR-specific facts decay fast) |
| Typical sources | File access events, git events, structured outputs                        |

```json
{
  "type": "Fact",
  "content": "ODOO18 workspace has 71 custom modules in singleflo/",
  "confidence": 0.99
}
```

### Decision

A choice made at a point in time, with reasoning preserved.

| Field           | Value                                                                |
| --------------- | -------------------------------------------------------------------- |
| When created    | Explicit decision moments (commits, planning sessions, declarations) |
| Decay (λ)       | 0.005 day⁻¹ (≈ 140-day half-life)                                    |
| Typical sources | Conversation, commit messages, ADRs                                  |

```json
{
  "type": "Decision",
  "content": "AlterEgo: self-host and open-source only, no SaaS",
  "reasoning": "privacy and control concerns",
  "ts": "2026-05-22"
}
```

### AntiPattern

Something that fails when tried. Negative knowledge.

| Field           | Value                                                                |
| --------------- | -------------------------------------------------------------------- |
| When created    | `error.encountered` followed by `retry.attempt`, or explicit warning |
| Decay (λ)       | 0.003 day⁻¹ (≈ 230-day half-life) — failures are remembered          |
| Typical sources | Errors, repeated retries, warnings in instructions                   |

```json
{
  "type": "AntiPattern",
  "content": "<tree> in Odoo 18 views fails — use <list>",
  "encounters": 4,
  "confidence": 0.98
}
```

### Solution

A fix that actually worked. Paired with an `AntiPattern` via `CausedBy` edge.

| Field           | Value                                                 |
| --------------- | ----------------------------------------------------- |
| When created    | `success.after_failure` event                         |
| Decay (λ)       | 0.005 day⁻¹ (context-specific solutions decay faster) |
| Typical sources | Successful retries, conversational fixes              |

```json
{
  "type": "Solution",
  "content": "opencode offline: restart with `opencode start --foreground`",
  "paired_with": "mem_antipattern_opencode_offline"
}
```

### Workflow

A recurring execution pattern. Captured at a different granularity from
events: from sequences, not single events.

| Field           | Value                                                           |
| --------------- | --------------------------------------------------------------- |
| When created    | Session-end retrospective or cross-session statistical analysis |
| Decay (λ)       | 0.005 day⁻¹ (≈ 140-day half-life)                               |
| Typical sources | Multiple sessions; structural patterns, not content             |

```json
{
  "type": "Workflow",
  "content": "research-before-action: typically fires 3-5 parallel research agents before architectural decisions",
  "evidence_sessions": 12,
  "confidence": 0.91
}
```

## Edge types

Memories connect through six edge types. Edges also carry timestamps and
confidence — relationships are first-class temporal facts.

| Edge          | Meaning                                                                  |
| ------------- | ------------------------------------------------------------------------ |
| `RelatedTo`   | Generic association                                                      |
| `Updates`     | Supersedes an older memory (sets `valid_to` on old, `valid_from` on new) |
| `Contradicts` | Conflict detected, awaiting resolution                                   |
| `CausedBy`    | Causal link (a `Solution` `CausedBy` an `AntiPattern`)                   |
| `PartOf`      | Hierarchy                                                                |
| `SupportedBy` | Provenance link to specific events                                       |

## Extending the schema

Add a type when:

- A class of memory recurs and doesn't map cleanly to the eight base types
- A domain-specific concept needs first-class representation
- Edge types alone cannot express the semantics

Declare the new type in the constitution (see [CONSTITUTION-TEMPLATE.md](./CONSTITUTION-TEMPLATE.md)) with:

- name and one-sentence definition
- creation trigger
- suggested decay rate
- example record

Resist proliferation. Eight is small on purpose — the goal is recognizable
behavior, not exhaustive ontology.
