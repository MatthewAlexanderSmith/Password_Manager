// ─── CONFIG ─────────────────────────────────────
const API_BASES = ["http://127.0.0.1:8000", "http://localhost:8000"];

// ─── GLOBALS ─────────────────────────────────────
let allEntries = [];
let lastGenerated = "";
let revealedPw = "";

const ROUTE_ALIASES = {
  "/": ["/vault/status"],
  "/vault/backup": [],
};

window.addEventListener("error", (e) => {
  console.error("window.error", e.error || e.message);
  toast("JS error: " + (e.error?.message || e.message || "unknown"), "error");
});

window.addEventListener("unhandledrejection", (e) => {
  console.error("unhandledrejection", e.reason);
  toast(
    "Promise error: " + (e.reason?.message || e.reason || "unknown"),
    "error",
  );
});

function getEl(id) {
  return document.getElementById(id);
}

function setText(id, value) {
  const el = getEl(id);
  if (el) el.textContent = value;
}

function setDisplay(id, value) {
  const el = getEl(id);
  if (el) el.style.display = value;
}

async function refreshVault({ clearSearch = false } = {}) {
  try {
    const data = await api("GET", "/entries");
    allEntries = Array.isArray(data) ? data : data.entries || [];

    if (clearSearch) {
      const search = getEl("search-input");
      if (search) search.value = "";
    }

    renderEntries(allEntries);
    updateBadge(allEntries.length);
  } catch (e) {
    console.error("refreshVault failed", e);
    toast("Refresh failed: " + (e.message || e), "error");
    throw e;
  }
}
function normalizePath(path) {
  return path.replace(/\/{2,}/g, "/");
}

async function requestViaPywebview(method, path, body = null) {
  if (
    !window.pywebview ||
    !window.pywebview.api ||
    typeof window.pywebview.api.request !== "function"
  ) {
    throw new Error("pywebview bridge unavailable");
  }
  return await window.pywebview.api.request(method, path, body);
}

async function requestViaFetch(base, method, path, body = null) {
  const opts = {
    method,
    headers: { "Content-Type": "application/json" },
    mode: "cors",
  };
  if (body !== null && body !== undefined) opts.body = JSON.stringify(body);

  const res = await fetch(base + path, opts);
  const text = await res.text();
  let data = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { raw: text };
    }
  }

  if (!res.ok) {
    throw new Error(data.detail || data.message || `HTTP ${res.status}`);
  }
  return data;
}

async function api(method, path, body = null) {
  path = normalizePath(path);

  const candidates = [path, ...(ROUTE_ALIASES[path] || [])];
  let lastErr = null;

  for (const candidate of candidates) {
    try {
      if (
        window.pywebview &&
        window.pywebview.api &&
        typeof window.pywebview.api.request === "function"
      ) {
        return await requestViaPywebview(method, candidate, body);
      }

      for (const base of API_BASES) {
        try {
          return await requestViaFetch(base, method, candidate, body);
        } catch (err) {
          lastErr = err;
        }
      }
    } catch (err) {
      lastErr = err;
    }
  }

  throw lastErr || new Error("Request failed");
}

// ─── VIEWS ──────────────────────────────────────
function showView(id) {
  document
    .querySelectorAll(".view")
    .forEach((v) => v.classList.remove("active"));
  document.getElementById(id).classList.add("active");
}

// ─── LOCK / UNLOCK ──────────────────────────────
async function handleUnlock() {
  const pw = getEl("master-pw-input").value;
  const errEl = getEl("lock-error");
  const btn = getEl("btn-unlock");

  if (errEl) errEl.textContent = "";

  if (!pw) {
    if (errEl) errEl.textContent = "⚠ Enter master password.";
    return;
  }

  btn.disabled = true;
  btn.textContent = "Unlocking…";

  try {
    const status = await api("GET", "/vault/status");

    if (status.first_run) {
      toast("No vault found. Create one first.", "error");
      btn.disabled = false;
      btn.textContent = "Unlock Vault";
      return;
    }

    await api("POST", "/vault/unlock", { password: pw });

    getEl("master-pw-input").value = "";

    await playVaultTransition();

    showView("view-app");
    switchPanel("vault");
    await refreshVault({ clearSearch: true });

    toast("Vault unlocked", "success");
  } catch (e) {
    if (errEl) errEl.textContent = "⚠ " + (e.message || "Unlock failed");
  } finally {
    btn.disabled = false;
    btn.textContent = "Unlock Vault";
  }
}

