#!/usr/bin/env python3
"""Build the review page (a) or a CodeTour (b) for a PR from steps.json, then open it.

usage: pr-visual.py <steps.json> [a|b|none]

steps.json (text fields take `code` in backticks):
{"repo": "owner/name", "number": 1, "head": "<headRefOid>", "title": "...", "state": "open|merged|closed",
 "summary": "the behaviour change in one or two sentences",
 "why": "why the PR exists, from the ticket", "context": [{"label": "Ticket X-1", "text": "..."}],
 "terms": {"word": "plain meaning"},
 "changes": [{"title": "verb first", "before": "...", "after": "...", "does": "one plain line",
              "picture": PICTURE,
              "why_not": {"q": "Why not <the simple way>?", "a": "...", "tag": "stated|inferred", "source": "..."},
              "steps": [{"title": "...", "file": "path", "line": 10, "end": 12, "note": "what these lines do and why",
                         "hunks": ["text in the hunks to show"] or "show": [start, end]}],
              "cost": "what now behaves differently, or must be undone later"}],
 "before": [CHAIN_NODE], "after": [CHAIN_NODE],
 "sequence": {"title": "...", "lanes": [{"name": "...", "kind": "new"}],
              "steps": [{"from": 0, "to": 1, "label": "on the arrow", "plain": "one sentence", "fail": true} | {"note": "..."}]},
 "cases": {"before": "before this PR: ...", "items": [{"when": "...", "steps": ["..."], "result": "ok|warn|fail|skip", "text": "..."}]},
 "watch": [{"title": "...", "level": "Low|Medium|High", "text": "..."}],
 "threads": [{"summary": "...", "state": "resolved|open"}],
 "other": [{"file": "path", "text": "tests, docs, config"}],
 "learn": {"concepts": [{"name": "...", "explain": "...", "use": "how this PR uses it", "source": "URL",
                         "picture": PICTURE, "change": N}],
           "quiz": [{"q": "What would happen if ...?", "a": "..."}]}}
CHAIN_NODE: {"name": "...", "kind": "new|changed|gone", "link": "what passes to the next node"}
PICTURE, exactly one of:
  {"chain": {"items": [{"text": "...", "kind": "new|changed|bad|ok", "step": N}], "note": "..."}}
  {"table": {"head": ["..."], "rows": [{"mark": "new|changed", "cells": ["text" | {"text", "example", "was", "step"}]}], "note": "..."}}
  {"compare": {"before": {"label": "...", "text": "..." | "tree": "..."}, "after": {...}, "note": "..."}}
Required: repo, number, head, title, summary, why, changes (each with title, before, after, does,
steps, cost; each step with title, file, line, note). A "step": N in a picture is that change's step N.
A step shows its file's diff hunks (all, or those holding a "hunks" string), or with "show" the
unchanged lines start..end at the PR head; lines line..end are lit and must be in what it shows.
learn adds a Learn tab: each concept needs a source; quiz has 3 to 5 questions; "change" links a
concept to that change's chapter. Fails if the PR head moved since "head".
Output lands next to steps.json; "none" writes the page without opening it.
"""
import html, json, pathlib, re, shutil, subprocess, sys


