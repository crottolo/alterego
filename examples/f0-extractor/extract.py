#!/usr/bin/env python3
"""
AlterEgo F0 Extractor — deterministic-first reference implementation.

Reads a JSONL file of canonical AlterEgo events and produces a `me.md`
memory profile using only deterministic extractors (regex, counters,
statistical patterns). No LLM call, no external dependencies.

This is the "deterministic-first" pass described in SPEC.md §Five operations.
The output is a starting profile that an LLM classifier would later refine.

Event schema (canonical):
    {
      "id":          "evt_<id>",
      "ts":          "2026-04-15T09:23:14Z",   ISO 8601 UTC
      "type":        "prompt.user" | "response.agent" | "tool.invoke" |
                     "tool.result" | "subagent.spawn" | "subagent.return" |
                     "web.fetch" | "file.access" | "error.encountered" |
                     "retry.attempt" | "success.after_failure" |
                     "session.start" | "session.end"
      "source_tool": "opencode" | "claude-code" | "cursor" | ...
      "session_id":  "ses_<id>",
      "payload":     <type-specific dict>
    }

Usage:
    python extract.py --input events.jsonl --output me.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

# --- Heuristics -----------------------------------------------------------

# Stopword lists for language detection. Short, high-signal words.
IT_STOPWORDS = {
    "il",
    "la",
    "le",
    "lo",
    "gli",
    "di",
    "che",
    "non",
    "per",
    "con",
    "una",
    "un",
    "ma",
    "se",
    "ne",
    "del",
    "della",
    "delle",
    "degli",
    "questa",
    "questo",
    "quella",
    "quello",
    "perché",
    "anche",
    "fare",
    "molto",
    "essere",
    "avere",
    "sono",
    "ecco",
    "così",
    "subito",
    "quindi",
    "allora",
    "voglio",
    "vorrei",
    "magari",
    "adesso",
    "ora",
    "facciamo",
    "vediamo",
}
EN_STOPWORDS = {
    "the",
    "is",
    "are",
    "have",
    "has",
    "do",
    "does",
    "this",
    "that",
    "these",
    "those",
    "with",
    "for",
    "from",
    "should",
    "would",
    "could",
    "want",
    "need",
    "make",
    "find",
    "search",
    "implement",
    "create",
    "build",
    "fix",
    "add",
    "remove",
    "use",
    "using",
}

# Package-manager command patterns (Bash tool args).
PM_PATTERNS = {
    "pnpm": re.compile(r"\bpnpm\b"),
    "npm": re.compile(r"\bnpm\b"),
    "yarn": re.compile(r"\byarn\b"),
    "bun": re.compile(r"\bbun\b"),
    "uv": re.compile(r"\buv\b"),
    "pip": re.compile(r"\bpip\b"),
    "cargo": re.compile(r"\bcargo\b"),
}

# Conventional Commits / project commit format detector.
COMMIT_RE = re.compile(
    r"^(?:\[(?P<bracket>[A-Z_]+)\]|"
    r"(?P<conv>feat|fix|chore|refactor|docs|test|perf|style|build|ci))"
    r"[\s:\-]+(?P<msg>.+)$",
    re.MULTILINE,
)


# --- Helpers --------------------------------------------------------------


def parse_ts(ts: str) -> datetime:
    """Parse an ISO 8601 timestamp into a UTC datetime."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)


def detect_language(text: str) -> str | None:
    """Return 'it', 'en', or None based on stopword frequency."""
    if not text or len(text) < 20:
        return None
    words = re.findall(r"\b[a-zA-ZàèéìòùÀÈÉÌÒÙ]+\b", text.lower())
    if not words:
        return None
    it_count = sum(1 for w in words if w in IT_STOPWORDS)
    en_count = sum(1 for w in words if w in EN_STOPWORDS)
    if it_count + en_count < 3:
        return None
    return "it" if it_count > en_count else "en"


def hour_bucket(ts: datetime) -> int:
    """Hour of day in local time approximation (UTC for portability)."""
    return ts.hour


def load_events(path: Path):
    """Yield parsed event dicts from a JSONL file."""
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                print(f"WARN: skipping malformed event: {e}", file=sys.stderr)


