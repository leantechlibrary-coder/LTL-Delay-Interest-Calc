/* 遅延損害金計算機 Service Worker
 * 方針: ネットワーク優先・キャッシュフォールバック
 *   - オンライン時は常に最新版を取得（古い計算ロジックを静かに使い続けない）
 *   - オフライン時はキャッシュ済みの版で動作
 * 更新手順: アプリを更新したら下の CACHE_VERSION を必ず上げること。
 */
const CACHE_VERSION = "entai-calc-v1.4.0";

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
        // 正常に取得できたときだけキャッシュを更新する
        // （404 や一時的なエラーページで、動いているキャッシュを上書きしない）
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE_VERSION).then((cache) => cache.put(req, copy));
        }
        return res;
      })
      .catch(() =>
        caches.match(req).then((hit) => {
          if (hit) return hit;
          // 画面遷移のときだけ index.html で代替する（JS や画像の代わりに HTML を返さない）
          if (req.mode === "navigate") return caches.match("./index.html");
          return Response.error();
        })
      )
  );
});
