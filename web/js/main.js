/* ═══════════════════════════════════════════════════════════════════════
   MECH — lógica compartida del sitio (sin dependencias)
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  /* ─── Nav: sombra al hacer scroll + menú móvil ────────────────────── */
  const nav = document.getElementById('nav');
  const burger = document.getElementById('navBurger');
  const links = document.getElementById('navLinks');

  if (nav) {
    const onScroll = () => nav.classList.toggle('scrolled', window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  if (burger && links) {
    const setOpen = (open) => {
      links.classList.toggle('open', open);
      burger.setAttribute('aria-expanded', String(open));
    };
    burger.addEventListener('click', () =>
      setOpen(burger.getAttribute('aria-expanded') !== 'true')
    );
    links.querySelectorAll('a').forEach((a) =>
      a.addEventListener('click', () => setOpen(false))
    );
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') setOpen(false);
    });
  }

  /* ─── Aparición en scroll (.reveal) con cascada (.stagger) ────────── */
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        e.target.classList.add('visible');
        if (e.target.classList.contains('stagger')) {
          e.target
            .querySelectorAll(':scope > .reveal')
            .forEach((c) => c.classList.add('visible'));
        }
        io.unobserve(e.target);
      });
    },
    { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
  );
  document.querySelectorAll('.stagger').forEach((el) => io.observe(el));
  document.querySelectorAll('.reveal').forEach((el) => {
    if (!el.closest('.stagger')) io.observe(el);
  });

  /* ─── Hero: máquina de escribir «ok MECH» ─────────────────────────── */
  const typed = document.getElementById('typedText');
  if (typed && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const phrases = [
      '«ok MECH»',
      'cuéntame Don Quijote',
      'explícame la fotosíntesis',
      '¿quién fue Juan Santamaría?',
      'háblame de este medicamento',
    ];
    let i = 0;
    const type = (text, done) => {
      let n = 0;
      typed.textContent = '';
      const t = setInterval(() => {
        typed.textContent = text.slice(0, ++n);
        if (n >= text.length) { clearInterval(t); setTimeout(done, 2000); }
      }, 62);
    };
    const erase = (done) => {
      const t = setInterval(() => {
        typed.textContent = typed.textContent.slice(0, -1);
        if (!typed.textContent) { clearInterval(t); setTimeout(done, 320); }
      }, 26);
    };
    const loop = () => type(phrases[i], () => erase(() => {
      i = (i + 1) % phrases.length;
      loop();
    }));
    loop();
  } else if (typed) {
    typed.textContent = '«ok MECH»';
  }

  /* ─── Barra de progreso de lectura (arriba del todo) ──────────────── */
  const barra = document.createElement('div');
  barra.className = 'scroll-progress';
  barra.setAttribute('aria-hidden', 'true');
  document.body.appendChild(barra);
  let pendiente = false;
  const pintarBarra = () => {
    pendiente = false;
    const total = document.documentElement.scrollHeight - window.innerHeight;
    barra.style.transform = 'scaleX(' + (total > 0 ? Math.min(1, window.scrollY / total) : 0) + ')';
  };
  window.addEventListener('scroll', () => {
    if (!pendiente) { pendiente = true; requestAnimationFrame(pintarBarra); }
  }, { passive: true });
  window.addEventListener('resize', pintarBarra);
  pintarBarra();

  /* ─── Foco que sigue al cursor en tarjetas (solo con ratón) ───────── */
  if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
    const conFoco = '.card, .tl, .cm-body, .trophy, .pager a, .stat, .shot, .strip figure';
    document.querySelectorAll(conFoco).forEach((el) => el.classList.add('fx-spot'));
    document.addEventListener('pointermove', (e) => {
      const el = e.target.closest && e.target.closest('.fx-spot');
      if (!el) return;
      const r = el.getBoundingClientRect();
      el.style.setProperty('--mx', (e.clientX - r.left) + 'px');
      el.style.setProperty('--my', (e.clientY - r.top) + 'px');
    }, { passive: true });
  }

  /* ─── Año en el pie ───────────────────────────────────────────────── */
  document.querySelectorAll('.year').forEach((el) => {
    el.textContent = new Date().getFullYear();
  });
})();
