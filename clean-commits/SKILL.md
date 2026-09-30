---
name: clean-commits
description: Use before running `git commit` or when asked to commit, split, or clean up commits. Enforces atomic commits, verification before committing, self-contained messages, and no `@word` auto-link hazards.
---

# Clean Commits

Commit *quality* rules. Whether you may commit at all, branch naming, and PR structure are governed elsewhere.

1. **One logical change per commit.** If the staged work mixes unrelated changes (a fix plus a refactor, a dependency bump plus app code), split it: `git add <specific files>`, not `git add -A`. Test: could this commit be reverted on its own? The same applies when asked to clean up existing commits. When unsure, split finer — squashing later is easy; un-mixing isn't.

2. **Verify first.** Run the relevant tests, type-check, lint, or build for what you touched. If you can't verify, tell the user so instead of implying it passed.

3. **Messages stand on their own.** Say what changed and *why* (the behavior or invariant), readable in `git log` years later. A ticket ID may supplement the message but never replace it. Avoid ephemeral phrasing ("this fix", "as discussed", "in this PR"). Match the language of the existing history (default: English).

4. **No auto-link hazards.** Scan every line for a bare `@` followed by a letter or digit (mentions, `@scope/pkg`, emails). Wrap it in backticks, drop the `@`, or rephrase.
