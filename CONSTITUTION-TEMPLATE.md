# AlterEgo Constitution Template

Copy this file to `~/.alterego/schema/manifest.md` and edit it.

The classifier reads this file on every batch. It is the programming interface
for AlterEgo — written in prose, not code. Edit it when the classifier
mis-categorizes, when you want to disable a memory type, or when you discover
a new pattern in your work.

---

## Identity

Your declared identity. Injected as high-priority context at session start.

- **Name:** `<your name>`
- **Primary domain:** `<e.g. "Full-stack developer, Odoo 18 specialist, Italy">`
- **Languages:** `<e.g. "Italian (native), English (technical, code)">`
- **Locale:** `<e.g. "it_IT">`
- **Public handles:** `<github: @username, x: @username>`

## Memory types enabled

Default: all eight base types. Disable any by removing from this list.
Custom types you've defined go at the bottom.

- [x] Identity
- [x] Preference
- [x] Convention
- [x] Fact
- [x] Decision
- [x] AntiPattern
- [x] Solution
- [x] Workflow

**Custom types:**

```
None yet.
```

## Extraction rules (deterministic)

Patterns that produce memories without invoking the LLM. Cheap, fast, exact.

```
# Git commit format
match: ^\[([A-Z_]+)\] - (.+)$
emit:  Convention{commit_format, value: "[$1] - $2"}

# Python import error
match: ImportError: No module named '(.+)'
emit:  Fact{missing_dependency, module: "$1"}

# pnpm successful install
match: progress: resolved (\d+), reused (\d+), downloaded
emit:  Preference{uses_pnpm, reinforcement: +1}

# Odoo module manifest
match: singleflo/([^/]+)/__manifest__.py
emit:  Fact{odoo_module, name: "$1", scope: project}
```

Add patterns from your own domain.

## Redaction rules

Never capture content matching these patterns. Applied before any storage,
before any LLM call.

**API keys and secrets:**

```
sk-[a-zA-Z0-9]{20,}
gho_[a-zA-Z0-9]{30,}
sk-ant-[a-zA-Z0-9-]{40,}
AKIA[0-9A-Z]{16}
ghp_[a-zA-Z0-9]{36}
```

**Sensitive paths:**

```
~/.ssh/
~/secrets/
~/.config/*/credentials
*/credentials.json
.env*
```

**Sensitive command output:**

```
env
printenv
cat .env*
gpg --decrypt
```

**Sensitive entities (opt-out per person):**

```
<person_name>: redact all messages; exclude from memory entirely
```

## Decay parameters

Tune `λ` (day⁻¹) per memory type. Higher λ = faster decay.

| Type        | λ              | Half-life                       |
| ----------- | -------------- | ------------------------------- |
| Identity    | 0.0001         | ~19 years                       |
| Convention  | 0.001          | ~2 years                        |
| AntiPattern | 0.003          | ~230 days                       |
| Decision    | 0.005          | ~140 days                       |
| Solution    | 0.005          | ~140 days                       |
| Workflow    | 0.005          | ~140 days                       |
| Preference  | 0.01           | ~70 days                        |
| Fact        | 0.01 (default) | ~70 days — overridable per fact |

Memories below `weight_threshold = 0.05` are filtered from context injection
but remain in the database.

## Entity resolution

Rules for collapsing identifiers that refer to the same person, project, or
thing. Update as you encounter aliases.

```
ent_self:
  - email: crotti.roberto@gmail.com
  - github: crottolo
  - all git commits authored by the above

ent_<person_name>:
  - whatsapp: <number>
  - email: <address>
  - slack: <handle>
  - mentioned-as: ["Marco", "marco", "MR"]

ent_proj_<name>:
  - paths: ["~/VSC/<project>"]
  - git remotes: ["github.com/.../<project>"]
  - referred-to-as: ["<aliases>"]
```

## Domain vocabulary

Terms specific to your domain. The classifier treats these as proper nouns
and avoids over-generalizing them.

- **Tools you use:** `<list>`
- **Project codenames:** `<list>`
- **Internal acronyms:** `<list>`
- **Frameworks/libraries dominant in your work:** `<list>`

## Privacy posture

- **All processing local:** yes / no
- **Cloud LLM for AI tool events:** yes / no
- **Cloud LLM for human channel events:** **no** (strongly recommended)
- **Encryption at rest:** SQLCipher / age / none
- **Multi-device sync:** local only / self-hosted VPS / never

## Schema version

```
schema_version: 0.1
last_edited: <YYYY-MM-DD>
edited_by: <handle>
```

---

This template is minimal on purpose. Add sections as your use of AlterEgo
matures. Anything not declared here falls back to the defaults in the
canonical [SPEC.md](./SPEC.md).
