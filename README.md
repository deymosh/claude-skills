# claude-skills

Personal collection of [Claude Code](https://claude.com/claude-code) skills, packaged as an installable plugin marketplace.

## Install

Add this repo as a marketplace, then install whichever skill you want:

```
/plugin marketplace add deymosh/claude-skills
/plugin install smart-subagent-routing
/plugin install clean-commits
```

## Skills

| Plugin | What it does |
|---|---|
| [`smart-subagent-routing`](smart-subagent-routing/SKILL.md) | Routes non-trivial execution to cheaper subagent models and reviews the result. Ships hooks that block untagged (quota-leaking) subagents behind a gateway and add `auto` / `ask` / `solo` modes. |
| [`clean-commits`](clean-commits/SKILL.md) | Commit hygiene: atomic commits, pre-commit verification, self-contained messages, and scanning for auto-link (`@word`) hazards. |

## smart-subagent-routing: modes and guard

Switch modes at any time with the slash command (requires `python3`):

```
/routing solo   # subagents only on the session's own model — e.g. when evaluating a model
/routing ask    # every subagent call needs your approval
/routing auto   # delegate when it fits (default)
/routing off    # disable the routing rules
/routing        # show the current mode
```

The mode applies to the current session only, survives resume and compaction, and is enforced by the hook, not just by instructions. To choose a default for new sessions, set the `SUBAGENT_ROUTING` env var (e.g. `SUBAGENT_ROUTING=solo claude`). `/clear` starts a new session, so it falls back to that default.

In `solo`, the hook reads the session's current model from its transcript (so it follows `/model` switches) and allows a subagent only if its routing tag points to that exact provider and model; CCR client IDs are decoded for the comparison. The session's model must therefore be in the gateway's subagent list for solo sessions to delegate at all. Without a gateway, solo allows only subagents that inherit the session model; built-in agent types that pin their own model are not detected.

Whenever `ANTHROPIC_BASE_URL` points at a gateway, the PreToolUse hook denies any Agent call whose prompt does not start with the routing tag (default `<CCR-SUBAGENT-MODEL>`, override with `SUBAGENT_ROUTING_TAG`). Untagged subagents inherit the parent or agent-type model, which is how work silently lands on a Claude subscription.

The hooks only cover subagents. Claude Code also makes background "small fast model" calls (titles, WebFetch summaries, compaction), which use the Haiku slot. Route those in the gateway too (for Claude Code Router, the `Router.background` rule), or set `ANTHROPIC_DEFAULT_HAIKU_MODEL`, so they don't reach Claude either. To let a non-Claude session delegate to its own model, add that model to the gateway's subagent model list.

## Adding a new skill

Each skill lives in its own top-level directory with a `SKILL.md` and a `.claude-plugin/plugin.json`. To add one:

1. Create `<skill-name>/SKILL.md` with the skill's frontmatter and instructions.
2. Create `<skill-name>/.claude-plugin/plugin.json` (see an existing one for the shape).
3. List it in `.claude-plugin/marketplace.json`.
4. Validate with:
   ```
   claude plugin validate . --strict
   ```