def gh(*args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def fail(msg):
    sys.exit(f"pr-visual: {msg}")


spec_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else fail(__doc__.split("\n\n")[1])
mode = sys.argv[2] if len(sys.argv) > 2 else "a"
mode in ("a", "b", "none") or fail(f"mode must be a, b or none, not {mode}")
out = spec_path.parent
spec = json.loads(spec_path.read_text())
for key in ("repo", "number", "head", "title", "summary", "why", "changes"):
    spec.get(key) or fail(f"steps.json needs {key!r}")
repo, number, head = spec["repo"], str(spec["number"]), spec["head"]

now = gh("pr", "view", number, "-R", repo, "--json", "headRefOid", "-q", ".headRefOid").strip()
now == head or fail(f"PR head moved from {head[:7]} to {now[:7]}; gather again and update steps.json")
diff = gh("pr", "diff", number, "-R", repo)
files = {}
for chunk in re.split(r"(?m)^(?=diff --git )", diff):
    m = re.match(r"diff --git a/\S+ b/(\S+)", chunk)
    if m:
        files[m.group(1)] = chunk

contents = {}


def content(path):
    if path not in contents:
        try:
            contents[path] = gh("api", "-H", "Accept: application/vnd.github.raw",
                                f"repos/{repo}/contents/{path}?ref={head}")
        except subprocess.CalledProcessError:
            contents[path] = ""  # deleted at head; the step's diff still shows the change
    return contents[path]


def step_diff(s):
    path = s["file"]
    path in files or fail(f"{path} is not in the PR diff; use \"show\" for unchanged code")
    header, *hunks = re.split(r"(?m)^(?=@@ )", files[path])
    needles = s.get("hunks")
    picked = [h for h in hunks if not needles or any(n in h for n in needles)]
    picked or fail(f"no hunk in {path} contains any of {needles}")
    return header, "".join(picked)


def inline(text):
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(str(text)))


def one_of(value, allowed, where):
    value in allowed or fail(f"{where} must be one of {', '.join(a or '(none)' for a in allowed)}, not {value!r}")
    return value


def code_rows(s):
    """(kind, old, new, text) rows: kind is add, del, ctx or hunk; old/new are line numbers or None."""
    if "show" in s:
        start, end = s["show"]
        text = content(s["file"]).splitlines()
        start <= min(end, len(text)) or fail(f"{s['file']} has no lines {start}..{end} at {head[:7]}")
        return [("ctx", i, i, text[i - 1]) for i in range(start, min(end, len(text)) + 1)]
    rows = []
    for hunk in re.split(r"(?m)^(?=@@ )", step_diff(s)[1]):
        m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@ ?(.*)", hunk)
        if not m:
            continue
        old, new = int(m.group(1)), int(m.group(2))
        rows.append(("hunk", None, None, m.group(3)))
        for line in hunk.split("\n")[1:]:
            if line.startswith("\\") or line == "":
                continue
            mark, body = line[0], line[1:]
            if mark == "+":
                rows.append(("add", None, new, body)); new += 1
            elif mark == "-":
                rows.append(("del", old, None, body)); old += 1
            else:
                rows.append(("ctx", old, new, body)); old += 1; new += 1
    return rows


def fold_context(rows, keep, edge=2):
    """Fold runs of more than 2*edge+1 unchanged lines; head lines in keep stay."""
    out, run = [], []
    def flush():
        if len(run) > 2 * edge + 1 and not any(r[2] in keep for r in run[edge:-edge]):
            out.extend(run[:edge] + [("skip", None, None, len(run) - 2 * edge)] + run[-edge:])
        else:
            out.extend(run)
        run.clear()
    for r in rows:
        if r[0] == "ctx":
            run.append(r)
        else:
            flush(); out.append(r)
    flush()
    return out


def mark(n):
    return f"<span class=mk>{n}</span>" if n else ""


def step_ref(n, count, where):
    if n is None:
        return None
    isinstance(n, int) and 1 <= n <= count or fail(f"{where} points to step {n}, but the change has {count} steps")
    return n


# ---------- pictures: the agent combines these for any kind of change ----------

