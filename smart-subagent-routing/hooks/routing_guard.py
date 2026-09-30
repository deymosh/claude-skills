#!/usr/bin/env python3
"""Deterministic guard for subagent routing.

SessionStart: injects the active routing mode into context, so the policy
applies even if the smart-subagent-routing skill never gets loaded.
PreToolUse (Agent): enforces the mode and blocks untagged subagents behind a
gateway, which would otherwise silently run on the parent/default model
(often the Claude subscription). In solo mode, only subagents routed to the
session's own model are allowed.

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
import re
import sys
import time
from pathlib import Path

MODES = ("auto", "ask", "solo", "off")
TAG = os.environ.get("SUBAGENT_ROUTING_TAG", "<CCR-SUBAGENT-MODEL>")
TAG_TARGET = re.compile(re.escape(TAG) + r"\s*([^<\s]+)")
CCR_CLIENT_ID = re.compile(r"claude-ccr-h([0-9a-fA-F]+)")
CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
STATE_DIR = CONFIG_DIR / "subagent-routing"
STATE_MAX_AGE = 14 * 24 * 3600


def state_file(session_id, suffix=""):
    return STATE_DIR / ("".join(c for c in session_id if c.isalnum() or c == "-") + suffix)


def read_state(session_id, suffix=""):
    try:
        return state_file(session_id, suffix).read_text().strip() if session_id else ""
    except OSError:
        return ""


def write_state(session_id, value, suffix=""):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_file(session_id, suffix).write_text(value)


def routing_mode(session_id):
    mode = read_state(session_id)
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
        write_state(session_id, mode)
    print(f"subagent-routing mode for this session: {routing_mode(session_id)}.")


def behind_gateway():
    url = os.environ.get("ANTHROPIC_BASE_URL", "")
    return bool(url) and "anthropic.com" not in url


def canonical_model(model):
    """Reduce a model reference to a comparable 'Provider/model' form.

    CCR client IDs hex-encode the target (anthropic/claude-ccr-h<hex>);
    context-window suffixes like [1m] are dropped.
    """
    model = (model or "").strip()
    match = CCR_CLIENT_ID.search(model)
    if match:
        try:
            model = bytes.fromhex(match.group(1)).decode()
        except ValueError:
            pass
    return re.sub(r"\[[^\]]*\]$", "", model).strip().lower()


def session_model(event):
    """The model the session is currently answering with (tracks /model)."""
    try:
        with open(event.get("transcript_path") or "", "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 512 * 1024))
            lines = f.read().decode("utf-8", "replace").splitlines()
        for line in reversed(lines):
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            message = entry.get("message") if isinstance(entry, dict) else None
            if entry.get("type") == "assistant" and isinstance(message, dict) and message.get("model"):
                return message["model"]
    except OSError:
        pass
    return read_state(event.get("session_id", ""), ".model")


def emit(output):
    json.dump({"hookSpecificOutput": output}, sys.stdout)
    sys.exit(0)


def session_start(mode, event):
    if event.get("model"):
        write_state(event.get("session_id", ""), event["model"], ".model")
    if mode == "off":
        sys.exit(0)
    notes = {
        "auto": "Before implementing or spawning a subagent, follow the smart-subagent-routing skill.",
        "ask": "Only delegate to a subagent after the user approves; say which model and why in one line.",
        "solo": (
            "The user is evaluating this session's model alone: subagents may only run on this same model. "
            "If it is not in the Agent tool's model list, do all work yourself."
        ),
    }
    context = f"subagent-routing mode: {mode}. {notes[mode]}"
    if behind_gateway():
        context += f" Every Agent prompt must start with the {TAG} routing tag; untagged calls are denied."
    emit({"hookEventName": "SessionStart", "additionalContext": context})


def pre_tool_use(mode, event):
    def decide(decision, reason):
        emit({
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        })

    tool_input = event.get("tool_input") or {}
    prompt = tool_input.get("prompt", "").lstrip()
    if mode == "off":
        sys.exit(0)
    if behind_gateway() and not prompt.startswith(TAG):
        decide("deny", (
            f"Untagged subagent behind the gateway: it would run on the parent/default model, "
            f"possibly the Claude subscription. Re-issue with the {TAG} tag from the Agent tool "
            f"description as the prompt's first line, or do the work yourself."
        ))
    if mode == "solo":
        own = session_model(event)
        if behind_gateway():
            match = TAG_TARGET.match(prompt)
            target = match.group(1) if match else ""
            allowed = bool(own) and canonical_model(target) == canonical_model(own)
        else:
            target = tool_input.get("model") or ""
            allowed = target in ("", "inherit")
        if not allowed:
            decide("deny", (
                f"subagent-routing solo mode: subagents may only run on this session's own model "
                f"({own or 'unknown'}), not '{target or 'default'}'. Route to that model if the Agent "
                f"tool lists it; otherwise do this work yourself."
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
        session_start(mode, event)
    else:
        pre_tool_use(mode, event)


if __name__ == "__main__":
    main()