document.getElementById("master-pw-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") handleUnlock();
});

async function handleLock() {
  try {
    await api("POST", "/vault/lock");
  } catch (e) {
    console.error("handleLock failed", e);
    toast("Lock failed: " + (e.message || e), "error");
  }

  showView("view-lock");
  allEntries = [];
  renderEntries([]);
  updateBadge(0);
  toast("Vault locked. Key wiped from memory.", "info");
}

// ─── CREATE VAULT ────────────────────────────────
function showCreateVaultModal() {
  openModal("modal-create");
}

async function handleCreateVault() {
  const pw = document.getElementById("create-pw").value;
  const confirm = document.getElementById("create-pw-confirm").value;
  if (!pw) {
    toast("Enter a master password", "error");
    return;
  }
  if (pw !== confirm) {
    toast("Passwords do not match", "error");
    return;
  }
  if (pw.length < 10) {
    toast("Master password must be at least 10 characters", "error");
    return;
  }
  try {
    const result = await api("POST", "/vault/create", { password: pw });

    closeModal("modal-create");

    document.getElementById("master-pw-input").value = "";

    await playVaultTransition();
    showView("view-app");
    await loadEntries();

    toast("Vault created and unlocked successfully.", "success");
  } catch (e) {
    toast(e.message || "Failed to create vault", "error");
  }
}

function playVaultTransition() {
  return new Promise((resolve) => {
    const el = document.getElementById("vault-transition");

    el.classList.add("active");

    setTimeout(() => {
      el.classList.remove("active");
      resolve();
    }, 550);
  });
}

// ─── NAV ────────────────────────────────────────
function switchPanel(name, evt = null) {
  document
    .querySelectorAll(".nav-item")
    .forEach((el) => el.classList.remove("active"));
  if (evt?.currentTarget) evt.currentTarget.classList.add("active");

  document
    .querySelectorAll(".panel")
    .forEach((p) => p.classList.remove("active"));
  const panel = getEl("panel-" + name);
  if (panel) panel.classList.add("active");

  const titles = {
    vault: "CREDENTIALS",
    generator: "PASSWORD GENERATOR",
    breach: "BREACH INTELLIGENCE",
    export: "EXPORT VAULT",
    settings: "SETTINGS & SECURITY",
  };

  const topbarTitle = getEl("topbar-title");
  if (topbarTitle) topbarTitle.textContent = titles[name] || name.toUpperCase();

  const showSearch = name === "vault";
  setDisplay("search-wrap", showSearch ? "" : "none");
  setDisplay("btn-add-entry", name === "vault" ? "" : "none");

  if (name === "generator") {
    generatePassword();
  }
}

// ─── ENTRIES ────────────────────────────────────
async function loadEntries() {
  try {
    await refreshVault({ clearSearch: false });
  } catch (e) {
    toast("Failed to load entries: " + e.message, "error");
  }
}

function ensureEntryItemsContainer(list, empty) {
  let items = document.getElementById("entry-items");

  if (!items) {
    items = document.createElement("div");
    items.id = "entry-items";
    items.className = "entry-items";
    items.style.display = "flex";
    items.style.flexDirection = "column";
    items.style.gap = "2px";
    list.insertBefore(items, empty);
  }

  return items;
}

function renderEntries(entries) {
  const list = getEl("entry-list");
  const empty = getEl("empty-state");
  const label = getEl("vault-count-label");
  const badge = getEl("entry-count-badge");

  if (!list || !empty || !label) {
    console.error("renderEntries missing elements", {
      list,
      empty,
      label,
      badge,
    });
    toast("Vault UI is missing required elements. Check HTML ids.", "error");
    return;
  }

  const items = ensureEntryItemsContainer(list, empty);

  label.textContent = `${entries.length} credential${entries.length !== 1 ? "s" : ""}`;
  if (badge) badge.textContent = String(entries.length);

  if (!entries.length) {
    items.innerHTML = "";
    empty.style.display = "block";
    return;
  }

  empty.style.display = "none";

  items.innerHTML = entries
    .map((e) => {
      const siteName = e.title || e.site_name || e[0] || "Unknown";
      const username = e.username || e[1] || "";
      const id = e.id || e.entry_id || e[2] || "";
      const initial = siteName.charAt(0).toUpperCase();

      return `
        <div class="entry-card" data-id="${escHtml(id)}" data-site="${escHtml(siteName)}" data-user="${escHtml(username)}">
          <div class="entry-avatar">${escHtml(initial)}</div>
          <div class="entry-info">
            <div class="entry-site">${escHtml(siteName)}</div>
            <div class="entry-user">${escHtml(username)}</div>
          </div>
          <div class="entry-actions">
            <button class="icon-btn" title="View / Copy" onclick="revealEntry('${escHtml(id)}','${escHtml(siteName)}','${escHtml(username)}');event.stopPropagation()">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.3">
                <path d="M1 8S3.5 3 8 3s7 5 7 5-2.5 5-7 5-7-5-7-5z"/><circle cx="8" cy="8" r="2"/>
              </svg>
            </button>
            <button class="icon-btn danger" title="Delete" onclick="deleteEntry('${escHtml(id)}');event.stopPropagation()">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.3">
                <path d="M3 5h10M8 8v4M5 5l1-2h4l1 2M4 5l1 9h6l1-9"/>
              </svg>
            </button>
          </div>
        </div>
      `;
    })
    .join("");
}

