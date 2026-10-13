/* Orbit ERP service worker — offline shell, push notifications, deep links. */
const CACHE = "orbit-erp-v1";
const SHELL = [
  "/static/css/app.css",
  "/static/js/chart.umd.min.js",
  "/static/pwa/icon-192.png",
  "/static/pwa/icon-512.png",
  "/offline/",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) =>
      Promise.allSettled(SHELL.map((u) => c.add(u).catch(() => null)))
    ).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== self.location.origin) return;
  // API + media: network only (always fresh)
  if (url.pathname.startsWith("/c/") && url.pathname.includes("/api/")) return;
  if (url.pathname.startsWith("/media/")) return;
  // static: cache first
  if (url.pathname.startsWith("/static/")) {
    e.respondWith(
      caches.match(e.request).then(
        (hit) => hit || fetch(e.request).then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy));
          return res;
        })
      )
    );
    return;
  }
  // pages: network first, fall back to offline page
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        if (res.ok && e.request.mode === "navigate") {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy));
        }
        return res;
      })
      .catch(() => caches.match(e.request).then((hit) => hit || caches.match("/offline/")))
  );
});

/* ---- web push ---- */
self.addEventListener("push", (e) => {
  let data = {};
  try { data = e.data ? e.data.json() : {}; } catch (_) {}
  const title = data.title || "Orbit ERP";
  const options = {
    body: data.body || "",
    icon: "/static/pwa/icon-192.png",
    badge: "/static/pwa/icon-192.png",
    tag: data.tag || "orbit-erp",
    renotify: true,
    data: { url: data.url || "/" },
  };
  e.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || "/";
  e.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((wins) => {
      for (const w of wins) {
        if (w.url === new URL(url, self.location.origin).href) return w.focus();
      }
      return self.clients.openWindow(url);
    })
  );
});
