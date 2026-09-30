---
name: ccr-subagent-routing
description: Route non-trivial work (code edits, multi-step tasks, bulk reading/research) to cheaper Claude Code Router (CCR) subagent models. Use before implementing and before every Agent call, including built-in types like Explore.
---

# CCR Subagent Routing

## Mode

The hook states it in context (`subagent-routing mode: …`); the user changes it with `/routing <mode>`. The latest statement wins. This skill applies in every mode except off, whatever the permission mode (default, plan, accept edits, bypass).

- **auto** — delegate whenever it fits (below).
- **ask** — delegate as in auto. The hook asks the user to approve each subagent call and names its model, so just make the call; don't ask in chat first. A denied call means the user declined: do that work yourself.
- **solo** — subagents only on this session's own provider/model; if it isn't in the Agent tool's list, do everything yourself.
- **off** — no rules.

## Every Agent call

- First line of `prompt`: the `<CCR-SUBAGENT-MODEL>…</CCR-SUBAGENT-MODEL>` tag exactly as the Agent tool description specifies. The tag alone routes the call.
- Leave `model` unset: it usually accepts only built-in aliases, and a CCR ID there fails validation before the agent runs.
- Choose only models listed there, by description; pick the cheapest that fits. No match → do it yourself.
- Don't use built-in aliases (`sonnet`, `haiku`, …) unless the user asks.

## When to delegate

- Decide the approach yourself first.
- Delegate well-specified bulk work: multi-file mechanical edits, boilerplate, tests, codebase searches, web research, long-file summaries.
- Keep: ≤3 tool calls, work needing this conversation's context, judgment calls.

## Brief and review

- Self-contained brief: approach, files, constraints, definition of done. Ask for a short report (e.g. ≤150 words).
- Never read a subagent's transcript file.
- Verify the actual result (diff, files, tests), not the report. Fix small issues yourself.
- A reader's claim it inferred rather than traced ("X runs on every update") can be wrong: check it in the code before acting on it.

## Failure

Rate limit, API error, empty or garbled output → retry once on another fitting listed model → else do it yourself. Never retry without the tag. Tell the user in one sentence which model did the work, by its readable `Provider/model` name.
