"use strict";

(function (root) {
  const KEY_RE = /^[a-z][a-z0-9_]{2,47}$/;
  const RUNGS = { do: true, see: true, why: true };
  const WINDOW = 8;
  const MAX_SAID = 80;
  const L = root.XiaoouLesson || {};

  L.SHRINK_MESSAGE = "太难了";
  L.REGULARITY_ASK = "你总结出什么规律了吗？";
  const SHRINK_PREFIXES = ["太难了", "再小一点", "再说简单点"];

  L.isShrinkTalk = function isShrinkTalk(text) {
    const said = String(text || "").trim();
    return SHRINK_PREFIXES.some((prefix) => said === prefix || said.indexOf(prefix) === 0);
  };

  L.emptyLesson = function emptyLesson() {
    return { rung: "do", shrinks: 0, view: "", discoveries: [] };
  };

  function fold(text) {
    return String(text || "").replace(/\s+/g, "");
  }

  L.leaksInsight = function leaksInsight(text, insight) {
    const t = fold(text);
    const i = fold(insight);
    if (!t || !i) return false;
    if (t.indexOf(i) >= 0 || i.indexOf(t) >= 0) return true;
    if (i.length >= WINDOW) {
      for (let n = 0; n <= i.length - WINDOW; n += 1) {
        if (t.indexOf(i.slice(n, n + WINDOW)) >= 0) return true;
      }
    }
    return false;
  };

  L.normalizeDiscovery = function normalizeDiscovery(item, topic) {
    if (!item || typeof item !== "object") return null;
    const key = String(item.insight_key || "").trim();
    const said = String(item.child_said || "").trim();
    if (!KEY_RE.test(key) || !said) return null;
    if (L.leaksInsight(said, item.insight || "")) return null;
    return {
      insight_key: key,
      child_said: said.slice(0, MAX_SAID),
      topic: String(item.topic || topic || "").trim(),
    };
  };

  L.normalizeLesson = function normalizeLesson(raw) {
    const src = raw && typeof raw === "object" ? raw : {};
    const rung = RUNGS[src.rung] ? src.rung : "do";
    let shrinks = parseInt(src.shrinks, 10);
    if (isNaN(shrinks)) shrinks = 0;
    shrinks = Math.max(0, Math.min(3, shrinks));
    const discoveries = [];
    const seen = {};
    (src.discoveries || []).forEach((item) => {
      const row = L.normalizeDiscovery(item, src.topic);
      if (!row || seen[row.insight_key]) return;
      seen[row.insight_key] = true;
      discoveries.push(row);
    });
    return {
      rung: rung,
      shrinks: shrinks,
      view: String(src.view || "").trim().slice(0, 32),
      discoveries: discoveries,
    };
  };

  L.resetForNewCard = function resetForNewCard(lesson) {
    const current = L.normalizeLesson(lesson);
    return {
      rung: "do",
      shrinks: 0,
      view: "",
      discoveries: current.discoveries,
    };
  };

  L.applyShrink = function applyShrink(lesson) {
    const current = L.normalizeLesson(lesson);
    if (current.shrinks <= 0) {
      current.shrinks = 1;
      return current;
    }
    if (current.shrinks === 1) {
      if (current.rung === "why") current.rung = "see";
      else if (current.rung === "see") current.rung = "do";
      current.shrinks = 2;
      return current;
    }
    current.shrinks = 3;
    return current;
  };

  L.harvestDiscovery = function harvestDiscovery(claim, childSaid, insight, insightKey, topic) {
    if (!claim || !claim.accepted_by_child) return null;
    if (!KEY_RE.test(String(insightKey || ""))) return null;
    const said = String(childSaid || "").trim();
    const statement = String(claim.statement || "").trim();
    let text = said && !L.leaksInsight(said, insight) ? said : "";
    if (!text && statement && !L.leaksInsight(statement, insight)) text = statement;
    if (!text) return null;
    return L.normalizeDiscovery({
      insight_key: insightKey,
      child_said: text,
      topic: topic || "",
    }, topic);
  };

  function compact(text) {
    return fold(text).replace(/[^\w\u4e00-\u9fff]+/g, "");
  }

  L.looksLikeMisconception = function looksLikeMisconception(said, card) {
    if (!card || typeof card !== "object") return false;
    const compactSaid = compact(said);
    return (card.misconceptions || []).some((item) => {
      const raw = String(item || "");
      if (L.leaksInsight(said, raw)) return true;
      const quoted = raw.match(/[「『'"“]([^」』'"”]{2,16})[」』'"”]/g) || [];
      return quoted.some((chunk) => {
        const core = compact(chunk.replace(/^[「『'"“]|[」』'"”]$/g, ""));
        return !!(core && /\d/.test(core) && compactSaid.indexOf(core) >= 0);
      });
    });
  };

  L.acceptRegularity = function acceptRegularity(said, card, topic) {
    const text = String(said || "").trim();
    if (text.length < 4 || L.isShrinkTalk(text)) return null;
    const insight = card && card.insight ? String(card.insight) : "";
    if (L.leaksInsight(text, insight)) return null;
    if (L.looksLikeMisconception(text, card)) return null;
    const key = String((card && card.insight_key) || "").trim();
    if (!KEY_RE.test(key)) return null;
    return L.normalizeDiscovery({
      insight_key: key,
      child_said: text,
      topic: topic || (card && card.topic) || "",
    }, topic);
  };

  L.askedRegularity = function askedRegularity(messages) {
    const list = Array.isArray(messages) ? messages : [];
    for (let i = list.length - 1; i >= 0; i -= 1) {
      const msg = list[i];
      if (!msg || msg.role !== "assistant") continue;
      const text = typeof msg.content === "string" ? msg.content : "";
      return text.indexOf(L.REGULARITY_ASK) >= 0;
    }
    return false;
  };

  L.mergeDiscovery = function mergeDiscovery(lesson, discovery) {
    const current = L.normalizeLesson(lesson);
    const row = L.normalizeDiscovery(discovery);
    if (!row) return current;
    current.discoveries = current.discoveries.filter((item) => item.insight_key !== row.insight_key);
    current.discoveries.push(row);
    return current;
  };

  L.lastChildText = function lastChildText(messages) {
    const list = Array.isArray(messages) ? messages : [];
    for (let i = list.length - 1; i >= 0; i -= 1) {
      const msg = list[i];
      if (!msg || msg.role !== "user") continue;
      let text = "";
      if (typeof msg.content === "string") text = msg.content.trim();
      else if (Array.isArray(msg.content)) {
        text = msg.content.map((part) => (part && part.type === "text" ? String(part.text || "") : "")).join("\n").trim();
      }
      if (!text || L.isShrinkTalk(text)) continue;
      return text;
    }
    return "";
  };

  root.XiaoouLesson = L;
  if (typeof module !== "undefined" && module.exports) module.exports = L;
})(typeof globalThis !== "undefined" ? globalThis : this);
