/* MECH · Trivia — la pantalla del juego de preguntas.
 *
 * El juego entero corre en el servidor (backend/trivia.py). Esta página SOLO
 * pinta lo que le mandan, igual que los subtítulos:
 *
 *     {type: "trivia", stage, title, number, total, question, options,
 *      letters, chosen, correct, result, explanation, score}
 *
 * y lo mismo llega en /api/state como `state.trivia`, así que una pantalla
 * que se recargue a media partida vuelve a la pregunta correcta sola.
 *
 * Etapas:
 *   offer     -> "¿Jugamos?" mientras MECH espera un sí o un no
 *   question  -> la pregunta con sus opciones
 *   result    -> se revela: acierto (celebración) o fallo (marca la buena)
 *   final     -> marcador
 *
 * El CSS se inyecta desde aquí a propósito: así la pantalla de proyección y
 * cualquier otra vista lo usan con una sola línea, sin copiar estilos.
 */
window.MechTrivia = (function () {
  const CSS = `
  .mt-wrap {
    position: fixed; inset: 0; z-index: 20;
    display: none; align-items: center; justify-content: center;
    background: radial-gradient(circle at 50% 35%, #16161f 0%, #0b0b10 70%);
    font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #fff; padding: 3vmin 5vmin; overflow: hidden;
  }
  .mt-wrap.on { display: flex; }
  .mt-card { width: 100%; max-width: 1600px; }

  /* Barra de arriba: de qué va la partida y por dónde vamos. */
  .mt-top {
    display: flex; align-items: center; gap: 2vmin;
    font-family: "Space Mono", ui-monospace, Consolas, monospace;
    font-size: clamp(11px, 1.15vw, 22px); letter-spacing: .22em;
    text-transform: uppercase; color: #8a86b8; margin-bottom: 3vmin;
  }
  .mt-top .mt-tag { color: #fff; background: #534AB7; border-radius: 999px;
    padding: .5em 1.1em; letter-spacing: .18em; }
  .mt-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .mt-dots { display: flex; gap: .8vmin; }
  .mt-dot { width: 1.1vw; height: 1.1vw; min-width: 10px; min-height: 10px;
    border-radius: 50%; background: #2b2b3a; }
  .mt-dot.hit { background: #5DCAA5; box-shadow: 0 0 1.6vmin rgba(93,202,165,.7); }
  .mt-dot.miss { background: #E5484D; }
  .mt-dot.now { background: #7F77DD; animation: mt-pulse 1.4s ease-in-out infinite; }

  .mt-q {
    font-size: clamp(26px, 4.2vw, 72px); font-weight: 650;
    line-height: 1.2; letter-spacing: -.01em; text-wrap: balance;
    margin-bottom: 3vmin;
  }

  .mt-opts { display: flex; flex-direction: column; gap: 1.3vmin; }
  .mt-opt {
    display: flex; align-items: center; gap: 2.4vmin;
    background: rgba(255,255,255,.05);
    border: 2px solid rgba(255,255,255,.09); border-radius: 1.6vmin;
    padding: 1.5vmin 2.4vmin;
    font-size: clamp(19px, 2.7vw, 44px); font-weight: 500;
    transition: transform .28s cubic-bezier(.2,.7,.3,1), background .28s ease,
                border-color .28s ease, opacity .28s ease;
  }
  .mt-letter {
    flex: none; width: 4.2vw; height: 4.2vw;
    min-width: 36px; min-height: 36px;
    display: flex; align-items: center; justify-content: center;
    border-radius: 1vmin; background: #23233a; color: #b9b5ee;
    font-family: "Space Mono", ui-monospace, Consolas, monospace;
    font-size: clamp(17px, 2.5vw, 42px); font-weight: 700;
  }
  /* Revelación: la correcta se ilumina SIEMPRE (también al fallar: la gracia
     del juego es enterarse), y la equivocada que eligió se marca en rojo. */
  .mt-opt.good {
    background: rgba(93,202,165,.18); border-color: #5DCAA5;
    transform: scale(1.035);
  }
  .mt-opt.good .mt-letter { background: #5DCAA5; color: #06231a; }
  .mt-opt.bad {
    background: rgba(229,72,77,.16); border-color: #E5484D;
    animation: mt-shake .45s cubic-bezier(.36,.07,.19,.97);
  }
  .mt-opt.bad .mt-letter { background: #E5484D; color: #2a0608; }
  .mt-opt.dim { opacity: .34; }

  /* Veredicto grande, debajo de las opciones. */
  .mt-verdict {
    display: flex; align-items: center; gap: 2vmin; margin-top: 2.5vmin;
    font-size: clamp(21px, 3.2vw, 54px); font-weight: 700;
    animation: mt-pop .45s cubic-bezier(.2,1.5,.4,1) both;
  }
  .mt-verdict .mt-mark {
    width: 5vw; height: 5vw; min-width: 44px; min-height: 44px;
    display: flex; align-items: center; justify-content: center;
    border-radius: 50%; font-size: clamp(23px, 3.6vw, 60px); font-weight: 900;
  }
  .mt-verdict.win { color: #7de3c0; }
  .mt-verdict.win .mt-mark { background: #5DCAA5; color: #06231a;
    box-shadow: 0 0 6vmin rgba(93,202,165,.55); }
  .mt-verdict.lose { color: #ff9ea1; }
  .mt-verdict.lose .mt-mark { background: #E5484D; color: #2a0608; }
  .mt-why {
    margin-top: 1.4vmin; color: #a9a6c8;
    font-size: clamp(15px, 1.9vw, 32px); font-weight: 400; line-height: 1.35;
  }

  /* Pantallas de "¿jugamos?" y del marcador final. */
  .mt-center { text-align: center; }
  .mt-big {
    font-size: clamp(44px, 11vw, 220px); font-weight: 800; line-height: 1;
    letter-spacing: -.02em;
    animation: mt-pop .5s cubic-bezier(.2,1.5,.4,1) both;
  }
  .mt-big .mt-of { color: #6c6a8f; }
  .mt-sub {
    margin-top: 2.5vmin; font-size: clamp(19px, 2.9vw, 50px); color: #cfcce9;
    text-wrap: balance;
  }
  .mt-hint {
    margin-top: 3.5vmin;
    font-family: "Space Mono", ui-monospace, Consolas, monospace;
    font-size: clamp(13px, 1.4vw, 28px); letter-spacing: .2em;
    text-transform: uppercase; color: #8a86b8;
  }

  /* Confeti de la victoria. Piezas absolutas que solo se mueven con
     transform: es lo único que la Pi anima sin despeinarse. */
  .mt-confetti { position: fixed; inset: 0; pointer-events: none; overflow: hidden; }
  .mt-piece {
    position: absolute; top: -8vh; width: 0.9vw; height: 1.6vw;
    border-radius: 2px; opacity: 0;
    animation: mt-fall linear forwards;
  }

  @keyframes mt-fall {
    0%   { opacity: 1; transform: translate3d(0,0,0) rotate(0deg); }
    100% { opacity: .9; transform: translate3d(var(--dx), 112vh, 0) rotate(var(--spin)); }
  }
  @keyframes mt-pop {
    0%   { opacity: 0; transform: scale(.72); }
    100% { opacity: 1; transform: scale(1); }
  }
  @keyframes mt-shake {
    10%, 90% { transform: translateX(-1%); }
    30%, 70% { transform: translateX(2%); }
    50%      { transform: translateX(-2%); }
  }
  @keyframes mt-pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%      { opacity: .45; transform: scale(.8); }
  }
  `;

  const COLORES = ['#5DCAA5', '#7F77DD', '#E8C468', '#fff', '#534AB7'];

  function inyectarCSS() {
    if (document.getElementById('mech-trivia-css')) return;
    const st = document.createElement('style');
    st.id = 'mech-trivia-css';
    st.textContent = CSS;
    document.head.appendChild(st);
  }

  function esc(t) {
    const d = document.createElement('div');
    d.textContent = t == null ? '' : String(t);
    return d.innerHTML;
  }

  /** Marcador de bolitas: una por pregunta (verde acertada, roja fallada). */
  function dots(d) {
    let html = '';
    for (let i = 1; i <= (d.total || 0); i++) {
      let cls = '';
      if (i < d.number) cls = 'hit';          // ya pasó (el detalle va en el score)
      else if (i === d.number) cls = 'now';
      html += `<span class="mt-dot ${cls}"></span>`;
    }
    return `<div class="mt-dots">${html}</div>`;
  }

  function confeti(wrap) {
    const capa = document.createElement('div');
    capa.className = 'mt-confetti';
    for (let i = 0; i < 40; i++) {
      const p = document.createElement('div');
      p.className = 'mt-piece';
      p.style.left = Math.random() * 100 + 'vw';
      p.style.background = COLORES[i % COLORES.length];
      p.style.setProperty('--dx', (Math.random() * 30 - 15) + 'vw');
      p.style.setProperty('--spin', (Math.random() * 900 - 450) + 'deg');
      p.style.animationDuration = (1.8 + Math.random() * 1.4) + 's';
      p.style.animationDelay = (Math.random() * 0.35) + 's';
      capa.appendChild(p);
    }
    wrap.appendChild(capa);
    setTimeout(() => capa.remove(), 4200);
  }

  /**
   * @param {Element} cont contenedor donde vive el juego (se le añade la capa).
   */
  function create(cont) {
    inyectarCSS();
    const wrap = document.createElement('div');
    wrap.className = 'mt-wrap';
    cont.appendChild(wrap);
    let firma = null;      // qué hay pintado, para no repintar de más

    function pintarPregunta(d, revelando) {
      const letras = d.letters || [];
      const opciones = (d.options || []).map((op, i) => {
        let cls = '';
        if (revelando) {
          if (i === d.correct) cls = 'good';
          else if (i === d.chosen) cls = 'bad';
          else cls = 'dim';
        }
        return `<div class="mt-opt ${cls}">
                  <span class="mt-letter">${esc(letras[i] || '')}</span>
                  <span>${esc(op)}</span>
                </div>`;
      }).join('');

      let veredicto = '';
      if (revelando) {
        const gano = d.result === 'correct';
        const marca = gano ? '✓' : '✕';
        const texto = gano ? '¡Correcto!'
          : (d.result === 'pass' ? 'Esta era la buena' : 'No era esa');
        veredicto = `<div class="mt-verdict ${gano ? 'win' : 'lose'}">
            <span class="mt-mark">${marca}</span>
            <span>${texto}${d.explanation ? `<div class="mt-why">${esc(d.explanation)}</div>` : ''}</span>
          </div>`;
      }

      wrap.innerHTML = `<div class="mt-card">
          <div class="mt-top">
            <span class="mt-tag">Trivia</span>
            <span class="mt-title">${esc(d.title || '')}</span>
            ${dots(d)}
            <span>${d.number || 0}/${d.total || 0}</span>
          </div>
          <div class="mt-q">${esc(d.question)}</div>
          <div class="mt-opts">${opciones}</div>
          ${veredicto}
        </div>`;
    }

    function pintarOferta(d) {
      wrap.innerHTML = `<div class="mt-card mt-center">
          <div class="mt-big">¿Jugamos?</div>
          <div class="mt-sub">Una trivia sobre ${esc(d.title || 'lo que te conté')}</div>
          <div class="mt-hint">Responde «sí» o «no»</div>
        </div>`;
    }

    function pintarFinal(d) {
      const total = d.total || 0, score = d.score || 0;
      const perfecto = total > 0 && score === total;
      const mensaje = perfecto ? '¡Todas correctas!'
        : (score === 0 ? 'Otra vez será' : '¡Bien jugado!');
      wrap.innerHTML = `<div class="mt-card mt-center">
          <div class="mt-hint" style="margin:0 0 2vmin">Resultado</div>
          <div class="mt-big">${score}<span class="mt-of">/${total}</span></div>
          <div class="mt-sub">${mensaje}</div>
        </div>`;
      if (perfecto) confeti(wrap);
    }

    return {
      /** Pinta el estado que manda el servidor (o lo esconde si no hay juego). */
      apply(d) {
        d = d || {};
        if (!d.active) {
          if (firma !== null) { wrap.className = 'mt-wrap'; wrap.innerHTML = ''; firma = null; }
          return;
        }
        const nueva = [d.stage, d.number, d.result, d.chosen, d.score].join('|');
        if (nueva === firma) return;
        const antes = firma;
        firma = nueva;
        wrap.className = 'mt-wrap on';

        if (d.stage === 'offer') pintarOferta(d);
        else if (d.stage === 'final') pintarFinal(d);
        else if (d.stage === 'result') {
          pintarPregunta(d, true);
          // El confeti solo al ACERTAR, y solo al llegar aquí (no si la
          // pantalla se recarga con el resultado ya puesto).
          if (d.result === 'correct' && antes !== null) confeti(wrap);
        } else pintarPregunta(d, false);
      },
      clear() { this.apply({ active: false }); },
    };
  }

  return { create };
})();
