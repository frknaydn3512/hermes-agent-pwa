// hermes-agent-pwa. Tabs: Chat (Hermes), Dev (Hermes tasks), Settings (model, optional PC).
// Every text from the server is written with textContent, never innerHTML.

// --- Language: English in the source, Turkish via TR. t("English text") -> current language ---
const TR = {
  "Enter your token. It stays on this device, you won't be asked again.": "Token'ı gir. Bu cihazda saklanır, bir daha sorulmaz.",
  "Log in": "Giriş", "Hello": "Merhaba",
  "Talk to Hermes: set reminders, search the web, plan things. It uses the model you connected.":
    "Hermes'e yaz: hatırlatıcı kur, web'de ara, iş planla. Bağladığın modeli kullanır.",
  "My reminders": "Hatırlatıcılarım", "What reminders do I have?": "Kurulu hatırlatıcılarım neler?",
  "Water in 10 min": "10 dk sonra su iç", "Remind me to drink water in 10 minutes.": "10 dakika sonra su iç diye hatırlat.",
  "Message": "Mesaj", "Send": "Gönder", "Status": "Durum",
  "Writes code, fixes bugs, runs tests in your repo. Give it a task, you get a notification when it's done.":
    "Repoda kod yazar, düzeltir, test çalıştırır. İşi ver, bitince bildirim gelir.",
  "Summarize tests": "Testleri özetle", "Run the tests and summarize the result.": "Testleri çalıştır, sonucu özetle.",
  "Explain the repo": "Repoyu anlat", "Explain what this repo does in a few lines.": "Bu repo ne yapıyor, birkaç satırda anlat.",
  "Give Hermes a task": "Hermes'e görev ver", "Repo changes": "Repo değişiklikleri",
  "Provider": "Sağlayıcı", "Model name": "Model adı", "URL": "Adres", "API key": "API anahtarı", "Save": "Kaydet",
  "Chat, reminders and Dev all use this model. The key is stored in Hermes on the server and never shown again.":
    "Sohbet, hatırlatıcılar ve Geliştir bu modeli kullanır. Anahtar sunucuda Hermes'e kaydedilir, bir daha gösterilmez.",
  "PC status": "PC durumu", "Refresh": "Yenile", "Power": "Güç", "Sleep": "Uyut", "Shut down": "Kapat",
  "Cancel": "İptal et", "Files": "Dosyalar", "Downloads": "İndirilenler", "App": "Uygulama",
  "Enable notifications": "Bildirimleri aç", "Log out": "Çıkış", "Chat": "Sohbet", "Dev": "Geliştir",
  "Settings": "Ayarlar", "Invalid token, log in again": "Token geçersiz, yeniden giriş yap",
  "Wrong token": "Token yanlış", "Server error": "Sunucu hatası", "Log out?": "Çıkış yapılsın mı?",
  "New": "Yeni", "New session": "Yeni oturum", "Sleep the PC": "PC uyutulsun", "Shut down the PC": "PC kapatılsın",
  "Delete file": "Dosya silinsin", "Approved": "Onaylandı", "Rejected": "Reddedildi", "Approve": "Onayla",
  "Reject": "Reddet", "Put the PC to sleep? The app is unreachable while it sleeps.": "PC uyusun mu? Uyurken uygulamaya erişemezsin.",
  "Shut the PC down in 60 s?": "PC 60 sn içinde kapansın mı?", "Error": "Hata",
  "running": "çalışıyor", "waiting": "onay bekliyor", "completed": "bitti", "failed": "hata", "error": "hata",
  "stopped": "durduruldu", "cancelled": "iptal", "expired": "süresi doldu",
  "New Hermes session": "Yeni Hermes oturumu",
  "Running… You'll get a notification, you can close the app.": "Çalışıyor… Bitince bildirim gelecek, uygulamayı kapatabilirsin.",
  "Stop": "Durdur", "Hermes asks approval for:": "Hermes şu komut için onay istiyor:", "Allow once": "Bir kez izin ver",
  "(no output)": "(çıktı yok)", "Show more": "Devamını göster", "Show less": "Kısalt",
  "HERMES_API_KEY missing in .env": "HERMES_API_KEY .env'de yok",
  "Hermes is down. Restart the server or check Hermes.": "Hermes kapalı. Sunucuyu yeniden başlat ya da Hermes'i kontrol et.",
  "No changes": "Değişiklik yok", "Empty diff": "Diff boş", "no model": "model yok",
  "Key saved ✓ (type to replace)": "Anahtar kayıtlı ✓ (değiştirmek için yaz)",
  "Enter an API key for this provider": "Bu sağlayıcı için API anahtarı gir",
  "Saving, Hermes restarts…": "Kaydediliyor, Hermes yeniden başlıyor…", "Saving…": "Kaydediliyor…",
  "Disk free": "Disk boş", "Uptime": "Açık kalma", "Battery": "Pil", "charging": "şarjda", "on battery": "pilde",
  "Get": "Al", "Delete": "Sil", "Empty": "Boş", "Download failed": "İndirilemedi",
  "Test notification": "Test bildirimi", "Test notification sent": "Test bildirimi gönderildi",
  "No push here. Open the app from the home screen.": "Push yok. Uygulamayı ana ekrandan aç.",
  "Notification permission denied": "Bildirim izni verilmedi", "Notifications on": "Bildirimler açıldı",
  "Shutdown cancelled": "Kapatma iptal edildi", "No pending shutdown": "Bekleyen kapatma yok",
  "PC goes to sleep in 5 seconds. The server is unreachable while it sleeps.": "PC 5 saniye içinde uyuyor. Uyurken sunucuya erişilemez.",
  "PC shuts down in 60 s. Cancel from the app.": "PC 60 sn içinde kapanacak. Uygulamadan iptal edebilirsin.",
};
const LANG = (() => { try { return localStorage.getItem("lang"); } catch { return null; } })()
  || (navigator.language.startsWith("tr") ? "tr" : "en");
