/* MECH · Modo música — el video que suena en la pantalla de proyección.
 *
 * El modo entero corre en el servidor (backend/music.py + mech_app). Esta
 * página hace dos cosas: PONE el video que le mandan y AVISA de cómo va.
 *
 *   llega  {type: "music", stage: "playing", play_id,
 *           track: {title, artist, seconds,
 *                   youtube: [{id, seconds, channel, thumb}, ...]},
 *           label, note, volume, lang}
 *   avisa  POST /api/music/event  {play_id, event: "playing"|"ended"|"error",
 *                                  detail}
 *
 * El servidor no sabe cuánto tarda en cargar ni cuándo acaba de verdad: lo
 * sabe quien lo reproduce. Es el mismo trato que con los videos de marketing
 * (/api/playlist/ended).
 *
 * QUÉ SE VE (oct 2026, pedido del equipo): el video a un lado y, al otro, la
 * TARJETA de la canción — título, artista, por dónde va y de dónde sale —
 * sobre la miniatura del video desenfocada de fondo. Es el diseño de la
 * primera versión (la de la carátula), con el video donde iba la carátula.
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
 * condiciones de uso de YouTube. La tarjeta va AL LADO, nunca sobre el video.
 * No lo escondas ni lo tapes para oír solo el audio.
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
 * Los textos que vienen de fuera (título, artista, canal) van con
 * textContent. Solo se animan transform y opacity, como en la trivia.
 */
