/* ═══════════════════════════════════════════════════════════════════════
   MECH — lógica compartida del sitio (sin dependencias)
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';
  // la ruta de este archivo sirve para encontrar assets/ desde cualquier
  // página (también la 404, que Vercel sirve en cualquier dirección)
  const scriptSrc = document.currentScript && document.currentScript.src;
  const reducir = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

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

  /* ─── La mascota (MECH-3) dentro de la página ─────────────────────── */
  // Cada .mascota trae un <img> de respaldo que ya se anima solo (reposo).
  // Aquí se cambia por el SVG mismo, para que la web le mueva brazos y
  // cabeza según data-pose (ver «LA MASCOTA» en styles.css). Si no se
  // puede bajar (página abierta con doble clic), se queda el <img>.
  const mascotas = document.querySelectorAll('.mascota');
  if (mascotas.length && scriptSrc && location.protocol !== 'file:') {
    fetch(new URL('../assets/mech3-mascota.svg', scriptSrc))
      .then((r) => (r.ok ? r.text() : Promise.reject(r.status)))
      .then((svg) => {
        mascotas.forEach((m, n) => {
          // ids únicos por mascota: si no, todas apuntarían a los
          // degradados de la primera
          m.innerHTML = svg
            .replace(/id="([^"]+)"/g, 'id="$1-m' + n + '"')
            .replace(/url\(#([^)]+)\)/g, 'url(#$1-m' + n + ')');
          const el = m.querySelector('svg');
          if (el) {
            el.removeAttribute('role');
            el.setAttribute('aria-hidden', 'true');
            el.setAttribute('focusable', 'false');
          }
        });
        iniciarPaseos();
      })
      .catch(() => {});
  }

  /* ─── MECH de la portada: al tocarlo saluda y dice hola ───────────── */
  // Solo el grande del hero (.mascota-boton). Funciona con el ratón, con
  // el dedo y con el teclado (es un <button>). Con el <img> de respaldo no
  // mueve el brazo, pero la nube sale igual.
  const botonMech = document.querySelector('.mascota-boton');
  if (botonMech) {
    const mHero = botonMech.querySelector('.mascota');
    const nube = document.querySelector('.bocadillo');
    const pistaToca = document.querySelector('.toca-pista');
    // lo que dice (y la etiqueta para lectores de pantalla) en los diez
    // idiomas de MECH; sigue al idioma de la página (<html lang>)
    const FRASES = {
      es: ['¡Hola, soy MECH!', 'Saludar a MECH'],
      en: ['Hi, I’m MECH!', 'Say hi to MECH'],
      fr: ['Salut, je suis MECH !', 'Saluer MECH'],
      pt: ['Olá, eu sou o MECH!', 'Cumprimentar o MECH'],
      de: ['Hallo, ich bin MECH!', 'MECH begrüßen'],
      it: ['Ciao, sono MECH!', 'Saluta MECH'],
      ja: ['こんにちは、MECHです！', 'MECHにあいさつする'],
      ru: ['Привет, я MECH!', 'Поздороваться с MECH'],
      zh: ['你好，我是MECH！', '和MECH打招呼'],
      ko: ['안녕하세요, 저는 MECH예요!', 'MECH에게 인사하기'],
    };
    const frase = (i) => (FRASES[document.documentElement.lang] || FRASES.es)[i];
    const etiqueta = () => botonMech.setAttribute('aria-label', frase(1));
    etiqueta();
    new MutationObserver(etiqueta).observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
    let tNube = 0, tPose = 0;
    botonMech.addEventListener('click', () => {
      if (pistaToca) pistaToca.classList.add('usada');
      // vuelve a empezar el saludo aunque estuviera a medias
      mHero.dataset.pose = 'idle';
      void mHero.offsetWidth;
      mHero.dataset.pose = 'saluda';
      if (nube) {
        nube.textContent = frase(0);
        nube.classList.remove('visible');
        void nube.offsetWidth;
        nube.classList.add('visible');
      }
      clearTimeout(tNube); clearTimeout(tPose);
      tNube = setTimeout(() => nube && nube.classList.remove('visible'), 3400);
      // después de su saludo descansa un rato y vuelve a saludar solo
      tPose = setTimeout(() => { mHero.dataset.pose = 'anfitrion'; }, 9000);
    });
  }

  /* ─── Paseo por el pie de página: camina, se para, saluda… ────────── */
  function iniciarPaseos() {
    if (reducir) return;
    document.querySelectorAll('.mascota-paseo').forEach((zona) => {
      const pista = zona.querySelector('.paseo-pista');
      const m = zona.querySelector('.mascota');
      if (!pista || !m) return;
      const VEL = 52; // px por segundo
      const PAUSAS = ['saluda', 'idle', 'saluda', 'busca'];
      let x = 0, visible = false, activo = false, t = 0;

      const paso = () => {
        if (!visible) { activo = false; return; }
        activo = true;
        const max = Math.max(0, zona.clientWidth - m.offsetWidth);
        // siempre un tramo largo, a un lado u otro
        let destino = Math.random() * max;
        if (Math.abs(destino - x) < max * 0.35) {
          destino = x < max / 2 ? max * (0.65 + Math.random() * 0.35) : max * Math.random() * 0.35;
        }
        const dur = Math.max(1.5, Math.abs(destino - x) / VEL);
        m.dataset.dir = destino < x ? 'izq' : 'der';
        m.dataset.pose = 'camina';
        pista.style.transition = 'transform ' + dur + 's linear';
        pista.style.transform = 'translateX(' + destino + 'px)';
        x = destino;
        t = setTimeout(() => {
          m.dataset.pose = PAUSAS[Math.floor(Math.random() * PAUSAS.length)];
          t = setTimeout(paso, 3600);
        }, dur * 1000);
      };

      // solo pasea mientras se ve: fuera de pantalla no gasta nada
      new IntersectionObserver((entradas) => {
        visible = entradas[0].isIntersecting;
        if (visible && !activo) paso();
        if (!visible) { clearTimeout(t); activo = false; m.dataset.pose = 'idle'; }
      }).observe(zona);
    });
  }

  /* ─── Año en el pie ───────────────────────────────────────────────── */
  document.querySelectorAll('.year').forEach((el) => {
    el.textContent = new Date().getFullYear();
  });
})();
