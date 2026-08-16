"use strict";

(function (root) {
  const T = root.XiaoouTerms || { all: [], byId: {}, wordIndex: [] };

  function escapeHtml(s) {
    return String(s || "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function splitByTerms(text) {
    const src = String(text || "");
    if (!src || !T.wordIndex.length) return [{ text: src, id: "" }];
    const hits = [];
    T.wordIndex.forEach((row) => {
      let from = 0;
      while (from < src.length) {
        const at = src.indexOf(row.word, from);
        if (at < 0) break;
        const end = at + row.word.length;
        const overlap = hits.some((hit) => at < hit.end && end > hit.start);
        if (!overlap) hits.push({ start: at, end, id: row.id, word: row.word });
        from = at + 1;
      }
    });
    hits.sort((a, b) => a.start - b.start || b.end - a.end);
    const parts = [];
    let cursor = 0;
    hits.forEach((hit) => {
      if (hit.start < cursor) return;
      if (hit.start > cursor) parts.push({ text: src.slice(cursor, hit.start), id: "" });
      parts.push({ text: hit.word, id: hit.id });
      cursor = hit.end;
    });
    if (cursor < src.length) parts.push({ text: src.slice(cursor), id: "" });
    return parts.length ? parts : [{ text: src, id: "" }];
  }

  function formatCaption(text, formatPlain) {
    const fmt = typeof formatPlain === "function" ? formatPlain : escapeHtml;
    return splitByTerms(text).map((part) => {
      const html = fmt(part.text);
      if (!part.id) return html;
      return `<button type="button" class="term-chip" data-term="${part.id}">${html}</button>`;
    }).join("");
  }

  function highlightKey(termId) {
    const term = T.byId[termId];
    return (term && term.highlight) || "";
  }

  function closeCard(onHighlight) {
    const card = document.getElementById("termCard");
    if (card) card.classList.add("hidden");
    if (typeof onHighlight === "function") onHighlight("");
  }

  function openCard(termId, hooks) {
    const term = T.byId[termId];
    const card = document.getElementById("termCard");
    if (!term || !card) return;
    const title = document.getElementById("termCardTitle");
    const kid = document.getElementById("termCardKid");
    const example = document.getElementById("termCardExample");
    if (title) title.textContent = term.words[0] || "";
    if (kid) kid.textContent = term.kid;
    if (example) example.textContent = term.example || "";
    card.classList.remove("hidden");
    if (hooks && typeof hooks.onHighlight === "function") hooks.onHighlight(highlightKey(termId));
    if (hooks && typeof hooks.onSeen === "function") hooks.onSeen(termId);
  }

  function bindCaption(rootEl, hooks) {
    if (!rootEl || rootEl.dataset.termBound) return;
    rootEl.dataset.termBound = "1";
    rootEl.addEventListener("click", (e) => {
      const btn = e.target.closest(".term-chip");
      if (!btn) return;
      openCard(btn.getAttribute("data-term"), hooks);
    });
    const close = document.getElementById("termCardClose");
    if (close) close.addEventListener("click", () => closeCard(hooks && hooks.onHighlight));
  }

  root.XiaoouTermScaffold = {
    splitByTerms,
    formatCaption,
    openCard,
    closeCard,
    bindCaption,
    highlightKey,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = root.XiaoouTermScaffold;
})(typeof globalThis !== "undefined" ? globalThis : this);
