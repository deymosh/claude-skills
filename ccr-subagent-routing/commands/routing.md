---
description: Set subagent routing for this session — auto, ask, solo, or off (no argument shows the current mode)
argument-hint: "[auto|ask|solo|off]"
allowed-tools: Bash(python3:*)
---

!`python3 "${CLAUDE_PLUGIN_ROOT}/hooks/routing_guard.py" set "${CLAUDE_SESSION_ID}" $ARGUMENTS`

Follow this routing mode from now on (see the ccr-subagent-routing skill). Reply with one short acknowledgement only.
