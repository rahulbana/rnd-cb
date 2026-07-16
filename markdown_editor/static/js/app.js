/* ============================================================
   Markdown Editor — front-end controller
   Pure vanilla JS, no build step. Talks to the Flask API for
   rendering, document CRUD and export.
   ============================================================ */
(function () {
  "use strict";

  // -------------------------------------------------------------- helpers
  const $ = (sel) => document.querySelector(sel);
  const api = {
    async render(text) {
      return post("/api/render", { text });
    },
    async list() {
      return getJSON("/api/documents");
    },
    async read(name) {
      return getJSON(`/api/documents/${encodeURIComponent(name)}`);
    },
    async create(name, content) {
      return post("/api/documents", { name, content });
    },
    async save(name, content) {
      return request("PUT", `/api/documents/${encodeURIComponent(name)}`, { content });
    },
    async rename(oldName, name) {
      return post(`/api/documents/${encodeURIComponent(oldName)}/rename`, { name });
    },
    async remove(name) {
      return request("DELETE", `/api/documents/${encodeURIComponent(name)}`);
    },
  };

  async function getJSON(url) {
    const r = await fetch(url);
    return handle(r);
  }
  async function post(url, body) {
    return request("POST", url, body);
  }
  async function request(method, url, body) {
    const r = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    return handle(r);
  }
  async function handle(r) {
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || `Request failed (${r.status})`);
    return data;
  }

  const debounce = (fn, ms) => {
    let t;
    return (...args) => {
      clearTimeout(t);
      t = setTimeout(() => fn(...args), ms);
    };
  };

  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
    );
  }

  // ---------------------------------------------------------------- state
  const state = {
    currentName: null, // null => unsaved scratch doc
    dirty: false,
    lastSavedContent: "",
    view: localStorage.getItem("md.view") || "split",
    theme: localStorage.getItem("md.theme") || "light",
    autosave: true,
  };

  // -------------------------------------------------------------- elements
  const editor = $("#editor");
  const gutter = $("#gutter");
  const preview = $("#preview");
  const docTitle = $("#doc-title");
  const dirtyDot = $("#dirty-dot");
  const fileList = $("#file-list");
  const outlineList = $("#outline-list");
  const statusMsg = $("#status-message");
  const main = $("#main");

  // =====================================================================
  //  Rendering / preview
  // =====================================================================
  const renderNow = async () => {
    try {
      const data = await api.render(editor.value);
      preview.innerHTML = data.html;
      updateStats(data);
      buildOutline(data.toc_tokens);
    } catch (err) {
      preview.innerHTML = `<p style="color:var(--danger)">Preview error: ${escapeHtml(
        err.message
      )}</p>`;
    }
  };
  const renderDebounced = debounce(renderNow, 180);

  function updateStats(data) {
    $("#stat-words").textContent = `${data.word_count} words`;
    $("#stat-chars").textContent = `${data.char_count} chars`;
    $("#stat-read").textContent = `${data.reading_minutes} min read`;
  }

  function buildOutline(tokens) {
    outlineList.innerHTML = "";
    const walk = (nodes) => {
      nodes.forEach((n) => {
        const li = document.createElement("li");
        li.className = `outline-item lvl-${n.level}`;
        li.textContent = n.name;
        li.title = n.name;
        li.addEventListener("click", () => {
          const el = preview.querySelector(`#${CSS.escape(n.id)}`);
          if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
        });
        outlineList.appendChild(li);
        if (n.children && n.children.length) walk(n.children);
      });
    };
    if (tokens && tokens.length) walk(tokens);
    else outlineList.innerHTML = `<li class="file-empty">No headings</li>`;
  }

  // =====================================================================
  //  Editor chrome: line numbers, cursor stats
  // =====================================================================
  function updateGutter() {
    const lines = editor.value.split("\n").length;
    let out = "";
    for (let i = 1; i <= lines; i++) out += i + "\n";
    gutter.textContent = out;
    gutter.scrollTop = editor.scrollTop;
  }

  function updateCursor() {
    const pos = editor.selectionStart;
    const before = editor.value.slice(0, pos);
    const line = before.split("\n").length;
    const col = pos - before.lastIndexOf("\n");
    $("#stat-line").textContent = `Ln ${line}, Col ${col}`;
    const selLen = editor.selectionEnd - editor.selectionStart;
    $("#stat-sel").textContent = selLen ? `(${selLen} selected)` : "";
  }

  // =====================================================================
  //  Dirty tracking + autosave
  // =====================================================================
  function markDirty() {
    const nowDirty = editor.value !== state.lastSavedContent;
    state.dirty = nowDirty;
    dirtyDot.hidden = !nowDirty;
    if (nowDirty) scheduleAutosave();
  }

  const scheduleAutosave = debounce(() => {
    if (state.autosave && state.dirty && state.currentName) saveDocument(true);
  }, 1500);

  function onEditorInput() {
    updateGutter();
    updateCursor();
    renderDebounced();
    markDirty();
  }

  // =====================================================================
  //  Document lifecycle
  // =====================================================================
  function setCurrent(name, content) {
    state.currentName = name;
    editor.value = content;
    state.lastSavedContent = content;
    state.dirty = false;
    dirtyDot.hidden = true;
    docTitle.textContent = name || "Untitled";
    document.title = `${name || "Untitled"} — Markdown Editor`;
    updateGutter();
    updateCursor();
    renderNow();
  }

  async function refreshFileList() {
    try {
      const { documents } = await api.list();
      renderFileList(documents);
    } catch (err) {
      flash(err.message, true);
    }
  }

  function renderFileList(documents) {
    const filter = $("#file-filter").value.trim().toLowerCase();
    fileList.innerHTML = "";
    const shown = documents.filter((d) => d.name.toLowerCase().includes(filter));
    if (!shown.length) {
      fileList.innerHTML = `<li class="file-empty">${
        documents.length ? "No matches" : "No documents yet"
      }</li>`;
      return;
    }
    shown.forEach((d) => {
      const li = document.createElement("li");
      li.className = "file-item" + (d.name === state.currentName ? " active" : "");
      const when = new Date(d.modified * 1000);
      li.innerHTML =
        `<span class="fi-name">${escapeHtml(d.name)}</span>` +
        `<span class="fi-meta">${fmtDate(when)}</span>` +
        `<button class="fi-del" title="Delete">🗑</button>`;
      li.querySelector(".fi-name").addEventListener("click", () => openDocument(d.name));
      li.querySelector(".fi-meta").addEventListener("click", () => openDocument(d.name));
      li.querySelector(".fi-del").addEventListener("click", (e) => {
        e.stopPropagation();
        deleteDocument(d.name);
      });
      fileList.appendChild(li);
    });
  }

  function fmtDate(d) {
    const now = new Date();
    const sameDay = d.toDateString() === now.toDateString();
    return sameDay
      ? d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      : d.toLocaleDateString([], { month: "short", day: "numeric" });
  }

  async function openDocument(name) {
    if (name === state.currentName) return;
    if (!(await confirmDiscardIfDirty())) return;
    try {
      const { document: doc } = await api.read(name);
      setCurrent(doc.name, doc.content);
      refreshFileList();
      flash(`Opened “${doc.name}”`);
    } catch (err) {
      flash(err.message, true);
    }
  }

  async function newDocument() {
    if (!(await confirmDiscardIfDirty())) return;
    setCurrent(null, "");
    editor.focus();
    flash("New document");
  }

  async function saveDocument(silent) {
    try {
      if (!state.currentName) {
        const name = await promptName("Save document as:", "Untitled");
        if (!name) return false;
        const { document: doc } = await api.create(name, editor.value);
        state.currentName = doc.name;
        docTitle.textContent = doc.name;
        document.title = `${doc.name} — Markdown Editor`;
      } else {
        await api.save(state.currentName, editor.value);
      }
      state.lastSavedContent = editor.value;
      state.dirty = false;
      dirtyDot.hidden = true;
      refreshFileList();
      if (!silent) flash(`Saved “${state.currentName}”`);
      return true;
    } catch (err) {
      flash(err.message, true);
      return false;
    }
  }

  async function deleteDocument(name) {
    if (!confirm(`Delete “${name}”? This cannot be undone.`)) return;
    try {
      await api.remove(name);
      if (name === state.currentName) setCurrent(null, editor.value); // keep text, detach
      refreshFileList();
      flash(`Deleted “${name}”`);
    } catch (err) {
      flash(err.message, true);
    }
  }

  async function renameCurrent() {
    if (!state.currentName) {
      // Renaming an unsaved doc == naming it on first save.
      return saveDocument(false);
    }
    const name = await promptName("Rename document:", state.currentName);
    if (!name || name === state.currentName) return;
    try {
      const { document: doc } = await api.rename(state.currentName, name);
      setCurrent(doc.name, doc.content);
      refreshFileList();
      flash(`Renamed to “${doc.name}”`);
    } catch (err) {
      flash(err.message, true);
    }
  }

  async function confirmDiscardIfDirty() {
    if (!state.dirty) return true;
    if (state.currentName && state.autosave) {
      return await saveDocument(true);
    }
    return confirm("You have unsaved changes. Discard them?");
  }

  function promptName(msg, def) {
    const v = prompt(msg, def);
    return Promise.resolve(v === null ? null : v.trim());
  }

  // =====================================================================
  //  Toolbar / markdown insertion commands
  // =====================================================================
  function getSel() {
    return {
      start: editor.selectionStart,
      end: editor.selectionEnd,
      text: editor.value.slice(editor.selectionStart, editor.selectionEnd),
    };
  }

  function replaceSel(newText, selStart, selEnd) {
    const { start, end } = getSel();
    editor.setRangeText(newText, start, end, "end");
    if (selStart !== undefined) {
      editor.selectionStart = start + selStart;
      editor.selectionEnd = start + (selEnd === undefined ? selStart : selEnd);
    }
    editor.focus();
    onEditorInput();
  }

  // Wrap selection with a marker, or insert placeholder if empty.
  function wrapInline(marker, placeholder) {
    const { text } = getSel();
    if (text) {
      // toggle off if already wrapped
      const full = marker + text + marker;
      replaceSel(full, marker.length, marker.length + text.length);
    } else {
      const ins = marker + placeholder + marker;
      replaceSel(ins, marker.length, marker.length + placeholder.length);
    }
  }

  function eachSelectedLine(transform) {
    const { start, end } = getSel();
    const val = editor.value;
    const lineStart = val.lastIndexOf("\n", start - 1) + 1;
    let lineEnd = val.indexOf("\n", end);
    if (lineEnd === -1) lineEnd = val.length;
    const block = val.slice(lineStart, lineEnd);
    const transformed = block
      .split("\n")
      .map((line, i) => transform(line, i))
      .join("\n");
    editor.setRangeText(transformed, lineStart, lineEnd, "end");
    editor.selectionStart = lineStart;
    editor.selectionEnd = lineStart + transformed.length;
    editor.focus();
    onEditorInput();
  }

  function toggleLinePrefix(prefix) {
    eachSelectedLine((line) =>
      line.startsWith(prefix) ? line.slice(prefix.length) : prefix + line
    );
  }

  const commands = {
    bold: () => wrapInline("**", "bold text"),
    italic: () => wrapInline("*", "italic text"),
    strike: () => wrapInline("~~", "strikethrough"),
    code: () => wrapInline("`", "code"),
    h1: () => toggleLinePrefix("# "),
    h2: () => toggleLinePrefix("## "),
    h3: () => toggleLinePrefix("### "),
    ul: () => toggleLinePrefix("- "),
    ol: () => eachSelectedLine((line, i) => `${i + 1}. ${line.replace(/^\d+\.\s+/, "")}`),
    task: () => toggleLinePrefix("- [ ] "),
    quote: () => toggleLinePrefix("> "),
    hr: () => replaceSel("\n---\n"),
    link: () => {
      const { text } = getSel();
      const label = text || "link text";
      const ins = `[${label}](https://)`;
      replaceSel(ins, label.length + 3, label.length + 11);
    },
    image: () => {
      const { text } = getSel();
      const alt = text || "alt text";
      const ins = `![${alt}](https://)`;
      replaceSel(ins, alt.length + 4, alt.length + 12);
    },
    codeblock: () => {
      const { text } = getSel();
      const body = text || "code here";
      const ins = "```\n" + body + "\n```";
      replaceSel(ins, 4, 4 + body.length);
    },
    table: () => {
      const t =
        "\n| Column A | Column B | Column C |\n" +
        "| --- | --- | --- |\n" +
        "| a1 | b1 | c1 |\n" +
        "| a2 | b2 | c2 |\n";
      replaceSel(t);
    },
    find: () => toggleFindBar(true),
  };

  // =====================================================================
  //  Find & Replace
  // =====================================================================
  const findState = { matches: [], index: -1 };

  function toggleFindBar(show) {
    const bar = $("#findbar");
    bar.hidden = show === undefined ? !bar.hidden : !show;
    if (!bar.hidden) {
      const { text } = getSel();
      if (text && !text.includes("\n")) $("#find-input").value = text;
      $("#find-input").focus();
      $("#find-input").select();
      runFind();
    } else {
      editor.focus();
    }
  }

  function buildFindRegex() {
    const term = $("#find-input").value;
    if (!term) return null;
    const flags = "g" + ($("#find-case").checked ? "" : "i");
    try {
      const pattern = $("#find-regex").checked
        ? term
        : term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      return new RegExp(pattern, flags);
    } catch {
      return null;
    }
  }

  function runFind() {
    const re = buildFindRegex();
    findState.matches = [];
    if (re) {
      let m;
      while ((m = re.exec(editor.value))) {
        findState.matches.push([m.index, m.index + m[0].length]);
        if (m.index === re.lastIndex) re.lastIndex++; // avoid zero-width loop
      }
    }
    findState.index = findState.matches.length ? 0 : -1;
    updateFindCount();
    if (findState.index >= 0) selectMatch(0);
  }

  function updateFindCount() {
    const n = findState.matches.length;
    $("#find-count").textContent = n ? `${findState.index + 1}/${n}` : "0/0";
  }

  function selectMatch(i) {
    const m = findState.matches[i];
    if (!m) return;
    editor.focus();
    editor.setSelectionRange(m[0], m[1]);
    // Scroll roughly to the match.
    const before = editor.value.slice(0, m[0]).split("\n").length;
    const lineHeight = parseFloat(getComputedStyle(editor).lineHeight) || 22;
    editor.scrollTop = Math.max(0, (before - 5) * lineHeight);
    updateCursor();
  }

  function findStep(dir) {
    if (!findState.matches.length) return;
    findState.index =
      (findState.index + dir + findState.matches.length) % findState.matches.length;
    updateFindCount();
    selectMatch(findState.index);
  }

  function replaceOne() {
    const m = findState.matches[findState.index];
    if (!m) return;
    editor.setRangeText($("#replace-input").value, m[0], m[1], "end");
    onEditorInput();
    runFind();
  }

  function replaceAll() {
    const re = buildFindRegex();
    if (!re) return;
    const replacement = $("#replace-input").value;
    const count = findState.matches.length;
    editor.value = editor.value.replace(re, () => replacement);
    onEditorInput();
    runFind();
    flash(`Replaced ${count} occurrence${count === 1 ? "" : "s"}`);
  }

  // =====================================================================
  //  Editor key handling (indent, list continuation, shortcuts)
  // =====================================================================
  function handleEditorKeydown(e) {
    // Tab / Shift-Tab indentation
    if (e.key === "Tab") {
      e.preventDefault();
      if (e.shiftKey) {
        eachSelectedLine((line) => line.replace(/^( {1,4}|\t)/, ""));
      } else {
        const { start, end } = getSel();
        if (start === end) {
          replaceSel("    ", 4);
        } else {
          eachSelectedLine((line) => "    " + line);
        }
      }
      return;
    }

    // Enter: continue lists / blockquotes
    if (e.key === "Enter" && !e.shiftKey) {
      const val = editor.value;
      const pos = editor.selectionStart;
      const lineStart = val.lastIndexOf("\n", pos - 1) + 1;
      const line = val.slice(lineStart, pos);
      const m = line.match(/^(\s*)([-*+]\s\[[ xX]\]\s|[-*+]\s|\d+\.\s|>\s?)/);
      if (m && editor.selectionStart === editor.selectionEnd) {
        const indent = m[1];
        let marker = m[2];
        const content = line.slice(m[0].length);
        if (content.trim() === "") {
          // empty list item -> end the list
          e.preventDefault();
          editor.setRangeText("", lineStart, pos, "end");
          onEditorInput();
          return;
        }
        e.preventDefault();
        if (/^\d+\.\s$/.test(marker)) {
          const num = parseInt(marker, 10) + 1;
          marker = `${num}. `;
        }
        marker = marker.replace(/\[[xX]\]/, "[ ]"); // new task starts unchecked
        replaceSel("\n" + indent + marker);
        return;
      }
    }

    // Ctrl/Cmd shortcuts
    const mod = e.ctrlKey || e.metaKey;
    if (!mod) return;
    const key = e.key.toLowerCase();
    const map = {
      b: "bold",
      i: "italic",
      k: "link",
      "`": "code",
    };
    if (map[key]) {
      e.preventDefault();
      commands[map[key]]();
    } else if (key === "s") {
      e.preventDefault();
      saveDocument(false);
    } else if (key === "f") {
      e.preventDefault();
      toggleFindBar(true);
    } else if (key === "g") {
      e.preventDefault();
      findStep(e.shiftKey ? -1 : 1);
    }
  }

  // =====================================================================
  //  View mode + theme + sidebar
  // =====================================================================
  function setView(view) {
    state.view = view;
    localStorage.setItem("md.view", view);
    main.classList.remove("view-edit", "view-split", "view-preview");
    main.classList.add(`view-${view}`);
    document.querySelectorAll(".view-toggle button").forEach((b) => {
      b.classList.toggle("active", b.dataset.view === view);
    });
  }

  function setTheme(theme) {
    state.theme = theme;
    localStorage.setItem("md.theme", theme);
    document.documentElement.setAttribute("data-theme", theme);
    $("#btn-theme").textContent = theme === "dark" ? "☀️" : "🌙";
  }

  function toggleSidebar() {
    $("#sidebar").classList.toggle("collapsed");
  }

  // =====================================================================
  //  Export
  // =====================================================================
  async function exportAs(kind) {
    $("#export-menu").hidden = true;
    const title = state.currentName || "document";
    if (kind === "print") {
      window.print();
      return;
    }
    const url = kind === "html" ? "/api/export/html" : "/api/export/markdown";
    try {
      const r = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: editor.value, title }),
      });
      if (!r.ok) throw new Error("Export failed");
      const blob = await r.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `${title}.${kind === "html" ? "html" : "md"}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(a.href);
      flash(`Exported as ${kind.toUpperCase()}`);
    } catch (err) {
      flash(err.message, true);
    }
  }

  // =====================================================================
  //  Scroll sync (editor -> preview)
  // =====================================================================
  let syncingFromEditor = false;
  function syncPreviewScroll() {
    if (state.view !== "split") return;
    const pp = $("#preview-pane");
    const ratio =
      editor.scrollTop / Math.max(1, editor.scrollHeight - editor.clientHeight);
    syncingFromEditor = true;
    pp.scrollTop = ratio * (pp.scrollHeight - pp.clientHeight);
    requestAnimationFrame(() => (syncingFromEditor = false));
  }

  // =====================================================================
  //  Status flash
  // =====================================================================
  let flashTimer;
  function flash(msg, isError) {
    statusMsg.textContent = msg;
    statusMsg.classList.toggle("error", !!isError);
    clearTimeout(flashTimer);
    flashTimer = setTimeout(() => (statusMsg.textContent = ""), 3200);
  }

  // =====================================================================
  //  Splitter drag
  // =====================================================================
  function initSplitter() {
    const splitter = $("#splitter");
    const editorPane = $("#editor-pane");
    const previewPane = $("#preview-pane");
    let dragging = false;
    splitter.addEventListener("mousedown", (e) => {
      dragging = true;
      splitter.classList.add("dragging");
      e.preventDefault();
    });
    window.addEventListener("mousemove", (e) => {
      if (!dragging) return;
      const panes = $("#panes");
      const rect = panes.getBoundingClientRect();
      let ratio = (e.clientX - rect.left) / rect.width;
      ratio = Math.min(0.85, Math.max(0.15, ratio));
      editorPane.style.flex = `1 1 ${ratio * 100}%`;
      previewPane.style.flex = `1 1 ${(1 - ratio) * 100}%`;
    });
    window.addEventListener("mouseup", () => {
      dragging = false;
      splitter.classList.remove("dragging");
    });
  }

  // =====================================================================
  //  Wiring
  // =====================================================================
  function bind() {
    editor.addEventListener("input", onEditorInput);
    editor.addEventListener("keydown", handleEditorKeydown);
    editor.addEventListener("keyup", updateCursor);
    editor.addEventListener("click", updateCursor);
    editor.addEventListener("scroll", () => {
      gutter.scrollTop = editor.scrollTop;
      syncPreviewScroll();
    });

    // Toolbar
    document.querySelectorAll(".tb").forEach((btn) => {
      btn.addEventListener("click", () => {
        const cmd = btn.dataset.cmd;
        if (commands[cmd]) commands[cmd]();
      });
    });

    // Top bar
    $("#btn-new").addEventListener("click", newDocument);
    $("#btn-save").addEventListener("click", () => saveDocument(false));
    $("#btn-sidebar").addEventListener("click", toggleSidebar);
    $("#btn-theme").addEventListener("click", () =>
      setTheme(state.theme === "dark" ? "light" : "dark")
    );
    $("#btn-refresh").addEventListener("click", refreshFileList);
    docTitle.addEventListener("click", renameCurrent);
    $("#file-filter").addEventListener("input", refreshFileList);

    // View toggle
    document.querySelectorAll(".view-toggle button").forEach((b) => {
      b.addEventListener("click", () => setView(b.dataset.view));
    });

    // Export menu
    $("#btn-export").addEventListener("click", (e) => {
      e.stopPropagation();
      const m = $("#export-menu");
      m.hidden = !m.hidden;
    });
    document.querySelectorAll("#export-menu button").forEach((b) => {
      b.addEventListener("click", () => exportAs(b.dataset.export));
    });
    document.addEventListener("click", () => ($("#export-menu").hidden = true));

    // Find bar
    $("#find-input").addEventListener("input", runFind);
    $("#find-case").addEventListener("change", runFind);
    $("#find-regex").addEventListener("change", runFind);
    $("#find-next").addEventListener("click", () => findStep(1));
    $("#find-prev").addEventListener("click", () => findStep(-1));
    $("#replace-one").addEventListener("click", replaceOne);
    $("#replace-all").addEventListener("click", replaceAll);
    $("#find-close").addEventListener("click", () => toggleFindBar(false));
    $("#find-input").addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        findStep(e.shiftKey ? -1 : 1);
      } else if (e.key === "Escape") {
        toggleFindBar(false);
      }
    });

    // Global shortcuts
    document.addEventListener("keydown", (e) => {
      const mod = e.ctrlKey || e.metaKey;
      if (mod && e.altKey && e.key.toLowerCase() === "n") {
        e.preventDefault();
        newDocument();
      } else if (mod && e.altKey && e.key.toLowerCase() === "t") {
        e.preventDefault();
        setTheme(state.theme === "dark" ? "light" : "dark");
      } else if (mod && e.key === "\\") {
        e.preventDefault();
        toggleSidebar();
      } else if (e.key === "Escape" && !$("#findbar").hidden) {
        toggleFindBar(false);
      }
    });

    // Warn before leaving with unsaved changes.
    window.addEventListener("beforeunload", (e) => {
      if (state.dirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    });
  }

  // =====================================================================
  //  Boot
  // =====================================================================
  const SAMPLE = `# Welcome to Markdown Editor 👋

