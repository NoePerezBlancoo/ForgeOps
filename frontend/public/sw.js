const CACHE_NAME = "forgeops-shell-v1.3.0";
const APP_SHELL = [
  "/offline",
  "/manifest.webmanifest",
  "/forgeops-icon.svg",
  "/forgeops-icon-192.png",
  "/forgeops-icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (
    request.method !== "GET" ||
    url.origin !== self.location.origin ||
    url.pathname.startsWith("/api/") ||
    url.pathname.startsWith("/control")
  ) {
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(
      (async () => {
        try {
          const response = await fetch(request);
          if (response.ok) {
            const copy = response.clone();
            const cache = await caches.open(CACHE_NAME);
            await cache.put(request, copy);
          }
          return response;
        } catch {
          return (await caches.match(request)) || (await caches.match("/offline")) || Response.error();
        }
      })(),
    );
    return;
  }

  if (url.pathname.startsWith("/_next/static/") || url.pathname.endsWith(".svg")) {
    event.respondWith(
      (async () => {
        const cached = await caches.match(request);
        if (cached) return cached;
        const response = await fetch(request);
        const cache = await caches.open(CACHE_NAME);
        await cache.put(request, response.clone());
        return response;
      })(),
    );
  }
});
