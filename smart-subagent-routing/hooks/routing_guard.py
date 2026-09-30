#!/usr/bin/env python3
"""Deterministic guard for subagent routing.

SessionStart: injects the active routing mode into context, so the policy
applies even if the smart-subagent-routing skill never gets loaded.
PreToolUse (Agent): enforces the mode and blocks untagged subagents behind a
gateway, which would otherwise silently run on the parent/default model
(often the Claude subscription).

Mode, highest precedence first:
  /routing <mode> slash command   per-session state file (see `set` below)
  SUBAGENT_ROUTING env var        auto (default) | ask | solo | off
Env:
  SUBAGENT_ROUTING_TAG  prompt prefix that routes a subagent (default: CCR tag)

CLI (used by the /routing command):
  routing_guard.py set <session_id> [mode]   store the mode, or show it if omitted
"""
import json
import os
import sys
import time
from pathlib import Path

MODES = ("auto", "ask", "solo", "off")
TAG = os.environ.get("SUBAGENT_ROUTING_TAG", "<CCR-SUBAGENT-MODEL>")
CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
STATE_DIR = CONFIG_DIR / "subagent-routing"
STATE_MAX_AGE = 14 * 24 * 3600


def state_file(session_id):
    return STATE_DIR / "".join(c for c in session_id if c.isalnum() or c == "-")


def routing_mode(session_id):
    try:
        mode = state_file(session_id).read_text().strip() if session_id else ""
    except OSError:
        mode = ""
    if mode not in MODES:
        mode = os.environ.get("SUBAGENT_ROUTING", "auto").strip().lower()
    return mode if mode in MODES else "auto"


def prune_old_state():
    cutoff = time.time() - STATE_MAX_AGE
    for path in STATE_DIR.glob("*"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            pass


def set_mode(session_id, mode):
    mode = mode.strip().lower()
    if mode and mode not in MODES:
        print(f"Unknown mode '{mode}'. Use one of: {', '.join(MODES)}.")
        return
    if mode:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        state_file(session_id).write_text(mode)
    print(f"subagent-routing mode for this session: {routing_mode(session_id)}.")


def behind_gateway():
    url = os.environ.get("ANTHROPIC_BASE_URL", "")
    return bool(url) and "anthropic.com" not in url


def emit(output):
    json.dump({"hookSpecificOutput": output}, sys.stdout)
    sys.exit(0)


def session_start(mode):
    if mode == "off":
        sys.exit(0)
    notes = {
        "auto": "Before implementing or spawning a subagent, follow the smart-subagent-routing skill.",
        "ask": "Only delegate to a subagent after the user approves; say which model and why in one line.",
        "solo": "Do all work yourself. Do not call the Agent tool: the user is evaluating this model alone.",
    }
    context = f"subagent-routing mode: {mode}. {notes[mode]}"
    if behind_gateway() and mode != "solo":
        context += f" Every Agent prompt must start with the {TAG} routing tag; untagged calls are denied."
    emit({"hookEventName": "SessionStart", "additionalContext": context})


def pre_tool_use(mode, tool_input):
    def decide(decision, reason):
        emit({
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        })

    if mode == "off":
        sys.exit(0)
    if mode == "solo":
        decide("deny", "subagent-routing solo mode: do this work yourself instead of delegating.")
    if behind_gateway() and not tool_input.get("prompt", "").lstrip().startswith(TAG):
        decide("deny", (
            f"Untagged subagent behind the gateway: it would run on the parent/default model, "
            f"possibly the Claude subscription. Re-issue with the {TAG} tag from the Agent tool "
            f"description as the prompt's first line, or do the work yourself."
        ))
    if mode == "ask":
        decide("ask", "subagent-routing ask mode: approve delegating this task to a subagent?")
    sys.exit(0)


def main():
    if sys.argv[1:2] == ["set"]:
        set_mode(sys.argv[2] if len(sys.argv) > 2 else "", " ".join(sys.argv[3:]))
        return
    event = json.load(sys.stdin)
    mode = routing_mode(event.get("session_id", ""))
    if event.get("hook_event_name") == "SessionStart":
        prune_old_state()
        session_start(mode)
    else:
        pre_tool_use(mode, event.get("tool_input") or {})


if __name__ == "__main__":
    main()