# --- Extractors -----------------------------------------------------------


def extract_facts(events: list[dict]) -> dict:
    """Aggregate facts: session count, message count, time span."""
    sessions = {e["session_id"] for e in events if "session_id" in e}
    timestamps = [parse_ts(e["ts"]) for e in events if "ts" in e]
    return {
        "total_events": len(events),
        "total_sessions": len(sessions),
        "first_event": min(timestamps) if timestamps else None,
        "last_event": max(timestamps) if timestamps else None,
        "source_tools": Counter(e.get("source_tool") for e in events),
        "event_types": Counter(e["type"] for e in events),
    }


def extract_identity(events: list[dict]) -> dict:
    """Language mix, active hours, source tool diversity."""
    lang_counter = Counter()
    hour_counter = Counter()
    for e in events:
        if e["type"] == "prompt.user":
            text = e.get("payload", {}).get("text", "")
            lang = detect_language(text)
            if lang:
                lang_counter[lang] += 1
        if "ts" in e:
            hour_counter[hour_bucket(parse_ts(e["ts"]))] += 1
    return {
        "language_mix": dict(lang_counter),
        "peak_hour": hour_counter.most_common(1)[0] if hour_counter else None,
        "active_hours": sorted(hour_counter.items()),
    }


def extract_tool_preferences(events: list[dict]) -> dict:
    """Tool invocation frequency. Package manager detection."""
    tool_counter = Counter()
    pm_counter = Counter()
    for e in events:
        if e["type"] != "tool.invoke":
            continue
        payload = e.get("payload", {})
        name = payload.get("tool")
        if name:
            tool_counter[name] += 1
        # Detect package manager from Bash args.
        if name == "Bash":
            cmd = payload.get("args", {}).get("command", "")
            for pm, pattern in PM_PATTERNS.items():
                if pattern.search(cmd):
                    pm_counter[pm] += 1
                    break
    return {
        "tool_usage": dict(tool_counter.most_common()),
        "package_managers": dict(pm_counter),
    }


def extract_subagent_patterns(events: list[dict]) -> dict:
    """Subagent delegation frequency and parallelism patterns."""
    agent_counter = Counter()
    sessions_with_spawn = defaultdict(int)
    for e in events:
        if e["type"] == "subagent.spawn":
            name = e.get("payload", {}).get("agent")
            if name:
                agent_counter[name] += 1
            sessions_with_spawn[e["session_id"]] += 1
    if sessions_with_spawn:
        avg_spawns = sum(sessions_with_spawn.values()) / len(sessions_with_spawn)
    else:
        avg_spawns = 0
    return {
        "delegated_agents": dict(agent_counter.most_common()),
        "sessions_w_delegate": len(sessions_with_spawn),
        "avg_spawns_per_sess": round(avg_spawns, 2),
    }


def extract_conventions(events: list[dict]) -> dict:
    """Detect commit format and other repeated conventions."""
    commit_formats = Counter()
    for e in events:
        if e["type"] != "tool.invoke":
            continue
        payload = e.get("payload", {})
        if payload.get("tool") != "Bash":
            continue
        cmd = payload.get("args", {}).get("command", "")
        # Look at git commit invocations.
        if "git commit" not in cmd:
            continue
        m = re.search(r"-m\s+[\"'](.+?)[\"']", cmd)
        if not m:
            continue
        msg = m.group(1)
        match = COMMIT_RE.match(msg)
        if match:
            if match.group("bracket"):
                commit_formats["[MODULE] - message"] += 1
            else:
                commit_formats["conventional commits"] += 1
        else:
            commit_formats["freeform"] += 1
    return {
        "commit_formats": dict(commit_formats),
    }


def extract_antipatterns(events: list[dict]) -> dict:
    """Recurring errors. Each unique error_kind counted; >= 2 occurrences flagged."""
    error_kinds = Counter()
    for e in events:
        if e["type"] != "error.encountered":
            continue
        kind = e.get("payload", {}).get("kind") or e.get("payload", {}).get(
            "error_kind",
        )
        if kind:
            error_kinds[kind] += 1
    recurring = {k: v for k, v in error_kinds.items() if v >= 2}
    return {
        "all_errors": dict(error_kinds),
        "recurring": recurring,
    }


