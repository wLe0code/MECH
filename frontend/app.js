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
    marcarEscritura(el.lastChild, msg);
    list.prepend(el);
    while (list.children.length > 80) list.removeChild(list.lastChild);
  }

  function escapeHTML(s) {
    return String(s).replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  // En qué escritura viene un texto. Se le pone como `lang` al elemento que
  // lo muestra, para que el navegador elija la letra que sabe dibujarla (y,
  // en los caracteres que comparten chino y japonés, la forma de cada país).
  function escritura(texto) {
    texto = String(texto || '');
    // hangul (piezas sueltas y sílabas) · kana · ideogramas
    if (/[\u1100-\u11FF\u3130-\u318F\uAC00-\uD7AF]/.test(texto)) return 'ko';
    if (/[\u3040-\u30FF]/.test(texto)) return 'ja';
    if (/[\u3400-\u4DBF\u4E00-\u9FFF]/.test(texto)) return state.language === 'ja' ? 'ja' : 'zh';
    return '';
  }

  function marcarEscritura(el, texto) {
    const code = escritura(texto);
    if (code) el.setAttribute('lang', code);
    else el.removeAttribute('lang');
  }

  function addChat(msg, isUser) {
    const list = $('chat-list');
    const el = document.createElement('div');
    el.className = 'chat-bubble ' + (isUser ? 'chat-user' : 'chat-mech');
    el.textContent = msg;
    marcarEscritura(el, msg);
    list.appendChild(el);
    while (list.children.length > 80) list.removeChild(list.firstChild);
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
      document.body.classList.remove('sin-servidor');
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
      // Aviso flotante «Sin conexión con MECH» (lo pinta el CSS).
      document.body.classList.add('sin-servidor');
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
      case 'trivia':      applyTrivia(msg); break;
      case 'facing':      applyFacing(msg.facing); break;
      case 'mic_level':   applyMicLevel(msg); break;
      case 'sismos':      if (window.Sismos) window.Sismos.evento(msg); break;
      case 'music':       applyMusic(msg); break;
      case 'pong':        break;
    }
  }

  // ─── Orientación del robot (maniobra de 180°) ─────────────────────
  // "projection" = mirando a donde proyecta (su sitio de trabajo).
  // "outward"    = de espaldas, saludando al público.
  // "manual"     = lo giraron a mano desde el panel: MECH no sabe hacia
  //                dónde mira, y «regresa a proyectar» gira igual.
  function applyFacing(facing) {
    const el = $('facing-val');
    if (!el) return;
    const textos = {
      outward: ['AFUERA (al público)', 'var(--amber)'],
      manual:  ['NO LO SÉ (lo giraste a mano)', 'var(--amber)'],
    };
    const [texto, color] = textos[facing] || ['la proyección', 'var(--text)'];
    el.textContent = texto;
    el.style.color = color;
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
      else if (!v.user_present) st.innerHTML = '<span style="color:var(--ok)">Cámara activa — sin usuario a la vista</span>';
      else st.innerHTML = `<span style="color:var(--ok)">Usuario detectado a ${v.distance != null ? v.distance.toFixed(1) : '?'} m (x=${v.x})</span>`;
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
    off:          { cls: 'phase-off',     icon: 'ti-microphone', text: 'Bucle de voz apagado', hint: 'Pulsa el micrófono o la tecla V para empezar' },
    dormant:      { cls: 'phase-dormant', icon: 'ti-bed',        text: 'MECH en reposo',       hint: "Di 'ok MECH' (español) o 'wake up MECH' (inglés)" },
    waiting:      { cls: 'phase-waiting', icon: 'ti-microphone', text: 'PUEDES HABLAR',        hint: 'Dile al juez/usuario que hable AHORA' },
    listening:    { cls: 'phase-listen',  icon: 'ti-microphone', text: 'Grabando tu voz…',     hint: 'Te estoy escuchando, sigue hablando' },
    transcribing: { cls: 'phase-work',    icon: 'ti-refresh',    text: 'Transcribiendo…',      hint: 'Convirtiendo la voz a texto' },
    thinking:     { cls: 'phase-work',    icon: 'ti-bulb',       text: 'MECH está pensando…',  hint: 'Generando la respuesta con Claude' },
    speaking:     { cls: 'phase-speak',   icon: 'ti-volume',     text: 'MECH está hablando…',  hint: "Di 'oye MECH' para interrumpirlo" },
  };

  function updateVoicePhase(phase) {
    const p = PHASES[phase] || PHASES.off;
    const banner = $('voice-phase-banner');
    banner.className = 'voice-phase-banner ' + p.cls;
    $('vpb-text').textContent = p.text;
    // El icono de la fase (en la barra y dentro del micrófono) y la fase
    // en <body data-phase>: de ahí saca el CSS el color del micrófono.
    const icono = 'ti ' + p.icon;
    if ($('vpb-icon')) $('vpb-icon').className = icono + ' vpb-icon';
    if ($('mic-icon')) $('mic-icon').className = icono;
    document.body.dataset.phase = PHASES[phase] ? phase : 'off';
    // La frase que lo corta es la del idioma en que despertó (en inglés,
    // 'hey MECH'; 'oye MECH' ahí no hace nada).
    const idioma = LANGS[state.language];
    $('vpb-hint').textContent = (phase === 'speaking' && idioma)
      ? `Di '${idioma.corta}' para interrumpirlo` : p.hint;

    // Texto del hero de la vista Voz.
    $('voice-status').textContent = p.text;

    // Punto del header + sensor del micrófono.
    const micActive = phase === 'waiting' || phase === 'listening';
    $('dot-mic').className = micActive ? 'dot-active' : (state.voiceLoopActive ? 'dot-ok' : 'dot-off');
    const micLabel = { waiting: 'PUEDES HABLAR', listening: 'GRABANDO', transcribing: 'PROCESANDO',
                       thinking: 'PENSANDO', speaking: 'HABLANDO', dormant: 'EN REPOSO', off: 'INACTIVO' }[phase] || 'INACTIVO';
    setSensor('sen-mic', micLabel, micActive ? 'val-active' : (phase === 'off' ? 'val-off' : 'val-ok'));
  }

  // Los diez idiomas de MECH. De aquí sale TODO lo que el panel enseña de
  // ellos: el menú de idioma, los desplegables del traductor y del saludo,
  // el log y la pista de qué frase lo corta. `wake` es la frase que lo
  // despierta en ese idioma (`suena` = cómo se pronuncia, para quien no lee
  // esa escritura) y `corta` la que interrumpe la narración.
  const LANGS = {
    es: { nombre: 'ESPAÑOL', es: 'Español', nativo: 'Español', wake: 'ok MECH', corta: 'oye MECH' },
    en: { nombre: 'INGLÉS', es: 'Inglés', nativo: 'English', wake: 'wake up MECH', corta: 'hey MECH' },
    fr: { nombre: 'FRANCÉS', es: 'Francés', nativo: 'Français', wake: 'bonjour MECH', corta: 'pardon MECH' },
    pt: { nombre: 'PORTUGUÉS', es: 'Portugués', nativo: 'Português', wake: 'bom dia MECH', corta: 'escuta MECH' },
    de: { nombre: 'ALEMÁN', es: 'Alemán', nativo: 'Deutsch', wake: 'guten Tag MECH', corta: 'warte MECH' },
    it: { nombre: 'ITALIANO', es: 'Italiano', nativo: 'Italiano', wake: 'ciao MECH', corta: 'scusa MECH' },
    ja: { nombre: 'JAPONÉS', es: 'Japonés', nativo: '日本語', wake: 'こんにちは MECH', suena: 'konnichiwa', corta: 'ねえ MECH' },
    ru: { nombre: 'RUSO', es: 'Ruso', nativo: 'Русский', wake: 'привет MECH', suena: 'privet', corta: 'эй MECH' },
    zh: { nombre: 'MANDARÍN', es: 'Mandarín', nativo: '中文', wake: '你好 MECH', suena: 'nǐ hǎo', corta: '嘿 MECH' },
    ko: { nombre: 'COREANO', es: 'Coreano', nativo: '한국어', wake: '안녕 MECH', suena: 'annyeong', corta: '저기 MECH' },
  };

  // ─── Menús desplegables ───────────────────────────────────────────
  // Un solo menú abierto a la vez. El desplegable cuelga de <body> y se
  // coloca con `position: fixed` junto a su botón: así no lo recorta ninguna
  // tarjeta, y se abre hacia arriba si abajo no cabe. La animación es de CSS
  // (clase `.open`); aquí solo se decide dónde va y cuándo se cierra.
  const Menus = (() => {
    let actual = null;   // { btn, pop, centrado }
    const MARGEN = 8;

    function colocar() {
      const { btn, pop, centrado } = actual;
      const r = btn.getBoundingClientRect();
      pop.style.maxHeight = 'none';
      pop.style.minWidth = Math.round(r.width) + 'px';
      const alto = pop.offsetHeight, ancho = pop.offsetWidth;
      const abajo = window.innerHeight - r.bottom - MARGEN * 2;
      const arriba = r.top - MARGEN * 2;
      const sube = alto > abajo && arriba > abajo;
      const h = Math.min(alto, Math.max(140, sube ? arriba : abajo));
      pop.style.maxHeight = h + 'px';
      let x = centrado ? r.left + r.width / 2 - ancho / 2 : r.left;
      x = Math.max(MARGEN, Math.min(x, window.innerWidth - ancho - MARGEN));
      pop.style.left = Math.round(x) + 'px';
      pop.style.top = Math.round(sube ? r.top - MARGEN - h : r.bottom + MARGEN) + 'px';
      // Crece desde su botón, no desde el centro del menú.
      pop.style.transformOrigin = `${Math.round(r.left + r.width / 2 - x)}px ${sube ? '100%' : '0%'}`;
      pop.classList.toggle('up', sube);
    }

    function enfocar(el) { if (el) el.focus({ preventScroll: true }); }

    function cerrar(devolverFoco) {
      if (!actual) return;
      const { btn, pop } = actual;
      actual = null;
      pop.classList.remove('open');
      btn.setAttribute('aria-expanded', 'false');
      if (devolverFoco) enfocar(btn);
    }

    function abrir(btn, pop, opts = {}) {
      if (actual && actual.pop === pop) { cerrar(); return; }
      cerrar();
      actual = { btn, pop, centrado: !!opts.centrado };
      // Se coloca con la transición apagada: si no, el menú "viaja" desde
      // donde se abrió la última vez.
      pop.style.transition = 'none';
      colocar();
      // Si la lista no cabe entera (teléfono), que se vea la opción elegida.
      const elegida = pop.querySelector('.menu-item.active');
      if (elegida) pop.scrollTop = elegida.offsetTop - (pop.clientHeight - elegida.offsetHeight) / 2;
      void pop.offsetWidth;
      pop.style.transition = '';
      pop.classList.add('open');
      btn.setAttribute('aria-expanded', 'true');
      // Abierto con el teclado: el foco entra al menú, en la opción elegida.
      if (opts.teclado) enfocar(pop.querySelector('.menu-item.active') || pop.querySelector('.menu-item'));
    }

    // Une un botón con su desplegable. `antes()` corre justo antes de abrir
    // (para repintar las opciones).
    function unir(btn, pop, opts = {}) {
      document.body.appendChild(pop);
      btn.addEventListener('click', (e) => {
        if (opts.antes) opts.antes();
        abrir(btn, pop, { centrado: opts.centrado, teclado: e.detail === 0 });
      });
    }

    document.addEventListener('pointerdown', (e) => {
      if (actual && !actual.pop.contains(e.target) && !actual.btn.contains(e.target)) cerrar();
    }, true);
    // Si la página se mueve, el menú se quedaría flotando lejos de su botón.
    document.addEventListener('scroll', (e) => {
      if (actual && !actual.pop.contains(e.target)) cerrar();
    }, true);
    window.addEventListener('resize', () => cerrar());
    document.addEventListener('keydown', (e) => {
      if (!actual) return;
      const items = Array.from(actual.pop.querySelectorAll('.menu-item'));
      const i = items.indexOf(document.activeElement);
      const paso = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[e.key];
      if (e.key === 'Escape') { e.preventDefault(); cerrar(true); }
      else if (e.key === 'Tab') cerrar();
      else if (paso && items.length) {
        e.preventDefault();
        enfocar(items[i < 0 ? (paso > 0 ? 0 : items.length - 1) : (i + paso + items.length) % items.length]);
      }
      else if (e.key === 'Home') { e.preventDefault(); enfocar(items[0]); }
      else if (e.key === 'End') { e.preventDefault(); enfocar(items[items.length - 1]); }
    }, true);

    return { unir, cerrar, abierto: () => !!actual };
  })();

  // Convierte un <select> en uno de los menús de arriba. El <select> sigue en
  // la página (escondido) y sigue siendo quien guarda el valor: todo lo que
  // hace `$('tr-src').value`, o le cambia el valor o las opciones, funciona
  // igual. Si algo falla, ese desplegable se queda como el del sistema.
  function mejorarSelect(sel) {
    const wrap = document.createElement('div');
    wrap.className = 'menu msel' + (sel.classList.contains('text-input') ? ' msel-wide' : '');
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'menu-btn msel-btn';
    btn.setAttribute('aria-haspopup', 'listbox');
    btn.setAttribute('aria-expanded', 'false');
    if (sel.title) btn.title = sel.title;
    const label = document.createElement('span');
    label.className = 'msel-label';
    const caret = document.createElement('span');
    caret.className = 'menu-caret';
    btn.append(label, caret);
    const pop = document.createElement('div');
    pop.className = 'menu-pop msel-pop';
    pop.setAttribute('role', 'listbox');

    // Un desplegable cuyas opciones son todas idiomas se pinta como el menú
    // de idioma: la etiqueta de dos letras y el nombre.
    const deIdiomas = () => sel.options.length > 1 && Array.from(sel.options).every((o) => LANGS[o.value]);
    const pinta = (o, idiomas) => idiomas
      ? `<span class="lang-code">${o.value.toUpperCase()}</span><span>${escapeHTML(LANGS[o.value].es)}</span>`
      : escapeHTML(o.textContent);

    function pintarBoton() {
      const o = sel.options[sel.selectedIndex];
      label.innerHTML = o ? pinta(o, deIdiomas()) : '';
    }

    function pintarOpciones() {
      const idiomas = deIdiomas();
      pop.classList.toggle('msel-langs', idiomas);
      pop.innerHTML = '';
      Array.from(sel.options).forEach((o, i) => {
        const it = document.createElement('button');
        it.type = 'button';
        it.className = 'menu-item' + (o.selected ? ' active' : '');
        it.setAttribute('role', 'option');
        it.setAttribute('aria-selected', o.selected ? 'true' : 'false');
        it.style.setProperty('--i', Math.min(i, 12));
        it.innerHTML = pinta(o, idiomas);
        it.addEventListener('click', () => {
          sel.value = o.value;
          sel.dispatchEvent(new Event('change', { bubbles: true }));
          Menus.cerrar(true);
        });
        pop.appendChild(it);
      });
    }

    sel.parentNode.insertBefore(wrap, sel);
    wrap.append(sel, btn);
    sel.classList.add('msel-native');
    sel.tabIndex = -1;
    sel.setAttribute('aria-hidden', 'true');
    Menus.unir(btn, pop, { antes: pintarOpciones });

    // El botón tiene que enterarse de TODO lo que cambie el valor: que lo
    // elijan, que el código haga `sel.value = …` (eso no avisa con ningún
    // evento, por eso se envuelve la propiedad) y que le cambien las opciones
    // (la lista de micrófonos se rehace al recargarla).
    const prop = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value');
    Object.defineProperty(sel, 'value', {
      configurable: true,
      get() { return prop.get.call(sel); },
      set(v) { prop.set.call(sel, v); pintarBoton(); },
    });
    sel.addEventListener('change', pintarBoton);
    new MutationObserver(pintarBoton).observe(sel, { childList: true });
    pintarBoton();
  }

  // Los diez idiomas del menú de la vista Voz, pintados desde LANGS.
  function pintarMenuIdiomas() {
    const grid = $('lang-grid');
    if (!grid || !$('lang-btn')) return;
    grid.innerHTML = '';
    Object.keys(LANGS).forEach((c, i) => {
      const L = LANGS[c];
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'menu-item lang-chip';
      b.id = 'lang-' + c;
      b.setAttribute('role', 'menuitemradio');
      b.setAttribute('aria-checked', 'false');
      b.style.setProperty('--i', i);
      const nativo = L.nativo !== L.es ? `<small lang="${c}">${L.nativo}</small>` : '';
      const suena = L.suena ? ` · ${L.suena}` : '';
      b.innerHTML = `<span class="lang-code">${c.toUpperCase()}</span>` +
        `<span class="lang-txt"><span class="lang-name">${L.es}${nativo}</span>` +
        `<span class="lang-wake" lang="${c}">«${L.wake}»${suena}</span></span>`;
      b.addEventListener('click', () => { Menus.cerrar(true); API.setLanguage(c); });
      grid.appendChild(b);
    });
    Menus.unir($('lang-btn'), $('lang-pop'), { centrado: true });
  }

  // Estado de la tarjeta del modo traductor (vista Voz).
  // El traductor va por TURNOS: «traduce MECH» -> pregunta -> escucha UNA
  // frase -> la dice -> se calla. El par de idiomas se recuerda entre turnos,
  // así que "APAGADO" con par recordado se muestra como "LISTO".
  function updateTranslator(t) {
    t = t || {};
    const badge = $('translator-state');
    const box = $('translator-box');
    if (!badge || !box) return;
    const nombre = (c) => (LANGS[c] ? LANGS[c].nombre : (c || '?'));
    const par = () => `${nombre(t.src)} ${t.auto_detect ? '↔' : '→'} ${nombre(t.dst)}`;
    const tienePar = !!(t.src && t.dst);

    let texto = 'APAGADO', clase = '';
    if (t.awaiting_pair) {
      texto = 'ESPERANDO IDIOMAS';
      clase = 'tr-waiting';
    } else if (t.awaiting_phrase) {
      texto = `ESCUCHANDO · ${par()}`;
      clase = 'tr-on';
    } else if (tienePar) {
      texto = `LISTO · ${par()}`;   // recuerda el par, esperando el comando
      clase = 'tr-idle';
    }
    badge.textContent = texto;
    badge.className = 'translator-state ' + clase;
    box.classList.toggle('active', !!t.active);
    // Los selectores reflejan el par en curso, para no perderlo de vista.
    if (tienePar) {
      if ($('tr-src')) $('tr-src').value = t.src;
      if ($('tr-dst')) $('tr-dst').value = t.dst;
    }
    if (state.translatorActive !== !!t.active) {
      if (state.translatorActive !== undefined) {
        log(t.active ? `Traductor escuchando (${texto}).`
                     : 'Traductor: turno terminado.', 'ok');
      }
      state.translatorActive = !!t.active;
    }
  }

  // Pone el idioma activo en el botón de la vista Voz, lo marca en su menú y
  // deja a la vista las dos frases que hacen falta en ese idioma.
  function updateLanguage(code) {
    if (state.language === code) return;
    if (!LANGS[code]) code = 'es';
    const info = LANGS[code];
    if (state.language) log(`MECH pasó a ${info.nombre} (${info.wake}).`, 'ok');
    state.language = code;
    Object.keys(LANGS).forEach((c) => {
      const chip = $('lang-' + c);
      if (!chip) return;
      chip.classList.toggle('active', c === code);
      chip.setAttribute('aria-checked', c === code ? 'true' : 'false');
    });
    if ($('lang-btn-code')) $('lang-btn-code').textContent = code.toUpperCase();
    if ($('lang-btn-name')) $('lang-btn-name').textContent = info.es;
    const pista = $('lang-hint');
    if (pista) {
      pista.textContent = `Se despierta con «${info.wake}» · se corta con «${info.corta}»`;
      pista.setAttribute('lang', code);
    }
  }

  // ─── Trivia (el juego de preguntas) ───────────────────────────────
  // El estado manda: aquí solo se pinta. Los botones A/B/C responden sin
  // micrófono, que es como se separa "el juego falla" de "no te entendió".
  const TRIVIA_ETAPAS = {
    offer:    { texto: '¿JUGAMOS?',  cls: 'tr-waiting' },
    loading:  { texto: 'PREPARANDO', cls: 'tr-waiting' },
    question: { texto: 'TU TURNO',   cls: 'tr-on' },
    result:   { texto: 'REVELANDO',  cls: 'tr-on' },
    final:    { texto: 'RESULTADO',  cls: 'tr-idle' },
  };

  // ─── Modo música ──────────────────────────────────────────────────
  // El modo corre en el servidor (backend/music.py) y la canción suena en la
  // pantalla de proyección; esta tarjeta enseña en qué va y deja pedir una
  // canción escribiendo.
  const MUSIC_ETAPAS = {
    ask:     { texto: '¿QUÉ CANCIÓN?', cls: 'tr-waiting' },
    artist:  { texto: '¿DE QUÉ ARTISTA?', cls: 'tr-waiting' },
    playing: { texto: 'SONANDO', cls: 'tr-on' },
    again:   { texto: '¿SEGUIMOS?', cls: 'tr-waiting' },
  };
  function applyMusic(m) {
    m = m || {};
    const box = $('music-box');
    if (!box) return;
    const activo = !!m.active;
    box.classList.toggle('active', activo);
    const et = MUSIC_ETAPAS[m.stage] || { texto: 'APAGADO', cls: '' };
    const badge = $('music-state');
    badge.textContent = activo ? et.texto : 'APAGADO';
    badge.className = 'translator-state ' + (activo ? et.cls : '');
    // Qué suena. El título y el artista vienen de fuera: con textContent.
    const ahora = $('music-now');
    const t = m.track || null;
    ahora.textContent = '';
    if (t) {
      ahora.textContent = t.artist ? `${t.title} — ${t.artist}` : t.title;
      marcarEscritura(ahora, t.title + (t.artist || ''));
    } else {
      const vacio = document.createElement('span');
      vacio.className = 'tq-empty';
      vacio.textContent = m.stage === 'artist' && m.pending_title
        ? `«${m.pending_title}»: falta el artista.`
        : (m.last ? `Lo último: ${m.last.title}${m.last.artist ? ' — ' + m.last.artist : ''}` : 'Nada sonando.');
      ahora.appendChild(vacio);
      marcarEscritura(ahora, vacio.textContent);
    }
  }

  function applyTrivia(t) {
    t = t || {};
    const box = $('trivia-box');
    if (!box) return;
    const activa = !!t.active;
    box.classList.toggle('active', activa);
    const et = TRIVIA_ETAPAS[t.stage] || { texto: 'APAGADA', cls: '' };
    const badge = $('trivia-state');
    badge.textContent = activa
      ? (t.total ? `${et.texto} · ${t.number}/${t.total}` : et.texto)
      : 'APAGADA';
    badge.className = 'translator-state ' + (activa ? et.cls : '');

    const q = $('trivia-q');
    if (activa && t.question) {
      const marcador = t.total ? ` <span style="color:var(--text-muted)">· aciertos: ${t.score}/${t.total}</span>` : '';
      q.innerHTML = escapeHTML(t.question) + marcador;
    } else if (activa && t.stage === 'final') {
      q.innerHTML = `Resultado: <b>${t.score}/${t.total}</b>`;
    } else if (activa && t.stage === 'offer') {
      q.innerHTML = '<span class="tq-empty">Esperando un sí o un no…</span>';
    } else if (activa && t.stage === 'loading') {
      q.innerHTML = '<span class="tq-empty">Claude está escribiendo las preguntas…</span>';
    } else {
      q.innerHTML = '<span class="tq-empty">Sin partida en marcha.</span>';
    }
    marcarEscritura(q, activa ? t.question : '');

    const cont = $('trivia-opts');
    cont.innerHTML = '';
    (t.options || []).forEach((op, i) => {
      const b = document.createElement('button');
      b.className = 'trivia-opt';
      b.innerHTML = `<b>${escapeHTML((t.letters || [])[i] || '')}</b>${escapeHTML(op)}`;
      marcarEscritura(b, op);
      b.disabled = t.stage !== 'question';
      b.title = t.stage === 'question'
        ? 'Responder esta opción sin micrófono'
        : 'Solo se puede responder mientras la pregunta está en pantalla';
      b.onclick = () => API.triviaAnswer((t.letters || [])[i] || String(i + 1));
      cont.appendChild(b);
    });
  }

  function applyState(s) {
    state.backend = s;
    // Idioma activo (español por defecto; los demás solo si lo despiertan
    // en ese idioma: "wake up MECH", "bonjour MECH", "こんにちは MECH"…).
    updateLanguage(s.language || 'es');
    // Modo traductor ("traduce MECH"): par de idiomas y si está encendido.
    updateTranslator(s.translator);
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

    // Transcript / respuesta. El estado llega en CADA cambio de fase (grabando,
    // pensando, hablando…) y siempre trae la última frase: solo se pinta si es
    // otra, o la conversación se llenaba de la misma burbuja repetida.
    if (s.last_transcript && s.last_transcript !== state.ultimoTranscript) showTranscript(s.last_transcript);
    if (s.last_ai_response && s.last_ai_response !== state.ultimaRespuesta) showAIResponse(s.last_ai_response);

    // Visión
    if (s.vision) applyVision(s.vision);

    // Trivia
    applyTrivia(s.trivia);
    // Modo música
    applyMusic(s.music);

    // Hacia dónde mira (maniobra de 180°)
    applyFacing(s.facing || 'projection');
  }

  function showTranscript(text) {
    state.ultimoTranscript = text;
    $('transcript').textContent = text;
    marcarEscritura($('transcript'), text);
    addChat(text, true);
  }

  function showAIResponse(text, segment, total) {
    state.ultimaRespuesta = text;
    const counter = (segment && total) ? ` <span style="color:var(--text-muted);font-size:10px">[${segment}/${total}]</span>` : '';
    const code = escritura(text);
    $('ai-resp').innerHTML = `<div class="ai-label">MECH responde${counter}</div>` +
      `<span${code ? ` lang="${code}"` : ''}>${escapeHTML(text)}</span>`;
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
    // El color respira entre verde azulado y azul, alrededor del cian del
    // panel (antes daba la vuelta entera al arcoíris, empezando en violeta).
    let fase = 0;
    let hue = 190;

    function draw() {
      state.immAnim = requestAnimationFrame(draw);
      ctx.fillStyle = 'rgba(6,8,9,0.18)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      fase += 0.004;
      hue = 190 + Math.sin(fase) * 22;
      pts.forEach(p => {
        p.x += p.vx; p.y += p.vy; p.a += 0.012;
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r * (1 + Math.sin(p.a) * 0.5), 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${hue + p.x / canvas.width * 36},80%,68%,0.85)`;
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

    // Modo traductor: un turno por pulsación, igual que «traduce MECH».
    // Desde el panel se manda el par ya elegido, así no pregunta los idiomas.
    async translateStart() {
      const src = $('tr-src') ? $('tr-src').value : 'es';
      const dst = $('tr-dst') ? $('tr-dst').value : 'en';
      if (src === dst) { log('Elegí dos idiomas distintos para traducir.', 'warn'); return; }
      const res = await fetchJSON(`/api/translate/start?src=${src}&dst=${dst}`);
      if (res && res.ok) log(`Traductor: preguntando qué traducir (${src} ↔ ${dst}).`, 'ok');
    },

    async translateStop() {
      const res = await fetchJSON('/api/translate/stop');
      if (res && !res.ok) log(res.reason || 'El traductor no estaba activo.', 'warn');
    },

    async interrupt() {
      const res = await fetchJSON('/api/voice/interrupt');
      if (res && res.ok) log('Narración interrumpida desde el panel.', 'ok');
      else if (res) log(res.reason || 'MECH no está narrando ahora.', 'warn');
    },

    async triviaStart() {
      log('Preparando las preguntas de la trivia…', 'info');
      const res = await fetchJSON('/api/trivia/start');
      if (res && !res.ok) log(res.reason || 'No se pudo empezar la trivia.', 'warn');
    },

    // ─── Modo música ────────────────────────────────────────────────
    async musicStart() {
      const res = await fetchJSON('/api/music/start');
      if (res && !res.ok) log(res.reason || 'No se pudo entrar al modo música.', 'warn');
    },

    async musicPlay() {
      const caja = $('music-text');
      const text = (caja.value || '').trim();
      if (!text) { caja.focus(); return; }
      log(`Busco en YouTube: ${text}`, 'info');
      const res = await fetchJSON('/api/music/play', { json: { text } });
      if (res && !res.ok) log(res.reason || 'No se pudo pedir la canción.', 'warn');
      else if (res) caja.value = '';
    },

    async musicStop() {
      const res = await fetchJSON('/api/music/stop');
      if (res && !res.ok) log(res.reason || 'El modo música no está activo.', 'warn');
    },

    async triviaStop() {
      const res = await fetchJSON('/api/trivia/stop');
      if (res && !res.ok) log(res.reason || 'No hay ninguna trivia en marcha.', 'warn');
    },

    async triviaAnswer(letra) {
      const res = await fetchJSON(`/api/trivia/answer/${encodeURIComponent(letra)}`);
      if (res && !res.ok) log(res.reason || 'Ahora no hay ninguna pregunta esperando.', 'warn');
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

    async advance(backwards) {
      const res = await fetchJSON('/api/move/advance', { json: { backwards: !!backwards } });
      if (res && res.ok) log(`${backwards ? 'Retrocediendo' : 'Avanzando'} ${res.seconds} s.`, 'ok');
      else if (res) log(res.reason || 'No pude moverme ahora.', 'warn');
    },

    async testTurn() {
      const res = await fetchJSON('/api/move/testturn');
      if (res && res.ok) log(`Probando media vuelta: ${res.seconds} s a potencia ${res.speed}. ` +
                             `¿Se quedó corto? Sube los segundos en Ajustes.`, 'ok');
      else if (res) log(res.reason || 'No pude probar el giro ahora.', 'warn');
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
      if ($('set-strictlang')) $('set-strictlang').checked = L.VOICE_STRICT_LANGUAGE !== false;
      if ($('set-trivia')) $('set-trivia').checked = L.TRIVIA_ENABLED !== false;
      if ($('set-trivia-offer')) $('set-trivia-offer').checked = L.TRIVIA_OFFER_AFTER_PLAN !== false;
      setSlider('set-trivia-n', 'trivian', L.TRIVIA_QUESTIONS);
      if ($('set-music')) $('set-music').checked = L.MUSIC_ENABLED !== false;
      if ($('set-music-explicit')) $('set-music-explicit').checked = !!L.MUSIC_ALLOW_EXPLICIT;
      setSlider('set-music-vol', 'musicvol', L.MUSIC_VOLUME);
      setSlider('set-ienergy', 'ienergy', L.INTERRUPT_ENERGY_FACTOR);
      if ($('set-armmode')) $('set-armmode').value = L.ARM_GESTURE_MODE || 'full';
      if ($('set-wheels')) $('set-wheels').checked = !!L.GESTURE_WHEELS;
      if ($('set-narrmode')) $('set-narrmode').value = L.NARRATION_GESTURE_MODE || 'simple';
      setSlider('set-wave', 'wave', L.ARM_WAVE_SECONDS);
      setSlider('set-wavehigh', 'wavehigh', L.ARM_WAVE_HIGH);
      setSlider('set-waveswing', 'waveswing', L.ARM_WAVE_SWING);
      setSlider('set-waverep', 'waverep', L.ARM_WAVE_REPEATS);
      // Por defecto va APAGADO (solo el brazo derecho), así que se lee tal
      // cual. Con `!== false`, la clave ausente lo marcaba.
      if ($('set-waveboth')) $('set-waveboth').checked = !!L.ARM_WAVE_BOTH;
      if ($('set-invr')) $('set-invr').checked = !!L.ARM_INVERT_R;
      if ($('set-invl')) $('set-invl').checked = !!L.ARM_INVERT_L;
      setSlider('set-hpf', 'hpf', L.AUDIO_HIGHPASS_HZ);
      setSlider('set-agc', 'agc', L.AUDIO_TARGET_DBFS);
      setSlider('set-beam', 'beam', L.WHISPER_BEAM_SIZE);
      setSlider('set-greetcd', 'greetcd', L.GREETING_COOLDOWN);
      setSlider('set-greetrearm', 'greetrearm', L.GREETING_REARM_SECONDS);
      setSlider('set-greetconfirm', 'greetconfirm', L.GREETING_CONFIRM_SECONDS);
      if ($('set-greetdormant')) $('set-greetdormant').checked = !!L.GREETING_ONLY_DORMANT;
      if ($('set-greetlang') && L.GREETING_LANGUAGE) $('set-greetlang').value = L.GREETING_LANGUAGE;
      // Calibración del giro de 180°
      setSlider('set-turnsec', 'turnsec', L.TURN_180_SECONDS);
      setSlider('set-turnvel', 'turnvel', L.TURN_180_SPEED);
      if ($('set-turninv')) $('set-turninv').checked = !!L.TURN_180_INVERT;
      if ($('set-fwdinv')) $('set-fwdinv').checked = !!L.DRIVE_INVERT_FORWARD;
      setSlider('set-advsec', 'advsec', L.ADVANCE_SECONDS);
      setSlider('set-advvel', 'advvel', L.ADVANCE_SPEED);
      setSlider('set-advmax', 'advmax', L.ADVANCE_MAX_SECONDS);
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
      // En el .env suele ir solo un trozo del nombre (AUDIO_INPUT_DEVICE=Steren),
      // que no coincide con ninguna opción: el desplegable quedaba EN BLANCO y
      // «Guardar en .env» borraba el micrófono. Va como una opción más.
      if (cur && !Array.from(sel.options).some((o) => o.value === cur)) {
        const opt = document.createElement('option');
        opt.value = cur;
        opt.textContent = `${cur} (lo configurado ahora)`;
        sel.appendChild(opt);
      }
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
        // Con guarda: si el navegador tiene el index.html viejo en caché, el
        // interruptor no existe y no puede tumbar el guardado entero.
        VOICE_STRICT_LANGUAGE: ($('set-strictlang') && !$('set-strictlang').checked) ? 'false' : 'true',
        TRIVIA_ENABLED: $('set-trivia').checked ? 'true' : 'false',
        TRIVIA_OFFER_AFTER_PLAN: $('set-trivia-offer').checked ? 'true' : 'false',
        TRIVIA_QUESTIONS: String(parseInt($('set-trivia-n').value)),
        MUSIC_ENABLED: $('set-music').checked ? 'true' : 'false',
        MUSIC_ALLOW_EXPLICIT: $('set-music-explicit').checked ? 'true' : 'false',
        MUSIC_VOLUME: $('set-music-vol').value,
        INTERRUPT_ENERGY_FACTOR: $('set-ienergy').value,
        ARM_GESTURE_MODE: $('set-armmode').value,
        GESTURE_WHEELS: $('set-wheels').checked ? 'true' : 'false',
        NARRATION_GESTURE_MODE: $('set-narrmode').value,
        ARM_WAVE_SECONDS: $('set-wave').value,
        ARM_WAVE_HIGH: String(parseInt($('set-wavehigh').value)),
        ARM_WAVE_SWING: String(parseInt($('set-waveswing').value)),
        ARM_WAVE_REPEATS: String(parseInt($('set-waverep').value)),
        ARM_WAVE_BOTH: $('set-waveboth').checked ? 'true' : 'false',
        ARM_INVERT_R: $('set-invr').checked ? 'true' : 'false',
        ARM_INVERT_L: $('set-invl').checked ? 'true' : 'false',
        AUDIO_HIGHPASS_HZ: $('set-hpf').value,
        AUDIO_TARGET_DBFS: $('set-agc').value,
        WHISPER_BEAM_SIZE: String(parseInt($('set-beam').value)),
        GREETING_COOLDOWN: $('set-greetcd').value,
        GREETING_REARM_SECONDS: $('set-greetrearm').value,
        GREETING_CONFIRM_SECONDS: $('set-greetconfirm').value,
        GREETING_ONLY_DORMANT: $('set-greetdormant').checked ? 'true' : 'false',
        GREETING_LANGUAGE: $('set-greetlang').value,
        TURN_180_SECONDS: $('set-turnsec').value,
        TURN_180_SPEED: String(parseInt($('set-turnvel').value)),
        TURN_180_INVERT: $('set-turninv').checked ? 'true' : 'false',
        DRIVE_INVERT_FORWARD: $('set-fwdinv').checked ? 'true' : 'false',
        ADVANCE_SECONDS: $('set-advsec').value,
        ADVANCE_SPEED: String(parseInt($('set-advvel').value)),
        ADVANCE_MAX_SECONDS: $('set-advmax').value,
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
                          trivian: ' preguntas', musicvol: '',
                          wave: ' s', greetcd: ' s', turnsec: ' s', latsec: ' s', turnvel: '', latvel: '',
                          wavehigh: '°', waveswing: '°', waverep: '', kick: ' s',
                          advsec: ' s', advvel: '', advmax: ' s',
                          hpf: ' Hz', agc: ' dBFS', beam: '', greetrearm: ' s', greetconfirm: ' s' };
  function setSlider(inputId, key, value) {
    const el = $(inputId);
    if (!el || value === undefined || value === null) return;
    el.value = value;
    pintarRango(el);
    $(inputId + '-val').textContent = value + (SETTING_UNITS[key] || '');
  }

  // El riel de un deslizador se rellena de color hasta la perilla. El
  // navegador no lo hace solo: aquí se le dice al CSS por dónde va (`--p`).
  function pintarRango(el) {
    const min = parseFloat(el.min) || 0;
    const max = parseFloat(el.max) || 100;
    const p = max > min ? (parseFloat(el.value) - min) / (max - min) * 100 : 0;
    el.style.setProperty('--p', Math.max(0, Math.min(100, p)) + '%');
  }

  // ─── Navegación ───────────────────────────────────────────────────
  // El resaltado del menú lateral es UNA pieza que se desliza hasta el botón
  // de la vista elegida. Aquí se le da la altura y la posición de ese botón;
  // el deslizamiento es una transición de CSS sobre `transform`.
  let glider = null;
  let conMenus = false;   // ¿styles.css trae los estilos de los menús? (ver Init)
  function moverGlider(animado) {
    const barra = document.querySelector('.sidebar');
    const activo = barra && barra.querySelector('.nav-item.active');
    if (!conMenus || !activo) return;
    if (!glider) {
      glider = document.createElement('div');
      glider.className = 'nav-glider';
      glider.setAttribute('aria-hidden', 'true');
      barra.prepend(glider);
      barra.classList.add('has-glider');
      animado = false;   // la primera vez aparece en su sitio, no viaja
    }
    if (!animado) glider.style.transition = 'none';
    glider.style.height = activo.offsetHeight + 'px';
    glider.style.transform = `translateY(${activo.offsetTop}px)`;
    if (!animado) { void glider.offsetWidth; glider.style.transition = ''; }
  }

  const UI = {
    // `navEl` solo llega cuando se pulsa un botón del menú. Con las teclas
    // 1/2/3 no llega, y entonces NADA se anima: lo que se dispara con el
    // teclado tiene que ser inmediato.
    showView(name, navEl) {
      const vista = $('view-' + name);
      const cambia = !vista.classList.contains('visible');
      Menus.cerrar();
      document.querySelectorAll('.view').forEach(v => v.classList.remove('visible', 'entra'));
      document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
      vista.classList.add('visible');
      if (navEl && cambia) vista.classList.add('entra');   // cascada de entrada
      if (navEl) navEl.classList.add('active');
      else {
        const nav = document.querySelector(`[data-view="${name}"]`);
        if (nav) nav.classList.add('active');
      }
      moverGlider(!!navEl);
      // Al abrir Ajustes, traemos los valores actuales del backend.
      if (name === 'settings') API.loadSettings();
      // El mapa de sismos solo trabaja (dibuja, pide datos) mientras se ve.
      if (window.Sismos) window.Sismos.mostrar(name === 'sismos');
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

  // Enter en la caja de «Canción y artista» = botón «Poner».
  if ($('music-text')) {
    $('music-text').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); API.musicPlay(); }
    });
  }

  // ─── Botón de paro de emergencia ──────────────────────────────────
  $('emergency-btn').addEventListener('click', () => API.emergencyStop());

  // ─── Exponer al global para los onclick inline ────────────────────
  window.API = API;
  window.UI = UI;

  // ─── Init ─────────────────────────────────────────────────────────
  // Menú de idiomas, y cada <select> convertido en menú animado. En pantallas
  // táctiles los <select> se quedan como los del sistema: en un teléfono su
  // selector nativo es más cómodo que cualquier menú hecho a mano.
  pintarMenuIdiomas();
  // Abierto desde la app de Windows (windows/app la abre con `?app=1`): si se
  // pierde al robot, el aviso ofrece volver a la pantalla que lo busca.
  if (new URLSearchParams(location.search).has('app')) {
    document.body.classList.add('en-app');
    if ($('net-back')) $('net-back').addEventListener('click', () => history.back());
  }
  // La ayuda de atajos y frases (botón del pie del menú lateral).
  if ($('keys-btn') && $('keys-pop')) Menus.unir($('keys-btn'), $('keys-pop'));
  // Los deslizadores: relleno hasta la perilla, ahora y cada vez que se muevan.
  document.querySelectorAll('input[type="range"]').forEach(pintarRango);
  document.addEventListener('input', (e) => {
    if (e.target.matches && e.target.matches('input[type="range"]')) pintarRango(e.target);
  });
  // `--menus` lo pone styles.css: si el navegador tiene guardada una hoja de
  // estilos vieja (sin los menús), no se monta nada de esto y el panel queda
  // con los controles de siempre.
  conMenus = getComputedStyle(document.documentElement).getPropertyValue('--menus').trim() === '1';
  if (conMenus && window.matchMedia('(pointer: fine)').matches) {
    document.querySelectorAll('select').forEach((sel) => {
      try { mejorarSelect(sel); } catch (e) { /* se queda el del sistema */ }
    });
  }
  // Menú lateral: turno de cada elemento en la cascada de entrada, y el
  // resaltado en su sitio (se recoloca si cambia el tamaño de la ventana o
  // cuando terminan de cargar las fuentes, que cambian la altura).
  if (conMenus) {
    document.querySelectorAll('.sidebar > .sidebar-label, .sidebar > .nav-item')
      .forEach((el, i) => el.style.setProperty('--n', i));
    moverGlider(false);
    window.addEventListener('resize', () => moverGlider(false));
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => moverGlider(false));
  }

  log('Panel MECH cargado', 'ok');
  connectWS();
  setTimeout(initImmDemo, 600);

  // PWA service worker registration (opcional, mejora "instalable")
  if ('serviceWorker' in navigator && !isFile) {
    navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(() => {});
  }
})();