const t = (s) => (LANG === "tr" && TR[s]) || s;
document.documentElement.lang = LANG;
for (const n of document.querySelectorAll("[data-t]")) n.textContent = t(n.textContent.trim());
for (const n of document.querySelectorAll("[placeholder]")) n.placeholder = t(n.placeholder);
for (const n of document.querySelectorAll("[aria-label]")) n.ariaLabel = t(n.getAttribute("aria-label"));
for (const n of document.querySelectorAll("[data-say]")) n.dataset.say = t(n.dataset.say);
for (const n of document.querySelectorAll("[data-task]")) n.dataset.task = t(n.dataset.task);

const el = (id) => document.getElementById(id);
const TITLES = { chat: t("Chat"), dev: t("Dev"), pc: t("Settings") };
let pcControl = false; // true when the server runs on a PC (/health)

let token = localStorage.getItem("token") || "";
let chatSession = null; // Hermes session; Hermes keeps the history
let hermesSession = localStorage.getItem("hermesSession") || "";
let tab = "chat";
let devSeg = "agent";
let taskTimer = null;

const auth = () => ({ Authorization: `Bearer ${token}` });

// --- Helpers ---

function node(tag, text, cls) {
  const n = document.createElement(tag);
  if (text != null) n.textContent = text;
  if (cls) n.className = cls;
  return n;
}

async function api(path, { method = "GET", body } = {}) {
  const opts = { method, headers: auth() };
  if (body !== undefined) {
    opts.headers = { ...opts.headers, "Content-Type": "application/json" };
    opts.body = JSON.stringify(body);
  }
  const r = await fetch(path, opts);
  if (r.status === 401) { logout(); throw new Error(t("Invalid token, log in again")); }
  if (!r.ok) {
    let detail = await r.text();
    try { detail = JSON.parse(detail).detail || detail; } catch {}
    throw new Error(String(detail));
  }
  return r.json();
}