window.MechMusic = (function () {
  /* Sin comillas invertidas dentro de este CSS: cerrarían la cadena. */
  const CSS = `
  .mm-wrap {
    position: fixed; inset: 0; z-index: 15;
    display: none; align-items: center; justify-content: center;
    background: #06080b; color: #fff; overflow: hidden;
    font-family: "Sora", -apple-system, "Segoe UI", Roboto, Helvetica, Arial, var(--cjk, sans-serif), sans-serif;
  }
  .mm-wrap.on { display: flex; }
  /* La miniatura del video, enorme y desenfocada, de fondo. Es una imagen
     quieta: el desenfoque se calcula una vez, no en cada fotograma. */
  .mm-fondo {
    position: absolute; inset: -12%;
    background-size: cover; background-position: center;
    filter: blur(60px) saturate(1.3); opacity: .5;
  }
  .mm-velo { position: absolute; inset: 0; background: radial-gradient(ellipse at center, rgba(6,8,11,.3), rgba(6,8,11,.9)); }
  .mm-caja {
    position: relative; display: flex; align-items: center; gap: 2.6vw;
    width: 95%; max-width: 2600px;
    animation: mm-entra .6s cubic-bezier(.23,1,.32,1) backwards;
  }
  @keyframes mm-entra { from { opacity: 0; transform: translateY(3vh) scale(.97); } }
  /* El video. NADA se pinta encima del reproductor. Mientras carga se ve su
     miniatura (va de fondo de este marco; el reproductor la tapa al llegar). */
  .mm-marco {
    position: relative; flex: none; width: min(62vw, 150vh); aspect-ratio: 16 / 9;
    border-radius: 2.2vmin; overflow: hidden;
    background: #000 center / cover no-repeat;
    box-shadow: 0 3vh 9vh rgba(0,0,0,.6), 0 0 0 1px rgba(255,255,255,.08);
  }
  .mm-marco iframe { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; }
  /* La tarjeta de la canción. */
  .mm-ficha {
    min-width: 0; flex: 1; display: flex; flex-direction: column; gap: 2.2vh;
    padding: 4vh 2.4vw; border-radius: 2.6vmin;
    background: rgba(9,12,16,.66); border: 1px solid rgba(255,255,255,.1);
    box-shadow: 0 2vh 6vh rgba(0,0,0,.4);
  }
  .mm-rotulo {
    display: flex; align-items: center; gap: 1vw;
    font-size: clamp(12px, 1.25vw, 22px); font-weight: 600; letter-spacing: .22em;
    text-transform: uppercase; color: #22d3ee; white-space: nowrap;
  }
  /* Las barritas bailan solo mientras suena: solo transform. */
  .mm-barras { display: inline-flex; align-items: flex-end; gap: .35vw; height: 1.5vw; min-height: 14px; }
  .mm-barras i {
    width: .4vw; min-width: 3px; height: 100%; border-radius: 2px; background: currentColor;
    transform-origin: bottom; transform: scaleY(.25);
  }
  .mm-wrap.sonando .mm-barras i { animation: mm-baila 1s ease-in-out infinite; }
  .mm-wrap.sonando .mm-barras i:nth-child(2) { animation-duration: .7s; animation-delay: -.3s; }
  .mm-wrap.sonando .mm-barras i:nth-child(3) { animation-duration: 1.2s; animation-delay: -.6s; }
  .mm-wrap.sonando .mm-barras i:nth-child(4) { animation-duration: .85s; animation-delay: -.15s; }
  @keyframes mm-baila { 0%, 100% { transform: scaleY(.25); } 50% { transform: scaleY(1); } }
  .mm-titulo {
    font-size: clamp(24px, 3.5vw, 64px); font-weight: 800; line-height: 1.08;
    letter-spacing: -.01em; text-wrap: balance; overflow-wrap: anywhere;
    display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden;
  }
  .mm-artista {
    font-size: clamp(16px, 2.1vw, 38px); font-weight: 500; color: rgba(255,255,255,.8);
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  }
  .mm-artista:empty { display: none; }
  .mm-riel { height: .6vh; min-height: 4px; margin-top: 1.6vh; border-radius: 99px; background: rgba(255,255,255,.16); overflow: hidden; }
  .mm-avance {
    display: block; height: 100%; border-radius: 99px; background: #22d3ee;
    transform-origin: left; transform: scaleX(0); transition: transform .5s linear;
  }
  .mm-tiempos {
    display: flex; justify-content: space-between; margin-top: -1vh;
    font-size: clamp(11px, 1.15vw, 20px); color: rgba(255,255,255,.62);
    font-variant-numeric: tabular-nums;
  }
  .mm-nota {
    font-size: clamp(11px, 1.15vw, 20px); color: rgba(255,255,255,.5); letter-spacing: .04em;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  /* Pantalla de pie (un teléfono): el video arriba y la tarjeta debajo. */
  @media (max-aspect-ratio: 1/1) {
    .mm-caja { flex-direction: column; align-items: stretch; gap: 3vh; }
    .mm-marco { width: 100%; }
    .mm-ficha { flex: none; }
  }
  @media (prefers-reduced-motion: reduce) {
    .mm-caja, .mm-wrap.sonando .mm-barras i { animation: none; }
    .mm-avance { transition: none; }
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

  // Un identificador de video de YouTube son 11 letras, números, - o _.
  const esVideo = (v) => !!(v && typeof v.id === 'string' && /^[\w-]{11}$/.test(v.id));
  // La miniatura viene de fuera y va dentro de un `url(...)`: solo https y
  // solo letras que no puedan cerrar esa regla.
  const segura = (u) => (typeof u === 'string' && /^https:\/\/[\w.-]+\/[\w\-./%?=&]*$/.test(u) ? u : '');
  const reloj = (s) => {
    s = Math.max(0, Math.floor(s || 0));
    return Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0');
  };

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
    const fondo = el('div', 'mm-fondo');
    el('div', 'mm-velo');
    const caja = el('div', 'mm-caja');
    const marco = el('div', 'mm-marco', caja);
    const ficha = el('div', 'mm-ficha', caja);
    const rotulo = el('div', 'mm-rotulo', ficha);
    const barras = el('span', 'mm-barras', rotulo);
    for (let i = 0; i < 4; i++) barras.appendChild(document.createElement('i'));
    const rotuloTxt = el('span', '', rotulo);
    const titulo = el('div', 'mm-titulo', ficha);
    const artista = el('div', 'mm-artista', ficha);
    const avance = el('span', 'mm-avance', el('div', 'mm-riel', ficha));
    const tiempos = el('div', 'mm-tiempos', ficha);
    const va = el('span', '', tiempos);
    const dura = el('span', '', tiempos);
    const nota = el('div', 'mm-nota', ficha);
    cont.appendChild(wrap);

    let player = null;     // el reproductor de YouTube en curso
    let espera = 0;        // espera a que un video arranque
    let pulso = 0;         // refresco de la barra de avance
    let actual = 0;        // play_id de lo que suena (0 = nada)

    function soltarVideo() {
      if (espera) { clearTimeout(espera); espera = 0; }
      if (pulso) { clearInterval(pulso); pulso = 0; }
      wrap.classList.remove('sonando');
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

    /* La barra de la tarjeta: por dónde va y cuánto dura. `segundos` es lo
       que dijo el buscador; en cuanto el reproductor sabe la duración de
       verdad, manda la suya. */
    function pintarAvance(va_s, total_s) {
      avance.style.transform = 'scaleX(' + (total_s > 0 ? Math.min(1, va_s / total_s) : 0) + ')';
      va.textContent = reloj(va_s);
      dura.textContent = total_s > 0 ? reloj(total_s) : '';
    }

    function sonar(d) {
      const t = d.track;
      parar();
      actual = d.play_id;
      wrap.setAttribute('lang', d.lang || 'es');
      rotuloTxt.textContent = d.label || '';
      titulo.textContent = t.title || '';
      artista.textContent = t.artist || '';
      // La tarjeta entra con su animación en cada canción.
      caja.style.animation = 'none';
      void caja.offsetWidth;
      caja.style.animation = '';
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
      // La tarjeta habla del video que se está probando: su miniatura de
      // fondo, de dónde sale y cuánto dura.
      const mini = segura(v.thumb);
      fondo.style.backgroundImage = mini ? 'url("' + mini + '")' : '';
      marco.style.backgroundImage = mini ? 'url("' + mini + '")' : '';
      nota.textContent = [v.channel, d.note].filter(Boolean).join('  ·  ');
      const segundos = v.seconds || d.track.seconds || 0;
      pintarAvance(0, segundos);
      let sonando = false;
      const siguiente = (porque) => {
        if (id === actual && !sonando) probarVideo(d, videos, i + 1, porque);
      };
      // Si en 10 s ni suena ni da error, se pasa al siguiente: no se deja la
      // pantalla esperando.
      espera = setTimeout(() => siguiente(
        'el video no arrancó (¿sin internet?, ¿el navegador bloqueó el sonido? ' +
        'Abre la proyección con el icono «Proyectar MECH»)'), 10000);
      cargarYouTube().then((YT) => {
        if (id !== actual || sonando) return;
        const hueco = document.createElement('div');
        marco.appendChild(hueco);
        const p = new YT.Player(hueco, {
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
                if (espera) { clearTimeout(espera); espera = 0; }
                wrap.classList.add('sonando');
                pulso = setInterval(() => {
                  if (player !== p) return;
                  try { pintarAvance(p.getCurrentTime() || 0, p.getDuration() || segundos); } catch (x) { /* aún no */ }
                }, 500);
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
        player = p;
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
