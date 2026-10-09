/* MECH · Modo música — el video que suena en la pantalla de proyección.
 *
 * El modo entero corre en el servidor (backend/music.py + mech_app). Esta
 * página hace dos cosas: PONE el video que le mandan y AVISA de cómo va.
 *
 *   llega  {type: "music", stage: "playing", play_id,
 *           track: {title, artist, youtube: [{id, seconds}, ...]},
 *           label, note, volume, lang}
 *   avisa  POST /api/music/event  {play_id, event: "playing"|"ended"|"error",
 *                                  detail}
 *
 * El servidor no sabe cuánto tarda en cargar ni cuándo acaba de verdad: lo
 * sabe quien lo reproduce. Es el mismo trato que con los videos de marketing
 * (/api/playlist/ended).
 *
 * QUÉ SUENA: la canción entera, con su video, desde YouTube, con el
 * reproductor OFICIAL (IFrame API). `track.youtube` trae hasta tres videos
 * candidatos de la misma canción: si uno se niega a reproducirse aquí (pasa:
 * su dueño no lo permite fuera de youtube.com) o no arranca en 10 s, se
 * prueba el siguiente. Al empezar se le dice al servidor CUÁL suena
 * ("youtube:<id>"), porque de eso depende cuánto espera el final. Si no
 * arranca ninguno, se avisa del error y MECH lo dice.
 *
 * ⚠️ El reproductor va A LA VISTA y sin nada encima: es lo que piden las
 * condiciones de uso de YouTube. No lo escondas para oír solo el audio.
 *
 * ⚠️ El código de YouTube se baja de youtube.com SOLO la primera vez que
 * hace falta, desde aquí. No va como <script> en el HTML a propósito: el
 * resto de la proyección tiene que seguir cargando sin internet.
 *
 * ⚠️ Un video solo EMPIEZA con el evento «music» (trae un play_id nuevo). El
 * «state», que llega a cada rato, solo sirve para saber que hay que callar:
 * si también arrancara videos, cada cambio de fase lo reiniciaría.
 *
 * ⚠️ AUDIO: el navegador no deja sonar sin un gesto del usuario. En la Pi,
 * Chromium se abre con --autoplay-policy=no-user-gesture-required (el icono
 * «Proyectar MECH» ya lo lleva). Sin eso el video no arranca solo.
 *
 * ANUNCIOS: con la sesión de YouTube Premium iniciada en ESTE navegador, el
 * reproductor no debería ponerlos. Sin sesión, puede salir uno antes.
 *
 * Los textos que vienen de fuera (título, artista) van con textContent.
 */