let toastTimer;
function toast(msg) {
  const t = el("toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add("hidden"), 3500);
}

function button(text, onclick, cls) {
  const b = node("button", text, cls);
  b.type = "button";
  b.onclick = async () => {
    b.disabled = true;
    try { await onclick(); } catch (e) { toast(e.message); }
    b.disabled = false;
  };
  return b;
}

function row(title, sub, right) {
  const r = node("div", null, "row");
  const g = node("div", title, "grow");
  if (sub) g.append(node("small", sub));
  r.append(g, ...[].concat(right || []));
  return r;
}

function autoGrow(t) {
  t.addEventListener("input", () => {
    t.style.height = "auto";
    t.style.height = Math.min(t.scrollHeight, 140) + "px";
  });
}

function enterSends(t, form) {
  // Enter sends, Shift+Enter adds a line. The iOS keyboard "send" key lands here too.
  t.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
  });
}

// --- Login / logout ---

function show(loggedIn) {
  el("login").classList.toggle("hidden", loggedIn);
  el("app").classList.toggle("hidden", !loggedIn);
  if (loggedIn) {
    setTab((location.hash || "#chat").slice(1));
    loadModel();
    refreshApprovals();
  }
}

function logout() {
  localStorage.removeItem("token");
  token = "";
  chatSession = null;
  show(false);
}

el("login-form").onsubmit = async (e) => {
  e.preventDefault();
  const candidate = el("token").value.trim();
  const err = el("login-err");
  try {
    const r = await fetch("/approvals", { headers: { Authorization: `Bearer ${candidate}` } });
    if (!r.ok) throw new Error(r.status === 401 ? t("Wrong token") : `${t("Server error")} ${r.status}`);
    token = candidate;
    localStorage.setItem("token", token);
    err.classList.add("hidden");
    show(true);
  } catch (e2) {
    err.textContent = e2.message;
    err.classList.remove("hidden");
  }
};

el("logout").onclick = () => { if (confirm(t("Log out?"))) logout(); };

// --- Tabs ---

function setTab(name) {
  if (!TITLES[name]) name = "chat";
  tab = name;
  for (const t of Object.keys(TITLES)) el(`tab-${t}`).classList.toggle("hidden", t !== name);
  for (const b of document.querySelectorAll("[data-tab]")) b.classList.toggle("on", b.dataset.tab === name);
  el("title").textContent = TITLES[name];
  window.history.replaceState(null, "", `#${name}`);

  el("model-pill").classList.toggle("hidden", name !== "chat" || !modelInfo);
  const action = el("top-action");
  action.classList.add("hidden");
  if (name === "chat") {
    action.textContent = t("New");
    action.onclick = newChat;
    action.classList.toggle("hidden", !chatSession);
  }
  if (name === "dev" && devSeg === "agent") {
    action.textContent = t("New session");
    action.onclick = newHermesSession;
    action.classList.remove("hidden");
  }
  if (name === "dev") loadDev();
  if (name === "pc") { loadModel(); if (pcControl) loadPc(); }
}

for (const b of document.querySelectorAll("[data-tab]")) b.onclick = () => setTab(b.dataset.tab);

// --- Approvals (on top of every tab) ---

const APPROVAL_LABELS = {
  sleep_pc: t("Sleep the PC"),
  shutdown_pc: t("Shut down the PC"),
  delete_file: t("Delete file"),
};

async function decide(id, ok) {
  const r = await api(`/approvals/${id}/${ok ? "approve" : "reject"}`, { method: "POST" });
  toast(t(r.result || (ok ? "Approved" : "Rejected")));
  refreshApprovals();
  if (tab !== "chat") setTab(tab);
}

