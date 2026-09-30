#!/usr/bin/env python3
"""Deterministic guard for subagent routing through Claude Code Router (CCR).

SessionStart: injects the active routing mode into context, so the policy
applies even if the ccr-subagent-routing skill never gets loaded.
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
TAG_TARGET = re.compile(re.escape(TAG) + r"([^<\n]+)")
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


def readable_model(model):
    """Turn a model reference into a readable 'Provider/model' name.

    Accepts CCR client IDs, which hex-encode the target
    (anthropic/claude-ccr-h<hex>), and CCR's plain 'provider,model' form;
    context-window suffixes like [1m] are dropped.
    """
    model = (model or "").strip()
    match = CCR_CLIENT_ID.search(model)
    if match:
        try:
            model = bytes.fromhex(match.group(1)).decode()
        except ValueError:
            pass
    elif "/" not in model:
        model = model.replace(",", "/", 1)
    return re.sub(r"\[[^\]]*\]$", "", model).strip()


def canonical_model(model):
    """Reduce a model reference to a comparable 'Provider/model' form."""
    return readable_model(model).lower()


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


def emit(output=None, message=None):
    payload = {"hookSpecificOutput": output} if output else {}
    if message:
        payload["systemMessage"] = message
    json.dump(payload, sys.stdout)
    sys.exit(0)


def subagent_model(event, prompt):
    """Readable name of the model the subagent will run on."""
    match = TAG_TARGET.match(prompt)
    if match:
        return readable_model(match.group(1))
    requested = (event.get("tool_input") or {}).get("model") or ""
    if requested and requested != "inherit":
        return readable_model(requested)
    override = os.environ.get("CLAUDE_CODE_SUBAGENT_MODEL", "")
    if override:
        return readable_model(override)
    own = readable_model(session_model(event))
    return f"{own} (inherited)" if own else "the session model (inherited)"


def session_start(mode, event):
    if event.get("model"):
        write_state(event.get("session_id", ""), event["model"], ".model")
    if mode == "off":
        sys.exit(0)
    notes = {
        "auto": "Delegate whenever it fits.",
        "ask": "Get the user's approval before each subagent call.",
        "solo": "Subagents only on this session's own model; if it isn't listed, do all work yourself.",
    }
    context = (
        f"subagent-routing mode: {mode}. {notes[mode]} "
        f"Follow the ccr-subagent-routing skill before implementing or calling Agent."
    )
    if behind_gateway():
        context += f" Agent prompts must start with the {TAG} tag."
    emit({"hookEventName": "SessionStart", "additionalContext": context})


def pre_tool_use(mode, event):
    tool_input = event.get("tool_input") or {}
    prompt = tool_input.get("prompt", "").lstrip()
    target = subagent_model(event, prompt)
    shown = f"Subagent model: {target}"

    def decide(decision, reason):
        emit({
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }, shown if decision != "deny" else None)

    if mode == "off":
        emit(message=shown)
    if behind_gateway() and not prompt.startswith(TAG):
        decide("deny", (
            f"Untagged subagent: start the prompt with the {TAG} tag from the Agent tool "
            f"description, or do the work yourself."
        ))
    if mode == "solo":
        own = session_model(event)
        if behind_gateway():
            match = TAG_TARGET.match(prompt)
            allowed = bool(own) and bool(match) and canonical_model(match.group(1)) == canonical_model(own)
        else:
            allowed = tool_input.get("model") in (None, "", "inherit")
        if not allowed:
            decide("deny", (
                f"Solo mode: subagents only on {readable_model(own) or 'this session model'}, not {target}; "
                f"otherwise do the work yourself."
            ))
    if mode == "ask":
        decide("ask", f"subagent-routing ask mode: run this subagent on {target}?")
    emit(message=shown)


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
