---
name: smart-subagent-routing
description: Use this skill whenever you are about to implement something non-trivial (write code, make edits, run a multi-step task) — before touching any files, decide whether to delegate the actual execution to an available subagent model instead of spending your own turns on it, and if so, which model to route it to. Inspects the Agent tool's currently available model options — built-in aliases and any gateway-routed models, each with its own description — matches the implementation task to the best-fit option, delegates, waits for it to finish, reviews the result, and falls back to doing the work yourself in the current session if no option is available or the chosen model errors out / reports a usage limit. Triggers on: "implement X", "about to write code", "which model should this subagent use", "spawn an agent for X", "use the gateway model", "route this subagent", "subagent is rate limited / failing".
---

# Smart Subagent Routing

You are the routing brain for implementation work. The point is to keep your own turns for thinking and reviewing, and push mechanical execution onto a subagent whenever one is available and fit for the job.

## 1. Think and decide, yourself, first

Never delegate the judgment call. Before anything else, do this part in your own reasoning:

- Understand the request and the relevant code.
- Decide the actual approach: what changes, in which files, in what order, and why.

Only once you know *what* you'd do should you move to the next step. Don't hand an underspecified task to a subagent hoping it figures out the approach — that defeats the point and produces worse results.

## 2. Before implementing, check whether you can delegate the execution

This is the step to never skip. Once you know what to build, pause before writing it yourself and ask: is there a subagent model available right now that could execute this instead of me?

- Read the `Agent` tool's description and its `model` parameter description in full, fresh, every time — do not rely on memory of what was available in a past session.
- Look for two kinds of options:
  - **Built-in aliases** (e.g. `sonnet`, `opus`, `haiku`, `fable`, or whatever the current tool schema lists) — one is normally the session's own model.
  - **Gateway-routed models** — listed as a block of configured/available gateway models or similar, each with a client-facing model ID and its own free-form capability description, whatever that description happens to say. These require a specific invocation contract (see §4) — follow whatever the tool text specifies verbatim; it may differ from environment to environment.
- **If at least one option exists that can plausibly do this task** → go delegate (§3). Prefer delegating over doing it yourself whenever a fit exists — that's the entire point of this skill: your own turns are the scarce resource, a subagent's turns usually aren't.
- **If nothing is available** (no Agent tool, no model options exposed, or the task is something a subagent structurally can't do — e.g. it depends on this exact conversation's context) → stop checking and just implement it yourself, directly. Don't force a delegation that doesn't fit.

## 3. Delegate, wait, then review

When a viable option exists:

1. Pick the best-fit model for the task (see §4 for how to choose, §5 for how to invoke it correctly).
2. Hand the subagent everything it needs to execute *your* decision from §1 as a self-contained brief: the concrete approach, the files/areas involved, and what "done" looks like. Don't make it re-derive the design.
3. Dispatch it and wait for it to actually finish before considering the step done — don't fire it off and move on assuming success.
4. Review its output yourself once it completes, the way you'd review a diff: does it match the approach you decided on, is it correct, did it miss anything. This review step is not optional — a subagent's completion message describes what it *attempted*, not a verified fact.
5. If review turns up small issues, fix them yourself directly rather than re-delegating over a minor nit. If it turns up that the approach itself was wrong or the result is substantially incomplete, treat that as a fresh cycle: go back to §1 with what you learned.

## 4. Match the task to a model, using the descriptions, not the names

There is no fixed vocabulary to pattern-match against — the exact wording, tiering, and number of options can differ every time you read the tool schema. Don't hardcode keywords from any past session. Instead, each time:

1. Read every available option's description in full, as freshly written text.
2. Independently size up the task at hand: how much reasoning depth, ambiguity, multi-step judgment, or risk of subtle mistakes it involves versus how narrow, mechanical, or well-specified it is.
3. Reason about which description's stated intent — whatever words it happens to use for capability, cost, or scope — best matches that task, the same way you'd match a job posting to a candidate's resume. Weigh the *meaning*, not surface adjectives.
4. Never pick a model by name-familiarity or position in the list alone (e.g. assuming the first-listed or biggest-sounding name is best) — the description is the only reliable signal, and the underlying provider/model behind an alias or gateway entry can change over time without the name changing.
5. When multiple candidates seem to fit equally well after this reasoning, prefer the built-in alias over a gateway route — it has one fewer moving part (no external gateway dependency) and fails less often.

## 5. Invoke the chosen model correctly

- **Built-in alias**: pass it directly as the `model` field on the `Agent` call.
- **Gateway-routed model**: follow the tool's stated contract exactly — this typically means prepending a specific tag (given verbatim in the tool description, e.g. a `<...>Provider/model</...>` marker) as the literal first line of the subagent's `prompt`, and, only if the `model` field accepts arbitrary strings, also setting `model` to the same ID. If the `model` field only accepts a fixed enum, leave it unset and rely on the prompt tag alone. Do not invent your own tag format — copy the one the tool description gives you.

## 6. Fallback protocol on failure

Treat these as failure signals from a subagent call or its result: an explicit rate-limit / quota / usage-limit message, a repeated API error, an empty or garbled result where a real one was expected, or the background task ending in an error status.

On failure, do **not** just retry the same model blindly. Follow this order:

1. **Retry once on a different candidate** — if another model option (alias or gateway) also fits the task per §4, retry there instead.
2. **If that also fails, drop subagent delegation entirely.** Do the task yourself, directly, in the current conversation:
   - Use the current session's own model (no `model` override, no `Agent` call at all).
   - Execute the work with your own tool calls as if the user had asked you directly — do not keep looping on subagent attempts.
3. Tell the user, briefly, which model actually did the work and whether a fallback happened (e.g. "routed the subagent to the gateway model that best fit the task, but it hit a rate limit, so I completed this directly instead"). Don't over-explain — one sentence is enough.

## Notes

- This skill is intentionally generic: it doesn't hardcode model names, gateway providers, or tag formats, because those are read fresh from the tool schema each time. If a future session's `Agent` tool lists different models or a different gateway contract, this same procedure still applies.
- The bias this skill encodes is: think and review yourself, execute via a subagent whenever one fits. It doesn't override cases where delegating is structurally wrong (e.g. the task needs live context only this conversation has) — use ordinary judgment for those, same as the `Agent` tool's own "when not to use" guidance.