def extract_solutions(events: list[dict]) -> dict:
    """Failures that were later resolved. Pair retry.attempt -> success.after_failure."""
    solutions = []
    by_session = defaultdict(list)
    for e in events:
        if e["type"] in ("error.encountered", "retry.attempt", "success.after_failure"):
            by_session[e["session_id"]].append(e)
    for sess_id, evs in by_session.items():
        for e in evs:
            if e["type"] == "success.after_failure":
                payload = e.get("payload", {})
                solutions.append(
                    {
                        "session": sess_id,
                        "summary": payload.get("summary", "(no summary)"),
                        "after": payload.get("after_attempts", 1),
                    },
                )
    return {
        "count": len(solutions),
        "solutions": solutions,
    }


def extract_workflows(events: list[dict]) -> dict:
    """Session-level patterns: avg duration, avg events per session, retry style."""
    by_session = defaultdict(list)
    for e in events:
        by_session[e["session_id"]].append(e)

    durations: list[float] = []
    events_per_session: list[int] = []
    retry_counts: list[int] = []
    parallel_spawns: list[int] = []

    for sess_id, evs in by_session.items():
        ts_list = sorted(parse_ts(e["ts"]) for e in evs if "ts" in e)
        if len(ts_list) >= 2:
            durations.append((ts_list[-1] - ts_list[0]).total_seconds() / 60.0)
        events_per_session.append(len(evs))
        retry_counts.append(sum(1 for e in evs if e["type"] == "retry.attempt"))
        spawns_in_burst = 0
        prev_ts = None
        max_burst = 0
        for e in evs:
            if e["type"] != "subagent.spawn":
                continue
            cur_ts = parse_ts(e["ts"])
            if prev_ts and (cur_ts - prev_ts).total_seconds() <= 30:
                spawns_in_burst += 1
                max_burst = max(max_burst, spawns_in_burst + 1)
            else:
                spawns_in_burst = 0
            prev_ts = cur_ts
        parallel_spawns.append(max_burst)

    def avg(xs: list) -> float:
        return round(sum(xs) / len(xs), 2) if xs else 0.0

    return {
        "sessions": len(by_session),
        "avg_duration_minutes": avg(durations),
        "avg_events_per_session": avg(events_per_session),
        "avg_retries_per_session": avg(retry_counts),
        "max_parallel_burst": max(parallel_spawns) if parallel_spawns else 0,
        "research_heavy_sessions": sum(1 for x in parallel_spawns if x >= 3),
    }


# --- Output renderer ------------------------------------------------------