A **full-featured**, browser-based Markdown editor with a *Python* backend.

## Features

- Live preview rendered by Python (\`python-markdown\`)
- Syntax highlighting via **Pygments**
- Document workspace: create, open, rename, delete, autosave
- Toolbar, keyboard shortcuts & find/replace
- Export to standalone **HTML**, **Markdown**, or **PDF** (print)

## Try some Markdown

> Blockquotes, tables and task lists all work.

| Feature | Supported |
| --- | :---: |
| Tables | ✅ |
| Task lists | ✅ |
| Footnotes | ✅ |

- [x] Write some docs
- [ ] Ship it

\`\`\`python
def greet(name: str) -> str:
    return f"Hello, {name}!"

print(greet("world"))
\`\`\`

Made with ☕ and Python. Press **Ctrl+B** to embolden, **Ctrl+S** to save.
`;

  async function boot() {
    setTheme(state.theme);
    setView(state.view);
    bind();
    initSplitter();
    await refreshFileList();

    // Restore last-opened doc, else show a sample scratch document.
    const last = localStorage.getItem("md.lastDoc");
    let opened = false;
    if (last) {
      try {
        const { document: doc } = await api.read(last);
        setCurrent(doc.name, doc.content);
        opened = true;
      } catch {
        /* doc was deleted externally */
      }
    }
    if (!opened) setCurrent(null, SAMPLE);

    // Persist last-open on change.
    setInterval(() => {
      if (state.currentName) localStorage.setItem("md.lastDoc", state.currentName);
    }, 2000);
  }

  document.addEventListener("DOMContentLoaded", boot);
})();