window.MechMusic = (function () {
  /* Sin comillas invertidas dentro de este CSS: cerrarían la cadena. */
  const CSS = `
  .mm-wrap {
    position: fixed; inset: 0; z-index: 15;
    display: none; flex-direction: column;
    background: #000; color: #fff; overflow: hidden;
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, var(--cjk, sans-serif), sans-serif;
  }
  .mm-wrap.on { display: flex; }
  /* El video ocupa la pantalla y debajo va un pie con el nombre. NADA se
     pinta encima del reproductor. */
  .mm-marco { position: relative; flex: 1; min-height: 0; background: #000; }
  .mm-marco iframe { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; }
  .mm-pie {
    flex: none; display: flex; align-items: center; gap: 2.4vw;
    padding: 1.5vh 3vw; background: #06080b; border-top: 1px solid rgba(255,255,255,.08);
  }
  .mm-rotulo {
    display: flex; align-items: center; gap: 1.2vw;
    font-size: clamp(13px, 1.5vw, 24px); font-weight: 600; letter-spacing: .22em;
    text-transform: uppercase; color: #22d3ee; white-space: nowrap;
  }
  /* Las barritas que bailan: solo transform. */
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
    min-width: 0; flex: 1; font-size: clamp(15px, 2.3vw, 40px); font-weight: 700;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .mm-titulo span { font-weight: 400; color: rgba(255,255,255,.7); }
  .mm-nota { font-size: clamp(11px, 1.25vw, 20px); color: rgba(255,255,255,.5); letter-spacing: .04em; }
  @media (prefers-reduced-motion: reduce) { .mm-barras i { animation: none; } }`;

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

  // Un identificador de video de YouTube son 11 letras, números, - o _.
  const esVideo = (v) => !!(v && typeof v.id === 'string' && /^[\w-]{11}$/.test(v.id));

  // ── El reproductor de YouTube (se baja la primera vez que hace falta) ──
  let cargaYT = null;
  function cargarYouTube() {
    if (window.YT && window.YT.Player) return Promise.resolve(window.YT);
    if (cargaYT) return cargaYT;
    cargaYT = new Promise((listo, fallo) => {
      const antes = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        if (typeof antes === 'function') antes();
        listo(window.YT);
      };
      const s = document.createElement('script');
      s.src = 'https://www.youtube.com/iframe_api';
      s.onerror = () => fallo(new Error('no se pudo cargar YouTube'));
      document.head.appendChild(s);
      setTimeout(() => fallo(new Error('YouTube tardó demasiado en cargar')), 9000);
    });
    // Si falló (sin internet), que la próxima canción lo vuelva a intentar.
    cargaYT.catch(() => { cargaYT = null; });
    return cargaYT;
  }

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
    const marco = el('div', 'mm-marco');
    const pie = el('div', 'mm-pie');
    const rotulo = el('div', 'mm-rotulo', pie);
    const barras = el('span', 'mm-barras', rotulo);
    for (let i = 0; i < 4; i++) barras.appendChild(document.createElement('i'));
    const rotuloTxt = el('span', '', rotulo);
    const titulo = el('div', 'mm-titulo', pie);
    const nota = el('div', 'mm-nota', pie);
    cont.appendChild(wrap);

    let player = null;     // el reproductor de YouTube en curso
    let reloj = 0;         // espera a que un video arranque
    let actual = 0;        // play_id de lo que suena (0 = nada)

    function soltarVideo() {
      if (reloj) { clearTimeout(reloj); reloj = 0; }
      if (player) {
        const p = player;
        player = null;
        try { p.stopVideo(); } catch (e) { /* aún no estaba listo */ }
        try { p.destroy(); } catch (e) { /* ya no existe */ }
      }
      marco.textContent = '';
    }

    function parar() {
      soltarVideo();
      actual = 0;
      wrap.classList.remove('on');
    }

    function sonar(d) {
      const t = d.track;
      parar();
      actual = d.play_id;
      wrap.setAttribute('lang', d.lang || 'es');
      rotuloTxt.textContent = d.label || '';
      titulo.textContent = t.title || '';
      if (t.artist) {
        const quien = document.createElement('span');
        quien.textContent = '  ·  ' + t.artist;
        titulo.appendChild(quien);
      }
      nota.textContent = d.note || '';
      wrap.classList.add('on');
      probarVideo(d, (t.youtube || []).filter(esVideo), 0, '');
    }

    function probarVideo(d, videos, i, motivo) {
      const id = d.play_id;
      if (id !== actual) return;                    // ya se pidió otra cosa
      soltarVideo();
      if (i >= videos.length) {
        // Ninguno arrancó: se avisa (MECH lo dice) y se quita la pantalla.
        avisar(id, 'error', motivo || 'no llegó ningún video de YouTube');
        parar();
        return;
      }
      const v = videos[i];
      let sonando = false;
      const siguiente = (porque) => {
        if (id === actual && !sonando) probarVideo(d, videos, i + 1, porque);
      };
      // Si en 10 s ni suena ni da error, se pasa al siguiente: no se deja la
      // pantalla en negro esperando.
      reloj = setTimeout(() => siguiente(
        'el video no arrancó (¿sin internet?, ¿el navegador bloqueó el sonido? ' +
        'Abre la proyección con el icono «Proyectar MECH»)'), 10000);
      cargarYouTube().then((YT) => {
        if (id !== actual || sonando) return;
        const hueco = document.createElement('div');
        marco.appendChild(hueco);
        player = new YT.Player(hueco, {
          videoId: v.id,
          width: '100%', height: '100%',
          playerVars: {
            autoplay: 1, controls: 0, rel: 0, fs: 0, disablekb: 1,
            playsinline: 1, iv_load_policy: 3, origin: location.origin,
          },
          events: {
            onReady: (e) => {
              const vol = typeof d.volume === 'number' ? d.volume : 0.9;
              try { e.target.setVolume(Math.round(Math.max(0, Math.min(1, vol)) * 100)); } catch (x) { /* da igual */ }
              try { e.target.playVideo(); } catch (x) { /* lo dirá el reloj */ }
            },
            onStateChange: (e) => {
              if (id !== actual) return;
              if (e.data === 1 && !sonando) {          // 1 = reproduciendo
                sonando = true;
                if (reloj) { clearTimeout(reloj); reloj = 0; }
                avisar(id, 'playing', 'youtube:' + v.id);
              } else if (e.data === 0 && sonando) {    // 0 = terminó
                avisar(id, 'ended');
                parar();
              }
            },
            onError: (e) => {
              if (id !== actual) return;
              if (sonando) {
                avisar(id, 'error', 'YouTube cortó el video (código ' + e.data + ')');
                parar();
              } else {
                // 101 y 150: su dueño no deja reproducirlo fuera de YouTube.
                siguiente('YouTube no dejó reproducir el video aquí (código ' + e.data + ')');
              }
            },
          },
        });
      }).catch((err) => {
        if (id !== actual || sonando) return;
        avisar(id, 'error', (err && err.message) || 'no se pudo cargar YouTube');
        parar();
      });
    }

    return {
      /* `d` = lo que manda el servidor. `deEvento` = llegó por el evento
         «music» (puede empezar un video) y no por el «state». */
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
