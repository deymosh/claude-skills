---
name: clean-commits
description: Use this skill whenever you are about to run `git commit` (or the user asks you to commit changes). Governs commit hygiene — splitting unrelated changes into separate atomic commits, verifying the change actually works before committing, writing messages that stand on their own without bare references or auto-link hazards. Triggers on: "commit this", "make a commit", "git commit", "clean up these commits", "split this into commits".
---

# Clean Commits

Before running `git commit`, check every point below. These are about the *quality* of the commit itself — not whether you're allowed to commit at all (that's a separate permission question, governed elsewhere).

## 1. One logical change per commit

Look at everything currently staged (or about to be staged). If it bundles more than one unrelated change — a bug fix plus an unrelated refactor, two independent features, a dependency bump plus app code — split it into separate commits instead of batching them together.

- Stage and commit each logical unit on its own (`git add <specific files>`, not a blanket `git add -A` when the working tree has more than one kind of change in it).
- A good test: could this commit be reverted on its own, cleanly, without dragging in unrelated work? If not, it's not atomic yet.
- This applies retroactively too: if you're asked to "clean up" or organize a set of already-made changes, re-split them into atomic commits rather than leaving one large commit.

## 2. Verify before you commit

A change is not ready to commit just because you wrote it. Before committing:

- Run whatever verification is available and relevant (tests, type-checking, linting, a build) for the code actually touched.
- If verification passes, commit.
- If verification can't be run (missing tooling, no test coverage for that area, environment limitation), say so explicitly in your summary to the user instead of silently committing as if it had been verified. Don't imply success you didn't check.

## 3. Write messages that stand on their own

A commit message will outlive the conversation, the ticket, and the PR it was part of. Someone reading it in `git log` a year from now, with none of that context, must be able to understand it.

- State what changed and, more importantly, *why* — the actual behavior or invariant being introduced or fixed — not just a pointer to a task.
- A ticket/issue ID is fine as a supplementary reference, but never as the *only* explanation (a message that says only "fixes JIRA-123" or "see PR #45" tells a future reader nothing on its own).
- Avoid ephemeral framing like "this fix", "as discussed", "per the task", "in this PR" — those phrases stop making sense the moment the surrounding context disappears. Describe the resulting behavior instead.
- Keep the message in whichever language the project's existing commit history is already written in — check `git log` if unsure, and default to English if the history gives no signal either way.

## 4. Scan for auto-link hazards before committing

Many git hosts auto-link a literal `@word` in a commit message as a user mention, which can notify a real, unrelated account. Before finalizing any message:

- Scan every line, including the body, for a bare `@` followed by letters/digits — not just names that look like handles. This also catches things that aren't meant as mentions, such as scoped package names (`@scope/package`) or email-shaped strings.
- If found, rewrite to avoid it: wrap it in backticks, drop the leading `@`, or rephrase the sentence so the token isn't needed verbatim.

## Notes

- This skill is about commit hygiene, not workflow policy: it doesn't decide branch naming, PR structure, or when it's acceptable to commit directly to a protected branch — follow whatever separate instructions the project gives for those.
- When in doubt about how granular to split, err toward more (smaller, focused) commits over fewer (larger, mixed) ones — atomic commits are easy to squash together later if truly needed, but a mixed commit can't be cleanly un-mixed after the fact.
