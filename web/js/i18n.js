/* ═══════════════════════════════════════════════════════════════════════
   MECH — idiomas de la web
   El sitio se escribe en español. Cada idioma vive en su archivo,
   js/i18n/<código>.js (window.MECH_I18N[código] = { titles, dict }), y
   solo se descarga cuando alguien lo elige: quien ve la web en español no
   baja nada. La CLAVE es el texto en español (sin etiquetas, espacios
   normalizados) y el VALOR es el HTML traducido — así la negrita/cursiva
   se conserva. Si una cadena no está en el diccionario, se queda en
   español (no rompe).
   Para añadir un idioma: su archivo en js/i18n/ con las MISMAS claves que
   en.js + una línea en IDIOMAS. Al cambiar cualquier archivo de js/i18n/,
   súbele el número a VERSION (Vercel guarda /js una hora).
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  const IDIOMAS = [
    { code: 'es', name: 'Español' },
    { code: 'en', name: 'English' },
    { code: 'fr', name: 'Français' },
    { code: 'pt', name: 'Português' },
    { code: 'de', name: 'Deutsch' },
    { code: 'it', name: 'Italiano' },
    { code: 'ru', name: 'Русский' },
    { code: 'ja', name: '日本語' },
    { code: 'zh', name: '中文' },
    { code: 'ko', name: '한국어' },
  ];
  const VERSION = '2';

  // Sora y Space Mono solo traen letras latinas. Para estos cuatro idiomas
  // se baja una Noto Sans con sus letras, SOLO cuando alguien los elige
  // (Google la sirve en trozos: el navegador baja solo los que usa).
  // El CSS la pone DETRÁS de Sora (ver «IDIOMAS CON OTRAS LETRAS»), así
  // las letras latinas y los números siguen saliendo en Sora.
  const FUENTES = {
    ru: 'Noto+Sans:wght@400;600;700;800',
    ja: 'Noto+Sans+JP:wght@400;600;700;800',
    zh: 'Noto+Sans+SC:wght@400;600;700;800',
    ko: 'Noto+Sans+KR:wght@400;600;700;800',
  };
  function fuente(code) {
    if (!FUENTES[code] || document.getElementById('mech-font-' + code)) return;
    const l = document.createElement('link');
    l.id = 'mech-font-' + code;
    l.rel = 'stylesheet';
    l.href = 'https://fonts.googleapis.com/css2?family=' + FUENTES[code] + '&display=swap';
    document.head.appendChild(l);
  }
  const base = (document.currentScript && document.currentScript.src) || location.href;

  const SEL = 'h1,h2,h3,h4,p,li,cite,figcaption,summary,th,td,blockquote,' +
    '.nav-links a,.footer-col h4,.pager .dir,.pager .ttl,.kicker,.tag,' +
    '.tl-status,.tl-tags span,.work-tags span,.sponsors-label,.stat span,' +
    '.stat b,.btn,.profile-kicker,.profile-role,.card-icon,.chip,.pipe-tag,' +
    '.sponsor-tile span,.versus-tag,.team-role,.skip,caption,.stat-src,' +
    '.award-txt,.trophy-rank,.card-fig,.cm-link,.hud-tag';
  // no se traducen (marcas, nombres propios, siglas)
  const SKIP = new Set(['MECH', 'Arduino', 'Backend', 'Frontend', 'Multisensory',
    'Engineering', 'Cyberphysical', 'Humanized', 'M', 'E', 'C', 'H', 'VR',
    'Py', 'JS', 'Doc', 'IG', 'wromech@gmail.com', 'Logitech C920', 'JBL Charge 5',
    'MECH‑1', 'MECH‑2', 'MECH‑3', 'MECH‑4', 'MECH‑5', 'MECH‑6', 'TitoBot']);

  const norm = (s) => s
    .replace(/ /g, ' ')
    .replace(/\s+/g, ' ')
    // al cambiar las etiquetas por espacio, "<b>se lee</b>." deja " .":
    // se vuelve a pegar la puntuacion para que la clave coincida.
    .replace(/\s+([.,;:!?%)»])/g, '$1')
    .replace(/([(«])\s+/g, '$1')
    .trim();

  // Quita etiquetas (poniendo un ESPACIO, para que un <br> no pegue las
  // palabras) y DECODIFICA las entidades: "&amp;" tiene que volver a ser "&"
  // o la clave nunca coincidiria con el diccionario.
  const _tmp = document.createElement('div');
  function stripTags(html) {
    _tmp.innerHTML = html.replace(/<[^>]*>/g, ' ');
    return _tmp.textContent;
  }

  /* ─── Carga del archivo de cada idioma (una sola vez) ─────────────── */
  const pendientes = {};
  function cargar(code) {
    if (code === 'es') return Promise.resolve(null);
    const ya = window.MECH_I18N && window.MECH_I18N[code];
    if (ya) return Promise.resolve(ya);
    if (!pendientes[code]) {
      pendientes[code] = new Promise((ok, mal) => {
        const s = document.createElement('script');
        s.src = new URL('i18n/' + code + '.js?v=' + VERSION, base).href;
        s.onload = () => {
          const d = window.MECH_I18N && window.MECH_I18N[code];
          if (d) ok(d); else mal();
        };
        s.onerror = () => { delete pendientes[code]; mal(); };
        document.head.appendChild(s);
      });
    }
    return pendientes[code];
  }

  /* ─── Traducir la página ──────────────────────────────────────────── */
  function traducir(lang, datos) {
    const dict = datos ? datos.dict : null;
    const done = [];
    document.querySelectorAll(SEL).forEach((el) => {
      // no tocar si un ancestro ya se tradujo, ni si contiene otro bloque
      if (done.some((d) => d.contains(el))) return;
      if (el.querySelector('h1,h2,h3,h4,p,li,ul,ol,div,figure,blockquote,table')) return;
      if (el.dataset.i18nEs === undefined) el.dataset.i18nEs = el.innerHTML;
      const key = norm(stripTags(el.dataset.i18nEs));
      if (!key || SKIP.has(key)) return;
      const tr = dict ? dict[key] : undefined;
      if (tr !== undefined) {
        el.innerHTML = tr; done.push(el);
      } else if (el.innerHTML !== el.dataset.i18nEs) {
        el.innerHTML = el.dataset.i18nEs; done.push(el);
      }
    });

    document.documentElement.lang = lang;
    const page = (location.pathname.split('/').pop() || 'index').replace('.html', '') || 'index';
    if (!document.body.dataset.titleEs) document.body.dataset.titleEs = document.title;
    const titulo = datos && datos.titles && datos.titles[page];
    document.title = titulo || document.body.dataset.titleEs;
    marcarMenu(lang);
    try { localStorage.setItem('mech-lang', lang); } catch (e) {}
  }

  let ultimo = 0;
  function apply(lang) {
    if (!IDIOMAS.some((i) => i.code === lang)) lang = 'es';
    const n = ++ultimo;
    fuente(lang);
    cargar(lang)
      .then((datos) => { if (n === ultimo) traducir(lang, datos); })
      .catch(() => { if (n === ultimo) traducir('es', null); });
  }

  /* ─── Menú de idiomas en la barra de navegación ───────────────────── */
  let menu = null;
  function marcarMenu(lang) {
    if (!menu) return;
    menu.querySelector('.lang-code').textContent = lang.toUpperCase();
    menu.querySelectorAll('.lang-op').forEach((b) =>
      b.setAttribute('aria-checked', String(b.dataset.lang === lang)));
  }

  function montarMenu() {
    const links = document.getElementById('navLinks');
    if (!links || links.querySelector('.lang-switch')) return;
    menu = document.createElement('div');
    menu.className = 'lang-switch';
    menu.innerHTML =
      '<button type="button" class="lang-actual" aria-haspopup="true" aria-expanded="false" aria-label="Idioma / Language">' +
        '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/></svg>' +
        '<span class="lang-code">ES</span><span class="lang-flecha" aria-hidden="true"></span>' +
      '</button>' +
      '<div class="lang-lista" role="menu" hidden>' +
        IDIOMAS.map((i) =>
          '<button type="button" class="lang-op" role="menuitemradio" aria-checked="false" data-lang="' + i.code + '" lang="' + i.code + '">' +
            '<span class="lang-nombre">' + i.name + '</span><span class="lang-cod">' + i.code.toUpperCase() + '</span>' +
          '</button>').join('') +
      '</div>';
    const cta = links.querySelector('.nav-cta');
    links.insertBefore(menu, cta || null);

    const boton = menu.querySelector('.lang-actual');
    const lista = menu.querySelector('.lang-lista');
    const ops = () => [...lista.querySelectorAll('.lang-op')];
    const abrir = (si, foco) => {
      lista.hidden = !si;
      boton.setAttribute('aria-expanded', String(si));
      menu.classList.toggle('abierto', si);
      if (si && foco) (lista.querySelector('[aria-checked="true"]') || ops()[0]).focus();
    };
    boton.addEventListener('click', () => abrir(lista.hidden, false));
    boton.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown') { e.preventDefault(); abrir(true, true); }
    });
    lista.addEventListener('click', (e) => {
      const b = e.target.closest('.lang-op');
      if (!b) return;
      apply(b.dataset.lang);
      abrir(false); boton.focus();
    });
    lista.addEventListener('keydown', (e) => {
      const todos = ops(), i = todos.indexOf(document.activeElement);
      if (e.key === 'ArrowDown') { e.preventDefault(); todos[(i + 1) % todos.length].focus(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); todos[(i - 1 + todos.length) % todos.length].focus(); }
      else if (e.key === 'Home') { e.preventDefault(); todos[0].focus(); }
      else if (e.key === 'End') { e.preventDefault(); todos[todos.length - 1].focus(); }
      else if (e.key === 'Escape') { abrir(false); boton.focus(); }
      else if (e.key === 'Tab') abrir(false);
    });
    document.addEventListener('click', (e) => { if (!menu.contains(e.target)) abrir(false); });
  }

  /* ─── Idioma inicial: el elegido antes, o el del navegador ────────── */
  let inicial = null;
  try { inicial = localStorage.getItem('mech-lang'); } catch (e) {}
  if (!inicial) {
    // primera visita: si el navegador está en un idioma que la web tiene,
    // se abre en ese (así un visitante de otro país la entiende sin buscar)
    const pref = (navigator.languages || [navigator.language || 'es'])
      .map((l) => String(l).slice(0, 2).toLowerCase());
    inicial = pref.find((l) => IDIOMAS.some((i) => i.code === l)) || 'es';
  }
  montarMenu();
  if (inicial !== 'es') apply(inicial); else marcarMenu('es');
})();
