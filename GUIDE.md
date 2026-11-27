---
name: pr-explain
description: "Explain a pull request in Simplified Technical English: 1 walkthrough, 2 lesson. Use when the user gives a PR link or number and wants to understand it. Read-only."
---

# PR explain

Input: `<PR> [1|2] [instructions]`. `<PR>` is a URL, `owner/repo#n`, or a bare number. For a bare
number, take the repo from the `prsum` prompt, else from `git remote get-url origin` in the cwd;
ask if neither gives one. No level means 1. Follow the user's instructions over the defaults below.

Workbench root: the `Workbench checkout:` path in the prompt, else three directories above this
skill's resolved real path (`cd <skill dir> && pwd -P`). Scripts and this skill's files are under the
prompt's `t2pr engine:` path, if given.

## Rules

- Read-only. Never edit, comment on, approve or check out the PR, and never fetch or switch
  branches in a local clone. The only writes are the level 2 note and the page files in `prs/<repo>-<n>/`.
- The goal is that the reader understands the PR fast. A diagram and short lines beat paragraphs.
- Write in ASD-STE100 Simplified Technical English: context first, one idea per sentence, at most
  20 words, active voice, one word for one meaning. Use the terms from
  `<workbench>/knowledge/glossary.md` and the repo's own glossary, when they exist. Define other
  jargon once.
- This explains; it is not a review. State risks as facts about behaviour, not verdicts. Mark
  anything not read in the code or ticket as an inference.
- Never write before the Gather and Explore steps are done. Never restate the PR description; the user can
  read it. Build each point from the diff, the code and the ticket.
- On a diff over ~1500 lines, list files first, then explore every file that changes behaviour.

## Gather

All of these, before writing:

```bash
gh pr view <n> -R <owner/repo> --json number,title,body,author,state,baseRefName,headRefName,headRefOid,url,additions,deletions,files,commits,closingIssuesReferences
gh pr diff <n> -R <owner/repo>
gh pr view <n> -R <owner/repo> --comments
gh api repos/<owner>/<repo>/pulls/<n>/comments --paginate --jq '.[] | {path, line, user: .user.login, body}'
gh api repos/<owner>/<repo>/pulls/<n>/reviews --paginate --jq '.[] | {user: .user.login, state, body}'
```