def picture(p, where, count):
    isinstance(p, dict) and len(p) == 1 and next(iter(p)) in ("chain", "table", "compare") or \
        fail(f"{where}: a picture is exactly one of chain, table or compare")
    kind, d = next(iter(p.items()))
    note = f"<p class=pnote>{inline(d['note'])}</p>" if d.get("note") else ""
    if kind == "chain":
        d.get("items") or fail(f"{where}: a chain needs items")
        boxes = []
        for i, it in enumerate(d["items"]):
            k = one_of(it.get("kind", ""), ("", "new", "changed", "bad", "ok"), f"{where} chain item kind")
            n = step_ref(it.get("step"), count, f"{where} chain item {i + 1}")
            boxes.append(f"{'<span class=par>→</span>' if i else ''}<span class=\"pbox {k}\">{mark(n)}{inline(it['text'])}</span>")
        return f"<div class=pchain>{''.join(boxes)}</div>{note}"
    if kind == "table":
        d.get("head") and d.get("rows") or fail(f"{where}: a table needs head and rows")
        def cell(c, i):
            if isinstance(c, str):
                return inline(c)
            n = step_ref(c.get("step"), count, f"{where} table cell")
            return (f"{mark(n)}{inline(c.get('text', ''))}"
                    + (f"<span class=ex>{inline(c['example'])}</span>" if c.get("example") else "")
                    + (f"<span class=was>{inline(c['was'])}</span>" if c.get("was") else ""))
        rows = []
        for r in d["rows"]:
            m = one_of(r.get("mark", ""), ("", "new", "changed"), f"{where} table row mark")
            badge = f" <span class=\"badge {m}\">{m.upper()}</span>" if m else ""
            rows.append(f"<tr class=\"{m}\">" + "".join(f"<td>{cell(c, i)}{badge if i == 0 else ''}</td>"
                                                        for i, c in enumerate(r["cells"])) + "</tr>")
        head_ = "".join(f"<th>{inline(h)}</th>" for h in d["head"])
        return f"<table class=ptab><tr>{head_}</tr>{''.join(rows)}</table>{note}"
    sides = []
    for side in ("before", "after"):
        s = d.get(side) or fail(f"{where}: a compare needs before and after")
        body = f"<pre class=tree>{html.escape(s['tree'])}</pre>" if s.get("tree") else f"<p>{inline(s.get('text', ''))}</p>"
        sides.append(f"<div class=\"pside {side}\"><h5>{inline(s.get('label', side.title()))}</h5>{body}</div>")
    return f"<div class=pcmp>{''.join(sides)}</div>{note}"


# ---------- the code walk ----------

def code_view(s, num, where):
    """One step's code: its file's hunks (or shown lines); lines line..end lit, the rest faded."""
    line, end = s["line"], s.get("end", s["line"])
    rows = code_rows(s)
    if "show" not in s:
        rows = fold_context(rows, set(range(line, end + 1)))
    lit = {i for i, r in enumerate(rows) if r[0] in ("add", "ctx") and r[2] is not None and line <= r[2] <= end}
    for i in sorted(lit):  # a lit added line also lights the removed lines it replaces
        if rows[i][0] == "add":
            j = i - 1
            while j >= 0 and rows[j][0] == "add":
                j -= 1
            while j >= 0 and rows[j][0] == "del":
                lit.add(j); j -= 1
    lit or fail(f"{where}: lines {line}..{end} of {s['file']} are not in the code it shows")
    body = []
    for i, (kind, old, new, text) in enumerate(rows):
        if kind == "skip":
            body.append(f"<div class=\"r gap\">⋯ {text} unchanged lines</div>")
        elif kind == "hunk":
            body.append(f"<div class=\"r gap\">⋯ {html.escape(text)}</div>")
        else:
            sign = {"add": "+", "del": "−"}.get(kind, "")
            body.append(f"<div class=\"r {kind}{' hl' if i in lit else ''}\"><span class=no>{new or ''}</span>"
                        f"<span class=sg>{sign}</span><span class=tx>{html.escape(text)}</span></div>")
    url = f"https://github.com/{repo}/blob/{head}/{s['file']}#L{line}" + (f"-L{end}" if end != line else "")
    return (f"<div class=cv><div class=fh><a href=\"{html.escape(url)}\">{html.escape(s['file'])}</a></div>"
            f"<div class=rows>{''.join(body)}</div><div class=pn>{mark(num)}<span>{inline(s['note'])}</span></div></div>")


