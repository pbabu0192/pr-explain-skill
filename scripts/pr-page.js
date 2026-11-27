// The PR review page (pr-visual.py inlines this file). Without script the page still reads top to
// bottom: each chapter shows its first step's code, and both tabs stay visible.
// Page controls are buttons, not links: lavish's annotate mode takes clicks on links.
const TERMS = JSON.parse(document.getElementById("terms").textContent);

// Terms: mark the first use in each tab with a dotted line and a tooltip.
// Never inside code, diagrams, tables, links or buttons.
const SKIP = "svg,code,pre,table,a,button,template,.cv,h1,.top";
function termify(root) {
  if (!root) return;
  const words = Object.keys(TERMS).sort((a, b) => b.length - a.length), seen = new Set();
  const esc = w => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT,
    {acceptNode: n => n.parentElement.closest(SKIP) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT});
  const queue = []; for (let n; (n = walker.nextNode());) queue.push(n);
  while (queue.length) {
    const node = queue.shift();
    let best = null;  // the earliest unmarked term in this text; the longer one wins a tie
    for (const w of words) {
      if (seen.has(w)) continue;
      const m = node.textContent.match(new RegExp(`(^|[^\\w/.])(${esc(w)})(?!\\w)`, "i"));
      if (m && (!best || m.index + m[1].length < best.at)) best = {w, at: m.index + m[1].length, len: m[2].length};
    }
    if (!best) continue;
    seen.add(best.w);
    const word = node.splitText(best.at), tail = word.splitText(best.len);
    const span = document.createElement("span");
    span.className = "t"; span.tabIndex = 0; span.dataset.w = best.w; span.textContent = word.textContent;
    word.replaceWith(span);
    queue.unshift(tail);  // the rest of the text may hold more terms
  }
}
termify(document.getElementById("walk"));
termify(document.getElementById("learn"));

const tip = document.getElementById("tip");
function showTip(el) {
  const w = el.dataset.w, r = el.getBoundingClientRect();
  tip.innerHTML = ""; const b = document.createElement("b"); b.textContent = w; tip.append(b, TERMS[w]);
  tip.style.display = "block";
  const tw = tip.offsetWidth, th = tip.offsetHeight;
  tip.style.left = Math.max(16, Math.min(r.left, innerWidth - tw - 16)) + "px";
  tip.style.top = (r.bottom + th + 8 > innerHeight ? r.top - th - 6 : r.bottom + 6) + "px";
}
const hideTip = () => tip.style.display = "none", isT = e => e.target.classList && e.target.classList.contains("t");
document.addEventListener("mouseover", e => { if (isT(e)) showTip(e.target); });
document.addEventListener("mouseout", e => { if (isT(e)) hideTip(); });
document.addEventListener("focusin", e => { if (isT(e)) showTip(e.target); });
document.addEventListener("focusout", hideTip);
addEventListener("scroll", hideTip, {passive: true});

// Tabs.
const tabs = document.querySelectorAll(".tabs button");
function showTab(name) {
  if (!tabs.length) return;
  tabs.forEach(b => b.setAttribute("aria-selected", b.dataset.tab === name));
  ["walk", "learn"].forEach(id => { const s = document.getElementById(id); if (s) s.hidden = id !== name; });
}
showTab(location.hash === "#learn" ? "learn" : "walk");

// Code walk: a step shows its code beside it, with its lines lit.
function showStep(c, k) {
  const tpl = document.getElementById(`code-${c}-${k}`), panel = document.getElementById(`cv${c}`);
  if (!tpl || !panel) return;
  panel.replaceChildren(tpl.content.cloneNode(true));
  document.querySelectorAll(`.sc[data-c="${c}"]`).forEach(b => b.classList.toggle("on", +b.dataset.k === k));
  const box = panel.querySelector(".rows"), hl = panel.querySelector(".hl");
  if (box && hl) box.scrollTop = hl.offsetTop - box.offsetTop - 30;
}
const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) showStep(+e.target.dataset.c, +e.target.dataset.k); }),
  {rootMargin: "-45% 0px -50% 0px"});
document.querySelectorAll(".sc").forEach(b => io.observe(b));

document.addEventListener("click", e => {
  if (isT(e)) { showTip(e.target); return; }
  hideTip();
  const t = e.target.closest ? e.target : null; if (!t) return;
  const tab = t.closest(".tabs button"), go = t.closest("[data-go]"), sc = t.closest(".sc"), plain = t.closest("#plain");
  if (tab) showTab(tab.dataset.tab);
  if (go) { showTab("walk"); const to = document.getElementById(go.dataset.go); if (to) to.scrollIntoView({behavior: "smooth", block: "start"}); }
  if (sc) showStep(+sc.dataset.c, +sc.dataset.k);
  if (plain) { const on = document.getElementById("walk").classList.toggle("plain"); plain.textContent = on ? "Show the code" : "Plain words only"; }
});
