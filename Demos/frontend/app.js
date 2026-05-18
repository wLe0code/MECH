/* MECH Control Panel — lógica del frontend.
 *
 * Tiene dos modos:
 *  - Servido (http://...): se conecta al backend FastAPI por WebSocket
 *    y todos los botones disparan comandos reales contra el robot.
 *  - Standalone (file://): modo demo. Los botones simulan acciones
 *    localmente para que puedas probar la UI sin servidor.
 */

(() => {
  'use strict';

  // ─── Detección de modo ────────────────────────────────────────────
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
    files: { s1: null, s2: null, imm: null }, // {url, isVideo} cargados localmente
    proj:  { s1: false, s2: false, imm: false },
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
    if (isFile) return null; // modo demo: no hace fetch
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
      log('Modo demo (file://) — botones simulan acciones localmente', 'warn');
      $('ws-badge-wrap').innerHTML =
        '<span class="ws-badge ws-disconnected"><i class="ti ti-wifi-off"></i>Modo demo</span>';
      $('dot-fw').className = 'dot-active';
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
      try { handleServerMsg(JSON.parse(e.data)); } catch (err) { /* ignore */ }
    };

    state.ws.onclose = () => {
      state.wsConnected = false;
      $('ws-badge-wrap').innerHTML =
        '<span class="ws-badge ws-disconnected"><i class="ti ti-wifi-off"></i>Reconectando…</span>';
      setSensor('sen-ws', 'DESCONECTADO', 'val-err');
      log('Servidor desconectado, reintentando en 3s', 'warn');
      setTimeout(connectWS, 3000);
    };

    state.ws.onerror = () => {};
  }

  function handleServerMsg(msg) {
    switch (msg.type) {
      case 'state':       applyState(msg.state); break;
      case 'log':         log(msg.message, msg.level || 'info'); break;
      case 'transcript':  showTranscript(msg.text); break;
      case 'ai_response': showAIResponse(msg.text, msg.segment, msg.total); break;
      case 'projector':   applyProjector(msg.id, msg.on, msg.file); break;
      case 'image':       applyAIImage(msg.url); break;
    }
  }

  function applyState(s) {
    state.voiceLoopActive = !!s.voice_loop_active;
    $('voice-status').textContent = s.voice_listening
      ? '● Escuchando…'
      : (state.voiceLoopActive ? 'Bucle activo, esperando voz' : 'Bucle de voz apagado');
    $('voice-btn').classList.toggle('listening', !!s.voice_listening);
    $('dot-mic').className = s.voice_listening ? 'dot-active' : (state.voiceLoopActive ? 'dot-ok' : 'dot-off');
    $('fw-voice').textContent = state.voiceLoopActive ? 'ACTIVO' : 'DETENIDO';
    if (s.voice_listening) startWaveAnim(); else stopWaveAnim();
    $('fw-mode').textContent = s.current_mode || 'IDLE';
    $('dot-fw').className = 'dot-ok';
    $('dot-ard').className = s.arduino_connected ? 'dot-ok' : 'dot-off';
    $('fw-arduino').textContent = s.arduino_connected ? 'CONECTADO' : 'DESCONECTADO';
    setSensor('sen-ard', s.arduino_connected ? 'CONECTADO' : 'DESCONECTADO',
              s.arduino_connected ? 'val-ok' : 'val-off');
    for (const id of ['s1', 's2', 'imm']) {
      const p = s.projectors?.[id];
      if (p) applyProjector(id, p.on, p.file);
    }
    if (s.current_image) applyAIImage(s.current_image);
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
    state.proj[id] = on;
    const screen = $(id === 'imm' ? 'imm-demo' : id + '-screen');
    if (!screen) return;

    if (!on || !fileUrl) {
      if (id !== 'imm') {
        screen.innerHTML = '<div class="screen-off-label">SIN SEÑAL</div>';
      }
    } else {
      const isVideo = /\.(mp4|webm|mov|m4v)$/i.test(fileUrl) || (state.files[id]?.isVideo);
      const url = isFile ? fileUrl : (fileUrl.startsWith('http') ? fileUrl : HTTP_BASE + fileUrl);
      screen.innerHTML = '';
      const el = document.createElement(isVideo ? 'video' : 'img');
      el.src = url;
      if (isVideo) { el.autoplay = el.loop = el.muted = true; }
      const cover = id === 'imm' ? 'cover' : 'contain';
      el.style.cssText = `width:100%;height:100%;object-fit:${cover};border-radius:12px`;
      screen.appendChild(el);
    }

    const senId = id === 'imm' ? 'sen-imm' : 'sen-' + id;
    setSensor(senId, on ? 'ACTIVO' : 'APAGADO', on ? 'val-ok' : 'val-off');
  }

  function applyAIImage(url) {
    if (!url) return;
    const fullUrl = url.startsWith('http') || url.startsWith('blob:') ? url : HTTP_BASE + url;
    const demo = $('imm-demo');
    cancelAnimationFrame(state.immAnim);
    demo.innerHTML = '';
    const img = document.createElement('img');
    img.src = fullUrl;
    img.style.cssText = 'width:100%;height:100%;object-fit:cover;border-radius:12px';
    demo.appendChild(img);
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

  // ─── Canvas inmersivo (placeholder) ───────────────────────────────
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

  // ─── Respuestas locales (modo demo) ───────────────────────────────
  function demoReply(text) {
    const lower = text.toLowerCase();
    if (lower.includes('romeo') || lower.includes('julieta'))
      return 'En la bella Verona, dos familias rivales se odiaban a muerte. Romeo, hijo de los Montesco, conocería a Julieta en un baile prohibido…';
    if (lower.includes('shrek'))
      return 'Hace mucho tiempo, en un pantano lejano, vivía un ogro verde llamado Shrek que solo deseaba estar solo. Pero su tranquilidad se vería interrumpida…';
    if (lower.includes('odisea') || lower.includes('homero'))
      return 'Tras la guerra de Troya, Odiseo emprende un viaje de diez años para regresar a Ítaca. Cíclopes, sirenas y dioses caprichosos pondrán a prueba su astucia.';
    if (lower.includes('quijote'))
      return 'En un lugar de la Mancha, vivía un hidalgo flaco que de tanto leer libros de caballería decidió convertirse él mismo en caballero andante.';
    if (lower.includes('saluda') || lower.includes('hola'))
      return '¡Hola! Soy MECH, encantado de conocerte. Pregúntame sobre obras culturales o sobre cómo estoy construido.';
    if (lower.includes('qué eres') || lower.includes('cómo funciona'))
      return 'Soy un robot interactivo para la WRO 2026. Combino voz, proyección inmersiva y movimiento para narrar obras culturales.';
    return 'Entendido. (Modo demo — la respuesta real la genera Claude.)';
  }

  // ─── Acciones ─────────────────────────────────────────────────────
  const API = {
    async toggleVoiceLoop() {
      if (isFile) {
        // demo: alternar localmente
        state.voiceLoopActive = !state.voiceLoopActive;
        applyState({
          voice_loop_active: state.voiceLoopActive,
          voice_listening: state.voiceLoopActive,
          current_mode: state.voiceLoopActive ? 'LISTEN' : 'IDLE',
          arduino_connected: false,
          projectors: { s1: { on: state.proj.s1, file: state.files.s1?.url },
                        s2: { on: state.proj.s2, file: state.files.s2?.url },
                        imm:{ on: state.proj.imm, file: state.files.imm?.url } },
        });
        log(`Bucle de voz: ${state.voiceLoopActive ? 'ON' : 'OFF'} (demo)`, 'info');
        return;
      }
      await fetchJSON(state.voiceLoopActive ? '/api/voice/loop/off' : '/api/voice/loop/on');
    },

    async sendTextCommand() {
      const input = $('text-cmd');
      const text = input.value.trim();
      if (!text) return;
      input.value = '';

      if (isFile) {
        showTranscript(text);
        log(`Voz simulada: ${text}`, 'info');
        setTimeout(() => showAIResponse(demoReply(text)), 500);
        // Si menciona una obra, también muestra una "imagen" placeholder
        if (/romeo|shrek|odisea|quijote/i.test(text)) {
          // Color random representando "imagen generada"
          const canvas = document.createElement('canvas');
          canvas.width = 800; canvas.height = 450;
          const ctx = canvas.getContext('2d');
          const grad = ctx.createLinearGradient(0,0,800,450);
          const hue = Math.floor(Math.random()*360);
          grad.addColorStop(0, `hsl(${hue},60%,30%)`);
          grad.addColorStop(1, `hsl(${(hue+60)%360},60%,15%)`);
          ctx.fillStyle = grad; ctx.fillRect(0,0,800,450);
          ctx.fillStyle = 'white'; ctx.font='bold 48px serif'; ctx.textAlign='center';
          ctx.fillText('[ Escena generada ]', 400, 225);
          applyAIImage(canvas.toDataURL());
        }
        return;
      }
      await fetchJSON('/api/voice/text', { json: { text } });
    },

    testCmd(text) {
      $('text-cmd').value = text;
      this.sendTextCommand();
    },

    async uploadFile(id, inputEl) {
      const file = inputEl.files[0];
      if (!file) return;
      log(`Archivo ${file.name} (${(file.size/1024/1024).toFixed(1)} MB) → ${id}`, 'info');

      if (isFile) {
        // demo: cargar localmente y mostrar
        const url = URL.createObjectURL(file);
        state.files[id] = { url, isVideo: file.type.includes('video') };
        log(`Cargado localmente (demo). Pulsa "Encender" para mostrarlo.`, 'ok');
        return;
      }
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch(HTTP_BASE + `/api/projector/${id}/upload`, { method: 'POST', body: fd });
      log(res.ok ? `Subida OK → ${id}` : `Subida falló: ${res.status}`, res.ok ? 'ok' : 'err');
    },

    projectorOn(id) {
      if (isFile) {
        const f = state.files[id];
        if (!f) { log(`Proyector ${id}: sube un archivo primero`, 'warn'); return; }
        applyProjector(id, true, f.url);
        log(`Proyector ${id}: ON (demo)`, 'ok');
        return;
      }
      fetchJSON(`/api/projector/${id}/on`);
    },

    projectorOff(id) {
      if (isFile) {
        applyProjector(id, false, null);
        log(`Proyector ${id}: OFF (demo)`, 'info');
        return;
      }
      fetchJSON(`/api/projector/${id}/off`);
    },

    arduinoMode(mode) {
      log(`Arduino MODE:${mode}`, 'info');
      $('fw-mode').textContent = mode;
      if (!isFile) fetchJSON(`/api/arduino/mode/${mode}`);
    },

    move(vx, vy, w) {
      log(`MOVE:${vx}:${vy}:${w}`, 'info');
      if (!isFile) fetchJSON('/api/arduino/move', { json: { vx, vy, w } });
    },
    stopMove() { this.move(0, 0, 0); },

    headLive() {
      const pan = parseInt($('head-pan').value);
      const tilt = parseInt($('head-tilt').value);
      $('head-pan-val').textContent = pan + '°';
      $('head-tilt-val').textContent = tilt + '°';
      if (!isFile) fetchJSON('/api/arduino/head', { json: { pan, tilt } });
    },

    armLive(side) {
      const id = side === 'L' ? 'arm-l' : 'arm-r';
      const angle = parseInt($(id).value);
      $(`${id}-val`).textContent = angle + '°';
      if (!isFile) fetchJSON('/api/arduino/arm', { json: { side, angle } });
    },

    sendRaw() {
      const cmd = $('raw-cmd').value.trim();
      if (!cmd) return;
      log(`Raw → ${cmd}`, 'info');
      if (!isFile) fetchJSON('/api/arduino/raw', { json: { cmd } });
      $('raw-cmd').value = '';
    },

    emergencyStop() {
      log('▶ PARO DE EMERGENCIA disparado', 'err');
      // Reset visual local
      ['s1','s2','imm'].forEach(id => applyProjector(id, false, null));
      $('fw-mode').textContent = 'STOP';
      state.voiceLoopActive = false;
      $('voice-status').textContent = 'Bucle de voz apagado';
      $('voice-btn').classList.remove('listening');
      $('dot-mic').className = 'dot-off';
      stopWaveAnim();
      setTimeout(initImmDemo, 100); // restaura el canvas en inmersivo
      if (!isFile) fetchJSON('/api/emergency/stop');
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
    if (e.target.matches('input, textarea')) return;

    if (e.code === 'Space') {
      e.preventDefault();
      API.emergencyStop();
    } else if (e.key === 'v' || e.key === 'V') {
      API.toggleVoiceLoop();
    } else if (e.key === '1') UI.showView('voice');
      else if (e.key === '2') UI.showView('stand');
      else if (e.key === '3') UI.showView('immersive');
  });

  $('emergency-btn').addEventListener('click', () => API.emergencyStop());

  // Exponer al global para los onclick inline.
  window.API = API;
  window.UI = UI;

  // ─── Init ─────────────────────────────────────────────────────────
  log('Panel MECH cargado', 'ok');
  connectWS();
  setTimeout(initImmDemo, 600);
})();