function updateBadge(n) {
  const badge = getEl("entry-count-badge");
  if (badge) badge.textContent = String(n);
}

function filterEntries() {
  const q = document.getElementById("search-input").value.toLowerCase();
  if (!q) {
    renderEntries(allEntries);
    return;
  }
  renderEntries(
    allEntries.filter((e) => {
      const site = (e.title || e.site_name || e[0] || "").toLowerCase();
      const user = (e.username || e[1] || "").toLowerCase();
      return site.includes(q) || user.includes(q);
    }),
  );
}

// ─── ADD ENTRY ───────────────────────────────────
function openAddModal() {
  document.getElementById("add-site").value = "";
  document.getElementById("add-user").value = "";
  document.getElementById("add-password").value = "";
  document.getElementById("add-strength-fill").style.width = "0%";
  document.getElementById("add-strength-label").textContent = "";
  document.getElementById("add-breach-result").textContent = "";
  openModal("modal-add");
}

async function handleAddEntry() {
  const site = getEl("add-site").value.trim();
  const user = getEl("add-user").value.trim();
  const pw = getEl("add-password").value;

  if (!site || !pw) {
    toast("Site and password are required", "error");
    return;
  }

  try {
    await api("POST", "/entries", {
      title: site,
      username: user,
      password: pw,
    });
    closeModal("modal-add");
    await refreshVault({ clearSearch: true });
    toast(`Saved: ${site}`, "success");
  } catch (e) {
    console.error("handleAddEntry failed", e);
    toast("Failed to add entry: " + (e.message || e), "error");
  }
}

// ─── REVEAL ENTRY ────────────────────────────────
async function revealEntry(id, site, user) {
  const title = getEl("reveal-title");
  const siteVal = getEl("reveal-site-val");
  const userVal = getEl("reveal-user-val");
  const pwVal = getEl("reveal-pw-val");
  const copy = getEl("reveal-copy-confirm");

  if (title) title.textContent = site;
  if (siteVal) siteVal.textContent = site;
  if (userVal) userVal.textContent = user;
  if (pwVal) pwVal.textContent = "⬤⬤⬤⬤⬤⬤⬤⬤⬤⬤⬤";
  if (copy) copy.textContent = "";

  revealedPw = "";
  openModal("modal-reveal");

  try {
    const data = await api("GET", `/entries/${id}`);
    revealedPw = data.password || data;
    if (pwVal) pwVal.textContent = revealedPw;
  } catch (e) {
    if (pwVal) pwVal.textContent = "Error: " + e.message;
  }
}

function copyRevealedPassword() {
  if (!revealedPw) return;
  navigator.clipboard.writeText(revealedPw).then(() => {
    document.getElementById("reveal-copy-confirm").textContent =
      "✓ Copied to clipboard";
    setTimeout(() => {
      document.getElementById("reveal-copy-confirm").textContent = "";
    }, 2000);
  });
}

// ─── DELETE ENTRY ────────────────────────────────
async function deleteEntry(id) {
  if (!confirm("Delete this credential? This action cannot be undone.")) return;

  try {
    await api("DELETE", `/entries/${id}`);
    await refreshVault({ clearSearch: true });
    toast("Entry securely deleted", "success");
  } catch (e) {
    console.error("deleteEntry failed", e);
    toast("Failed to delete: " + (e.message || e), "error");
  }
}