def chapter(ch, c):
    where = f"change {c + 1}"
    for key in ("title", "before", "after", "does", "steps", "cost"):
        ch.get(key) or fail(f"{where} needs {key!r}")
    steps = ch["steps"]
    buttons, templates = [], []
    for k, s in enumerate(steps):
        for key in ("title", "file", "line", "note"):
            s.get(key) or fail(f"{where} step {k + 1} needs {key!r}")
        rng = f"{s['line']}" + (f"–{s['end']}" if s.get("end", s["line"]) != s["line"] else "")
        buttons.append(f"<button type=button class=sc data-c={c} data-k={k}>{mark(k + 1)}<b>{inline(s['title'])}</b>"
                       f"<span class=pl>{inline(s['note'])}</span><span class=sref>{html.escape(s['file'])}:{rng}</span></button>")
        templates.append(f"<template id=code-{c}-{k}>{code_view(s, k + 1, f'{where} step {k + 1}')}</template>")
    pic = f"<div class=pic>{picture(ch['picture'], where, len(steps))}</div>" if ch.get("picture") else ""
    why = ""
    if ch.get("why_not"):
        w = ch["why_not"]
        w.get("q") and w.get("a") or fail(f"{where}: why_not needs q and a")
        tag = one_of(w.get("tag"), ("stated", "inferred"), f"{where} why_not tag")
        src = f", {html.escape(w['source'])}" if w.get("source") else ""
        why = (f"<div class=whyline><p class=wq>{inline(w['q'])}</p>"
               f"<p class=wa>{inline(w['a'])} <span class=\"tag {tag}\">{tag}{src}</span></p></div>")
    first = templates[0].split(">", 1)[1].rsplit("</template>", 1)[0]  # the first step shows without script
    return (f"<div class=chap id=ch{c + 1}><h3><span class=cnum>{c + 1}</span>{inline(ch['title'])}</h3>"
            f"<p class=does>{inline(ch['does'])}</p>{pic}{why}"
            f"<div class=cwalk><div>{''.join(buttons)}</div><div class=cpanel id=cv{c}>{first}</div></div>"
            f"<p class=cost><b>Costs:</b> {inline(ch['cost'])}</p>{''.join(templates)}</div>")


# ---------- the other sections ----------

def chain(nodes, where):
    out = []
    for i, n in enumerate(nodes):
        k = one_of(n.get("kind", ""), ("", "new", "changed", "gone"), f"{where} kind")
        badge = f"<span class=\"badge {k}\">{k.upper()}</span>" if k in ("new", "changed") else ""
        out.append(f"<span class=\"node {k}\">{inline(n['name'])}{badge}</span>")
        if n.get("link") and i < len(nodes) - 1:
            out.append(f"<span class=link>↓ {inline(n['link'])}</span>")
    return f"<div class=chain>{''.join(out)}</div>"


def seq_svg(seq):
    lanes, items = seq["lanes"], seq["steps"]
    W, top, step = 156, 40, 36
    H, width = top + len(items) * step + 14, len(lanes) * W
    x = lambda i: W // 2 + i * W
    e = html.escape
    s = [f"<svg viewBox=\"0 0 {width} {H}\" width=\"{width}\" role=img aria-label=\"{e(seq['title'])}\">"
         "<defs><marker id=ok viewBox=\"0 0 8 8\" refX=7 refY=4 markerWidth=7 markerHeight=7 orient=auto-start-reverse>"
         "<path d=\"M0,0 L8,4 L0,8 z\" fill=\"var(--accent)\"/></marker>"
         "<marker id=bad viewBox=\"0 0 8 8\" refX=7 refY=4 markerWidth=7 markerHeight=7 orient=auto-start-reverse>"
         "<path d=\"M0,0 L8,4 L0,8 z\" fill=\"var(--bad)\"/></marker></defs>"]
    for i, l in enumerate(lanes):
        s.append(f"<rect class=\"lh {e(l.get('kind', ''))}\" x={x(i) - 72} y=4 width=144 height=28 rx=6 />"
                 f"<text x={x(i)} y=22 text-anchor=middle font-weight=600>{e(l['name'])}</text>"
                 f"<line class=life x1={x(i)} y1=32 x2={x(i)} y2={H - 4} />")
    num = 0
    for k, it in enumerate(items):
        y = top + 18 + k * step
        if "note" in it:
            s.append(f"<rect class=note x=8 y={y - 15} width={width - 16} height=20 rx=4 /><text class=nt x=16 y={y - 1}>{e(it['note'])}</text>")
            continue
        a, b = it["from"], it["to"]
        0 <= a < len(lanes) and 0 <= b < len(lanes) or fail(f"sequence step {k + 1} points to a lane that does not exist")
        num += 1
        fail_ = it.get("fail")
        col, mk_, cls = ("var(--bad)", "bad", " fail") if fail_ else ("var(--accent)", "ok", "")
        label = e(it.get("label", ""))
        if a == b:
            s.append(f"<path d=\"M{x(a)},{y - 8} h26 v14 h-23\" fill=none stroke=\"{col}\" stroke-width=1.5 marker-end=\"url(#{mk_})\"/>"
                     f"<text class=\"mt{cls}\" x={x(a) + 32} y={y + 3}>{label}</text>")
            dx = x(a) - 14
        else:
            s.append(f"<line x1={x(a)} y1={y} x2={x(b) + (-3 if b > a else 3)} y2={y} stroke=\"{col}\" stroke-width=1.5 marker-end=\"url(#{mk_})\"/>"
                     f"<text class=\"mt{cls}\" x={(x(a) + x(b)) // 2} y={y - 6} text-anchor=middle>{label}</text>")
            dx = min(x(a), x(b)) + 14
        s.append(f"<circle class=\"dot{cls}\" cx={dx} cy={y - 10} r=8 /><text class=dn x={dx} y={y - 6.5} text-anchor=middle>{num}</text>")
    s.append("</svg>")
    steps, n = [], 0
    for it in items:
        if "note" in it:
            steps.append(f"<li class=note>{inline(it['note'])}</li>")
        else:
            n += 1
            steps.append(f"<li class=\"{'fail' if it.get('fail') else ''}\"><span class=n>{n}</span><span>{inline(it.get('plain', ''))}</span></li>")
    return f"<div class=seqwrap><div class=seq>{''.join(s)}</div><ol class=steps>{''.join(steps)}</ol></div>"


