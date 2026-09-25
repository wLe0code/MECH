/* MECH · Trivia — la pantalla del juego de preguntas, estilo Kahoot.
 *
 * El juego entero corre en el servidor (backend/trivia.py). Esta página SOLO
 * pinta lo que le mandan, igual que los subtítulos:
 *
 *     {type: "trivia", stage, title, number, total, question, options,
 *      letters, chosen, correct, result, explanation, score, history, lang}
 *
 * y lo mismo llega en /api/state como `state.trivia`, así que una pantalla
 * que se recargue a media partida vuelve a la pregunta correcta sola.
 *
 * Etapas:
 *   offer     -> "¿Jugamos?" mientras MECH espera un sí o un no
 *   loading   -> "Preparando las preguntas…" (Claude las está escribiendo)
 *   question  -> la pregunta con sus opciones en fichas de colores
 *   result    -> acierto (confeti) o fallo (se marca la buena y se dice)
 *   final     -> marcador
 *
 * ESTILO KAHOOT (pedido del equipo, sep 2026): fondo morado y una ficha de
 * color por opción, cada una con su figura (triángulo rojo, rombo azul,
 * círculo amarillo, cuadrado verde). Las fichas llevan además la LETRA bien
 * grande, porque aquí se contesta hablando: «la A», «la B»…
 *
 * Los textos fijos de la pantalla salen en el idioma activo (`lang`), igual
 * que lo que dice MECH. Las preguntas ya vienen escritas en ese idioma.
 *
 * Todo lo que se anima usa solo transform y opacity: es lo único que la Pi
 * anima sin despeinarse. Nada de filtros ni sombras animadas.
 *
 * El CSS se inyecta desde aquí a propósito: así la pantalla de proyección y
 * cualquier otra vista lo usan con una sola línea, sin copiar estilos.
 */
