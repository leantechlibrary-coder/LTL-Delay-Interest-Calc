/* 遅延損害金計算機 Service Worker
 * 方針: ネットワーク優先・キャッシュフォールバック
 *   - オンライン時は常に最新版を取得（古い計算ロジックを静かに使い続けない）
 *   - オフライン時はキャッシュ済みの版で動作
 * 更新手順: アプリを更新したら下の CACHE_VERSION を必ず上げること。
 */
const CACHE_VERSION = "entai-calc-v1.3.0";

const ASSETS = [
  "./",
  "./index.html",
  "./calc.js",
  "./app.js",
  "./manifest.webmanifest",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/icon-maskable-512.png",
  "./icons/apple-touch-icon.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // 外部リンク（GitHub等）は素通し

  event.respondWith(
    fetch(req)
      .then((res) => {
        // 取得成功 → キャッシュを更新してから返す
        const copy = res.clone();
        caches.open(CACHE_VERSION).then((cache) => cache.put(req, copy));
        return res;
      })
      .catch(() =>
        caches.match(req).then((hit) => hit || caches.match("./index.html"))
      )
  );
});
