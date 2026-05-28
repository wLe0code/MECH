/* MECH Control Panel — lógica del frontend.
 *
 * Se comunica con el backend (FastAPI) vía:
 *   - REST  para acciones (POST /api/...).
 *   - WebSocket /ws para estado en vivo + eventos.
 *
 * Detecta automáticamente la URL del servidor: misma host que sirvió la
 * página. Si abres este HTML como archivo suelto (file://), funciona
 * en "modo demo" sin servidor.
 */

(() => {
  'use strict';

  // ─── Config / detección de servidor ───────────────────────────────
  const isFile = location.protocol === 'file:';
  const HTTP_BASE = isFile ? '' : `${location.protocol}//${location.host}`;
  const WS_URL    = isFile ? null : `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`;

  // ─── Estado local ─────────────────────────────────────────────────
  const state = {
    ws: null,
    wsConnected: false,
    voiceLoopActive: false,
    waveInterval: null,
    immAnim: null,
    backend: {},   // estado replicado del backend
  };

  // ─── Helpers ──────────────────────────────────────────────────────
  const $ = (id) => document.getElementById(id);

  function log(msg, level = 'info') {
    const list = $('log-list');
    const el = document.createElement('div');
    el.className = 'log-item';
    const t = new Date().toTimeString().split(' ')[0].substring(3);
    el.innerHTML = `<span class="log-time">${t}</span><span class="log-msg log-${level}">${escapeHTML(msg)}</span>`;
    list.prepend(el);
    while (list.children.length > 80) list.removeChild(list.lastChild);
  }

  function escapeHTML(s) {
    return String(s).replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  function addChat(msg, isUser) {
    const list = $('chat-list');
    const el = document.createElement('div');
    el.className = 'chat-bubble ' + (isUser ? 'chat-user' : 'chat-mech');
    el.textContent = msg;
    list.appendChild(el);
    list.scrollTop = list.scrollHeight;
  }

  function setSensor(id, text, cls) {
    const el = $(id);
    if (!el) return;
    el.textContent = text;
    el.className = 'sensor-val ' + cls;
  }

  async function fetchJSON(path, opts = {}) {
    try {
      const res = await fetch(HTTP_BASE + path, {
        method: opts.method || 'POST',
        headers: opts.json ? { 'Content-Type': 'application/json' } : undefined,
        body: opts.json ? JSON.stringify(opts.json) : opts.body,
      });
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      return await res.json();
    } catch (e) {
      log(`Error ${path}: ${e.message}`, 'err');
      return null;
    }
  }

  // ─── Reloj ────────────────────────────────────────────────────────
  setInterval(() => {
    $('clock').textContent = new Date().toTimeString().split(' ')[0];
  }, 1000);

  // ─── WebSocket ────────────────────────────────────────────────────
  function connectWS() {
    if (!WS_URL) {
      log('Modo standalone (file://) — sin servidor', 'warn');
      $('ws-badge-wrap').innerHTML =
        '<span class="ws-badge ws-disconnected"><i class="ti ti-wifi-off"></i>Sin servidor</span>';
      return;
    }

    state.ws = new WebSocket(WS_URL);

    state.ws.onopen = () => {
      state.wsConnected = true;
      log('Conectado al servidor MECH', 'ok');
      $('ws-badge-wrap').innerHTML =
        '<span class="ws-badge ws-connected"><i class="ti ti-wifi"></i>Servidor OK</span>';
      setSensor('sen-ws', 'CONECTADO', 'val-ok');
    };

    state.ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        handleServerMsg(msg);
      } catch (err) { /* ignore */ }
    };

    state.ws.onclose = () => {
      state.wsConnected = false;
      $('ws-badge-wrap').innerHTML =
        '<span class="ws-badge ws-disconnected"><i class="ti ti-wifi-off"></i>Reconectando…</span>';
      setSensor('sen-ws', 'DESCONECTADO', 'val-err');
      log('Servidor desconectado, reintentando en 3s', 'warn');
      setTimeout(connectWS, 3000);
    };

    state.ws.onerror = () => { /* onclose lo maneja */ };
  }

  function handleServerMsg(msg) {
    switch (msg.type) {
      case 'state':       applyState(msg.state); break;
      case 'log':         log(msg.message, msg.level || 'info'); break;
      case 'transcript':  showTranscript(msg.text); break;
      case 'ai_response': showAIResponse(msg.text, msg.segment, msg.total); break;
      case 'projector':   applyProjector(msg.id, msg.on, msg.file); break;
      case 'image':       applyAIImage(msg.url); break;
      case 'video':       applyAIVideo(msg.url); break;
      case 'pong':        break;
    }
  }

  function applyState(s) {
    state.backend = s;
    // Bucle de voz
    state.voiceLoopActive = !!s.voice_loop_active;
    $('voice-status').textContent = s.voice_listening
      ? '● Escuchando…'
      : (state.voiceLoopActive ? 'Bucle activo, esperando voz' : 'Bucle de voz apagado');
    $('voice-btn').classList.toggle('listening', !!s.voice_listening);
    $('dot-mic').className = s.voice_listening ? 'dot-active' : (state.voiceLoopActive ? 'dot-ok' : 'dot-off');
    setSensor('sen-mic', s.voice_listening ? 'ESCUCHANDO' : (state.voiceLoopActive ? 'EN ESPERA' : 'INACTIVO'),
              s.voice_listening ? 'val-active' : (state.voiceLoopActive ? 'val-ok' : 'val-off'));
    $('fw-voice').textContent = state.voiceLoopActive ? 'ACTIVO' : 'DETENIDO';
    if (s.voice_listening) startWaveAnim(); else stopWaveAnim();

    // Modo / firmware
    $('fw-mode').textContent = s.current_mode || 'IDLE';
    $('dot-fw').className = 'dot-ok';

    // Arduino
    $('dot-ard').className = s.arduino_connected ? 'dot-ok' : 'dot-off';
    $('fw-arduino').textContent = s.arduino_connected ? 'CONECTADO' : 'DESCONECTADO';
    setSensor('sen-ard', s.arduino_connected ? 'CONECTADO' : 'DESCONECTADO',
              s.arduino_connected ? 'val-ok' : 'val-off');

    // Proyectores
    for (const id of ['s1', 's2', 'imm']) {
      const p = s.projectors?.[id];
      if (p) applyProjector(id, p.on, p.file);
    }

    // Visual AI: video de biblioteca tiene prioridad sobre imagen generada.
    if (s.current_video) applyAIVideo(s.current_video);
    else if (s.current_image) applyAIImage(s.current_image);

    // Transcript / respuesta
    if (s.last_transcript) showTranscript(s.last_transcript);
    if (s.last_ai_response) showAIResponse(s.last_ai_response);
  }

  function showTranscript(text) {
    $('transcript').textContent = text;
    addChat(text, true);
  }

  function showAIResponse(text, segment, total) {
    const counter = (segment && total) ? ` <span style="color:var(--text-muted);font-size:10px">[${segment}/${total}]</span>` : '';
    $('ai-resp').innerHTML = `<div class="ai-label">MECH responde${counter}</div>${escapeHTML(text)}`;
    addChat(text, false);
  }

  function applyProjector(id, on, fileUrl) {
    const screen = $(`${id === 'imm' ? 'imm-demo' : id + '-screen'}`);
    if (!screen) return;

    if (!on || !fileUrl) {
      if (id === 'imm') return; // el inmersivo tiene su propio canvas
      screen.innerHTML = '<div class="screen-off-label">SIN SEÑAL</div>';
    } else {
      const isVideo = /\.(mp4|webm|mov|m4v)$/i.test(fileUrl);
      const url = isFile ? fileUrl : (fileUrl.startsWith('http') ? fileUrl : HTTP_BASE + fileUrl);
      if (id === 'imm') {
        cancelAnimationFrame(state.immAnim);
        screen.innerHTML = '';
        const el = document.createElement(isVideo ? 'video' : 'img');
        el.src = url;
        if (isVideo) { el.autoplay = el.loop = el.muted = true; }
        el.style.cssText = 'width:100%;height:100%;object-fit:cover;border-radius:12px';
        screen.appendChild(el);
      } else {
        screen.innerHTML = '';
        const el = document.createElement(isVideo ? 'video' : 'img');
        el.src = url;
        if (isVideo) { el.autoplay = el.loop = el.muted = true; }
        el.style.cssText = 'width:100%;height:100%;object-fit:contain';
        screen.appendChild(el);
      }
    }

    // Sensores
    const senId = id === 'imm' ? 'sen-imm' : 'sen-' + id;
    setSensor(senId, on ? 'ACTIVO' : 'APAGADO', on ? 'val-ok' : 'val-off');
  }

  function applyAIImage(url) {
    // La imagen que Claude+NanoBanana acaban de generar la mostramos
    // en el cuadro inmersivo del control panel (preview).
    if (!url) return;
    const fullUrl = url.startsWith('http') ? url : HTTP_BASE + url;
    const demo = $('imm-demo');
    cancelAnimationFrame(state.immAnim);
    demo.innerHTML = '';
    const img = document.createElement('img');
    img.src = fullUrl;
    img.style.cssText = 'width:100%;height:100%;object-fit:cover;border-radius:12px';
    demo.appendChild(img);
  }

  function applyAIVideo(url) {
    // Video pre-renderizado de la biblioteca (Opción B). Preview en el
    // cuadro inmersivo del panel, en loop y muteado para no chocar con TTS.
    if (!url) return;
    const fullUrl = url.startsWith('http') ? url : HTTP_BASE + url;
    const demo = $('imm-demo');
    cancelAnimationFrame(state.immAnim);
    demo.innerHTML = '';
    const vid = document.createElement('video');
    vid.src = fullUrl;
    vid.autoplay = true;
    vid.loop = true;
    vid.muted = true;
    vid.playsInline = true;
    vid.style.cssText = 'width:100%;height:100%;object-fit:cover;border-radius:12px';
    demo.appendChild(vid);
  }

  // ─── Animación de waveform ────────────────────────────────────────
  function startWaveAnim() {
    if (state.waveInterval) return;
    const bars = document.querySelectorAll('.wave-bar');
    bars.forEach(b => b.classList.add('active'));
    state.waveInterval = setInterval(() => {
      bars.forEach(b => b.style.height = (Math.random() * 22 + 4) + 'px');
    }, 120);
  }
  function stopWaveAnim() {
    if (!state.waveInterval) return;
    clearInterval(state.waveInterval);
    state.waveInterval = null;
    const bars = document.querySelectorAll('.wave-bar');
    const defaults = [8, 14, 20, 10, 18, 8, 24, 12, 16, 8];
    bars.forEach((b, i) => { b.classList.remove('active'); b.style.height = defaults[i] + 'px'; });
  }

  // ─── Animación canvas inmersivo (placeholder cuando no hay imagen) ─
  function initImmDemo() {
    const demo = $('imm-demo');
    if (demo.querySelector('video, img')) return;
    if (!$('imm-canvas')) {
      demo.innerHTML = '<canvas id="imm-canvas"></canvas><div class="immersive-overlay"><h2>ESPACIO INMERSIVO</h2><p>Esperando contenido…</p></div>';
    }
    const canvas = $('imm-canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = demo.offsetWidth || 700;
    canvas.height = demo.offsetHeight || 350;

    const pts = Array.from({ length: 90 }, () => ({
      x: Math.random() * canvas.width, y: Math.random() * canvas.height,
      r: Math.random() * 2 + 0.4,
      vx: (Math.random() - 0.5) * 0.6, vy: (Math.random() - 0.5) * 0.6,
      a: Math.random() * Math.PI * 2,
    }));
    let hue = 240;

    function draw() {
      state.immAnim = requestAnimationFrame(draw);
      ctx.fillStyle = 'rgba(5,5,20,0.18)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      hue = (hue + 0.25) % 360;
      pts.forEach(p => {
        p.x += p.vx; p.y += p.vy; p.a += 0.012;
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r * (1 + Math.sin(p.a) * 0.5), 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${hue + p.x / canvas.width * 80},80%,70%,0.85)`;
        ctx.fill();
      });
    }
    draw();
  }

  // ─── Acciones (UI → server) ───────────────────────────────────────
  const API = {
    async toggleVoiceLoop() {
      const path = state.voiceLoopActive ? '/api/voice/loop/off' : '/api/voice/loop/on';
      await fetchJSON(path);
    },

    async sendTextCommand() {
      const input = $('text-cmd');
      const text = input.value.trim();
      if (!text) return;
      input.value = '';
      await fetchJSON('/api/voice/text', { json: { text } });
    },

    testCmd(text) {
      $('text-cmd').value = text;
      this.sendTextCommand();
    },

    async uploadFile(id, inputEl) {
      const file = inputEl.files[0];
      if (!file) return;
      const fd = new FormData();
      fd.append('file', file);
      log(`Subiendo ${file.name} (${(file.size / 1024 / 1024).toFixed(1)} MB) a ${id}…`, 'info');
      const res = await fetch(HTTP_BASE + `/api/projector/${id}/upload`, { method: 'POST', body: fd });
      if (res.ok) log(`Subida OK → ${id}`, 'ok');
      else        log(`Subida falló: ${res.status}`, 'err');
    },

    projectorOn(id)  { fetchJSON(`/api/projector/${id}/on`); },
    projectorOff(id) { fetchJSON(`/api/projector/${id}/off`); },

    arduinoMode(mode) { fetchJSON(`/api/arduino/mode/${mode}`); },

    move(vx, vy, w) { fetchJSON('/api/arduino/move', { json: { vx, vy, w } }); },
    stopMove() { this.move(0, 0, 0); },

    headLive() {
      const pan = parseInt($('head-pan').value);
      const tilt = parseInt($('head-tilt').value);
      $('head-pan-val').textContent = pan + '°';
      $('head-tilt-val').textContent = tilt + '°';
      fetchJSON('/api/arduino/head', { json: { pan, tilt } });
    },

    armLive(side) {
      const id = side === 'L' ? 'arm-l' : 'arm-r';
      const angle = parseInt($(id).value);
      $(`${id}-val`).textContent = angle + '°';
      fetchJSON('/api/arduino/arm', { json: { side, angle } });
    },

    sendRaw() {
      const cmd = $('raw-cmd').value.trim();
      if (!cmd) return;
      fetchJSON('/api/arduino/raw', { json: { cmd } });
      $('raw-cmd').value = '';
    },

    async emergencyStop() {
      log('▶ PARO DE EMERGENCIA disparado desde el panel', 'err');
      await fetchJSON('/api/emergency/stop');
    },
  };

  // ─── Navegación ───────────────────────────────────────────────────
  const UI = {
    showView(name, navEl) {
      document.querySelectorAll('.view').forEach(v => v.classList.remove('visible'));
      document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
      $('view-' + name).classList.add('visible');
      if (navEl) navEl.classList.add('active');
      else {
        const nav = document.querySelector(`[data-view="${name}"]`);
        if (nav) nav.classList.add('active');
      }
    }
  };

  // ─── Atajos de teclado ────────────────────────────────────────────
  document.addEventListener('keydown', (e) => {
    // Si está escribiendo en un input, ignorar atajos.
    if (e.target.matches('input, textarea')) return;

    if (e.code === 'Space') {
      e.preventDefault();
      API.emergencyStop();
    } else if (e.key === 'v' || e.key === 'V') {
      API.toggleVoiceLoop();
    } else if (e.key === '1') {
      UI.showView('voice');
    } else if (e.key === '2') {
      UI.showView('stand');
    } else if (e.key === '3') {
      UI.showView('immersive');
    }
  });

  // ─── Botón de paro de emergencia ──────────────────────────────────
  $('emergency-btn').addEventListener('click', () => API.emergencyStop());

  // ─── Exponer al global para los onclick inline ────────────────────
  window.API = API;
  window.UI = UI;

  // ─── Init ─────────────────────────────────────────────────────────
  log('Panel MECH cargado', 'ok');
  connectWS();
  setTimeout(initImmDemo, 600);

  // PWA service worker registration (opcional, mejora "instalable")
  if ('serviceWorker' in navigator && !isFile) {
    navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(() => {});
  }
})();
