/* MECH · Modo música — lo que suena y se ve en la pantalla de proyección.
 *
 * El modo entero corre en el servidor (backend/music.py + mech_app). Esta
 * página hace dos cosas: PONE la canción que le mandan y AVISA de cómo va.
 *
 *   llega  {type: "music", stage: "playing", play_id, track: {title, artist,
 *           artwork, preview, seconds}, label, note, volume, lang}
 *   avisa  POST /api/music/event  {play_id, event: "playing"|"ended"|"error"}
 *
 * El servidor no sabe cuánto tarda en cargar el audio ni cuándo acaba de
 * verdad: lo sabe quien lo reproduce. Es el mismo trato que con los videos de
 * marketing (`/api/playlist/ended`).
 *
 * ⚠️ Una canción solo EMPIEZA con el evento `music` (trae un `play_id`
 * nuevo). El `state`, que llega a cada rato, solo sirve para saber que hay
 * que callar: si también arrancara canciones, cada cambio de fase la
 * reiniciaría.
 *
 * QUÉ SUENA hoy: `track.preview`, el fragmento oficial de 30 s de Apple, un
 * archivo de audio normal. La canción entera (MusicKit, con la cuenta de
 * desarrollador de Apple) entraría por aquí mismo, en `sonar()`, sin tocar
 * nada más.
 *
 * ⚠️ AUDIO: igual que los videos de marketing, el navegador no deja sonar sin
 * un gesto del usuario. En la Pi, Chromium se abre con
 * `--autoplay-policy=no-user-gesture-required` (el icono «Proyectar MECH» ya
 * lo lleva). Si lo bloquea, se avisa al servidor y se pide un toque.
 *
 * Los textos que vienen de fuera (título, artista) van con `textContent`.
 * Solo se animan `transform` y `opacity`, como en la trivia.
 */
