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
      case 'image':       msg.url ? applyAIImage(msg.url) : clearImmersivePreview(); break;
      case 'video':       msg.url ? applyAIVideo(msg.url) : clearImmersivePreview(); break;
      case 'vision':      applyVision(msg); break;
      case 'facing':      applyFacing(msg.facing); break;
      case 'mic_level':   applyMicLevel(msg); break;
      case 'pong':        break;
    }
  }

  // ─── Orientación del robot (maniobra de 180°) ─────────────────────
  // "projection" = mirando a donde proyecta (su sitio de trabajo).
  // "outward"    = de espaldas, saludando al público.
  function applyFacing(facing) {
    const el = $('facing-val');
    if (!el) return;
    const outward = facing === 'outward';
    el.textContent = outward ? 'AFUERA (al público)' : 'la proyección';
    el.style.color = outward ? 'var(--amber)' : 'var(--text)';
  }

  // ─── Visión (cámara) ──────────────────────────────────────────────
  function applyVision(v) {
    state.backend.vision = v;
    let text, cls;
    if (!v.enabled)            { text = 'APAGADA'; cls = 'val-off'; }
    else if (!v.user_present)  { text = 'SIN USUARIO'; cls = 'val-ok'; }
    else {
      const d = v.distance != null ? `${v.distance.toFixed(1)} m` : '? m';
      const near = v.distance != null && v.distance <= (v.min_distance || 1.2) + 0.3;
      text = `USUARIO a ${d}`;
      cls = near ? 'val-active' : 'val-ok';
    }
    setSensor('sen-cam', text, cls);
    const st = $('vision-status');
    if (st) {
      if (!v.enabled) st.innerHTML = '<span style="color:var(--text-muted)">Cámara apagada</span>';
      else if (!v.user_present) st.innerHTML = '<span style="color:#5DCAA5">Cámara activa — sin usuario a la vista</span>';
      else st.innerHTML = `<span style="color:#5DCAA5">Usuario detectado a ${v.distance != null ? v.distance.toFixed(1) : '?'} m (x=${v.x})</span>`;
    }
  }

  // ─── Nivel de micrófono en vivo (barras de onda reales) ───────────
  function applyMicLevel(m) {
    const bars = document.querySelectorAll('.wave-bar');
    if (!bars.length) return;
    state.micLevelAt = Date.now();  // los niveles reales le ganan a la animación
    // Escala: el umbral de disparo ocupa ~la mitad de la barra.
    const ratio = m.threshold > 0 ? m.level / m.threshold : 0;
    bars.forEach((b) => {
      const jitter = 0.7 + Math.random() * 0.6;
      const h = Math.max(4, Math.min(28, ratio * 14 * jitter));
      b.style.height = h + 'px';
      b.classList.toggle('active', m.recording);
    });
  }

  // Mapa de fases del ciclo de voz → texto + estilo del banner grande.
  const PHASES = {
    off:          { cls: 'phase-off',     text: 'Bucle de voz apagado',     hint: 'Pulsa el micrófono o la tecla V para empezar' },
    dormant:      { cls: 'phase-dormant', text: '😴 MECH en reposo',         hint: "Di 'ok MECH' (español) o 'wake up MECH' (inglés)" },
    waiting:      { cls: 'phase-waiting', text: '🎤 PUEDES HABLAR',          hint: 'Dile al juez/usuario que hable AHORA' },
    listening:    { cls: 'phase-listen',  text: '● Grabando tu voz…',         hint: 'Te estoy escuchando, sigue hablando' },
    transcribing: { cls: 'phase-work',    text: 'Transcribiendo…',           hint: 'Convirtiendo la voz a texto' },
    thinking:     { cls: 'phase-work',    text: 'MECH está pensando…',        hint: 'Generando la respuesta con Claude' },
    speaking:     { cls: 'phase-speak',   text: '🔊 MECH está hablando…',     hint: "Di 'oye MECH' (o 'hey MECH') para interrumpirlo" },
  };

  function updateVoicePhase(phase) {
    const p = PHASES[phase] || PHASES.off;
    const banner = $('voice-phase-banner');
    banner.className = 'voice-phase-banner ' + p.cls;
    $('vpb-text').textContent = p.text;
    $('vpb-hint').textContent = p.hint;

    // Texto del hero de la vista Voz.
    $('voice-status').textContent = p.text;

    // Punto del header + sensor del micrófono.
    const micActive = phase === 'waiting' || phase === 'listening';
    $('dot-mic').className = micActive ? 'dot-active' : (state.voiceLoopActive ? 'dot-ok' : 'dot-off');
    const micLabel = { waiting: 'PUEDES HABLAR', listening: 'GRABANDO', transcribing: 'PROCESANDO',
                       thinking: 'PENSANDO', speaking: 'HABLANDO', dormant: 'EN REPOSO', off: 'INACTIVO' }[phase] || 'INACTIVO';
    setSensor('sen-mic', micLabel, micActive ? 'val-active' : (phase === 'off' ? 'val-off' : 'val-ok'));
  }

  // Marca qué idioma está activo en los chips de la vista Voz.
  function updateLanguage(code) {
    if (state.language === code) return;
    if (state.language) {
      log(code === 'en' ? 'MECH pasó a INGLÉS (wake up MECH).'
                        : 'MECH pasó a ESPAÑOL (ok MECH).', 'ok');
    }
    state.language = code;
    const es = $('lang-es'), en = $('lang-en');
    if (es) es.classList.toggle('active', code === 'es');
    if (en) en.classList.toggle('active', code === 'en');
  }

  function applyState(s) {
    state.backend = s;
    // Idioma activo (español por defecto; inglés solo con "wake up MECH").
    updateLanguage(s.language || 'es');
    // Bucle de voz
    state.voiceLoopActive = !!s.voice_loop_active;
    // Fase detallada: off|waiting|listening|transcribing|thinking|speaking.
    // Si el backend es viejo y no la manda, la derivamos de los bools.
    const phase = s.voice_phase || (
      s.voice_listening ? 'listening' : (state.voiceLoopActive ? 'waiting' : 'off')
    );
    updateVoicePhase(phase);

    $('voice-btn').classList.toggle('listening', phase === 'waiting' || phase === 'listening');
    $('fw-voice').textContent = state.voiceLoopActive
      ? (phase === 'dormant' ? 'EN REPOSO' : 'ACTIVO') : 'DETENIDO';
    if (phase === 'waiting' || phase === 'listening') startWaveAnim(); else stopWaveAnim();

    // Modo / firmware
    $('fw-mode').textContent = s.current_mode || 'IDLE';
    if (s.claude_model) $('fw-model').textContent = s.claude_model;
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

    // Visión
    if (s.vision) applyVision(s.vision);

    // Hacia dónde mira (maniobra de 180°)
    applyFacing(s.facing || 'projection');
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

  function clearImmersivePreview() {
    // Limpia el preview inmersivo del panel y vuelve a la animación idle.
    cancelAnimationFrame(state.immAnim);
    const demo = $('imm-demo');
    if (!demo) return;
    demo.innerHTML = '';
    initImmDemo();
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
      // Si están llegando niveles reales del micrófono, esos mandan.
      if (Date.now() - (state.micLevelAt || 0) < 600) return;
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

    async setLanguage(code) {
      const res = await fetchJSON(`/api/language/${code}`);
      if (res && res.ok) updateLanguage(res.language);
    },

    async interrupt() {
      const res = await fetchJSON('/api/voice/interrupt');
      if (res && res.ok) log('Narración interrumpida desde el panel.', 'ok');
      else if (res) log(res.reason || 'MECH no está narrando ahora.', 'warn');
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

    // ─── Maniobras (giro de 180°) ───────────────────────────────────
    async lookOutward() {
      const res = await fetchJSON('/api/move/outward');
      if (res && res.ok) log('Girando 180° para mirar hacia afuera…', 'ok');
      else if (res) log(res.reason || 'No pude girar ahora.', 'warn');
    },

    async backToProjection() {
      const res = await fetchJSON('/api/move/projection');
      if (res && res.ok) log('Volviendo a la posición de proyección…', 'ok');
      else if (res) log(res.reason || 'No pude girar ahora.', 'warn');
    },

    // ─── Playlist promo (marketing) ─────────────────────────────────
    async playMarketing() {
      const res = await fetchJSON('/api/marketing/play');
      if (res && res.ok) log(`Proyectando marketing (${res.items} archivos, con audio).`, 'ok');
      else if (res) log(res.reason || 'No se pudo proyectar.', 'warn');
    },

    async stopMarketing() {
      const res = await fetchJSON('/api/marketing/stop');
      if (res && res.ok) log('Proyección cortada.', 'ok');
      else if (res) log(res.reason || 'No hay nada proyectándose.', 'warn');
    },

    async greetNow() {
      const res = await fetchJSON('/api/move/greet');
      if (res && res.ok) log('Saludo disparado a mano.', 'ok');
      else if (res) log(res.reason || 'No pude saludar ahora.', 'warn');
    },

    move(vx, vy, w) { fetchJSON('/api/arduino/move', { json: { vx, vy, w } }); },
    stopMove() { this.move(0, 0, 0); },

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
      log(`Serial → ${cmd}`, 'info');
      $('raw-cmd').value = '';
    },

    // Manda un comando serial directo (botones de LED, etc.).
    sendRawCmd(cmd) {
      fetchJSON('/api/arduino/raw', { json: { cmd } });
      log(`Serial → ${cmd}`, 'info');
    },

    // Rellena el input de comando crudo con una plantilla (para editarla).
    rawPreset(cmd) {
      const input = $('raw-cmd');
      input.value = cmd;
      input.focus();
    },

    async emergencyStop() {
      log('▶ PARO DE EMERGENCIA disparado desde el panel', 'err');
      await fetchJSON('/api/emergency/stop');
    },

    // ─── Ajustes ────────────────────────────────────────────────────
    async ttsTest() {
      const text = $('tts-test-text').value.trim() || 'Prueba de sonido.';
      log('Probando voz (TTS)…', 'info');
      await fetchJSON('/api/tts/test', { json: { text } });
    },

    async loadSettings() {
      const cfg = await fetchJSON('/api/config', { method: 'GET' });
      if (!cfg) return;
      const L = cfg.live || {}, R = cfg.restart || {};
      // En vivo
      setSlider('set-vad', 'vad', L.VAD_AGGRESSIVENESS);
      setSlider('set-silence', 'silence', L.VAD_SILENCE_TIMEOUT);
      setSlider('set-energy', 'energy', L.VAD_ENERGY_FACTOR);
      setSlider('set-lead', 'lead', L.AUDIO_LEAD_SILENCE);
      setSlider('set-listen', 'listen', L.AUDIO_LISTEN_MAX_SECONDS);
      if ($('set-dryrun')) $('set-dryrun').checked = !!L.TTS_DRY_RUN;
      if ($('set-subs')) $('set-subs').checked = L.SUBTITLES_ENABLED !== false;
      if ($('set-interrupt')) $('set-interrupt').checked = L.VOICE_INTERRUPT_ENABLED !== false;
      setSlider('set-ienergy', 'ienergy', L.INTERRUPT_ENERGY_FACTOR);
      if ($('set-armmode')) $('set-armmode').value = L.ARM_GESTURE_MODE || 'full';
      if ($('set-wheels')) $('set-wheels').checked = !!L.GESTURE_WHEELS;
      if ($('set-narrmode')) $('set-narrmode').value = L.NARRATION_GESTURE_MODE || 'simple';
      setSlider('set-wave', 'wave', L.ARM_WAVE_SECONDS);
      setSlider('set-wavehigh', 'wavehigh', L.ARM_WAVE_HIGH);
      setSlider('set-waveswing', 'waveswing', L.ARM_WAVE_SWING);
      setSlider('set-waverep', 'waverep', L.ARM_WAVE_REPEATS);
      if ($('set-waveboth')) $('set-waveboth').checked = L.ARM_WAVE_BOTH !== false;
      setSlider('set-greetcd', 'greetcd', L.GREETING_COOLDOWN);
      // Calibración del giro de 180°
      setSlider('set-turnsec', 'turnsec', L.TURN_180_SECONDS);
      setSlider('set-turnvel', 'turnvel', L.TURN_180_SPEED);
      setSlider('set-latsec', 'latsec', L.TURN_LATERAL_SECONDS);
      setSlider('set-latvel', 'latvel', L.TURN_LATERAL_SPEED);
      setSlider('set-kick', 'kick', L.MOTOR_KICK_SECONDS);
      // Visión
      if ($('set-vision')) $('set-vision').checked = !!L.VISION_ENABLED;
      setSlider('set-dist', 'dist', L.VISION_MIN_DISTANCE);
      if ($('set-approach')) $('set-approach').checked = !!L.VISION_APPROACH;
      if ($('set-gate')) $('set-gate').checked = !!L.VISION_PROJECT_GATE;
      // Reinicio
      if ($('set-rate'))    $('set-rate').value = String(R.AUDIO_SAMPLE_RATE ?? 48000);
      if ($('set-whisper')) $('set-whisper').value = R.WHISPER_MODEL || 'base';
      if ($('set-voiceid')) $('set-voiceid').value = R.ELEVENLABS_VOICE_ID || '';
      await this.refreshDevices(R.AUDIO_INPUT_DEVICE);
    },

    async refreshDevices(current) {
      const data = await fetchJSON('/api/audio/devices', { method: 'GET' });
      const sel = $('set-device');
      if (!data || !sel) return;
      const cur = current !== undefined ? current : (data.current || '');
      sel.innerHTML = '<option value="">(por defecto del sistema)</option>';
      data.devices.forEach(d => {
        const opt = document.createElement('option');
        opt.value = d.name;
        opt.textContent = `[${d.index}] ${d.name} (${d.channels} in)`;
        sel.appendChild(opt);
      });
      sel.value = cur;
    },

    async saveLiveSettings() {
      const updates = {
        VAD_AGGRESSIVENESS: String(parseInt($('set-vad').value)),
        VAD_SILENCE_TIMEOUT: $('set-silence').value,
        VAD_ENERGY_FACTOR: $('set-energy').value,
        AUDIO_LEAD_SILENCE: $('set-lead').value,
        AUDIO_LISTEN_MAX_SECONDS: $('set-listen').value,
        TTS_DRY_RUN: $('set-dryrun').checked ? 'true' : 'false',
        SUBTITLES_ENABLED: $('set-subs').checked ? 'true' : 'false',
        VOICE_INTERRUPT_ENABLED: $('set-interrupt').checked ? 'true' : 'false',
        INTERRUPT_ENERGY_FACTOR: $('set-ienergy').value,
        ARM_GESTURE_MODE: $('set-armmode').value,
        GESTURE_WHEELS: $('set-wheels').checked ? 'true' : 'false',
        NARRATION_GESTURE_MODE: $('set-narrmode').value,
        ARM_WAVE_SECONDS: $('set-wave').value,
        ARM_WAVE_HIGH: String(parseInt($('set-wavehigh').value)),
        ARM_WAVE_SWING: String(parseInt($('set-waveswing').value)),
        ARM_WAVE_REPEATS: String(parseInt($('set-waverep').value)),
        ARM_WAVE_BOTH: $('set-waveboth').checked ? 'true' : 'false',
        GREETING_COOLDOWN: $('set-greetcd').value,
        TURN_180_SECONDS: $('set-turnsec').value,
        TURN_180_SPEED: String(parseInt($('set-turnvel').value)),
        TURN_LATERAL_SECONDS: $('set-latsec').value,
        TURN_LATERAL_SPEED: String(parseInt($('set-latvel').value)),
        MOTOR_KICK_SECONDS: $('set-kick').value,
        VISION_MIN_DISTANCE: $('set-dist').value,
        VISION_APPROACH: $('set-approach').checked ? 'true' : 'false',
        VISION_PROJECT_GATE: $('set-gate').checked ? 'true' : 'false',
      };
      const res = await fetchJSON('/api/config', { json: { updates } });
      if (res && res.ok) {
        log(`Ajustes aplicados en vivo: ${res.applied.join(', ')}`, 'ok');
        if ($('set-dryrun').checked) log('Modo ahorro ON: el TTS no gastará créditos', 'warn');
      }
    },

    async visionToggle(on) {
      const res = await fetchJSON(`/api/vision/${on ? 'on' : 'off'}`);
      if (!res || !res.ok) {
        // Falló (ej. falta opencv/mediapipe o la cámara no está): revertimos.
        if ($('set-vision')) $('set-vision').checked = false;
        log('No se pudo encender la visión. Revisa el log del servidor.', 'err');
        return;
      }
      log(on ? 'Visión encendida (cámara activa).' : 'Visión apagada.', on ? 'ok' : 'info');
    },

    async arduinoReconnect() {
      log('Intentando reconectar al Arduino…', 'info');
      const res = await fetchJSON('/api/arduino/reconnect');
      if (res && res.connected) log('Arduino conectado.', 'ok');
      else log('Arduino no encontrado todavía (el servidor sigue reintentando solo).', 'warn');
    },

    async saveRestartSettings() {
      const updates = {
        AUDIO_INPUT_DEVICE: $('set-device').value,
        AUDIO_SAMPLE_RATE: $('set-rate').value,
        WHISPER_MODEL: $('set-whisper').value,
        ELEVENLABS_VOICE_ID: $('set-voiceid').value.trim(),
      };
      const res = await fetchJSON('/api/config', { json: { updates } });
      if (res && res.ok) {
        log('Guardado en .env. Reinicia el servidor para aplicar.', 'warn');
      }
    },
  };

  // Helpers de sliders de ajustes (texto con unidad).
  const SETTING_UNITS = { vad: '', silence: ' s', lead: ' s', listen: ' s', energy: '×', ienergy: '×', dist: ' m',
                          wave: ' s', greetcd: ' s', turnsec: ' s', latsec: ' s', turnvel: '', latvel: '',
                          wavehigh: '°', waveswing: '°', waverep: '', kick: ' s' };
  function setSlider(inputId, key, value) {
    const el = $(inputId);
    if (!el || value === undefined || value === null) return;
    el.value = value;
    $(inputId + '-val').textContent = value + (SETTING_UNITS[key] || '');
  }

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
      // Al abrir Ajustes, traemos los valores actuales del backend.
      if (name === 'settings') API.loadSettings();
    },

    // Actualiza la etiqueta de un slider de ajustes con su unidad.
    settingLabel(inputId, key) {
      $(inputId + '-val').textContent = $(inputId).value + (SETTING_UNITS[key] || '');
    },
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