window.MechTrivia = (function () {
  const CSS = `
  .mt-wrap {
    position: fixed; inset: 0; z-index: 20;
    display: none; flex-direction: column;
    background:
      radial-gradient(circle at 18% 12%, rgba(255,255,255,.07) 0 9vmin, transparent 9.2vmin),
      radial-gradient(circle at 88% 85%, rgba(255,255,255,.05) 0 14vmin, transparent 14.2vmin),
      linear-gradient(160deg, #4a1c96 0%, #34106f 55%, #230a4d 100%);
    font-family: "Sora", -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #fff; padding: 3vmin 4vmin 4vmin; overflow: hidden;
  }
  .mt-wrap.on { display: flex; }

  /* Barra de arriba: de qué va la partida y por dónde vamos. */
  .mt-top {
    display: flex; align-items: center; gap: 2vmin; flex: none;
    font-family: "Space Mono", ui-monospace, Consolas, monospace;
    font-size: clamp(11px, 1.2vw, 22px); letter-spacing: .18em;
    text-transform: uppercase; color: rgba(255,255,255,.75);
  }
  .mt-tag { color: #34106f; background: #fff; border-radius: 999px;
    padding: .45em 1.1em; font-weight: 700; }
  .mt-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .mt-dots { display: flex; gap: .9vmin; }
  .mt-dot { width: 1.3vmin; height: 1.3vmin; min-width: 9px; min-height: 9px;
    border-radius: 50%; background: rgba(255,255,255,.25); }
  .mt-dot.correct { background: #2fd26b; }
  .mt-dot.wrong { background: #ff4d6a; }
  .mt-dot.pass { background: rgba(255,255,255,.55); }
  .mt-dot.now { background: #fff; animation: mt-pulse 1.3s ease-in-out infinite; }
  .mt-count { font-weight: 700; color: #fff; }

  /* La pregunta: una banda blanca, como en Kahoot. */
  .mt-q {
    flex: none; margin: 2.6vmin 0 1.2vmin;
    background: #fff; color: #1c1033; border-radius: 1.4vmin;
    padding: 2.4vmin 3.4vmin; text-align: center;
    font-size: clamp(22px, 3.5vw, 64px); font-weight: 700; line-height: 1.18;
    text-wrap: balance; box-shadow: 0 .8vmin 0 rgba(0,0,0,.18);
    animation: mt-drop .45s cubic-bezier(.2,.9,.3,1.2) both;
  }
  .mt-say {
    flex: none; text-align: center; margin-bottom: 2vmin;
    font-family: "Space Mono", ui-monospace, Consolas, monospace;
    font-size: clamp(11px, 1.25vw, 22px); letter-spacing: .14em;
    text-transform: uppercase; color: rgba(255,255,255,.72);
  }

  /* Las fichas de las opciones. */
  .mt-grid { flex: 1; display: grid; gap: 1.8vmin; min-height: 0; }
  .mt-grid.n2 { grid-template-columns: repeat(2, 1fr); }
  .mt-grid.n3 { grid-template-columns: repeat(3, 1fr); }
  .mt-grid.n4 { grid-template-columns: repeat(2, 1fr); grid-template-rows: repeat(2, 1fr); }
  .mt-tile {
    position: relative; border-radius: 1.6vmin; min-height: 0;
    display: flex; flex-direction: column; justify-content: space-between;
    padding: 2.4vmin 2.8vmin; color: #fff;
    box-shadow: inset 0 -.9vmin 0 rgba(0,0,0,.22);
    animation: mt-rise .5s cubic-bezier(.2,.9,.3,1.15) both;
    transition: opacity .35s ease, transform .35s cubic-bezier(.2,.9,.3,1.2);
  }
  .mt-tile:nth-child(2) { animation-delay: .07s; }
  .mt-tile:nth-child(3) { animation-delay: .14s; }
  .mt-tile:nth-child(4) { animation-delay: .21s; }
  .mt-c0 { background: #e21b3c; }
  .mt-c1 { background: #1368ce; }
  .mt-c2 { background: #d89e00; }
  .mt-c3 { background: #26890c; }
  .mt-tile-head { display: flex; align-items: center; justify-content: space-between; }
  .mt-shape { width: 7vmin; height: 7vmin; min-width: 34px; min-height: 34px; }
  .mt-shape svg { width: 100%; height: 100%; display: block; }
  .mt-letter {
    width: 8vmin; height: 8vmin; min-width: 38px; min-height: 38px;
    border-radius: 50%; background: rgba(255,255,255,.95);
    display: flex; align-items: center; justify-content: center;
    font-family: "Space Mono", ui-monospace, Consolas, monospace;
    font-size: clamp(18px, 4.4vmin, 60px); font-weight: 700; color: #1c1033;
  }
  .mt-opt-text {
    font-size: clamp(20px, 3.1vw, 58px); font-weight: 700; line-height: 1.15;
    text-shadow: 0 .3vmin 0 rgba(0,0,0,.25); text-wrap: balance;
    overflow-wrap: anywhere;
  }
  /* Marca de acierto/fallo encima de la ficha al revelar. */
  .mt-mark {
    position: absolute; top: 50%; left: 50%;
    width: 14vmin; height: 14vmin; min-width: 60px; min-height: 60px;
    margin: -7vmin 0 0 -7vmin; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: clamp(34px, 8vmin, 120px); font-weight: 900; line-height: 1;
    animation: mt-pop .45s cubic-bezier(.2,1.6,.4,1) both;
  }
  .mt-tile.good .mt-mark { background: #fff; color: #26890c; }
  .mt-tile.bad .mt-mark { background: #fff; color: #e21b3c; }
  .mt-tile.good { transform: scale(1.04); z-index: 1; }
  .mt-tile.bad { opacity: .8; }
  .mt-tile.dim { opacity: .22; }
  /* Al revelar NO se repite la entrada: su último fotograma (opacidad 1) se
     queda "pegado" y taparía el atenuado de las fichas que no eran. Solo se
     animan la buena (celebración) y la equivocada (sacudida). */
  .mt-wrap.reveal .mt-q, .mt-wrap.reveal .mt-tile { animation: none; }
  .mt-wrap.reveal .mt-tile.good.win { animation: mt-cheer .9s cubic-bezier(.2,1.4,.4,1) .1s both; }
  .mt-wrap.reveal .mt-tile.bad { animation: mt-shake .5s cubic-bezier(.36,.07,.19,.97) both; }

  /* Banda del veredicto, abajo, que sube al revelar. Va EN el flujo (no
     encima): así las fichas se encogen y su texto no queda tapado. */
  .mt-banner {
    position: relative; flex: none; margin: 2.2vmin -4vmin -4vmin;
    padding: 2.6vmin 4vmin; display: flex; align-items: center; gap: 2.4vmin;
    font-size: clamp(22px, 3.4vw, 62px); font-weight: 800;
    animation: mt-slide .45s cubic-bezier(.2,.9,.3,1.1) both; z-index: 2;
  }
  .mt-banner.win { background: #26890c; }
  .mt-banner.lose { background: #e21b3c; }
  .mt-banner.pass { background: #1c1033; }
  .mt-banner .mt-icon {
    flex: none; width: 9vmin; height: 9vmin; min-width: 44px; min-height: 44px;
    border-radius: 50%; background: #fff;
    display: flex; align-items: center; justify-content: center;
    font-size: clamp(24px, 5.4vmin, 80px); font-weight: 900;
  }
  .mt-banner.win .mt-icon { color: #26890c; }
  .mt-banner.lose .mt-icon { color: #e21b3c; }
  .mt-banner.pass .mt-icon { color: #1c1033; }
  .mt-banner small {
    display: block; font-size: .5em; font-weight: 600; opacity: .95;
    margin-top: .35em; line-height: 1.3;
  }
  .mt-banner small + small { font-weight: 400; opacity: .85; }

  /* Pantallas centradas: ¿jugamos?, preparando y marcador. */
  .mt-center {
    flex: 1; display: flex; flex-direction: column; align-items: center;
    justify-content: center; text-align: center;
  }
  .mt-big {
    font-size: clamp(46px, 10vw, 200px); font-weight: 800; line-height: 1;
    letter-spacing: -.02em;
    animation: mt-pop .55s cubic-bezier(.2,1.5,.4,1) both;
  }
  .mt-big .mt-of { opacity: .55; }
  .mt-sub {
    margin-top: 2.6vmin; max-width: 80vw;
    font-size: clamp(20px, 3vw, 54px); font-weight: 600; text-wrap: balance;
  }
  .mt-hint {
    margin-top: 3.4vmin;
    font-family: "Space Mono", ui-monospace, Consolas, monospace;
    font-size: clamp(12px, 1.4vw, 26px); letter-spacing: .2em;
    text-transform: uppercase; color: rgba(255,255,255,.75);
  }
  .mt-shapes { display: flex; gap: 3vmin; margin-bottom: 4vmin; }
  .mt-shapes .mt-shape {
    width: 11vmin; height: 11vmin; border-radius: 1.4vmin;
    padding: 2vmin; box-sizing: border-box;
    animation: mt-float 2.2s ease-in-out infinite;
  }
  .mt-shapes .mt-shape:nth-child(2) { animation-delay: .25s; }
  .mt-shapes .mt-shape:nth-child(3) { animation-delay: .5s; }
  .mt-shapes .mt-shape:nth-child(4) { animation-delay: .75s; }
  .mt-shapes.spin .mt-shape { animation: mt-hop .9s ease-in-out infinite; }
  .mt-shapes.spin .mt-shape:nth-child(2) { animation-delay: .15s; }
  .mt-shapes.spin .mt-shape:nth-child(3) { animation-delay: .3s; }
  .mt-shapes.spin .mt-shape:nth-child(4) { animation-delay: .45s; }

  /* Confeti de la victoria. Piezas absolutas que solo se mueven con
     transform. */
  .mt-confetti { position: fixed; inset: 0; pointer-events: none; overflow: hidden; z-index: 3; }
  .mt-piece {
    position: absolute; top: -8vh; width: 1vw; height: 1.8vw;
    min-width: 8px; min-height: 14px; border-radius: 2px; opacity: 0;
    animation: mt-fall linear forwards;
  }

  @keyframes mt-fall {
    0%   { opacity: 1; transform: translate3d(0,0,0) rotate(0deg); }
    100% { opacity: .9; transform: translate3d(var(--dx), 115vh, 0) rotate(var(--spin)); }
  }
  @keyframes mt-pop {
    0%   { opacity: 0; transform: scale(.6); }
    100% { opacity: 1; transform: scale(1); }
  }
  @keyframes mt-drop {
    0%   { opacity: 0; transform: translateY(-3vh) scale(.97); }
    100% { opacity: 1; transform: none; }
  }
  @keyframes mt-rise {
    0%   { opacity: 0; transform: translateY(6vh) scale(.94); }
    100% { opacity: 1; transform: none; }
  }
  @keyframes mt-slide {
    0%   { transform: translateY(100%); }
    100% { transform: none; }
  }
  @keyframes mt-cheer {
    0%   { transform: scale(1.04); }
    30%  { transform: scale(1.12) rotate(-1.5deg); }
    55%  { transform: scale(1.02) rotate(1deg); }
    100% { transform: scale(1.06); }
  }
  @keyframes mt-shake {
    10%, 90% { transform: translateX(-1%); }
    30%, 70% { transform: translateX(2%); }
    50%      { transform: translateX(-2%); }
  }
  @keyframes mt-pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%      { opacity: .45; transform: scale(.75); }
  }
  @keyframes mt-float {
    0%, 100% { transform: translateY(0) rotate(0deg); }
    50%      { transform: translateY(-2.2vmin) rotate(-4deg); }
  }
  @keyframes mt-hop {
    0%, 100% { transform: translateY(0) scale(1); }
    40%      { transform: translateY(-3vmin) scale(1.08); }
  }
  @media (prefers-reduced-motion: reduce) {
    .mt-wrap * { animation-duration: .01s !important; animation-iteration-count: 1 !important; }
  }
  `;

  // Las cuatro figuras de Kahoot, en blanco sobre el color de la ficha.
  const SHAPES = [
    '<svg viewBox="0 0 32 32"><path fill="#fff" d="M16 3 30 28H2Z"/></svg>',             // triángulo
    '<svg viewBox="0 0 32 32"><path fill="#fff" d="M16 2 30 16 16 30 2 16Z"/></svg>',     // rombo
    '<svg viewBox="0 0 32 32"><circle fill="#fff" cx="16" cy="16" r="13"/></svg>',        // círculo
    '<svg viewBox="0 0 32 32"><rect fill="#fff" x="4" y="4" width="24" height="24" rx="2"/></svg>', // cuadrado
  ];
  const COLORES = ['#e21b3c', '#1368ce', '#d89e00', '#26890c', '#ffffff'];

  // Textos fijos de la pantalla, en los cuatro idiomas de MECH.
  const T = {
    es: {
      offer: '¿Jugamos?',
      offerSub: '¿Te gustaría realizar una trivia para comprobar tu conocimiento?',
      offerHint: 'Responde «sí» o «no»',
      about: 'Sobre',
      loading: 'Preparando las preguntas…',
      say: 'Contesta en voz alta: «la A», «la B»…',
      correct: '¡Correcto!',
      wrong: 'No has acertado',
      pass: 'Esta era la respuesta',
      rightIs: (l, a) => `La respuesta correcta es la ${l}: ${a}`,
      result: 'Resultado',
      perfect: '¡Todas correctas!',
      zero: 'Otra vez será',
      good: '¡Bien jugado!',
    },
    en: {
      offer: 'Shall we play?',
      offerSub: 'Would you like to take a trivia to test your knowledge?',
      offerHint: 'Answer “yes” or “no”',
      about: 'About',
      loading: 'Getting the questions ready…',
      say: 'Answer out loud: “A”, “B”…',
      correct: 'Correct!',
      wrong: 'Not quite',
      pass: 'Here is the answer',
      rightIs: (l, a) => `The correct answer is ${l}: ${a}`,
      result: 'Score',
      perfect: 'All correct!',
      zero: 'Better luck next time',
      good: 'Well played!',
    },
    fr: {
      offer: 'On joue ?',
      offerSub: 'Aimerais-tu faire un quiz pour tester tes connaissances ?',
      offerHint: 'Réponds « oui » ou « non »',
      about: 'Sur',
      loading: 'Je prépare les questions…',
      say: 'Réponds à voix haute : « la A », « la B »…',
      correct: 'Correct !',
      wrong: 'Raté',
      pass: 'Voici la réponse',
      rightIs: (l, a) => `La bonne réponse est la ${l} : ${a}`,
      result: 'Résultat',
      perfect: 'Tout juste !',
      zero: 'Ce sera pour la prochaine fois',
      good: 'Bien joué !',
    },
    pt: {
      offer: 'Vamos jogar?',
      offerSub: 'Gostarias de fazer uma trivia para testar o teu conhecimento?',
      offerHint: 'Responde «sim» ou «não»',
      about: 'Sobre',
      loading: 'A preparar as perguntas…',
      say: 'Responde em voz alta: «a A», «a B»…',
      correct: 'Certo!',
      wrong: 'Não acertaste',
      pass: 'Esta era a resposta',
      rightIs: (l, a) => `A resposta certa é a ${l}: ${a}`,
      result: 'Resultado',
      perfect: 'Todas certas!',
      zero: 'Fica para a próxima',
      good: 'Bem jogado!',
    },
  };

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

  function textos(d) {
    return T[(d && d.lang) || 'es'] || T.es;
  }

  /** Bolitas de progreso: verde acertada, roja fallada, gris regalada. */
  function dots(d) {
    const hist = d.history || [];
    let html = '';
    for (let i = 1; i <= (d.total || 0); i++) {
      let cls = hist[i - 1] || '';
      if (!cls && i === d.number) cls = 'now';
      html += `<span class="mt-dot ${cls}"></span>`;
    }
    return `<div class="mt-dots">${html}</div>`;
  }

  function figuras(extra) {
    return `<div class="mt-shapes ${extra || ''}">` + SHAPES.map((s, i) =>
      `<div class="mt-shape mt-c${i}">${s}</div>`).join('') + '</div>';
  }

  function confeti(wrap, n) {
    const capa = document.createElement('div');
    capa.className = 'mt-confetti';
    for (let i = 0; i < (n || 60); i++) {
      const p = document.createElement('div');
      p.className = 'mt-piece';
      p.style.left = Math.random() * 100 + 'vw';
      p.style.background = COLORES[i % COLORES.length];
      p.style.setProperty('--dx', (Math.random() * 30 - 15) + 'vw');
      p.style.setProperty('--spin', (Math.random() * 900 - 450) + 'deg');
      p.style.animationDuration = (1.8 + Math.random() * 1.5) + 's';
      p.style.animationDelay = (Math.random() * 0.4) + 's';
      capa.appendChild(p);
    }
    wrap.appendChild(capa);
    setTimeout(() => capa.remove(), 4400);
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

    function barra(d) {
      return `<div class="mt-top">
          <span class="mt-tag">Trivia</span>
          <span class="mt-title">${esc(d.title || '')}</span>
          ${dots(d)}
          <span class="mt-count">${d.number || 0}/${d.total || 0}</span>
        </div>`;
    }

    function pintarPregunta(d, revelando, celebrar) {
      const tx = textos(d);
      const letras = d.letters || [];
      const n = Math.min(Math.max((d.options || []).length, 2), 4);
      const fichas = (d.options || []).map((op, i) => {
        let cls = '';
        let marca = '';
        if (revelando) {
          if (i === d.correct) {
            cls = 'good' + (d.result === 'correct' && celebrar ? ' win' : '');
            marca = '<span class="mt-mark">✓</span>';
          } else if (i === d.chosen) {
            cls = 'bad';
            marca = '<span class="mt-mark">✕</span>';
          } else {
            cls = 'dim';
          }
        }
        return `<div class="mt-tile mt-c${i % 4} ${cls}">
            <div class="mt-tile-head">
              <span class="mt-shape">${SHAPES[i % 4]}</span>
              <span class="mt-letter">${esc(letras[i] || '')}</span>
            </div>
            <div class="mt-opt-text">${esc(op)}</div>
            ${marca}
          </div>`;
      }).join('');

      let banda = '';
      if (revelando) {
        const buena = (d.options || [])[d.correct];
        const letra = letras[d.correct] || '';
        const porque = d.explanation ? `<small>${esc(d.explanation)}</small>` : '';
        if (d.result === 'correct') {
          banda = `<div class="mt-banner win"><span class="mt-icon">✓</span>
              <span>${tx.correct}${porque}</span></div>`;
        } else {
          const tipo = d.result === 'pass' ? 'pass' : 'lose';
          const titulo = d.result === 'pass' ? tx.pass : tx.wrong;
          banda = `<div class="mt-banner ${tipo}"><span class="mt-icon">${tipo === 'pass' ? '?' : '✕'}</span>
              <span>${titulo}<small>${esc(tx.rightIs(letra, buena))}</small>${porque}</span></div>`;
        }
      }

      wrap.classList.toggle('reveal', revelando);
      wrap.innerHTML = `${barra(d)}
          <div class="mt-q">${esc(d.question)}</div>
          <div class="mt-say">${revelando ? '&nbsp;' : tx.say}</div>
          <div class="mt-grid n${n}">${fichas}</div>
          ${banda}`;
    }

    function pintarOferta(d) {
      const tx = textos(d);
      wrap.innerHTML = `<div class="mt-center">
          ${figuras()}
          <div class="mt-big">${tx.offer}</div>
          <div class="mt-sub">${tx.offerSub}</div>
          ${d.title ? `<div class="mt-hint">${tx.about}: ${esc(d.title)}</div>` : ''}
          <div class="mt-hint">${tx.offerHint}</div>
        </div>`;
    }

    function pintarCarga(d) {
      const tx = textos(d);
      wrap.innerHTML = `<div class="mt-center">
          ${figuras('spin')}
          <div class="mt-sub">${tx.loading}</div>
          ${d.title ? `<div class="mt-hint">${esc(d.title)}</div>` : ''}
        </div>`;
    }

    function pintarFinal(d, celebrar) {
      const tx = textos(d);
      const total = d.total || 0, score = d.score || 0;
      const perfecto = total > 0 && score === total;
      const mensaje = perfecto ? tx.perfect : (score === 0 ? tx.zero : tx.good);
      wrap.innerHTML = `${barra(d)}<div class="mt-center">
          <div class="mt-hint" style="margin:0 0 2vmin">${tx.result}</div>
          <div class="mt-big">${score}<span class="mt-of">/${total}</span></div>
          <div class="mt-sub">${mensaje}</div>
        </div>`;
      if (celebrar && score > 0) confeti(wrap, perfecto ? 90 : 35);
    }

    return {
      /** Pinta el estado que manda el servidor (o lo esconde si no hay juego). */
      apply(d) {
        d = d || {};
        if (!d.active) {
          if (firma !== null) { wrap.className = 'mt-wrap'; wrap.innerHTML = ''; firma = null; }
          return;
        }
        const nueva = [d.stage, d.number, d.result, d.chosen, d.score, d.lang].join('|');
        if (nueva === firma) return;
        // Las celebraciones solo al LLEGAR a esa etapa, no si la pantalla se
        // recarga con el resultado ya puesto.
        const celebrar = firma !== null;
        firma = nueva;
        wrap.className = 'mt-wrap on';

        if (d.stage === 'offer') pintarOferta(d);
        else if (d.stage === 'loading') pintarCarga(d);
        else if (d.stage === 'final') pintarFinal(d, celebrar);
        else if (d.stage === 'result') {
          pintarPregunta(d, true, celebrar);
          if (d.result === 'correct' && celebrar) confeti(wrap, 60);
        } else pintarPregunta(d, false, false);
      },
      clear() { this.apply({ active: false }); },
    };
  }

  return { create };
})();
