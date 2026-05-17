/* Service Worker mínimo para que MECH sea instalable como PWA.
 *
 * No cacheamos agresivamente porque el panel necesita comunicarse en
 * vivo con el servidor — un cache stale rompería el WebSocket.
 *
 * Solo respondemos a `install` y `fetch` (pass-through) para que
 * Chrome/Edge ofrezcan la opción "Instalar como aplicación".
 */

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  // Pass-through. La red es la fuente de verdad.
  event.respondWith(fetch(event.request).catch(() => {
    if (event.request.mode === 'navigate') {
      return new Response(
        '<html><body style="background:#0e0e12;color:#fff;font-family:sans-serif;padding:40px"><h1>MECH offline</h1><p>No hay conexión al servidor de la Raspberry Pi. Verifica que esté encendida y en la misma red.</p></body></html>',
        { headers: { 'Content-Type': 'text/html' } }
      );
    }
    return new Response('', { status: 503 });
  }));
});