Ticket ref: the first Jira key (`[A-Z][A-Z0-9]+-[0-9]+`) in the title, branch or body, or a linked
GitHub issue (`closingIssuesReferences`, `#123`, `owner/repo#123`). When there is one, always read
it with the `tracker` skill's adapter (`acli jira workitem view <KEY> --fields
summary,description,comment` or `gh issue view <n> -R <owner/repo> --comments`); the "why" comes
from it. Skip it only if the tracker CLI is missing or fails, and say so in one line.

Read the surrounding code at the PR head where the diff alone does not show the flow:

```bash
gh api -H 'Accept: application/vnd.github.raw' 'repos/<owner>/<repo>/contents/<path>?ref=<headRefOid>'
```

If the repo has a local clone (`<workbench>/repositories.local.yaml`), read its `AGENTS.md` for
vocabulary. `git -C <clone> show <sha>:<path>` works only if `git cat-file -e <sha>` succeeds.

## Explore

Understand each change before you write about it. The reader must never meet a guess or a gap.

- Read every file that changes behaviour in full at the PR head, then the callers and callees the
  diff touches. Read config, schema and infra changes with the code that reads them.
- Group the diff by change in behaviour, not by file. One change is one thing a user, a caller or
  an operator can see. Tests, docs and pure renames are not changes; they go under "other".
- For each change, answer the questions a newcomer asks: what was there before, what calls this,
  what happens on failure, what does it cost. Find the answer in the code, the ticket or a review
  thread; else mark it inferred.
- Check each claim against the code at `path:line` before it goes on the page.

## Levels

### 1 - Walkthrough (default)

The chat and the page tell the same story, in this order:

- **Summary:** the behaviour change in one or two sentences.
- **Why:** from the ticket; then context lines such as the ticket and "part 2 of 4".
- **What this PR does:** the changes, numbered, each title verb first, each with one "before" and
  one "after" line. The same number is its chapter below.
- **The whole picture:** the parts before and after, as chains. Mark each part new, changed or
  gone; each arrow says what passes to the next part.
- **Step by step** (when parts call each other): a sequence of the main path and the failure path,
  one plain sentence per step.
- **What happens now** (when inputs lead to different results): one card per situation: the
  steps, then the result. Start with what happened before this PR.
- **How the code does it:** one chapter per change:
  - `does`: one plain line.
  - `picture`: the shape that shows the change best. A chain for a flow, a table for a mapping,
    a rule or settings (with an example value, and the old value crossed out), a compare for
    before/after values or folder trees. A step number on a part links it to that code step.
  - `why_not`: the simple way and the exact reason it fails, tagged `stated` (name the PR body,
    ticket, commit or review thread) or `inferred`. Skip it when the PR took the simple way. Read
    the commit messages in order: an approach that changed between commits is often the answer.
  - `steps`: in run order. Each lights the lines `line`..`end` of one file and says what they do
    and why. Put changed contracts, schemas and config before the code that uses them.
  - `cost`: what now behaves differently, or must be undone later.
- **Watch for:** what could behave differently after the merge, with a level (Low, Medium, High).
  Include what is not tested, config, flags, migrations and contracts with other repos.
- **Review threads:** one line each, resolved or open.
- **Terms:** each word a newcomer may not know, with its plain meaning. The page explains it on
  first use.

In chat, give the summary, the numbered changes, and one line per chapter; the page holds the rest.

### 2 - Learn

Level 1, then a `learn` block:

- **Concepts:** each pattern, library or platform feature that is likely new: a plain
  explanation, how this PR uses it, a primary source for the version the build resolves, and a
  picture when it helps. `change` links it to the chapter that uses it.
- **Check yourself:** 3 to 5 "What would happen if…" questions, answers hidden.

If the page exists, add the block to `steps.json` and rerun `<workbench>/scripts/pr-visual.py
<page folder>/steps.json none`; a running builder keeps answering. If no builder runs, use
`pr-page.sh start` (Page step 3). Do not gather again for level 2.

Write the note with the headings of `<workbench>/templates/learning.md`, kept to what was new.
If `<workbench>/tasks/<KEY>/` exists (the task folder for that ref), append it to that `learning.md` under
`## PR <repo>#<n>: <title>`. Otherwise write `<workbench>/prs/<repo>-<n>/learning.md`. Say where.

## Page

Right after the in-session output, without asking, start the review page. The user reads the
chat summary first, then asks questions on the page; a background builder answers there.

1. Write `<workbench>/prs/<repo>-<n>/steps.json` (`<repo>` without the owner) in the format of the
   `<workbench>/scripts/pr-visual.py` docstring, with the `headRefOid` you read and the content
   above. A step shows its file's hunks (`hunks` picks the ones holding a string) or unchanged code
   (`show: [start, end]`); its lit lines must be in what it shows.
2. Write `context.md` beside it: `Head: <headRefOid>`, `## Summary` (the in-session summary and
   changes), `## Sources read` (PR body, ticket, threads, reviews, commits, files read; one per
   line), `## Prepared answers` (the newcomer questions from Explore that the page does not
   answer, each with a short answer and `path:line`), `## Questions` (empty).
3. Run `<workbench>/scripts/pr-page.sh start <workbench>/prs/<repo>-<n>`. It builds
   `explain.html`, fails if the PR head moved (then gather again), and starts the background
   builder ([BUILDER.md](BUILDER.md)), which opens the page with lavish and sends a notification.
4. Tell the user in one line: the page is coming, ask on the page; `prsum --resume <PR>` later
   if the builder has stopped. If `pr-page.sh` says the page is ready without a builder (no
   Node.js), give its two lines instead.

CodeTour only on request: run `<workbench>/scripts/pr-visual.py <steps.json> b`.

## Close

End with one line offering level 2 after level 1. Reuse what you already read.