def sec(id_, title, how, body):
    return f"<h2 id={id_}>{html.escape(title)}</h2><p class=how>{how}</p>{body}"


LEGEND = ("<p class=legend><span><i class=sw style=\"border-color:var(--new);background:var(--new-soft)\"></i>new in this PR</span>"
          "<span><i class=sw style=\"border-color:var(--warn);background:var(--warn-soft)\"></i>changed by this PR</span>"
          "<span><i class=sw style=\"border-color:var(--line)\"></i>not changed</span></p>")


def walk_html():
    changes = spec["changes"]
    rows = "".join(f"<li><span class=cnum>{c + 1}</span><div><h3>{inline(ch['title'])}</h3><div class=ba>"
                   f"<span class=bl>Before</span><span class=bt>{inline(ch.get('before', ''))}</span>"
                   f"<span class=al>After</span><span>{inline(ch.get('after', ''))}</span></div></div>"
                   f"<button type=button class=howbtn data-go=ch{c + 1}>How ↓</button></li>" for c, ch in enumerate(changes))
    whole = ""
    if spec.get("before") and spec.get("after"):
        whole = (f"<h3 class=sub2>The whole picture</h3><p class=how>Read top to bottom. Each arrow says what passes to the next part.</p>"
                 f"<div class=cols><div class=\"col before\"><h4>Before</h4>{chain(spec['before'], 'before')}</div>"
                 f"<div class=\"col after\"><h4>After</h4>{chain(spec['after'], 'after')}</div></div>{LEGEND}")
    count = f"{len(changes)} change{'s' if len(changes) > 1 else ''}"
    parts = [("does", "What this PR does", sec("does", "What this PR does",
              f"{count}. Each has a number; the same number is its chapter in “How the code does it”.",
              f"<ol class=changes>{rows}</ol>{whole}"))]
    if spec.get("sequence"):
        sq = spec["sequence"]
        parts.append(("seqh", sq["title"], sec("seqh", sq["title"],
                      "Each column is one part of the system. Arrows go down in time order; the numbers match the steps on the right. Red is a failure path.",
                      seq_svg(sq))))
    if spec.get("cases"):
        cs = spec["cases"]
        cards = "".join(
            f"<div class=case><span class=when>{inline(it['when'])}</span><div class=csteps>"
            + "".join(f"{'→' if i else ''}<span class=s>{inline(t)}</span>" for i, t in enumerate(it.get("steps", [])))
            + f"</div><span class=\"end {one_of(it.get('result'), ('ok', 'warn', 'fail', 'skip'), 'case result')}\">{inline(it['text'])}</span></div>"
            for it in cs["items"])
        before = f"<p class=beforeall>{inline(cs['before'])}</p>" if cs.get("before") else ""
        parts.append(("now", "What happens now", sec("now", "What happens now", "One card per situation: the steps, then the result.",
                      f"{before}<div class=cases>{cards}</div>")))
    parts.append(("how", "How the code does it", sec("how", "How the code does it",
                  "One chapter per change. Click a step, or scroll to it: the code beside it shows that file and lights up its lines. "
                  "A number in a picture is the step with the same number.",
                  "<div class=plainbar><button type=button id=plain>Plain words only</button>"
                  "<span>hides the code and shows what each step does in words</span></div>"
                  + "".join(chapter(ch, c) for c, ch in enumerate(changes)))))
    if spec.get("watch"):
        items = "".join(f"<div class=w><b>{inline(w['title'])} <span class=\"lvl {one_of(w.get('level'), ('Low', 'Medium', 'High'), 'watch level')}\">"
                        f"{w['level']}</span></b>{inline(w['text'])}</div>" for w in spec["watch"])
        parts.append(("watch", "Watch for", sec("watch", "Watch for", "What could behave differently after the merge, and how likely it is to matter.",
                      f"<div class=watch>{items}</div>")))
    threads = spec.get("threads", [])
    items = "".join(f"<li><span class=\"st {one_of(t.get('state'), ('resolved', 'open'), 'thread state')}\">{t['state']}</span>"
                    f"<span>{inline(t['summary'])}</span></li>" for t in threads)
    parts.append(("threads", "Review threads", sec("threads", "Review threads", "What reviewers asked, and if it is settled.",
                  f"<ul class=threads>{items}</ul>" if threads else "<p class=nothing>No review comments yet.</p>")))
    toc = "".join(f"<button type=button data-go={i}>{html.escape(t)} ↓</button>" for i, t, _ in parts)
    ctx = "".join(f"<li><b>{inline(x['label'])}</b>: {inline(x['text'])}</li>" for x in spec.get("context", []))
    other = spec.get("other", [])
    other_html = (f"<details class=other><summary>Other changes ({len(other)} file{'s' if len(other) > 1 else ''})</summary><ul>"
                  + "".join(f"<li><code>{html.escape(o['file'])}</code>: {inline(o['text'])}</li>" for o in other)
                  + "</ul></details>") if other else ""
    return (f"<nav class=toc aria-label=\"Jump to a section\"><span class=tocl>Jump to:</span>"
            f"<button type=button data-go=why>Why ↓</button>{toc}</nav>"
            f"<div class=whyfull id=why><span class=k>Why</span><p>{inline(spec['why'])}</p>{f'<ul class=ctx>{ctx}</ul>' if ctx else ''}</div>"
            + "".join(p for _, _, p in parts) + other_html
            + "<div class=ask>💬 Anything unclear? Select any word or part of this page and add a note. "
              "The answer appears in the Conversation panel beside the page.</div>")