async function refreshApprovals() {
  if (!token) return;
  try {
    const list = await api("/approvals");
    const box = el("approvals");
    box.replaceChildren(
      ...list.map((a) => {
        const card = node("div", null, "approval");
        const what = node("div", null, "what");
        what.append(node("b", APPROVAL_LABELS[a.action] || a.action));
        const params = Object.entries(a.params).map(([k, v]) => `${k}: ${v}`).join(", ");
        what.append(node("small", `#${a.id}${params ? " · " + params : ""}`));
        card.append(what, button(t("Approve"), () => decide(a.id, true), "ok"), button(t("Reject"), () => decide(a.id, false), "danger"));
        return card;
      })
    );
    box.classList.toggle("hidden", !list.length);
  } catch {}
}

// Commands started from the panel go through the approval queue too (one log). confirm() is the approval.
async function runAction(action, params, question) {
  if (!confirm(question)) return;
  const a = await api("/approvals", { method: "POST", body: { action, params } });
  await decide(a.id, true);
}

const ACTION_QUESTIONS = {
  sleep_pc: t("Put the PC to sleep? The app is unreachable while it sleeps."),
  shutdown_pc: t("Shut the PC down in 60 s?"),
};
for (const b of document.querySelectorAll("[data-action]")) {
  b.onclick = async () => {
    try { await runAction(b.dataset.action, {}, ACTION_QUESTIONS[b.dataset.action]); } catch (e) { toast(e.message); }
  };
}

// --- Chat ---

const messages = el("messages");
const input = el("input");
autoGrow(input);
enterSends(input, el("chat-form"));

function bubble(cls, text = "") {
  el("chat-empty")?.classList.add("hidden");
  const div = node("div", text, `msg ${cls}`);
  messages.append(div);
  messages.scrollTop = messages.scrollHeight;
  return div;
}

function newChat() {
  chatSession = null;
  for (const m of [...messages.querySelectorAll(".msg")]) m.remove();
  el("chat-empty").classList.remove("hidden");
  el("top-action").classList.add("hidden");
}

async function sendChat(message) {
  const sendBtn = el("chat-form").querySelector("button");
  sendBtn.disabled = true;
  bubble("user", message);
  const out = bubble("bot pending");
  try {
    const r = await fetch("/chat/stream", {
      method: "POST",
      headers: { ...auth(), "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: chatSession }),
    });
    if (!r.ok) {
      const detail = await r.text();
      throw new Error(r.status === 429 ? `Limit: ${detail}` : `${t("Error")} ${r.status}: ${detail}`);
    }
    chatSession = r.headers.get("X-Session-Id") || chatSession;
    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let reply = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      reply += decoder.decode(value, { stream: true });
      out.textContent = reply;
      messages.scrollTop = messages.scrollHeight;
    }
    if (tab === "chat") el("top-action").classList.remove("hidden");
  } catch (e) {
    out.remove();
    bubble("sys", e.message);
  } finally {
    out.classList.remove("pending");
    sendBtn.disabled = false;
    refreshApprovals();
  }
}

el("chat-form").onsubmit = (e) => {
  e.preventDefault();
  const m = input.value.trim();
  if (!m) return;
  input.value = "";
  input.style.height = "auto";
  sendChat(m);
};
for (const c of document.querySelectorAll("[data-say]")) c.onclick = () => sendChat(c.dataset.say);

// --- Dev: Hermes ---


for (const b of document.querySelectorAll("[data-seg]")) {
  b.onclick = () => {
    devSeg = b.dataset.seg;
    for (const x of document.querySelectorAll("[data-seg]")) x.classList.toggle("on", x === b);
    el("seg-agent").classList.toggle("hidden", devSeg !== "agent");
    el("seg-status").classList.toggle("hidden", devSeg !== "status");
    setTab("dev");
  };
}

function newHermesSession() {
  hermesSession = "";
  localStorage.removeItem("hermesSession");
  renderTasks([]);
  toast(t("New Hermes session"));
}

