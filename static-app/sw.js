// Service Worker for 第二種電気工事士 CBT練習
// キャッシュ名を変更するとインストール時に全キャッシュが再取得される
const CACHE_NAME = 'denki2-cbt-v1';

const APP_SHELL = [
  './',
  './index.html',
  './app.js',
  './style.css',
  './questions.js',
  './manifest.json',
];

importScripts('./precache-manifest.js');

// --- install: アプリシェル + 全画像をキャッシュ ---
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(async cache => {
      // アプリシェルは必須（失敗したら install 失敗）
      await cache.addAll(APP_SHELL);
      // 画像はベストエフォート（失敗しても install は続行）
      await Promise.allSettled(
        PRECACHE_URLS.map(url =>
          cache.add(url).catch(err => console.warn('[SW] precache miss:', url, err))
        )
      );
    })
  );
  self.skipWaiting();
});

// --- activate: 古いキャッシュを削除 ---
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// --- fetch: cache-first ---
self.addEventListener('fetch', event => {
  // POSTなど GET 以外はスルー
  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(response => {
        // 正常レスポンスのみキャッシュに追加
        if (response && response.status === 200 && response.type !== 'opaqueredirect') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      }).catch(() => {
        // オフラインかつキャッシュなし → 何もできない
      });
    })
  );
});
