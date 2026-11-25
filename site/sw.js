// Service worker: makes the site installable and lets it open offline.
// Strategy: network first for everything (so online visitors always get the
// latest data), saving each successful response; when the network fails, answer
// from that saved copy. Pages and data loaded once are therefore available offline.
const CACHE = "job-watcher-v1";
const SHELL = [
  "./", "index.html", "browse.html", "market.html", "style.css", "common.js",
  "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png", "icons/maskable-512.png",
  "data/status.json", "data/history.csv",
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE)
      .then(cache => Promise.all(SHELL.map(url => cache.add(new Request(url, { cache: "reload" })).catch(() => {}))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", event => {
  const req = event.request;
  if (req.method !== "GET" || new URL(req.url).origin !== self.location.origin) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    try {
      const fresh = await fetch(req, { cache: "no-cache" });
      if (fresh.ok) cache.put(req, fresh.clone());
      return fresh;
    } catch (err) {
      const saved = await cache.match(req, { ignoreSearch: true });
      if (saved) return saved;
      if (req.mode === "navigate") {
        const home = await cache.match("index.html");
        if (home) return home;
      }
      throw err;
    }
  })());
});
