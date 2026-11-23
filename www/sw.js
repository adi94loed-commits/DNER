/* Offline-Speicher für die Web-App (iPhone & Browser). In der Android-App wird er nicht verwendet. */
const CACHE="doener-web-v4";
const CORE=["./","index.html","manifest.webmanifest","vendor/maplibre-gl.js","vendor/maplibre-gl.css",
  "fonts/bricolage-grotesque-latin-400-normal.woff2","fonts/bricolage-grotesque-latin-600-normal.woff2","fonts/bricolage-grotesque-latin-800-normal.woff2",
  "icons/icon-192.png","icons/apple-touch-icon.png"];
self.addEventListener("install",e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(CORE)).then(()=>self.skipWaiting()))});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
// Eigene Dateien: erst Netz (damit Updates ankommen), bei Funkloch aus dem Speicher. Fremde Server (Karte, OpenStreetMap) bleiben unberührt.
self.addEventListener("fetch",e=>{
  const u=new URL(e.request.url);
  if(e.request.method!=="GET"||u.origin!==self.location.origin)return;
  e.respondWith(fetch(e.request).then(r=>{if(r.ok){const cp=r.clone();caches.open(CACHE).then(c=>c.put(e.request,cp))}return r})
    .catch(()=>caches.match(e.request,{ignoreSearch:true}).then(m=>m||caches.match("index.html"))));
});