// ─── STRENGTH SCORING ────────────────────────────
let scoreDebounce = null;
async function scorePassword(pw, fillId, labelId, breachId) {
  clearTimeout(scoreDebounce);
  if (!pw) {
    setStrength(fillId, labelId, 0, "");
    if (breachId) document.getElementById(breachId).textContent = "";
    return;
  }
  scoreDebounce = setTimeout(async () => {
    try {
      const d = await api("POST", "/ai/score-password", { password: pw });
      const score = d.score !== undefined ? d.score : (d.strength_score ?? 0);
      const label =
        d.label || (score <= 20 ? "Weak" : score <= 60 ? "Moderate" : "Strong");
      setStrength(fillId, labelId, score, label);
    } catch (_) {
      // Fallback: local heuristic
      const score = localScore(pw);
      const label = score <= 20 ? "Weak" : score <= 60 ? "Moderate" : "Strong";
      setStrength(fillId, labelId, score, label);
    }
    if (breachId) {
      await checkBreachInline(pw, breachId);
    }
  }, 400);
}

function setStrength(fillId, labelId, score, label) {
  const fill = document.getElementById(fillId);
  const lbl = document.getElementById(labelId);
  if (!fill || !lbl) return;
  fill.style.width = score + "%";
  const color = score <= 20 ? "#c0283d" : score <= 60 ? "#d4a017" : "#2ed573";
  fill.style.background = color;
  lbl.style.color = color;
  lbl.textContent = label ? `Strength: ${label}` : "";
}

function localScore(pw) {
  let s = 0;
  if (pw.length >= 8) s += 10;
  if (pw.length >= 12) s += 15;
  if (pw.length >= 16) s += 15;
  if (/[A-Z]/.test(pw)) s += 10;
  if (/[a-z]/.test(pw)) s += 10;
  if (/[0-9]/.test(pw)) s += 10;
  if (/[^A-Za-z0-9]/.test(pw)) s += 15;
  if (/^[a-zA-Z]+$/.test(pw)) s = Math.min(s, 30);
  return Math.min(s, 100);
}

async function checkBreachInline(pw, elId) {
  const el = document.getElementById(elId);
  if (!el) return;
  try {
    const d = await api("POST", "/breach/check", { password: pw });
    const breached = d.breached ?? d.is_breached ?? false;
    el.style.color = breached ? "var(--crimson-bright)" : "#2ed573";
    el.textContent = breached
      ? "⚠ Found in breach database"
      : "✓ Not found in known breaches";
  } catch (_) {
    el.textContent = "";
  }
}

// ─── BREACH CHECK PANEL ──────────────────────────
async function checkBreach() {
  const pw = document.getElementById("breach-input").value;
  const resultBox = document.getElementById("breach-result");
  const status = document.getElementById("breach-status");
  const detail = document.getElementById("breach-detail");
  if (!pw) {
    toast("Enter a password to check", "error");
    return;
  }
  resultBox.className = "breach-result-box";
  status.textContent = "Checking…";
  resultBox.classList.add("show");
  try {
    const d = await api("POST", "/breach/check", { password: pw });
    const breached = d.breached ?? d.is_breached ?? false;
    resultBox.classList.add(breached ? "breached" : "safe");
    if (breached) {
      status.textContent = "⚠ BREACH DETECTED";
      detail.textContent =
        "This password appears in known breach databases. Do not use it. Choose a different password immediately.";
    } else {
      status.textContent = "✓ NOT FOUND IN BREACHES";
      detail.textContent =
        "This password was not found in the Bloom Filter breach corpus. However, always use unique passwords per service.";
    }
  } catch (e) {
    status.textContent = "Check unavailable";
    detail.textContent = e.message + " — Bloom Filter may not be loaded yet.";
    resultBox.classList.add("safe");
  }
}

// ─── GENERATOR ───────────────────────────────────
function generatePassword() {
  const length = parseInt(document.getElementById("gen-length").value);
  const useUpper = document
    .getElementById("tog-upper")
    .classList.contains("on");
  const useLower = document
    .getElementById("tog-lower")
    .classList.contains("on");
  const useDigits = document
    .getElementById("tog-digits")
    .classList.contains("on");
  const useSymbols = document
    .getElementById("tog-symbols")
    .classList.contains("on");

  let charset = "";
  if (useUpper) charset += "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  if (useLower) charset += "abcdefghijklmnopqrstuvwxyz";
  if (useDigits) charset += "0123456789";
  if (useSymbols) charset += "!@#$%^&*()-_=+[]{}|;:,.<>?";
  if (!charset) charset = "abcdefghijklmnopqrstuvwxyz";

  const arr = new Uint32Array(length);
  crypto.getRandomValues(arr);
  const pw = Array.from(arr)
    .map((n) => charset[n % charset.length])
    .join("");
  lastGenerated = pw;
  document.getElementById("gen-output").textContent = pw;
  scorePassword(pw, "gen-strength-fill", "gen-strength-label", null);
}