function choicesOf(pending) {
  const c = Array.isArray(pending) ? pending[0] : pending;
  const list = (c && (c.choices || c.options)) || ["once", "deny"];
  return list.map((x) => (typeof x === "string" ? x : x.value || x.id || String(x)));
}

function describe(pending) {
  const c = Array.isArray(pending) ? pending[0] : pending;
  return (c && (c.description || c.command || c.prompt)) || JSON.stringify(c);
}

function renderTasks(list) {
  const box = el("tasks");
  const empty = box.querySelector(".empty");
  for (const n of [...box.children]) if (n !== empty) n.remove();
  empty.classList.toggle("hidden", list.length > 0);
  // API returns newest first; show oldest first like a chat
  for (const task of [...list].reverse()) {
    box.append(node("div", task.prompt, "msg user"));
    const card = node("div", null, "task");
    const head = node("div", null, "task-head");
    head.append(node("span", t(task.status), `badge b-${task.status}`), node("small", task.created));
    card.append(head);

    if (task.status === "running") {
      card.append(node("div", t("Running… You'll get a notification, you can close the app."), "muted"));
      card.append(button(t("Stop"), async () => { await api(`/agent/tasks/${task.id}/stop`, { method: "POST" }); loadTasks(); }, "danger"));
    } else if (task.status === "waiting" && task.pending) {
      card.append(node("div", t("Hermes asks approval for:"), "muted"));
      card.append(node("pre", describe(task.pending), "mono"));
      const btns = node("div", null, "btn-row");
      for (const ch of choicesOf(task.pending)) {
        btns.append(button(ch === "deny" ? t("Reject") : ch === "once" ? t("Allow once") : ch, async () => {
          await api(`/agent/tasks/${task.id}/answer`, { method: "POST", body: { choice: ch } });
          loadTasks();
        }, ch === "deny" ? "danger" : "ok"));
      }
      card.append(btns);
    } else {
      const out = node("div", task.output || t("(no output)"), "task-out");
      card.append(out);
      if ((task.output || "").length > 600) {
        out.classList.add("clamp");
        const more = node("button", t("Show more"), "more");
        more.onclick = () => { out.classList.toggle("clamp"); more.textContent = out.classList.contains("clamp") ? t("Show more") : t("Show less"); };
        card.append(more);
      }
    }
    box.append(card);
  }
  box.scrollTop = box.scrollHeight;
}

async function loadTasks() {
  clearTimeout(taskTimer);
  if (!hermesSession) { renderTasks([]); return; }
  try {
    const list = await api(`/agent/tasks?session_id=${encodeURIComponent(hermesSession)}`);
    renderTasks(list);
    const busy = list.some((t) => t.status === "running" || t.status === "waiting");
    el("dev-dot").classList.toggle("hidden", !list.some((t) => t.status === "waiting"));
    // Poll every 5 s while a task runs and the tab is open
    if (busy && tab === "dev" && !document.hidden) taskTimer = setTimeout(loadTasks, 5000);
  } catch (e) {
    toast(e.message);
  }
}

const taskInput = el("task-input");
autoGrow(taskInput);
enterSends(taskInput, el("task-form"));

async function sendTask(prompt) {
  const btn = el("task-form").querySelector("button");
  btn.disabled = true;
  try {
    const r = await api("/agent/tasks", { method: "POST", body: { prompt, session_id: hermesSession || null } });
    hermesSession = r.session_id;
    localStorage.setItem("hermesSession", hermesSession);
    await loadTasks();
  } catch (e) {
    toast(e.message);
  } finally {
    btn.disabled = false;
  }
}

el("task-form").onsubmit = (e) => {
  e.preventDefault();
  const p = taskInput.value.trim();
  if (!p) return;
  taskInput.value = "";
  taskInput.style.height = "auto";
  sendTask(p);
};
for (const c of document.querySelectorAll("[data-task]")) c.onclick = () => sendTask(c.dataset.task);