def render_me_md(
    facts: dict,
    identity: dict,
    tools: dict,
    subagents: dict,
    conventions: dict,
    antipatterns: dict,
    solutions: dict,
    workflows: dict,
) -> str:
    """Render extracted memories as a markdown profile."""
    lines: list[str] = []
    add = lines.append

    add("# me.md")
    add("")
    add("Generated by AlterEgo F0 extractor (deterministic-first pass).")
    add(
        f"Source: {facts['total_events']} events across {facts['total_sessions']} sessions.",
    )
    add(
        f"Span: {facts['first_event'].isoformat() if facts['first_event'] else '?'} "
        f"→ {facts['last_event'].isoformat() if facts['last_event'] else '?'}",
    )
    add("")
    add("This file is the deterministic-first output. An LLM classifier would")
    add("refine these claims and surface natural-language patterns next.")
    add("")
    add("---")
    add("")

    # Identity
    add("## Identity")
    add("")
    if identity["language_mix"]:
        total = sum(identity["language_mix"].values())
        it_pct = (
            round(100 * identity["language_mix"].get("it", 0) / total) if total else 0
        )
        en_pct = (
            round(100 * identity["language_mix"].get("en", 0) / total) if total else 0
        )
        add(
            f"- Language mix in prompts: Italian {it_pct}%, English {en_pct}% "
            f"(detected on {total} prompts)",
        )
    if identity["peak_hour"]:
        h, n = identity["peak_hour"]
        add(f"- Peak activity hour (UTC): {h:02d}:00 ({n} events)")
    add(
        f"- Source tools observed: "
        f"{', '.join(f'{k} ({v})' for k, v in facts['source_tools'].most_common())}",
    )
    add("")

    # Conventions
    add("## Conventions")
    add("")
    if conventions["commit_formats"]:
        for fmt, n in sorted(
            conventions["commit_formats"].items(),
            key=lambda x: -x[1],
        ):
            add(f"- Commit format observed: `{fmt}` ({n} commits)")
    else:
        add("- No commit conventions detected yet.")
    add("")

    # Tool preferences
    add("## Tool preferences")
    add("")
    if tools["package_managers"]:
        for pm, n in sorted(tools["package_managers"].items(), key=lambda x: -x[1]):
            add(f"- Package manager: **{pm}** ({n} invocations)")
    add("")
    add("Top tools invoked:")
    for tool, n in list(tools["tool_usage"].items())[:10]:
        add(f"  - `{tool}` — {n}")
    add("")

    # Subagent delegation
    add("## Delegation patterns")
    add("")
    if subagents["delegated_agents"]:
        add(f"- Sessions with subagent delegation: {subagents['sessions_w_delegate']}")
        add(
            f"- Average spawns per delegating session: {subagents['avg_spawns_per_sess']}",
        )
        add("- Subagents most invoked:")
        for ag, n in list(subagents["delegated_agents"].items())[:8]:
            add(f"  - `{ag}` — {n}")
    else:
        add("- No delegation pattern detected.")
    add("")

    # Anti-patterns
    add("## Anti-patterns (errors that recur)")
    add("")
    if antipatterns["recurring"]:
        for kind, n in sorted(antipatterns["recurring"].items(), key=lambda x: -x[1]):
            add(f"- `{kind}` — encountered {n} times")
    else:
        add("- No recurring error patterns detected yet.")
    add("")

    # Solutions
    add("## Known solutions (recovered failures)")
    add("")
    if solutions["solutions"]:
        for s in solutions["solutions"][:10]:
            add(f"- {s['summary']} _(after {s['after']} attempts)_")
    else:
        add("- No success-after-failure patterns detected yet.")
    add("")

    # Workflows
    add("## Workflow patterns")
    add("")
    add(f"- Total sessions analyzed: {workflows['sessions']}")
    add(f"- Average session duration: {workflows['avg_duration_minutes']} min")
    add(f"- Average events per session: {workflows['avg_events_per_session']}")
    add(f"- Average retries per session: {workflows['avg_retries_per_session']}")
    add(f"- Max parallel subagent burst: {workflows['max_parallel_burst']}")
    add(
        f"- Research-heavy sessions (3+ parallel subagents): "
        f"{workflows['research_heavy_sessions']}",
    )
    add("")

    add("---")
    add("")
    add("_Generated by `extract.py` — see `README.md` in this directory._")
    add("")

    return "\n".join(lines)


# --- Entry point ----------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description="AlterEgo F0 deterministic extractor")
    ap.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to events JSONL file (canonical AlterEgo schema)",
    )
    ap.add_argument(
        "--output",
        default=Path("me.md"),
        type=Path,
        help="Output markdown file (default: me.md)",
    )
    args = ap.parse_args()

    if not args.input.is_file():
        print(f"ERROR: input file not found: {args.input}", file=sys.stderr)
        return 1

    events = list(load_events(args.input))
    if not events:
        print("ERROR: no events loaded", file=sys.stderr)
        return 1

    facts = extract_facts(events)
    identity = extract_identity(events)
    tools = extract_tool_preferences(events)
    subagents = extract_subagent_patterns(events)
    conventions = extract_conventions(events)
    antipatterns = extract_antipatterns(events)
    solutions = extract_solutions(events)
    workflows = extract_workflows(events)

    md = render_me_md(
        facts,
        identity,
        tools,
        subagents,
        conventions,
        antipatterns,
        solutions,
        workflows,
    )
    args.output.write_text(md, encoding="utf-8")

    print(f"OK: processed {len(events)} events → {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