function copyGenerated() {
  if (!lastGenerated) return;
  navigator.clipboard
    .writeText(lastGenerated)
    .then(() => toast("Password copied", "success"));
}

function fillGenerated(inputId) {
  if (!lastGenerated) generatePassword();
  document.getElementById(inputId).value = lastGenerated;
  document.getElementById(inputId).dispatchEvent(new Event("input"));
}

function toggleOpt(el) {
  el.classList.toggle("on");
  generatePassword();
}

function togglePwVis(inputId, btn) {
  const input = document.getElementById(inputId);
  input.type = input.type === "password" ? "text" : "password";
}

// ─── EXPORT ─────────────────────────────────────
async function handleExport() {
  const format = document.getElementById("export-format").value;
  const exportPw = document.getElementById("export-password").value;
  try {
    const body = { format };
    if (exportPw) body.export_password = exportPw;
    const d = await api("POST", "/export/quantum-safe", body);
    toast("Export initiated: " + (d.path || d.message || "Done"), "success");
  } catch (e) {
    toast("Export failed: " + e.message, "error");
  }
}

async function handleImport() {
  const input = getEl("import-file");
  const btn = getEl("btn-import");
  const file = input?.files?.[0];

  if (!file) {
    toast("Select an export file first", "error");
    return;
  }

  const prevLabel = btn ? btn.textContent : "";
  if (btn) {
    btn.disabled = true;
    btn.textContent = "Importing…";
  }

  try {
    const content = await file.text();
    const result = await api("POST", "/import/quantum-safe", {
      content,
      filename: file.name,
      clear_existing: false,
    });

    input.value = "";
    await refreshVault({ clearSearch: true });
    toast(
      `Imported ${result.imported || 0} entr${result.imported === 1 ? "y" : "ies"} from ${file.name}`,
      "success",
    );

    if ((result.skipped || 0) > 0) {
      toast(
        `Skipped ${result.skipped} invalid entr${result.skipped === 1 ? "y" : "ies"}`,
        "info",
      );
    }
  } catch (e) {
    console.error("handleImport failed", e);
    toast("Import failed: " + (e.message || e), "error");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = prevLabel || "Import Vault";
    }
  }
}

// ─── BACKUP ──────────────────────────────────────
async function handleBackup() {
  try {
    const d = await api("POST", "/vault/backup");
    toast("Backup created: " + (d.path || "Done"), "success");
  } catch (e) {
    console.error("handleBackup failed", e);
    toast("Backup failed: " + (e.message || e), "error");
  }
}

// ─── MODALS ─────────────────────────────────────
function openModal(id) {
  document.getElementById(id).classList.add("open");
}
function closeModal(id) {
  document.getElementById(id).classList.remove("open");
}

document.querySelectorAll(".modal-overlay").forEach((overlay) => {
  overlay.addEventListener("click", function (e) {
    if (e.target === this) this.classList.remove("open");
  });
});

// ─── TOAST ──────────────────────────────────────
function toast(msg, type = "info") {
  console.error(`[${type}]`, msg);

  const container = getEl("toast-container");
  if (!container) {
    alert(`${type.toUpperCase()}: ${msg}`);
    return;
  }

  const el = document.createElement("div");
  el.className = `toast ${type}`;
  const icon = type === "success" ? "✓" : type === "error" ? "⚠" : "◈";
  el.innerHTML = `<span style="color:${type === "success" ? "#2ed573" : type === "error" ? "var(--crimson-bright)" : "var(--gold)"}">${icon}</span> ${escHtml(msg)}`;
  container.appendChild(el);

  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transition = "opacity 0.3s";
    setTimeout(() => el.remove(), 300);
  }, 3500);
}

// ─── UTILS ──────────────────────────────────────
function escHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ─── INIT ────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  try {
    const status = await api("GET", "/vault/status");

    if (status.first_run) {
      // Force user to create vault
      getEl("btn-unlock").disabled = true;
      showView("view-lock");
      toast("Create a vault to begin", "info");
      return;
    }

    if (!status.locked) {
      const d = await api("GET", "/entries");
      allEntries = Array.isArray(d) ? d : d.entries || [];
      renderEntries(allEntries);
      updateBadge(allEntries.length);
      showView("view-app");
    } else {
      showView("view-lock");
    }
  } catch {
    showView("view-lock");
  }
});