def learn_html():
    learn = spec.get("learn")
    if not learn:
        return ""
    concepts, quiz = learn.get("concepts", []), learn.get("quiz", [])
    3 <= len(quiz) <= 5 or fail(f"learn quiz needs 3 to 5 questions, not {len(quiz)}")
    parts = ["<p class=how>The ideas behind this PR, then questions to check yourself.</p>"]
    for c in concepts:
        name = c.get("name", "?")
        c.get("source") or fail(f"learn concept {name!r} needs a primary source")
        go = ""
        if c.get("change"):
            n = c["change"]
            isinstance(n, int) and 1 <= n <= len(spec["changes"]) or fail(f"learn concept {name!r} links change {n}, but there are {len(spec['changes'])}")
            go = f"<button type=button class=learngo data-go=ch{n}>See it in the code: change {n} ↓</button>"
        pic = f"<div class=pic>{picture(c['picture'], f'learn concept {name!r}', 0)}</div>" if c.get("picture") else ""
        use = f"<p><b>In this PR:</b> {inline(c['use'])}</p>" if c.get("use") else ""
        parts.append(f"<div class=concept><h3>{inline(name)}</h3><p>{inline(c.get('explain', ''))} "
                     f"<a class=src href=\"{html.escape(c['source'])}\">Source</a></p>{use}{pic}{go}</div>")
    parts.append("<h3>Check yourself</h3><p class=how>Write your answer as a note on a question. "
                 "The answer in the Conversation panel says if it is right, partly right or wrong, and why.</p>")
    parts += [f"<div class=quiz><p>{i}. {inline(q['q'])}</p><details><summary>Show answer</summary>{inline(q['a'])}</details></div>"
              for i, q in enumerate(quiz, 1)]
    return "".join(parts)


