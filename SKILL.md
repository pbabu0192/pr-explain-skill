---
name: pr-explain
description: "Explain a pull request in Simplified Technical English: 1 walkthrough, 2 lesson, as a page you can ask questions on. Use when the user gives a PR link or number and wants to understand it. Read-only."
---

# PR explain (stand-alone)

Follow [GUIDE.md](GUIDE.md) from Input to Close, with the changes below. GUIDE.md and
[BUILDER.md](BUILDER.md) come unchanged from t2pr; where they disagree with this file, this file
wins.

## Paths

- `<skill>`: this file's folder (`cd <skill dir> && pwd -P`).
- `<workbench>` means the current folder. There is no `repositories.local.yaml`, no
  `knowledge/glossary.md` and no `tasks/`: skip the steps that need them.
- `<workbench>/scripts/pr-visual.py` is `<skill>/scripts/pr-visual.py`.
- `<workbench>/templates/learning.md` is `<skill>/templates/learning.md`.
- Page files still go in `./prs/<repo>-<n>/`. Level 2 always writes `./prs/<repo>-<n>/learning.md`.
- No `prsum` command: a bare PR number takes its repo from `git remote get-url origin`, else ask.
- Ticket: read a linked GitHub issue with `gh issue view <n> -R <owner/repo> --comments`, and a
  Jira key with `acli jira workitem view <KEY> --fields summary,description,comment` if `acli`
  is installed. Else say in one line that the ticket was not read.

## Page (replaces GUIDE.md Page steps 3 and 4)

There is no background builder. This session builds the page and answers on it.

1. After `steps.json` and `context.md` (GUIDE.md Page steps 1 and 2), run
   `python3 <skill>/scripts/pr-visual.py ./prs/<repo>-<n>/steps.json none`. It writes
   `explain.html` and fails if the PR head moved; then gather again.
2. If `npx` is missing: tell the user the page path, to open it in a browser, and that Node.js is
   needed to ask questions on it. Stop there.
3. Else do [BUILDER.md](BUILDER.md) Start steps 2 to 4 and its Answer loop, in this session. Skip
   its notification and `prsum` lines. Tell the user in one line: the page is open, ask on it.
4. Stop the loop when the user closes the page or says stop. Then write `## Last stopped` in
   `context.md`, and say: "To ask more later, ask me to resume the page for <repo>#<n>." On that
   request, do BUILDER.md Start step 1, then steps 2 to 4 and the Answer loop.

Read-only still holds: never edit, comment on, approve or check out the PR. The only writes are
in `./prs/<repo>-<n>/`.
