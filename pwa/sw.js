const CACHE = "mhp-v13";
const SHELL = ["/", "/app.js", "/style.css", "/manifest.json", "/icon-192.png"];
const API = ["/chat", "/approvals", "/health", "/push", "/pc", "/files", "/dev", "/agent", "/hermes"];
// Push titles come in English; Turkish phones get them translated.
// ponytail: follows the phone language, not the in-app language switch (SW can't read localStorage).
const TR = navigator.language.startsWith("tr") && {
  "Reminder": "Hatırlatma", "Hermes done": "Hermes bitti", "Hermes needs approval": "Hermes onay istiyor",
  "Hermes job failed: ": "Hermes işi başarısız: ", "Test notification works.": "Test bildirimi çalışıyor.",
};
const tr = (s) => {
  if (!TR || !s) return s;
  const k = Object.keys(TR).find((k) => s === k || (k.endsWith(": ") && s.startsWith(k)));
  return k ? TR[k] + s.slice(k.length) : s;
};

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  // API calls are never cached: a stale answer is a wrong answer.
  if (e.request.method !== "GET" || API.some((p) => url.pathname.startsWith(p))) return;
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request).then((r) => r || caches.match("/")))
  );
});

self.addEventListener("push", (e) => {
  let d = {};
  try {
    d = e.data ? e.data.json() : {};
  } catch {
    d = { body: e.data ? e.data.text() : "" };
  }
  e.waitUntil(
    self.registration.showNotification(tr(d.title) || "Hermes", {
      body: tr(d.body) || "",
      icon: "/icon-192.png",
      badge: "/icon-192.png",
      data: { url: d.url || "/" },
    })
  );
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const target = (e.notification.data && e.notification.data.url) || "/";
  e.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
      // Reuse an open window instead of opening a new one.
      for (const w of list) if ("focus" in w) return w.focus();
      return self.clients.openWindow(target);
    })
  );
});