def build_page():
    here = pathlib.Path(__file__).resolve().parent
    css, js = (here / "pr-page.css").read_text(), (here / "pr-page.js").read_text()
    walk, learn = walk_html(), learn_html()
    terms = json.dumps(spec.get("terms", {}), ensure_ascii=False).replace("</", "<\\/")
    state = f"<span class=pill>{html.escape(spec['state'])}</span>" if spec.get("state") else ""
    tabs = ("<nav class=tabs><button type=button data-tab=walk aria-selected=true>Walkthrough</button>"
            "<button type=button data-tab=learn aria-selected=false>Learn</button></nav>") if learn else ""
    return f"""<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>PR #{number} {html.escape(spec['title'])}</title>
<style>{css}</style>
<div class=top><span class=pill>{html.escape(repo)}#{number}</span>{state}<span class=pill>head {head[:7]}</span></div>
<h1>{html.escape(spec['title'])}</h1>
<p class=summary>{inline(spec['summary'])}</p>
{tabs}
<section id=walk>{walk}</section>
{f'<section id=learn>{learn}</section>' if learn else ''}
<div class=tip id=tip role=tooltip></div>
<script type=application/json id=terms>{terms}</script>
<script>{js}</script>
</html>
"""


def build_tour():
    # Each step embeds the head file so no checkout is needed.
    virtual = dict(file="OVERVIEW.md", contents=f"PR #{number}: {spec['title']} @ {head[:7]}\n")
    tour = [dict(title="Overview", description=f"{spec['summary']}\n\n**Why.** {spec['why']}", **virtual)]
    for c, ch in enumerate(spec["changes"], 1):
        for k, s in enumerate(ch["steps"], 1):
            desc = s["note"] + ("" if "show" in s else f"\n\n```diff\n{step_diff(s)[1]}```")
            if k == 1:
                desc = f"**Change {c}: {ch['title']}.** {ch['does']}\n\n{desc}"
            lines = content(s["file"]).count("\n") + 1
            step = dict(title=f"{c}.{k} {s['title']}", file=s["file"], contents=content(s["file"]),
                        line=min(s.get("end", s["line"]), lines), description=desc)
            if "end" in s:
                step["selection"] = {"start": {"line": s["line"], "character": 1},
                                     "end": {"line": min(s["end"], lines), "character": 200}}
            tour.append(step)
    watch = [f"- **{w['title']}** ({w.get('level', '')}): {w['text']}" for w in spec.get("watch", [])]
    if watch:
        tour.append(dict(title="Watch for", description="\n".join(watch), **virtual))
    return {"$schema": "https://aka.ms/codetour-schema", "title": f"PR #{number} {spec['title']}", "steps": tour}


if mode == "b":
    (out / ".tours").mkdir(exist_ok=True)
    tour_path = out / ".tours/pr.tour"
    tour_path.write_text(json.dumps(build_tour(), indent=2))
    print(f"wrote {tour_path}")
    subprocess.run(["code", "-n", str(out)], check=True)
    print("In VS Code: CodeTour panel in Explorer, press play on the tour.")
else:
    page_path = out / "explain.html"
    page_path.write_text(build_page())
    print(f"wrote {page_path}")
    if mode == "a":
        subprocess.run([shutil.which("open") or "xdg-open", str(page_path)], check=True)
