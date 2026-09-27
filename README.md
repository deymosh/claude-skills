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
| [`smart-subagent-routing`](smart-subagent-routing/SKILL.md) | Before implementing anything non-trivial, checks whether an available subagent model can execute it instead, delegates and reviews the result, and falls back to doing it directly if none fits or it fails. |
| [`clean-commits`](clean-commits/SKILL.md) | Commit hygiene: atomic commits, pre-commit verification, self-contained messages, and scanning for auto-link (`@word`) hazards. |

## Adding a new skill

Each skill lives in its own top-level directory with a `SKILL.md` and a `.claude-plugin/plugin.json`. To add one:

1. Create `<skill-name>/SKILL.md` with the skill's frontmatter and instructions.
2. Create `<skill-name>/.claude-plugin/plugin.json` (see an existing one for the shape).
3. List it in `.claude-plugin/marketplace.json`.
4. Validate with:
   ```
   claude plugin validate . --strict
   ```