// --- Dev: Status ---

async function loadDevStatus() {
  try {
    const s = await api("/dev/status");
    const st = el("hermes-state");
    st.textContent = t(!s.hermes.enabled ? "HERMES_API_KEY missing in .env" : "Hermes is down. Restart the server or check Hermes.");
    st.classList.toggle("hidden", s.hermes.enabled && s.hermes.up);
    el("dev-changes").textContent = s.changes || t("No changes");
  } catch (e) {
    el("dev-changes").textContent = e.message;
  }
}

el("show-diff").onclick = async () => {
  const d = el("dev-diff");
  if (!d.classList.contains("hidden")) return d.classList.add("hidden");
  try {
    d.textContent = (await api("/agent/diff")).diff || t("Empty diff");
    d.classList.remove("hidden");
  } catch (e) { toast(e.message); }
};

function loadDev() {
  loadDevStatus();
  if (devSeg === "agent") loadTasks();
}

// --- Model (Hermes' model; chat, cron and Dev all use it) ---

let modelInfo = null;
const MODEL_HINTS = {
  gemini: "gemini-3.1-flash-lite",
  anthropic: "claude-sonnet-5-5",
  openrouter: "provider/model-name",
  custom: "llama-3.3-70b-versatile",
};

function updateModelForm() {
  const p = el("m-provider").value;
  const info = modelInfo?.providers.find((x) => x.id === p);
  el("m-base").classList.toggle("hidden", p !== "custom");
  el("m-base").required = p === "custom";
  el("m-model").placeholder = MODEL_HINTS[p] || t("Model name");
  el("m-key").placeholder = info?.key_set ? t("Key saved ✓ (type to replace)") : t("API key");
}

function renderModel(m) {
  modelInfo = m;
  const label = m.providers.find((x) => x.id === m.provider)?.label || m.provider;
  el("model-pill").textContent = m.model || t("no model");
  el("model-pill").classList.toggle("hidden", tab !== "chat");
  el("model-now").textContent = `${label} · ${m.model}`;
  const sel = el("m-provider");
  sel.replaceChildren(...m.providers.map((x) => {
    const o = node("option", x.label + (x.key_set ? " ✓" : ""));
    o.value = x.id;
    return o;
  }));
  sel.value = m.provider;
  el("m-model").value = m.model;
  el("m-base").value = m.base_url || "";
  updateModelForm();
}

async function loadModel() {
  try { renderModel(await api("/hermes/model")); } catch (e) { el("model-now").textContent = e.message; }
}

el("m-provider").onchange = () => {
  updateModelForm();
  // A new provider most likely needs a new model name
  el("m-model").value = el("m-provider").value === modelInfo?.provider ? modelInfo.model : "";
};
el("model-pill").onclick = () => setTab("pc");

el("model-form").onsubmit = async (e) => {
  e.preventDefault();
  const provider = el("m-provider").value;
  const api_key = el("m-key").value.trim();
  if (!api_key && !modelInfo?.providers.find((x) => x.id === provider)?.key_set) {
    return toast(t("Enter an API key for this provider"));
  }
  const btn = el("model-form").querySelector("button");
  btn.disabled = true;
  btn.textContent = api_key ? t("Saving, Hermes restarts…") : t("Saving…");
  try {
    const m = await api("/hermes/model", {
      method: "POST",
      body: { provider, model: el("m-model").value.trim(), api_key, base_url: el("m-base").value.trim() },
    });
    el("m-key").value = "";
    renderModel(m);
    toast(`Model: ${m.model}`);
  } catch (e2) {
    toast(e2.message);
  } finally {
    btn.disabled = false;
    btn.textContent = t("Save");
  }
};

// --- PC ---

