const CACHE_NAME = "yukinavi-v32";
const CORE_ASSETS = ["./", "./index.html", "./manifest.json", "./icons/icon-192.png", "./icons/icon-512.png", "./data/resorts_all.json", "./data/resorts.json", "./vendor/leaflet/leaflet.min.js", "./vendor/leaflet/leaflet.min.css", "./photos/sea-of-clouds.webp"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(CORE_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  // 天気APIなど外部データは常にネットワークから取得し、キャッシュしない
  if (url.origin !== self.location.origin) return;

  // HTMLとデータは更新を即反映させたいのでネットワーク優先、オフライン時のみキャッシュ
  const networkFirst = event.request.mode === "navigate" || url.pathname.endsWith(".html") || url.pathname.endsWith(".json");
  if (networkFirst) {
    event.respondWith(
      fetch(event.request).then((response) => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        return response;
      }).catch(() => caches.match(event.request))
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => {
      return (
        cached ||
        fetch(event.request).then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          return response;
        }).catch(() => cached)
      );
    })
  );
});