window.MechMusic = (function () {
  const CSS = `
  .mm-wrap {
    position: fixed; inset: 0; z-index: 15;
    display: none; align-items: center; justify-content: center;
    background: #06080b; color: #fff; overflow: hidden;
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, var(--cjk, sans-serif), sans-serif;
  }
  .mm-wrap.on { display: flex; }
  /* La carátula, enorme y desenfocada, de fondo. Es una imagen quieta: el
     desenfoque se calcula una vez, no en cada fotograma. */
  .mm-fondo {
    position: absolute; inset: -12%;
    background-size: cover; background-position: center;
    filter: blur(60px) saturate(1.3); opacity: .45;
  }
  .mm-velo { position: absolute; inset: 0; background: radial-gradient(ellipse at center, rgba(6,8,11,.25), rgba(6,8,11,.88)); }
  .mm-caja {
    position: relative; display: flex; align-items: center; gap: 6vw;
    width: 86%; max-width: 1500px;
    animation: mm-entra .6s cubic-bezier(.23,1,.32,1) backwards;
  }
  @keyframes mm-entra { from { opacity: 0; transform: translateY(3vh) scale(.97); } }
  .mm-caratula {
    flex: none; width: min(38vw, 62vh); aspect-ratio: 1; border-radius: 3.2vmin;
    object-fit: cover; background: #151b22;
    box-shadow: 0 3vh 9vh rgba(0,0,0,.6), 0 0 0 1px rgba(255,255,255,.08);
  }
  .mm-texto { min-width: 0; display: flex; flex-direction: column; gap: 2.2vh; }
  .mm-rotulo {
    display: flex; align-items: center; gap: 1.2vw;
    font-size: clamp(13px, 1.5vw, 24px); font-weight: 600; letter-spacing: .22em;
    text-transform: uppercase; color: #22d3ee;
  }
  /* Las barritas que bailan: solo transform. (Sin comillas invertidas aquí
     dentro: cerrarían la cadena de JavaScript que guarda este CSS.) */
  .mm-barras { display: inline-flex; align-items: flex-end; gap: .35vw; height: 1.6vw; min-height: 14px; }
  .mm-barras i {
    width: .42vw; min-width: 3px; height: 100%; border-radius: 2px; background: currentColor;
    transform-origin: bottom; animation: mm-baila 1s ease-in-out infinite;
  }
  .mm-barras i:nth-child(2) { animation-duration: .7s; animation-delay: -.3s; }
  .mm-barras i:nth-child(3) { animation-duration: 1.2s; animation-delay: -.6s; }
  .mm-barras i:nth-child(4) { animation-duration: .85s; animation-delay: -.15s; }
  @keyframes mm-baila { 0%, 100% { transform: scaleY(.25); } 50% { transform: scaleY(1); } }
  .mm-titulo {
    font-size: clamp(30px, 5.6vw, 96px); font-weight: 800; line-height: 1.06;
    letter-spacing: -.01em; text-wrap: balance;
    display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
  }
  .mm-artista { font-size: clamp(18px, 2.9vw, 50px); font-weight: 500; color: rgba(255,255,255,.78); }
  .mm-riel { height: .6vh; min-height: 4px; margin-top: 1.4vh; border-radius: 99px; background: rgba(255,255,255,.16); overflow: hidden; }
  .mm-avance { display: block; height: 100%; background: #22d3ee; transform-origin: left; transform: scaleX(0); }
  .mm-nota { font-size: clamp(11px, 1.25vw, 20px); color: rgba(255,255,255,.5); letter-spacing: .04em; }
  .mm-toca {
    display: none; position: absolute; left: 50%; top: 4vh; transform: translateX(-50%);
    padding: 1.2vh 2.4vw; border-radius: 999px; z-index: 2;
    background: rgba(0,0,0,.75); border: 1px solid rgba(255,255,255,.3);
    font-size: clamp(13px, 1.5vw, 22px);
  }
  .mm-wrap.bloqueado .mm-toca { display: block; }
  @media (max-aspect-ratio: 1/1) {
    .mm-caja { flex-direction: column; text-align: center; gap: 4vh; }
    .mm-caratula { width: min(70vw, 44vh); }
    .mm-rotulo { justify-content: center; }
  }
  @media (prefers-reduced-motion: reduce) {
    .mm-caja, .mm-barras i { animation: none; }
  }`;

  let conEstilos = false;
  function estilos() {
    if (conEstilos) return;
    const st = document.createElement('style');
    st.textContent = CSS;
    document.head.appendChild(st);
    conEstilos = true;
  }

  function avisar(play_id, event, detail) {
    fetch('/api/music/event', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ play_id, event, detail: detail || '' }),
    }).catch(() => {});
  }

  // Solo direcciones https: la ficha viene de fuera.
  const segura = (url) => (typeof url === 'string' && /^https:\/\//i.test(url) ? url : '');

  function create(cont) {
    estilos();
    const wrap = document.createElement('div');
    wrap.className = 'mm-wrap';
    const el = (etiqueta, clase, padre) => {
      const e = document.createElement(etiqueta);
      e.className = clase;
      (padre || wrap).appendChild(e);
      return e;
    };
    const fondo = el('div', 'mm-fondo');
    el('div', 'mm-velo');
    const toca = el('div', 'mm-toca');
    toca.textContent = 'Toca la pantalla para activar el sonido';
    const caja = el('div', 'mm-caja');
    const caratula = el('img', 'mm-caratula', caja);
    caratula.alt = '';
    const texto = el('div', 'mm-texto', caja);
    const rotulo = el('div', 'mm-rotulo', texto);
    const barras = el('span', 'mm-barras', rotulo);
    for (let i = 0; i < 4; i++) barras.appendChild(document.createElement('i'));
    const rotuloTxt = el('span', '', rotulo);
    const titulo = el('div', 'mm-titulo', texto);
    const artista = el('div', 'mm-artista', texto);
    const riel = el('div', 'mm-riel', texto);
    const avance = el('span', 'mm-avance', riel);
    const nota = el('div', 'mm-nota', texto);
    cont.appendChild(wrap);

    let audio = null;      // el reproductor de la canción en curso
    let actual = 0;        // play_id de lo que suena (0 = nada)
    let raf = 0;

    function pintarAvance() {
      raf = 0;
      if (!audio) return;
      const total = audio.duration && isFinite(audio.duration) ? audio.duration : 30;
      avance.style.transform = `scaleX(${Math.min(1, (audio.currentTime || 0) / total)})`;
      raf = requestAnimationFrame(pintarAvance);
    }

    function parar() {
      if (raf) { cancelAnimationFrame(raf); raf = 0; }
      if (audio) {
        // Sin `src` y sin oyentes: que un `error` tardío no avise de nada.
        audio.onplaying = audio.onended = audio.onerror = null;
        try { audio.pause(); } catch (e) { /* ya estaba parado */ }
        audio.removeAttribute('src');
        try { audio.load(); } catch (e) { /* nada que soltar */ }
        audio = null;
      }
      actual = 0;
      wrap.classList.remove('on', 'bloqueado');
    }

    function sonar(d) {
      const t = d.track;
      const url = segura(t.preview);
      const id = d.play_id;
      parar();
      actual = id;
      // La pantalla, antes que el audio: se ve qué va a sonar mientras carga.
      wrap.setAttribute('lang', d.lang || 'es');
      rotuloTxt.textContent = d.label || '';
      titulo.textContent = t.title || '';
      artista.textContent = t.artist || '';
      nota.textContent = d.note || '';
      const arte = segura(t.artwork);
      caratula.src = arte;
      caratula.style.visibility = arte ? 'visible' : 'hidden';
      fondo.style.backgroundImage = arte ? `url("${arte.replace(/["\\]/g, '')}")` : 'none';
      avance.style.transform = 'scaleX(0)';
      wrap.classList.add('on');
      if (!url) { avisar(id, 'error', 'la canción no trae audio'); return; }

      const a = new Audio();
      audio = a;
      a.preload = 'auto';
      a.volume = Math.max(0, Math.min(1, typeof d.volume === 'number' ? d.volume : 0.9));
      let avisado = false;
      a.onplaying = () => {
        if (a !== audio) return;
        wrap.classList.remove('bloqueado');
        if (!avisado) { avisado = true; avisar(id, 'playing'); }
        if (!raf) raf = requestAnimationFrame(pintarAvance);
      };
      a.onended = () => {
        if (a !== audio) return;
        avisar(id, 'ended');
        parar();
      };
      a.onerror = () => {
        if (a !== audio) return;
        const cod = (a.error && a.error.code) || 0;
        avisar(id, 'error', 'el navegador no pudo abrir el audio (código ' + cod + ')');
        parar();
      };
      a.src = url;
      const promesa = a.play();
      if (promesa && promesa.catch) {
        promesa.catch((err) => {
          if (a !== audio) return;
          if (err && err.name === 'NotAllowedError') {
            // El navegador bloqueó el sonido (falta el permiso de autoplay).
            // Se avisa al servidor para que no espere la canción entera, y se
            // pide un toque: ese toque deja el sonido activado para la
            // siguiente.
            wrap.classList.add('bloqueado');
            avisar(id, 'error', 'el navegador bloqueó el sonido: abre la proyección con el icono «Proyectar MECH» o toca la pantalla una vez');
          }
        });
      }
    }

    // Un toque en la pantalla: si el sonido estaba bloqueado, queda activado.
    document.addEventListener('click', () => {
      if (!wrap.classList.contains('bloqueado')) return;
      wrap.classList.remove('bloqueado');
      try {
        const prueba = new Audio();
        prueba.muted = true;
        const p = prueba.play();
        if (p && p.catch) p.catch(() => {});
      } catch (e) { /* da igual */ }
      parar();
    });

    return {
      /* `d` = lo que manda el servidor. `deEvento` = llegó por el evento
         `music` (puede empezar una canción) y no por el `state`. */
      apply(d, deEvento) {
        const suena = d && d.stage === 'playing' && d.track;
        if (!suena) { if (actual || wrap.classList.contains('on')) parar(); return; }
        if (!deEvento || d.play_id === actual) return;
        sonar(d);
      },
      clear() { parar(); },
    };
  }

  return { create };
})();
