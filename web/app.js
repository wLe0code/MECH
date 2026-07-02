/* ═══════════════════════════════════════════════════════════════════════
   MECH — sitio de presentación · lógica de la página
   Sin dependencias: funciona abriendo index.html directo (file://)
   ═══════════════════════════════════════════════════════════════════════ */

(function () {
  'use strict';

  /* ─── Nav: fondo al hacer scroll + menú móvil ─────────────────────── */

  const nav = document.getElementById('nav');
  const burger = document.getElementById('navBurger');
  const navLinks = document.getElementById('navLinks');

  function onScrollNav() {
    nav.classList.toggle('scrolled', window.scrollY > 30);
  }
  window.addEventListener('scroll', onScrollNav, { passive: true });
  onScrollNav();

  burger.addEventListener('click', () => navLinks.classList.toggle('open'));
  navLinks.querySelectorAll('a').forEach((a) =>
    a.addEventListener('click', () => navLinks.classList.remove('open'))
  );

  /* ─── Aparición de elementos (.reveal) ────────────────────────────── */

  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('visible');
          revealObserver.unobserve(e.target);
        }
      });
    },
    { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
  );
  document.querySelectorAll('.reveal').forEach((el) => revealObserver.observe(el));

  /* ─── Hero: animación de escritura "ok MECH" ──────────────────────── */

  const typedEl = document.getElementById('typedText');
  const phrases = [
    '«ok MECH»',
    'cuéntame Don Quijote',
    'háblame de Malpaís',
    '¿quién fue Juan Santamaría?',
    'muéstrame a Con Wong',
  ];
  let phraseIdx = 0;

  function typePhrase(text, done) {
    let i = 0;
    typedEl.textContent = '';
    const t = setInterval(() => {
      typedEl.textContent = text.slice(0, ++i);
      if (i >= text.length) {
        clearInterval(t);
        setTimeout(done, 2100);
      }
    }, 65);
  }

  function erasePhrase(done) {
    const t = setInterval(() => {
      const cur = typedEl.textContent;
      typedEl.textContent = cur.slice(0, -1);
      if (!typedEl.textContent) {
        clearInterval(t);
        setTimeout(done, 350);
      }
    }, 28);
  }

  function typeLoop() {
    typePhrase(phrases[phraseIdx], () =>
      erasePhrase(() => {
        phraseIdx = (phraseIdx + 1) % phrases.length;
        typeLoop();
      })
    );
  }
  if (typedEl) typeLoop();

  /* ─── Showcase estilo Apple: fotos con respaldo SVG ───────────────── */

  const showcase = document.querySelector('.showcase');
  const frames = Array.from(document.querySelectorAll('.showcase .frame'));
  const dots = Array.from(document.querySelectorAll('#showcaseDots .dot'));
  const renderTpl = document.getElementById('robotRenderTpl');

  // Carga cada foto; si no existe el archivo, usa el render SVG del template
  frames.forEach((frame) => {
    const media = frame.querySelector('.frame-media');
    const src = frame.dataset.img;
    const img = new Image();
    img.onload = () => {
      img.alt = '';
      media.appendChild(img);
    };
    img.onerror = () => {
      const svg = renderTpl.content.firstElementChild.cloneNode(true);
      if (frame.dataset.viewbox) svg.setAttribute('viewBox', frame.dataset.viewbox);
      media.appendChild(svg);
      frame.classList.add('is-render');
    };
    img.src = src;
  });

  let currentFrame = -1;

  function setFrame(idx) {
    if (idx === currentFrame) return;
    frames.forEach((f, i) => {
      f.classList.toggle('active', i === idx);
      f.classList.toggle('leaving', i < idx);
    });
    dots.forEach((d, i) => d.classList.toggle('active', i === idx));
    currentFrame = idx;
  }

  function onScrollShowcase() {
    if (!showcase) return;
    const rect = showcase.getBoundingClientRect();
    const vh = window.innerHeight;
    const total = showcase.offsetHeight - vh;
    // progreso 0..1 dentro de la sección sticky
    const progress = Math.min(1, Math.max(0, -rect.top / total));
    const idx = Math.min(frames.length - 1, Math.floor(progress * frames.length));
    setFrame(idx);
  }
  window.addEventListener('scroll', onScrollShowcase, { passive: true });
  window.addEventListener('resize', onScrollShowcase);
  onScrollShowcase();
  setFrame(0);

  /* ─── Año en el footer ────────────────────────────────────────────── */

  const yearEl = document.getElementById('year');
  if (yearEl) yearEl.textContent = new Date().getFullYear();
})();
