---
description: Set subagent routing for this session — auto, ask, solo, or off (no argument shows the current mode)
argument-hint: "[auto|ask|solo|off]"
allowed-tools: Bash(python3:*)
---

!`python3 "${CLAUDE_PLUGIN_ROOT}/hooks/routing_guard.py" set "${CLAUDE_SESSION_ID}" $ARGUMENTS`

The line above is the routing mode now in force for this session, enforced by the plugin's hook. From here on follow it: solo = subagents only on this session's own model, otherwise do all work yourself; ask = get the user's approval before each delegation; auto = delegate per the smart-subagent-routing skill; off = no routing rules. Acknowledge in one short line; don't do anything else.
