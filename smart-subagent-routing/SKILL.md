---
name: smart-subagent-routing
description: Decide who executes non-trivial work (code edits, multi-step tasks, bulk reading/research) — you, or a cheaper subagent model — and route it explicitly. Use before implementing and before every Agent/subagent call, including built-in agent types like Explore.
---

# Smart Subagent Routing

Goal: spend the session model's quota on thinking and reviewing; push well-specified execution to cheaper subagent models — without ever leaking work onto a model the user didn't choose.

## 1. Check the routing mode first

The plugin's hook states it in context (`subagent-routing mode: …`); the most recent statement wins, and the user can change it any time with `/routing <mode>`. Plain requests in chat also count ("do it yourself", "I'm testing this model" → solo; "ask before offloading" → ask), but only `/routing` is enforced, so suggest it if they want the rule to hold.

- **solo** — the user is evaluating the current model, so every result must come from it. Subagents are allowed only when routed to this session's own model (same provider and model in the Agent tool's list); if it isn't listed, do all the work yourself.
- **ask** — before each delegation, say in one line what you'd offload and to which model, and wait for a yes.
- **auto** (default) — delegate whenever §3 says it fits.

## 2. Never spawn an unrouted subagent

An Agent call without an explicit route does not run on something cheap: it inherits the parent model or the agent type's pinned model, and a gateway may forward that to the user's Claude subscription without anyone noticing.

- Read the Agent tool description fresh each time. If it defines a gateway routing contract (e.g. a `<…>Provider/model</…>` tag), follow it verbatim on **every** call — built-in types (Explore, Plan, general-purpose) included. Set `model` to the same ID only if that field accepts arbitrary strings.
- Choose only from models the tool description lists. If none fits, do the work yourself rather than fall back to a default.
- Built-in Claude aliases (`sonnet`, `haiku`, …) are *not* a cheaper option when the session itself runs on a Claude subscription — they draw from the same quota. Use them only if the user asks.

## 3. Decide whether to delegate (auto / ask)

1. **Decide the approach yourself.** What changes, where, and why. Never hand off the judgment.
2. **Delegate** when the work is well-specified and bulky: multi-file mechanical edits, boilerplate, tests, broad codebase searches, web research, summarizing long files. Big reads are the best offload — the subagent pays for the tokens and you only receive its conclusion.
3. **Don't delegate** when it's cheaper to just do it (roughly ≤3 tool calls), when it needs this conversation's context, or when it's mostly judgment.
4. **Pick by description, not name.** Match each listed model's stated intent to the task's difficulty; choose the cheapest one that clearly fits.

## 4. Brief, wait, review

- Write a self-contained brief: the approach, files, constraints (e.g. "don't commit"), and what "done" means. Ask for a **short** report (e.g. "≤150 words: files changed, anything skipped") — the report lands in your context.
- Let it run in the background; never read its transcript file.
- Review the real result (`git diff`, the files, test output), not the subagent's claims. Fix small issues yourself; if the approach was wrong, re-plan.

## 5. On failure

Rate limit, quota, repeated API error, empty or garbled output → retry once on another listed model that fits → otherwise do it yourself. Never "retry" by dropping the routing tag: that is exactly the silent leak from §2.

Always tell the user in one sentence which model did the work and whether a fallback happened.
