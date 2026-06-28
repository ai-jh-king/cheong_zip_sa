/* 청주집사 서비스워커 — 앱 셸 캐싱 + 오프라인 폴백 + 웹푸시 */
var VERSION = "v2";                         // 캐시 무효화 시 숫자만 올리면 됨
var SHELL_CACHE = "cj-shell-" + VERSION;
var OFFLINE_URL = "/offline.html";

/* 설치: 오프라인 페이지 + 앱 셸 진입(/)을 미리 캐시 (개별 실패해도 설치 진행) */
self.addEventListener("install", function (e) {
  e.waitUntil(
    caches.open(SHELL_CACHE).then(function (c) {
      return Promise.all([
        c.add(OFFLINE_URL).catch(function () {}),
        c.add("/").catch(function () {})
      ]);
    })
  );
  self.skipWaiting();
});

/* 활성화: 구버전 셸 캐시 정리 후 즉시 제어 */
self.addEventListener("activate", function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) { if (k !== SHELL_CACHE) return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

/* fetch 라우팅
   - navigate(페이지 이동): 네트워크 우선 → 캐시된 셸(/) → 오프라인 페이지
   - 정적 자산(/assets·/icons·manifest): 캐시 우선 + 백그라운드 갱신(stale-while-revalidate)
       · Vite 자산은 파일명에 해시가 있어 캐시 우선이 안전(새 빌드=새 파일명=새로 받음)
   - 그 외(=API 등): 가로채지 않음 → 항상 네트워크(시세 데이터 신선도 보장, 절대 캐시 안 함) */
self.addEventListener("fetch", function (event) {
  var req = event.request;
  if (req.method !== "GET") return;
  var url;
  try { url = new URL(req.url); } catch (e) { return; }
  if (url.origin !== self.location.origin) return;   // 타 오리진(별도 API 서버 등) 미개입

  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req).then(function (res) {
        var copy = res.clone();
        caches.open(SHELL_CACHE).then(function (c) { c.put("/", copy); });
        return res;
      }).catch(function () {
        return caches.match("/").then(function (m) { return m || caches.match(OFFLINE_URL); });
      })
    );
    return;
  }

  var p = url.pathname;
  var isShellAsset = p.indexOf("/assets/") === 0 || p.indexOf("/icons/") === 0 || p === "/manifest.webmanifest";
  if (!isShellAsset) return;                          // API 등은 네트워크 그대로

  event.respondWith(
    caches.open(SHELL_CACHE).then(function (c) {
      return c.match(req).then(function (hit) {
        var net = fetch(req).then(function (res) {
          if (res && res.status === 200) c.put(req, res.clone());
          return res;
        }).catch(function () { return hit; });
        return hit || net;                             // 캐시 있으면 즉시, 없으면 네트워크
      });
    })
  );
});

self.addEventListener("push", function (event) {
  var data = {};
  try { data = event.data ? event.data.json() : {}; }
  catch (e) { data = { body: event.data && event.data.text ? event.data.text() : "" }; }
  var title = data.title || "청주집사";
  var options = {
    body: data.body || "",
    tag: data.tag || "cheongju",
    renotify: true,
    data: { url: data.url || "/" }
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", function (event) {
  event.notification.close();
  var url = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(function (list) {
      for (var i = 0; i < list.length; i++) {
        var c = list[i];
        if ("focus" in c) { if (c.navigate) { try { c.navigate(url); } catch (e) {} } return c.focus(); }
      }
      if (self.clients.openWindow) return self.clients.openWindow(url);
    })
  );
});
