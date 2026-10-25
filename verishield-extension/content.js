(() => {
  if (window.__verishieldLoaded) return;
  window.__verishieldLoaded = true;

  const TEXT_SELECTORS = "article, [data-testid='tweetText'], [itemprop='articleBody'], .post-content, .entry-content, .article-body, .articleBody, .story-content, .storyBody";
  const MAX_CONCURRENT = 3;
  const records = new Map();
  let nextId = 1;
  let active = true;
  let generation = 0;
  let running = 0;
  let queue = [];
  let scanTimer;
  let hud;

  const words = (text) => (text.trim().match(/\S+/g) || []).length;
  function cleanClone(node) {
    const clone = node.cloneNode(true);
    clone.querySelectorAll(".verishield-root, .verishield-hud, script, style, nav, aside, footer, header, form, button, svg, noscript")
      .forEach((unwanted) => unwanted.remove());
    return clone;
  }
  const visible = (node) => {
    if (!node.isConnected || node.closest("nav, aside, footer, header, .verishield-root, .verishield-hud")) return false;
    const style = getComputedStyle(node);
    const rect = node.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" &&
      rect.height > 0 && rect.bottom >= -innerHeight && rect.top <= innerHeight * 2;
  };

  function make(tag, className, value) {
    const node = document.createElement(tag);
    node.className = className;
    if (value !== undefined) node.textContent = value;
    return node;
  }

  function createBar(node, kind) {
    const root = make("div", "verishield-root");
    root.dataset.expanded = "false";
    const button = make("button", "verishield-toggle");
    button.type = "button";
    button.setAttribute("aria-expanded", "false");
    const brand = make("span", "verishield-brand", `VERISHIELD / ${kind}`);
    const result = make("span", "verishield-result", kind === "MEDIA" ? "NOT ANALYZED ▾" : "ANALYZING… ▾");
    button.append(brand, result);
    const meter = make("div", "verishield-meter");
    const fill = make("span", "");
    meter.append(fill);
    const detail = make("div", "verishield-detail");
    const grid = make("div", "verishield-grid");
    const cells = ["METHOD", "CONFIDENCE", "WORDS"].map((label) => {
      const cell = make("div", "verishield-cell");
      cell.append(make("b", "", label), make("span", "", "—"));
      grid.append(cell);
      return cell.lastChild;
    });
    const note = make("div", "verishield-note", kind === "MEDIA"
      ? "Audio, video, image manipulation and C2PA origin are not checked in this version."
      : "Analyzing text with the local API…");
    detail.append(grid, note);
    root.append(button, meter, detail);
    button.addEventListener("click", () => {
      const expanded = root.dataset.expanded !== "true";
      root.dataset.expanded = String(expanded);
      button.setAttribute("aria-expanded", String(expanded));
    });
    if (kind === "TEXT") node.prepend(root);
    else node.before(root);
    return { root, result, fill, cells, note };
  }

  function setBar(bar, data) {
    bar.result.textContent = data.label + " ▾";
    bar.fill.style.width = data.score == null ? "0%" : `${Math.max(0, Math.min(100, data.score))}%`;
    bar.cells[0].textContent = data.method;
    bar.cells[1].textContent = data.confidence == null ? "—" : `${data.confidence.toFixed(1)}%`;
    bar.cells[2].textContent = data.wordCount == null ? "—" : String(data.wordCount);
    bar.note.textContent = data.note;
  }

  function localPatternScore(text) {
    const sentences = text.match(/[^.!?]+[.!?]+|[^.!?]+$/g) || [];
    const lengths = sentences.map((sentence) => words(sentence)).filter(Boolean);
    const mean = lengths.reduce((sum, length) => sum + length, 0) / Math.max(1, lengths.length);
    const variance = lengths.reduce((sum, length) => sum + (length - mean) ** 2, 0) / Math.max(1, lengths.length);
    const burstiness = mean ? Math.sqrt(variance) / mean : 0;
    const markers = (text.match(/\b(furthermore|moreover|in conclusion|it is important to note|delve into)\b/gi) || []).length;
    const score = Math.round(Math.max(0, Math.min(100, 55 - 25 * burstiness + 4 * markers)));
    return {
      score,
      method: "LOCAL PATTERN",
      confidence: null,
      wordCount: words(text),
      label: `PATTERN ${score}%`,
      note: "Server unavailable. This simple writing-pattern score is not an AI probability or proof of authorship."
    };
  }

  function sendForAnalysis(html) {
    return new Promise((resolve, reject) => {
      let finished = false;
      const timeout = setTimeout(() => {
        finished = true;
        reject(new Error("Local analysis timed out"));
      }, 25000);
      chrome.runtime.sendMessage({ type: "VERISHIELD_VERIFY", html }, (reply) => {
        if (finished) return;
        finished = true;
        clearTimeout(timeout);
        const error = chrome.runtime.lastError;
        if (error) reject(new Error(error.message));
        else if (!reply?.ok) reject(new Error(reply?.error || "Local API unavailable"));
        else resolve(reply.result);
      });
    });
  }

  async function analyze(item) {
    const { node, bar, token, id } = item;
    const clone = cleanClone(node);
    const text = clone.textContent || "";
    try {
      const response = await sendForAnalysis(clone.outerHTML.slice(0, 30000));
      if (!active || generation !== token || !node.isConnected || !records.has(id)) return;
      const data = response.status === "analyzed" && Number.isFinite(response.ai_probability)
        ? {
            score: response.ai_probability,
            method: "GPT-2 MODEL",
            confidence: response.model_confidence,
            wordCount: response.word_count,
            label: `GPT-2-LIKE ${Math.round(response.ai_probability)}%`,
            note: response.detail || "Model estimate; not proof of authorship."
          }
        : {
            score: null,
            method: "NONE",
            confidence: null,
            wordCount: response.word_count,
            label: "TOO SHORT",
            note: response.detail || "Not enough text to analyze."
          };
      setBar(bar, data);
      records.get(id).data = data;
    } catch (_error) {
      if (!active || generation !== token || !node.isConnected || !records.has(id)) return;
      const data = localPatternScore(text);
      setBar(bar, data);
      records.get(id).data = data;
    }
    updateHud();
  }

  function drain() {
    while (active && running < MAX_CONCURRENT && queue.length) {
      const item = queue.shift();
      if (!item.node.isConnected || item.token !== generation || !records.has(item.id)) continue;
      running++;
      analyze(item).finally(() => {
        running--;
        drain();
      });
    }
  }

  function addCandidate(node, kind) {
    if (!visible(node)) return;
    if ([...records.values()].some((record) => record.node === node)) return;
    const id = nextId++;
    const bar = createBar(node, kind);
    const data = kind === "MEDIA" ? {
      score: null, method: "NONE", confidence: null, wordCount: null,
      label: "NOT ANALYZED", note: "Audio, video, image manipulation and C2PA origin are not checked in this version."
    } : null;
    records.set(id, { node, bar, data, kind });
    if (kind === "TEXT") queue.push({ id, node, bar, token: generation });
  }

  function collectArticleElements() {
    const selected = [];
    for (const node of document.querySelectorAll(TEXT_SELECTORS)) {
      if (!visible(node) || words(node.innerText || "") < 30) continue;
      if (selected.some((parent) => parent.contains(node))) continue;
      selected.push(node);
    }
    if (selected.length === 0) {
      const parents = new Set([...document.querySelectorAll("p")].map((node) => node.parentElement).filter(Boolean));
      for (const parent of parents) {
        if (!visible(parent) || parent.querySelectorAll("p").length < 2 || words(parent.innerText || "") < 50) continue;
        if (selected.some((node) => node.contains(parent) || parent.contains(node))) continue;
        selected.push(parent);
      }
    }
    // Many news sites render story paragraphs as plain divs rather than <article>
    // or <p>. Pick the smallest substantial text blocks so page navigation and
    // recommendation lists are not sent to the model.
    {
      const candidates = [...document.querySelectorAll("main, [role='main'], section, div")].slice(0, 4000);
      const count = new Map();
      const wordCount = (node) => {
        if (!count.has(node)) count.set(node, words(node.innerText || ""));
        return count.get(node);
      };
      for (const node of candidates) {
        if (wordCount(node) < 50 || !visible(node)) continue;
        if (selected.some((existing) => existing.contains(node) || node.contains(existing))) continue;
        if ([...node.querySelectorAll("div, section, p")].some((child) => wordCount(child) >= Math.max(50, wordCount(node) * 0.6))) continue;
        const linkWords = [...node.querySelectorAll("a")].reduce((sum, link) => sum + words(link.innerText || ""), 0);
        if (linkWords > wordCount(node) * 0.25) continue;
        selected.push(node);
        if (selected.length >= 12) break;
      }
    }
    return selected;
  }

  function scan() {
    if (!active || !document.body) return;
    for (const [id, record] of records) {
      if (!record.node.isConnected) {
        record.bar.root.remove();
        records.delete(id);
      }
    }
    collectArticleElements().forEach((node) => addCandidate(node, "TEXT"));
    document.querySelectorAll("video, audio, img").forEach((node) => {
      if (node.tagName === "IMG") {
        const rect = node.getBoundingClientRect();
        if (rect.width < 320 || rect.height < 180) return;
      }
      addCandidate(node, "MEDIA");
    });
    drain();
    updateHud();
  }

  function scheduleScan() {
    clearTimeout(scanTimer);
    scanTimer = setTimeout(scan, 400);
  }

  function updateHud() {
    if (!active) return;
    if (!hud) {
      hud = make("div", "verishield-hud");
      document.body.append(hud);
    }
    const model = [...records.values()].map((record) => record.data).filter((data) => data?.method === "GPT-2 MODEL");
    const patterns = [...records.values()].map((record) => record.data).filter((data) => data?.method === "LOCAL PATTERN");
    const average = model.length ? Math.round(model.reduce((sum, item) => sum + item.score, 0) / model.length) : null;
    hud.replaceChildren(
      make("strong", "", "VERISHIELD // PAGE INDEX"),
      make("span", "", model.length ? `${average}% GPT-2-like · ${model.length} text items` : `${patterns.length} local pattern results · no model scores`)
    );
  }

  function clearResults() {
    generation++;
    queue = [];
    for (const record of records.values()) record.bar.root.remove();
    records.clear();
    hud?.remove();
    hud = null;
  }

  function summary() {
    const model = [...records.values()].map((record) => record.data).filter((data) => data?.method === "GPT-2 MODEL");
    const patterns = [...records.values()].map((record) => record.data).filter((data) => data?.method === "LOCAL PATTERN");
    return {
      active,
      scanned: [...records.values()].filter((record) => record.kind === "TEXT" && record.data).length,
      modelScanned: model.length, patternScanned: patterns.length,
      averageScore: model.length ? Math.round(model.reduce((sum, item) => sum + item.score, 0) / model.length) : null
    };
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type === "VERISHIELD_SUMMARY") sendResponse(summary());
    if (message?.type === "VERISHIELD_RESCAN") {
      clearResults();
      if (active) scan();
      sendResponse(summary());
    }
  });

  chrome.storage.onChanged.addListener((changes) => {
    if (!changes.verishieldActive) return;
    active = changes.verishieldActive.newValue !== false;
    if (active) scan();
    else clearResults();
  });

  const observer = new MutationObserver((mutations) => {
    if (!active || !mutations.some((mutation) => {
      if (mutation.target.closest?.(".verishield-root, .verishield-hud")) return false;
      return [...mutation.addedNodes].some((node) => node.nodeType === Node.ELEMENT_NODE &&
        !node.classList?.contains("verishield-root") && !node.classList?.contains("verishield-hud"));
    })) return;
    scheduleScan();
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });
  window.addEventListener("scroll", scheduleScan, { passive: true });
  window.addEventListener("load", scheduleScan);
  chrome.storage.local.get({ verishieldActive: true }, ({ verishieldActive }) => {
    active = verishieldActive;
    if (active) scan();
  });
})();
