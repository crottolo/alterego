# Adapters

Per-platform implementation reference. Maps each AI tool to its hook surface,
skill location, and state config.

## The three-layer pattern

Every adapter writes up to three artifacts:

1. **Skill file** — teaches the AI tool about AlterEgo and how to invoke it
2. **State injection** — instructs the AI to fetch context at session start
3. **Hook or plugin** — pushes events to the local AlterEgo daemon (where supported)

A single CLI command — `alterego install --platform <name>` — places the right
files in the right places for each platform.

## Tier classification

Platforms differ in what they expose. Adapters work at four tiers:

| Tier  | Capability                          | Coverage                       | Examples                                 |
| ----- | ----------------------------------- | ------------------------------ | ---------------------------------------- |
| **1** | Native hooks + skill + state config | Full pull + full push          | Claude Code, opencode, Gemini CLI, Codex |
| **2** | On-disk logs available + skill      | Full pull + tail-based push    | (overlap with T1)                        |
| **3** | MCP server only                     | Full pull + MCP-call push only | Cursor, Claude Desktop, Aider            |
| **4** | Skill file only                     | Pull only, no push             | Copilot CLI, Trae, Pi                    |

Tier 2 is opportunistic: when a Tier 1 tool also keeps useful on-disk logs
(opencode's SQLite, Claude Code's JSONL), the same adapter can capture
historical events without instrumentation. This is also how F0 backfill works.

## Platform reference

### Claude Code (mac/linux/windows) — Tier 1

```
Skill:          ~/.claude/skills/alterego/SKILL.md
Hook config:    ~/.claude/settings.json
Hook types:     PreToolUse, PostToolUse, UserPromptSubmit, Stop, Notification
State config:   <project>/CLAUDE.md + ~/.claude/CLAUDE.md (global)
On-disk logs:   ~/.claude/projects/<encoded-path>/<session-uuid>.jsonl
```

Events captured via hooks: `prompt.user`, `tool.invoke`, `tool.result`,
`session.start`, `session.end`. JSONL transcripts allow Tier 2 tail of
historical sessions.

### opencode — Tier 1

```
Skill:          ~/.config/opencode/skills/alterego/SKILL.md
Plugin:         ~/.config/opencode/plugins/alterego.ts
Lifecycle:      onSessionStart, onBeforeExecute, onAfterExecute, onError
State config:   <project>/AGENTS.md + .opencode/instructions/*.md
On-disk logs:   ~/.local/share/opencode/opencode.db (SQLite)
Tail tables:    session, message, part, todo
```

opencode's plugin API exposes the richest event surface of any Tier 1 platform.

### Gemini CLI — Tier 1

```
Skill:          ~/.gemini/skills/alterego/SKILL.md
Hook config:    ~/.gemini/settings.json
Hook types:     BeforeTool, AfterTool
State config:   <project>/GEMINI.md
```

### Codex (OpenAI CLI) — Tier 1

```
Skill:          ~/.agents/skills/alterego/SKILL.md
Hook config:    .codex/hooks.json
Hook types:     PreToolUse
State config:   <project>/AGENTS.md
Extra:          multi_agent = true in .codex/config.toml
```

### Cursor — Tier 3

```
Skill:          .cursor/rules/alterego.mdc  (with alwaysApply: true)
MCP config:     .cursor/mcp.json
State config:   .cursor/rules/*.mdc files
```

No native hooks. Push-side via MCP server (captures MCP tool calls only).

### Claude Desktop — Tier 3

```
MCP config:     ~/Library/Application Support/Claude/claude_desktop_config.json
Skill:          (not supported in app — context lives in MCP tools)
```

Chat content is not directly accessible. Only MCP tool calls captured.
IndexedDB inspection is technically possible but TOS-risky and not recommended.

### Aider — Tier 3 (+ Tier 2 fallback)

```
Skill:          .aider.conf.yml (limited skill support)
MCP config:     (version-dependent)
On-disk logs:   <project>/.aider.input.history, <project>/.aider.chat.history.md
```

Logs are plain text — easy to tail. Useful Tier 2 source.

### OpenClaw — Tier 3 (multi-channel host)

```
Skill:          ~/.openclaw/workspace/skills/alterego/SKILL.md
State config:   ~/.openclaw/workspace/AGENTS.md
```

OpenClaw is itself a channel hub for WhatsApp/Telegram/Slack/Discord/iMessage.
AlterEgo can subscribe to its event bus for cross-channel push without
instrumenting each messenger individually.

### Factory Droid — Tier 3

```
Skill:          ~/.droid/skills/alterego/SKILL.md
State config:   <project>/AGENTS.md
```

### Trae / Trae CN — Tier 3

```
Skill:          .agents/skills/alterego/SKILL.md (project-local)
State config:   <project>/AGENTS.md
```

### Kiro IDE — Tier 3

```
Skill:          ~/.kiro/skills/alterego/SKILL.md
State config:   <project>/AGENTS.md
```

### Pi coding agent — Tier 3-4

```
Skill:          ~/.pi/skills/alterego/SKILL.md
```

Emerging platform; capabilities evolving.

### Google Antigravity — Tier 3-4

```
Skill:          ~/.antigravity/skills/alterego/SKILL.md
MCP config:     (assumed, evolving)
```

### Hermes / Kimi Code — Tier 4

```
Skill:          ~/.<tool>/skills/alterego/SKILL.md
```

Pull-only. No native hook or MCP at time of writing.

### GitHub Copilot (CLI + VS Code Chat) — Tier 4

```
Skill:          ~/.copilot/skills/alterego/SKILL.md (CLI)
VS Code:        custom-instructions file
```

No native hook. Pull works via the skill file. Push not possible without
external instrumentation.

## The universal MCP server

For any platform supporting MCP, AlterEgo exposes a single server with five tools:

```
alterego_context(project?, tool?, recency?, budget?) → markdown context
alterego_remember(content, type)                     → explicit memory push
alterego_recall(query)                               → semantic + temporal search
alterego_forget(memory_id)                           → invalidate a memory
alterego_why(claim)                                  → show evidence for a claim
```

Every MCP tool invocation is itself an event, so even Tier 3 platforms
contribute push signal — limited to operations visible at MCP layer.

## Log-tail adapters (zero installation)

For platforms with stable on-disk logs, AlterEgo daemon can passively tail
without touching the platform's config:

| Tool           | Path                                    | Format | Strategy                          |
| -------------- | --------------------------------------- | ------ | --------------------------------- |
| opencode       | `~/.local/share/opencode/opencode.db`   | SQLite | WAL watcher + incremental queries |
| Claude Code    | `~/.claude/projects/<enc>/<uuid>.jsonl` | JSONL  | fsevents/inotify + `tail -F`      |
| Aider          | `<project>/.aider.chat.history.md`      | text   | `tail -F`                         |
| iMessage (Mac) | `~/Library/Messages/chat.db`            | SQLite | WAL watcher (channels, V2)        |

Log-tail is the safest install mode: nothing is written into the user's tools.
It is also how the F0 backfill works against pre-existing sessions.

## Adding a new platform

1. Identify the platform's surfaces: skill dir? hooks? MCP? logs?
2. Choose tier (1/2/3/4)
3. Open an issue with the [Adapter Proposal](.github/ISSUE_TEMPLATE/adapter-proposal.md) template
4. Implement: `alterego install --platform <name>` writes the right files

Adapters average 100–300 lines of code each. The work is integration, not
invention.