async function loadPc() {
  try {
    const lines = (await api("/pc/status")).text.split("\n");
    el("pc").replaceChildren(
      ...lines.map((l) => {
        const m = l.match(/^(\D+?)\s+([%\d].*)$/) || [null, l, ""];
        // "%75 (11.7 GB / 15.7 GB)" -> big "%75", small "11.7 GB / 15.7 GB" below
        const [, main, detail] = m[2].match(/^(\S+(?: GB)?)\s*[(/]?\s*(.*?)\)?$/) || [null, m[2], ""];
        const s = node("div", null, "stat");
        s.append(node("small", t(m[1])), node("b", main));
        if (detail) s.append(node("small", t(detail), "stat-sub"));
        return s;
      })
    );
  } catch (e) {
    el("pc").textContent = e.message;
  }
  try {
    const list = await api("/files");
    el("files").replaceChildren(
      ...(list.length
        ? list.map((f) => row(f.name, `${(f.size / 2 ** 20).toFixed(1)} MB · ${f.mtime}`, [
            button(t("Get"), () => download(f.name)),
            button(t("Delete"), () => runAction("delete_file", { name: f.name }, `${t("Delete")}: ${f.name}?`), "danger"),
          ]))
        : [node("span", t("Empty"), "muted")])
    );
  } catch (e) {
    el("files").textContent = e.message;
  }
}

async function download(name) {
  const r = await fetch(`/files/${encodeURIComponent(name)}`, { headers: auth() });
  if (!r.ok) throw new Error(`${t("Download failed")}: ${r.status}`);
  const a = node("a");
  a.href = URL.createObjectURL(await r.blob());
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 60000);
}

el("refresh-pc").onclick = loadPc;
el("cancel-shutdown").onclick = async () => {
  try { toast(t((await api("/pc/cancel-shutdown", { method: "POST" })).text)); } catch (e) { toast(e.message); }
};

// --- Push notifications ---

const b64ToBytes = (b64) => {
  const padded = (b64 + "=".repeat((4 - (b64.length % 4)) % 4)).replace(/-/g, "+").replace(/_/g, "/");
  return Uint8Array.from(atob(padded), (c) => c.charCodeAt(0));
};

async function pushSub() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window)) return null;
  return (await navigator.serviceWorker.ready).pushManager.getSubscription();
}

async function markBell() {
  el("bell").textContent = t((await pushSub()) ? "Test notification" : "Enable notifications");
}

el("bell").onclick = async () => {
  try {
    if (await pushSub()) {
      await api("/push/test", { method: "POST" });
      toast(t("Test notification sent"));
    } else {
      if (!("PushManager" in window)) throw new Error(t("No push here. Open the app from the home screen."));
      if ((await Notification.requestPermission()) !== "granted") throw new Error(t("Notification permission denied"));
      const reg = await navigator.serviceWorker.ready;
      const { key } = await api("/push/key");
      const sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToBytes(key) });
      await api("/push/subscribe", { method: "POST", body: sub.toJSON() });
      toast(t("Notifications on"));
    }
  } catch (e) {
    toast(e.message);
  }
  markBell();
};

el("lang").textContent = LANG === "tr" ? "English" : "Türkçe";
el("lang").onclick = () => {
  try { localStorage.setItem("lang", LANG === "tr" ? "en" : "tr"); } catch {}
  location.reload();
};

// --- Lifecycle ---

// Back from a notification: refresh approvals and the open tab.
document.addEventListener("visibilitychange", () => {
  if (document.hidden || !token) return;
  refreshApprovals();
  if (tab !== "chat") setTab(tab);
});
setInterval(() => { if (!document.hidden) refreshApprovals(); }, 15000);

fetch("/health").then((r) => r.json()).then((h) => {
  pcControl = Boolean(h.pc);
  el("pc-section").classList.toggle("hidden", !pcControl);
  if (pcControl && tab === "pc") loadPc();
}).catch(() => {});
show(Boolean(token));
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").then(markBell);
