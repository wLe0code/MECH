/* MECH · Sismos recientes — el mapa de la vista «Sismos» del panel.
 *
 * Pedido del equipo (oct 2026): un apartado con un mapa animado que muestre
 * los sismos recientes en cuanto son públicos.
 *
 * QUÉ ES Y QUÉ NO: pinta lo que YA tembló, tal como lo publican las redes
 * sísmicas (entre 2 y 10 minutos después). No predice nada ni es una alerta.
 *
 * Es un pintor: los datos los baja el servidor (backend/sismos.py) y llegan
 * por `GET /api/sismos` (la lista entera) y por el evento WebSocket `sismos`
 * (los nuevos). Esta página NO consulta internet: ni los datos ni el mapa.
 * El contorno de los países va en vendor/mech-mapa.json (lo genera
 * scripts/mkmapa.py), igual que los iconos y las fuentes.
 *
 * Dos lienzos, uno encima del otro:
 *   - el de ABAJO es el mapa (80 000 puntos): solo se repinta al mover o
 *     acercar, nunca en cada fotograma;
 *   - el de ARRIBA son los sismos y sus animaciones: se repinta ~30 veces
 *     por segundo si algo se mueve y dos veces por segundo si no.
 *
 * ⚠️ Los nombres de los lugares vienen de fuera: se escriben SIEMPRE con
 * `textContent`, nunca con `innerHTML`.
 *
 * app.js llama a `Sismos.mostrar(sí/no)` al cambiar de vista y a
 * `Sismos.evento(msg)` cuando llega el evento `sismos`.
 */
(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const vista = $('view-sismos');
  const caja = $('sm-mapa');
  if (!vista || !caja) return;

  const sinServidor = location.protocol === 'file:';
  const quieto = !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);

  // ─── Constantes ───────────────────────────────────────────────────
  const RAD = Math.PI / 180;
  const R_TIERRA = 6371;          // km
  const Y_NORTE = merY(85), Y_SUR = merY(-85);
  // Velocidades típicas de las ondas en la corteza (km/s). Son aproximadas:
  // sirven para dar una idea de cuánto tarda la sacudida en llegar.
  const V_P = 6.5, V_S = 3.7;
  // Colores (los mismos tonos de styles.css): rojo = última hora,
  // ámbar = últimas 24 h, gris azulado = esta semana.
  const TONO = { hora: '240,74,74', dia: '255,176,32', semana: '134,156,178' };
  const ACENTO = '34,211,238';
  // Sitios para «Dónde está MECH». Se puede poner cualquier otro en el .env
  // (SISMOS_ZONE_NAME / _LAT / _LON) y aparece aquí como una opción más.
  const ZONAS = [
    { n: 'Costa Rica', lat: 9.9, lon: -84.1 },
    { n: 'Puerto Rico', lat: 18.2, lon: -66.5 },
    { n: 'Panamá', lat: 8.98, lon: -79.52 },
    { n: 'California (Los Ángeles)', lat: 34.05, lon: -118.25 },
    { n: 'California (San Francisco)', lat: 37.77, lon: -122.42 },
    { n: 'México (Ciudad de México)', lat: 19.43, lon: -99.13 },
    { n: 'Japón (Tokio)', lat: 35.68, lon: 139.69 },
  ];
  const PERIODOS = { 3600: '1 hora', 86400: '24 horas', 604800: '7 días' };

  // ─── Estado ───────────────────────────────────────────────────────
  const S = {
    visible: false,
    sismos: [],          // todo lo que mandó el servidor (7 días)
    visibles: [],        // lo que pasa los filtros, del más viejo al más nuevo
    desfase: 0,          // reloj del servidor − reloj de este equipo (s)
    zona: null, activo: true, consultado: 0, error: null, cada: 60,
    cargado: false,      // ¿ya llegó la primera respuesta?
    caido: false,        // ¿no se pudo hablar con el servidor de MECH?
    periodo: 86400, minMag: 0,
    sel: null,           // id del sismo elegido
    onda: null,          // animación de las ondas P y S del elegido
    llegadas: new Map(), // id -> cuándo llegó EN VIVO (para el destello)
    repaso: null,        // repaso animado del periodo
    formularioTocado: false,
  };
  const V = { k: 1, cx: 0, cy: -0.5 };   // vista: escala y centro (en Mercator)
  let w = 0, h = 0, dpr = 1, kMin = 1;
  let mapa = null, pidiendoMapa = false;
  let sucio = true, vuelo = null, raf = 0, ultimoCuadro = 0;
  let enPantalla = [];   // [{s, x, y, r}] del último fotograma, para el ratón
  let circuloZona = null;
  let temporizadores = [];
  let rellenando = false;

  const cvB = $('sm-base'), cvC = $('sm-capa');
  const ctxB = cvB.getContext('2d'), ctxC = cvC.getContext('2d');

  // ─── Geometría ────────────────────────────────────────────────────
  function merX(lon) { return lon * RAD; }
  function merY(lat) {
    const l = Math.max(-85, Math.min(85, lat)) * RAD;
    return -Math.log(Math.tan(Math.PI / 4 + l / 2));
  }
  function aPantalla(lat, lon) {
    return [w / 2 + (merX(lon) - V.cx) * V.k, h / 2 + (merY(lat) - V.cy) * V.k];
  }
  // Círculo de `km` alrededor de un punto, sobre la esfera (en un mapa plano
  // un círculo grande NO es redondo). Devuelve [[lat, lon], ...].
  function circulo(lat, lon, km, n) {
    const d = km / R_TIERRA, f1 = lat * RAD, l1 = lon * RAD, pts = [];
    for (let i = 0; i <= n; i++) {
      const t = (i / n) * 2 * Math.PI;
      const f2 = Math.asin(Math.sin(f1) * Math.cos(d) + Math.cos(f1) * Math.sin(d) * Math.cos(t));
      const l2 = l1 + Math.atan2(Math.sin(t) * Math.sin(d) * Math.cos(f1),
                                 Math.cos(d) - Math.sin(f1) * Math.sin(f2));
      pts.push([f2 / RAD, ((l2 / RAD + 540) % 360) - 180]);
    }
    return pts;
  }
  function trazar(c, pts) {
    c.beginPath();
    let antes = null;
    for (const [lat, lon] of pts) {
      const [x, y] = aPantalla(lat, lon);
      // Si salta de un borde del mapa al otro, se corta la línea ahí.
      if (antes === null || Math.abs(lon - antes) > 180) c.moveTo(x, y); else c.lineTo(x, y);
      antes = lon;
    }
  }
  const limita = (x, a, b) => Math.max(a, Math.min(b, x));

  // ─── Vista (acercar, mover) ───────────────────────────────────────
  function ajustarVista() {
    V.k = limita(V.k, kMin, kMin * 60);
    const mx = Math.PI - w / (2 * V.k);
    V.cx = mx > 0 ? limita(V.cx, -mx, mx) : 0;
    const arriba = Y_NORTE + h / (2 * V.k), abajo = Y_SUR - h / (2 * V.k);
    V.cy = arriba < abajo ? limita(V.cy, arriba, abajo) : (Y_NORTE + Y_SUR) / 2;
    sucio = true;
  }
  function vistaMundo() { return { k: kMin, cx: 0, cy: -0.5 }; }
  function vistaZona() {
    if (!S.zona) return vistaMundo();
    const z = S.zona;
    // Que el círculo de la zona ocupe unos tres cuartos del alto.
    const k = Math.min(w, h) * R_TIERRA * Math.cos(z.lat * RAD) / (2.7 * z.radio_km);
    return { k, cx: merX(z.lon), cy: merY(z.lat) };
  }
  function irA(destino, ms) {
    if (quieto || !ms) { Object.assign(V, destino); vuelo = null; ajustarVista(); return; }
    vuelo = { de: { k: V.k, cx: V.cx, cy: V.cy }, a: destino, t0: performance.now(), ms };
  }
  function avanzarVuelo(t) {
    if (!vuelo) return;
    const p = limita((t - vuelo.t0) / vuelo.ms, 0, 1);
    const e = 1 - Math.pow(1 - p, 3);   // sale rápido y frena
    const { de, a } = vuelo;
    V.k = Math.exp(Math.log(de.k) + (Math.log(Math.max(a.k, kMin)) - Math.log(de.k)) * e);
    V.cx = de.cx + (a.cx - de.cx) * e;
    V.cy = de.cy + (a.cy - de.cy) * e;
    if (p >= 1) vuelo = null;
    ajustarVista();
  }
  function acercar(factor, px, py) {
    vuelo = null;
    const mx = V.cx + (px - w / 2) / V.k, my = V.cy + (py - h / 2) / V.k;
    V.k = limita(V.k * factor, kMin, kMin * 60);
    V.cx = mx - (px - w / 2) / V.k;
    V.cy = my - (py - h / 2) / V.k;
    ajustarVista();
  }

  function medir() {
    const r = caja.getBoundingClientRect();
    if (r.width < 10 || r.height < 10) return false;
    const enMundo = V.k <= kMin * 1.001;
    w = r.width; h = r.height;
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    for (const cv of [cvB, cvC]) {
      cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
    }
    nitido = null;                   // cambió el tamaño: la imagen guardada ya no vale
    kMin = w / (2 * Math.PI);        // el mundo entero cabe a lo ancho
    if (enMundo) Object.assign(V, vistaMundo());
    ajustarVista();
    return true;
  }

  // ─── El mapa (lienzo de abajo) ────────────────────────────────────
  async function pedirMapa() {
    if (mapa || pidiendoMapa) return;
    pidiendoMapa = true;
    try {
      const r = await fetch('vendor/mech-mapa.json');
      if (!r.ok) throw new Error(r.status);
      mapa = construirMapa(await r.json());
      sucio = true;
    } catch (e) {
      // Sin el contorno, los sismos se siguen viendo sobre el fondo.
      mapa = null;
    }
    pidiendoMapa = false;
  }
  function construirMapa(d) {
    const q = d.q;
    // Cada arco, ya proyectado: [x0, y0, x1, y1, ...]
    const arcos = d.arcos.map((a) => {
      const p = new Float64Array(a.length);
      let x = a[0], y = a[1];
      p[0] = merX(x / q); p[1] = merY(y / q);
      for (let i = 2; i < a.length; i += 2) {
        x += a[i]; y += a[i + 1];
        p[i] = merX(x / q); p[i + 1] = merY(y / q);
      }
      return p;
    });
    // Añade una línea (o un anillo cerrado) a un trazado. Lo que cruza el
    // borde del mapa (Chukotka, Fiyi, la Antártida pasan de 180° a −180°) se
    // dibuja seguido, saliéndose por un lado, y otra vez desplazado una
    // vuelta entera para que asome por el otro. Sin esto, cada cruce pinta
    // una raya de lado a lado del mapa.
    const VUELTA = 2 * Math.PI;
    function trazo(destino, xy, cerrado) {
      let salto = 0, cruza = false;
      const xs = [xy[0]];
      for (let i = 2; i < xy.length; i += 2) {
        const dx = xy[i] - xy[i - 2];
        if (dx > Math.PI) { salto -= VUELTA; cruza = true; }
        else if (dx < -Math.PI) { salto += VUELTA; cruza = true; }
        xs.push(xy[i] + salto);
      }
      for (const corre of (cruza ? [0, -VUELTA, VUELTA] : [0])) {
        destino.moveTo(xs[0] + corre, xy[1]);
        for (let j = 1; j < xs.length; j++) destino.lineTo(xs[j] + corre, xy[j * 2 + 1]);
        if (cerrado) destino.closePath();
      }
    }
    const tierra = new Path2D();
    for (const anillo of d.tierra) {
      const xy = [];
      for (const ref of anillo) {
        const p = arcos[ref < 0 ? ~ref : ref], n = p.length / 2;
        // Cada arco empieza donde acabó el anterior: ese punto no se repite.
        for (let j = xy.length ? 1 : 0; j < n; j++) {
          const i = (ref < 0 ? n - 1 - j : j) * 2;
          xy.push(p[i], p[i + 1]);
        }
      }
      trazo(tierra, xy, true);
    }
    const esFrontera = new Set(d.fronteras);
    const costas = new Path2D(), fronteras = new Path2D();
    arcos.forEach((p, n) => trazo(esFrontera.has(n) ? fronteras : costas, p, false));
    // Retícula cada 30°, para que se lea como un mapa.
    const reticula = new Path2D();
    for (let lon = -150; lon <= 150; lon += 30) {
      reticula.moveTo(merX(lon), Y_NORTE); reticula.lineTo(merX(lon), Y_SUR);
    }
    for (let lat = -60; lat <= 60; lat += 30) {
      reticula.moveTo(-Math.PI, merY(lat)); reticula.lineTo(Math.PI, merY(lat));
    }
    return { tierra, costas, fronteras, reticula };
  }
  // Pintar el mapa entero son 80 000 puntos: en la Raspberry Pi, hacerlo en
  // cada fotograma mientras se arrastra iría a tirones. Así que mientras la
  // vista se MUEVE (`rapido`) se reutiliza la última imagen nítida, estirada
  // y corrida a donde toca, y al parar se vuelve a pintar bien (`cuadro`).
  const cvCopia = document.createElement('canvas');
  const ctxCopia = cvCopia.getContext('2d');
  let nitido = null;        // la vista {k, cx, cy} que hay guardada en cvCopia
  let afinarDesde = 0;      // cuándo fue el último fotograma «rápido»
  function pintarBase(rapido) {
    const c = ctxB;
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.clearRect(0, 0, cvB.width, cvB.height);
    if (!mapa) return;
    if (rapido && nitido) {
      const e = V.k / nitido.k;
      c.setTransform(e, 0, 0, e,
        dpr * (w / 2 + (nitido.cx - V.cx) * V.k - (w / 2) * e),
        dpr * (h / 2 + (nitido.cy - V.cy) * V.k - (h / 2) * e));
      c.drawImage(cvCopia, 0, 0);
      return;
    }
    const k = V.k;
    c.setTransform(dpr * k, 0, 0, dpr * k, dpr * (w / 2 - V.cx * k), dpr * (h / 2 - V.cy * k));
    c.lineJoin = 'round';
    c.lineWidth = 1 / k;
    c.strokeStyle = 'rgba(255,255,255,0.045)';
    c.stroke(mapa.reticula);
    c.fillStyle = '#1c2530';
    c.fill(mapa.tierra, 'evenodd');
    c.lineWidth = 0.8 / k;
    c.strokeStyle = 'rgba(160,178,196,0.22)';
    c.stroke(mapa.fronteras);
    c.lineWidth = 1 / k;
    c.strokeStyle = 'rgba(160,178,196,0.55)';
    c.stroke(mapa.costas);
    // Se guarda la imagen nítida para los fotogramas rápidos que vengan.
    if (cvCopia.width !== cvB.width || cvCopia.height !== cvB.height) {
      cvCopia.width = cvB.width; cvCopia.height = cvB.height;
    }
    ctxCopia.setTransform(1, 0, 0, 1, 0, 0);
    ctxCopia.clearRect(0, 0, cvCopia.width, cvCopia.height);
    ctxCopia.drawImage(cvB, 0, 0);
    nitido = { k: V.k, cx: V.cx, cy: V.cy };
  }

  // ─── Los sismos (lienzo de arriba) ────────────────────────────────
  const horaServidor = () => Date.now() / 1000 + S.desfase;
  // El «ahora» del mapa: el de verdad, o el del repaso mientras corre.
  const relojMapa = () => (S.repaso ? S.repaso.T : horaServidor());

  // El tamaño del punto: crece con la magnitud. En un mapa pequeño (el
  // teléfono) se encoge todo, o los puntos tapan los continentes.
  function radio(mag) {
    const escala = limita(w / 760, 0.6, 1);
    return (2 + 1.25 * Math.pow(Math.max(0.3, mag - 2.2), 1.55)) * escala;
  }
  function tono(edad) { return edad < 3600 ? TONO.hora : edad < 86400 ? TONO.dia : TONO.semana; }
  function clase(edad) { return edad < 3600 ? 'e1' : edad < 86400 ? 'e2' : 'e3'; }

  function pintarCapa(t) {
    const c = ctxC;
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.clearRect(0, 0, w, h);
    const ahora = relojMapa();
    let animando = !!(vuelo || S.repaso || S.onda);

    // «Mi zona»: el círculo y el punto donde está MECH.
    if (S.zona && circuloZona) {
      trazar(c, circuloZona);
      c.setLineDash([5, 5]);
      c.lineWidth = 1.2;
      c.strokeStyle = `rgba(${ACENTO},0.55)`;
      c.stroke();
      c.setLineDash([]);
      const [zx, zy] = aPantalla(S.zona.lat, S.zona.lon);
      c.beginPath(); c.arc(zx, zy, 3.5, 0, 6.2832);
      c.fillStyle = `rgb(${ACENTO})`; c.fill();
      c.lineWidth = 1.5; c.strokeStyle = '#0a0c10'; c.stroke();
      const [, arribaY] = aPantalla(circuloZona[0][0], circuloZona[0][1]);
      c.font = '600 11px Sora, sans-serif';
      c.textAlign = 'center'; c.textBaseline = 'bottom';
      c.fillStyle = `rgba(${ACENTO},0.9)`;
      c.fillText(S.zona.nombre, zx, Math.max(14, arribaY - 5));
    }

    enPantalla = [];
    const rep = S.repaso;
    for (const s of S.visibles) {
      const edad = ahora - s.t;
      if (edad < 0) continue;                      // en el repaso: todavía no ocurre
      const [x, y] = aPantalla(s.lat, s.lon);
      const r = radio(s.mag);
      if (x < -60 || x > w + 60 || y < -60 || y > h + 60) continue;
      const col = tono(edad);

      // Destellos. En vivo: los de los últimos 15 minutos laten sin parar, y
      // el que acaba de llegar suelta tres ondas grandes. En el repaso: una
      // onda cuando el reloj pasa por su hora.
      const aro = (extra, p, grosor, fuerza) => {
        c.beginPath(); c.arc(x, y, r + extra * p, 0, 6.2832);
        c.lineWidth = grosor; c.strokeStyle = `rgba(${col},${(1 - p) * fuerza})`; c.stroke();
      };
      if (quieto) {
        // sin destellos
      } else if (rep) {
        if (!rep.vistos.has(s.id)) rep.vistos.set(s.id, t);
        const p = (t - rep.vistos.get(s.id)) / 1500;
        if (p < 1) { animando = true; aro(16 + r * 2.2, p, 2, 0.9); }
      } else if (S.llegadas.has(s.id)) {
        const nace = S.llegadas.get(s.id);
        if (t - nace > 9000) S.llegadas.delete(s.id);
        else {
          animando = true;
          for (let i = 0; i < 3; i++) aro(40 + r * 2, (((t - nace) / 1800) + i / 3) % 1, 2.2, 0.85);
        }
      } else if (edad < 900) {
        animando = true;
        aro(22, ((t + (s.t % 7) * 331) % 2400) / 2400, 1.5, 0.7);   // cada uno a su compás
      }

      c.beginPath(); c.arc(x, y, r, 0, 6.2832);
      c.fillStyle = `rgba(${col},${edad < 86400 ? 0.34 : 0.2})`; c.fill();
      c.lineWidth = s.cerca ? 1.8 : 1.1;
      c.strokeStyle = `rgba(${col},${edad < 86400 ? 0.95 : 0.6})`; c.stroke();
      enPantalla.push({ s, x, y, r });
    }

    // El elegido: aro de acento y, al elegirlo, sus ondas P y S.
    const sel = S.sel && S.sismos.find((s) => s.id === S.sel);
    if (sel) {
      const [x, y] = aPantalla(sel.lat, sel.lon);
      if (S.onda && S.onda.id === sel.id) pintarOnda(c, sel, x, y, t);
      c.beginPath(); c.arc(x, y, radio(sel.mag) + 4.5, 0, 6.2832);
      c.lineWidth = 2; c.strokeStyle = `rgb(${ACENTO})`; c.stroke();
    }
    return animando;
  }

  // Las dos ondas de un sismo, en cámara rápida. La P viaja casi el doble de
  // rápido y sacude poco; la S llega después y es la que hace el daño. Esa
  // diferencia es TODO el margen que tiene una alerta temprana.
  function pintarOnda(c, s, x, y, t) {
    const o = S.onda, p = (t - o.t0) / o.ms;
    if (p >= 1) { S.onda = null; return; }
    const kmS = o.alcance * p;                    // por dónde va la onda S
    const segundos = kmS / V_S;                   // tiempo REAL transcurrido
    const apaga = p > 0.8 ? (1 - p) / 0.2 : 1;
    const ondas = [['S', kmS, '240,74,74', 2.2], ['P', segundos * V_P, '255,255,255', 1.2]];
    c.font = '600 11px Sora, sans-serif';
    c.textAlign = 'center'; c.textBaseline = 'bottom';
    for (const [nombre, km, col, grosor] of ondas) {
      if (km < 2) continue;
      const pts = circulo(s.lat, s.lon, km, 60);
      trazar(c, pts);
      c.lineWidth = grosor;
      c.strokeStyle = `rgba(${col},${0.75 * apaga})`;
      c.stroke();
      const [ex, ey] = aPantalla(pts[0][0], pts[0][1]);
      c.fillStyle = `rgba(${col},${0.95 * apaga})`;
      c.fillText('onda ' + nombre, ex, ey - 4);
    }
    c.textBaseline = 'top';
    c.fillStyle = `rgba(255,255,255,${0.9 * apaga})`;
    c.fillText('+' + Math.round(segundos) + ' s', x, y + radio(s.mag) + 8);
  }

  function cuadro(t) {
    raf = 0;
    if (!S.visible) return;
    avanzarVuelo(t);
    if (S.repaso) avanzarRepaso(t);
    if (sucio) {
      const habiaImagen = !!nitido;
      pintarBase(true);            // rápido si hay imagen guardada; si no, entero
      afinarDesde = habiaImagen ? t : 0;
      sucio = false; ultimoCuadro = 0;
    } else if (afinarDesde && t - afinarDesde > 140) {
      pintarBase(false);           // la vista se quedó quieta: ahora sí, nítido
      afinarDesde = 0;
    }
    // 30 fotogramas por segundo si algo se mueve; dos si no (solo cambia el
    // color con la edad). En la Raspberry Pi se nota.
    if (t - ultimoCuadro >= (cuadro.animando ? 33 : 500)) {
      cuadro.animando = pintarCapa(t);
      ultimoCuadro = t;
    }
    raf = requestAnimationFrame(cuadro);
  }
  function despertar() {
    ultimoCuadro = 0;
    if (S.visible && !raf) raf = requestAnimationFrame(cuadro);
  }

  // ─── Repaso animado del periodo ───────────────────────────────────
  function empezarRepaso() {
    const hasta = horaServidor(), desde = hasta - S.periodo;
    const ms = S.periodo <= 3600 ? 8000 : S.periodo <= 86400 ? 14000 : 20000;
    S.repaso = { desde, hasta, T: desde, t0: performance.now(), ms, vistos: new Map() };
    S.onda = null;
    $('sm-repasar-txt').textContent = 'Parar';
    $('sm-reloj').classList.add('on');
    despertar();
  }
  function pararRepaso() {
    S.repaso = null;
    $('sm-repasar-txt').textContent = 'Repasar';
    $('sm-reloj').classList.remove('on');
    despertar();
  }
  function avanzarRepaso(t) {
    const r = S.repaso, p = limita((t - r.t0) / r.ms, 0, 1);
    r.T = r.desde + (r.hasta - r.desde) * p;
    $('sm-reloj-txt').textContent = new Date((r.T - S.desfase) * 1000).toLocaleString('es', {
      weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
    });
    $('sm-reloj-barra').style.transform = `scaleX(${p})`;
    if (p >= 1 && t - r.t0 > r.ms + 1600) pararRepaso();   // deja acabar el último destello
  }

  // ─── Textos ───────────────────────────────────────────────────────
  function hace(seg) {
    seg = Math.max(0, seg);
    if (seg < 90) return `hace ${Math.round(seg)} s`;
    if (seg < 5400) return `hace ${Math.round(seg / 60)} min`;
    if (seg < 172800) return `hace ${Math.round(seg / 3600)} h`;
    return `hace ${Math.round(seg / 86400)} días`;
  }
  function tarda(seg) {
    seg = Math.round(seg);
    return seg < 90 ? `${seg} s` : `${Math.floor(seg / 60)} min ${seg % 60} s`;
  }
  function el(etiqueta, clases, texto) {
    const e = document.createElement(etiqueta);
    if (clases) e.className = clases;
    if (texto !== undefined) e.textContent = texto;
    return e;
  }

  // ─── Lista y ficha ────────────────────────────────────────────────
  function filtrar() {
    const ahora = horaServidor();
    S.visibles = S.sismos
      .filter((s) => ahora - s.t <= S.periodo && s.mag >= S.minMag)
      .sort((a, b) => a.t - b.t);
    pintarLista();
    despertar();
  }
  function pintarLista() {
    const ahora = horaServidor();
    const lista = $('sm-lista');
    lista.textContent = '';
    const orden = S.visibles.slice().reverse();
    for (const s of orden.slice(0, 80)) {
      const edad = ahora - s.t;
      const b = el('button', 'sm-item' + (s.cerca ? ' cerca' : '') + (s.id === S.sel ? ' sel' : ''));
      b.type = 'button';
      b.dataset.id = s.id;
      b.appendChild(el('span', 'sm-mag ' + clase(edad), s.mag.toFixed(1)));
      const txt = el('span', 'sm-item-txt');
      txt.appendChild(el('span', 'sm-lugar', s.lugar));
      txt.appendChild(el('span', 'sm-sub',
        hace(edad) + (s.cerca && S.zona ? ` · a ${s.dist} km de ${S.zona.nombre}` : '')));
      b.appendChild(txt);
      lista.appendChild(b);
    }
    if (!orden.length) {
      lista.appendChild(el('div', 'sm-vacio',
        !S.cargado ? 'Cargando…'
          : !S.sismos.length ? 'Todavía no hay datos.'
          : `Ninguno en ${PERIODOS[S.periodo]} con esos filtros.`));
    } else if (orden.length > 80) {
      lista.appendChild(el('div', 'sm-vacio', `…y ${orden.length - 80} más en el mapa.`));
    }
    const cerca = S.visibles.filter((s) => s.cerca).length;
    $('sm-cuenta').textContent = orden.length
      ? `${orden.length} en ${PERIODOS[S.periodo]}` + (S.zona ? ` · ${cerca} cerca de ${S.zona.nombre}` : '')
      : '';
  }
  function pintarFicha() {
    const f = $('sm-ficha');
    const s = S.sel && S.sismos.find((x) => x.id === S.sel);
    f.textContent = '';
    f.hidden = !s;
    if (!s) return;
    const edad = horaServidor() - s.t;
    const cab = el('div', 'sm-ficha-cab');
    cab.appendChild(el('span', 'sm-mag grande ' + clase(edad), s.mag.toFixed(1)));
    const tit = el('div', 'sm-ficha-tit');
    tit.appendChild(el('div', 'sm-lugar', s.lugar));
    const cuando = new Date((s.t - S.desfase) * 1000).toLocaleString('es', {
      weekday: 'long', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit',
    });
    tit.appendChild(el('div', 'sm-sub', `${cuando} (${hace(edad)})`));
    cab.appendChild(tit);
    const cerrar = el('button', 'sm-cerrar', '×');
    cerrar.type = 'button';
    cerrar.title = 'Cerrar';
    cerrar.addEventListener('click', () => elegir(null));
    cab.appendChild(cerrar);
    f.appendChild(cab);

    const datos = el('div', 'sm-datos');
    const dato = (rotulo, valor) => {
      const d = el('div', 'sm-dato');
      d.appendChild(el('span', 'kicker', rotulo));
      d.appendChild(el('span', '', valor));
      datos.appendChild(d);
    };
    dato('Profundidad', s.prof === null || s.prof === undefined ? 'sin dato' : `${Math.round(s.prof)} km`);
    if (S.zona) dato('Distancia', `${s.dist} km de ${S.zona.nombre}` + (s.cerca ? ' (en tu zona)' : ''));
    // Cuánto tardó cada onda en llegar al centro de la zona. Solo si está a
    // una distancia a la que se habría podido sentir.
    if (S.zona && s.dist <= 1500) {
      const recorrido = Math.hypot(s.dist, s.prof || 0);
      dato('Ondas', `hasta el centro de tu zona, la P tardó unos ${tarda(recorrido / V_P)} ` +
                    `y la S (la fuerte) unos ${tarda(recorrido / V_S)}`);
    }
    dato('Lo reportó', s.agencia + ' · vía ' + s.fuentes.join(' y '));
    f.appendChild(datos);
    if (s.tsunami) {
      f.appendChild(el('div', 'sm-aviso',
        'El USGS marcó este sismo para revisar si hay aviso de tsunami. ' +
        'Consulta SOLO los avisos oficiales.'));
    }
    if (s.url) {
      const a = el('a', 'sm-enlace', 'Ver la ficha oficial');
      a.href = s.url; a.target = '_blank'; a.rel = 'noopener';
      f.appendChild(a);
    }
  }
  function elegir(id, centrar) {
    S.sel = id;
    const s = id && S.sismos.find((x) => x.id === id);
    S.onda = null;
    if (s) {
      if (!quieto && !S.repaso) {
        // Hasta dónde se dibujan las ondas: más o menos hasta donde se pudo
        // sentir (crece con la magnitud).
        const alcance = limita(Math.pow(10, 0.5 * s.mag), 60, 2500);
        S.onda = { id, t0: performance.now(), ms: 6500, alcance };
      }
      if (centrar) irA({ k: Math.max(V.k, kMin * 5), cx: merX(s.lon), cy: merY(s.lat) }, 550);
    }
    document.querySelectorAll('#sm-lista .sm-item').forEach((b) => {
      b.classList.toggle('sel', b.dataset.id === id);
    });
    pintarFicha();
    if (s && $('sm-rollo')) $('sm-rollo').scrollTop = 0;   // que la ficha quede a la vista
    despertar();
  }

  // ─── Estado de la conexión ────────────────────────────────────────
  function pintarEstado() {
    const caja2 = $('sm-estado');
    let cls = 'gris', txt = 'Cargando…', titulo = '';
    if (sinServidor) txt = 'Sin servidor (modo demostración)';
    else if (S.caido) { cls = 'ambar'; txt = 'Sin conexión con MECH'; }
    else if (!S.cargado) txt = 'Cargando…';
    else if (!S.activo) txt = 'Apagado · se enciende abajo, en «Mi zona»';
    else if (!S.consultado) {
      cls = S.error ? 'ambar' : 'gris';
      txt = S.error ? 'Sin conexión con las fuentes (¿hay internet en MECH?)' : 'Consultando las fuentes…';
    } else {
      const edad = horaServidor() - S.consultado;
      if (edad < Math.max(150, S.cada * 2.5)) { cls = 'verde'; txt = 'En vivo · actualizado ' + hace(edad); }
      else { cls = 'ambar'; txt = 'Datos de ' + hace(edad) + ' · sin conexión con las fuentes'; }
      titulo = S.error || '';
    }
    caja2.className = 'sm-estado ' + cls;
    caja2.title = titulo;
    $('sm-estado-txt').textContent = txt;
  }

  // ─── Datos ────────────────────────────────────────────────────────
  async function cargar() {
    if (sinServidor) { pintarEstado(); return; }
    try {
      const r = await fetch('/api/sismos', { cache: 'no-store' });
      if (!r.ok) throw new Error(r.status);
      aplicar(await r.json());
      S.caido = false;
    } catch (e) {
      S.caido = true;
    }
    pintarEstado();
  }
  function aplicar(d) {
    const antes = S.zona;
    S.desfase = d.ahora - Date.now() / 1000;
    S.sismos = d.sismos || [];
    S.zona = d.zona || null;
    S.activo = !!d.activo;
    S.consultado = d.consultado || 0;
    S.error = d.error || null;
    S.cada = d.cada_s || 60;
    S.cargado = true;
    const z = S.zona;
    if (z && (!antes || antes.lat !== z.lat || antes.lon !== z.lon || antes.radio_km !== z.radio_km)) {
      circuloZona = circulo(z.lat, z.lon, z.radio_km, 90);
    }
    if (!S.formularioTocado) rellenarFormulario();
    if (S.sel && !S.sismos.some((s) => s.id === S.sel)) { S.sel = null; pintarFicha(); }
    filtrar();
  }
  // Evento WebSocket `sismos`: novedades y estado de la consulta.
  function evento(msg) {
    if (typeof msg.ahora === 'number') S.desfase = msg.ahora - Date.now() / 1000;
    S.activo = !!msg.activo;
    S.consultado = msg.consultado || S.consultado;
    S.error = msg.error || null;
    S.caido = false;
    const nuevos = msg.nuevos || [];
    let enZona = false;
    for (const s of nuevos) {
      const i = S.sismos.findIndex((x) => x.id === s.id);
      if (i >= 0) S.sismos[i] = s; else S.sismos.unshift(s);
      S.llegadas.set(s.id, performance.now());
      enZona = enZona || !!s.cerca;
    }
    if (nuevos.length) {
      if (S.visible) filtrar();
      else if (enZona) marcarMenu(true);   // un punto en el menú: «mira Sismos»
    }
    if (S.visible) pintarEstado();
  }
  function marcarMenu(si) {
    const nav = document.querySelector('.nav-item[data-view="sismos"]');
    if (nav) nav.classList.toggle('sm-novedad', si);
  }

  // ─── «Mi zona» (formulario) ───────────────────────────────────────
  function rellenarFormulario() {
    const sel = $('sm-zona-sel');
    if (!sel) return;
    if (!sel.options.length) {
      ZONAS.forEach((z, i) => sel.appendChild(new Option(z.n, String(i))));
    }
    $('sm-activo').checked = S.activo;
    const z = S.zona;
    if (!z) return;
    let i = ZONAS.findIndex((p) => Math.abs(p.lat - z.lat) < 0.01 && Math.abs(p.lon - z.lon) < 0.01);
    if (i < 0) {
      // Una zona puesta a mano en el .env: va como una opción más.
      const propia = Array.from(sel.options).find((o) => o.value === 'propia') || new Option('', 'propia');
      propia.textContent = `${z.nombre} (lo configurado ahora)`;
      if (!propia.parentNode) sel.appendChild(propia);
      sel.value = 'propia';
    } else {
      sel.value = String(i);
    }
    const radio2 = $('sm-radio');
    radio2.value = z.radio_km;
    $('sm-radio-val').textContent = Math.round(z.radio_km) + ' km';
    // app.js rellena el riel del deslizador al oír `input`. La marca es para
    // que este aviso no cuente como «el usuario tocó el formulario».
    rellenando = true;
    radio2.dispatchEvent(new Event('input', { bubbles: true }));
    rellenando = false;
  }
  async function guardarZona() {
    const msg = $('sm-zona-msg');
    const updates = {
      SISMOS_ENABLED: $('sm-activo').checked ? 'true' : 'false',
      SISMOS_ZONE_RADIUS_KM: $('sm-radio').value,
    };
    const v = $('sm-zona-sel').value;
    const z = v === 'propia' ? null : ZONAS[parseInt(v, 10)];
    if (z) {
      updates.SISMOS_ZONE_NAME = z.n;
      updates.SISMOS_ZONE_LAT = String(z.lat);
      updates.SISMOS_ZONE_LON = String(z.lon);
    }
    msg.textContent = 'Guardando…';
    try {
      const r = await fetch('/api/config', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ updates }),
      });
      if (!r.ok) throw new Error(r.status);
    } catch (e) {
      msg.textContent = 'No se pudo guardar. ¿Está encendido MECH?';
      return;
    }
    S.formularioTocado = false;
    msg.textContent = updates.SISMOS_ENABLED === 'true'
      ? 'Guardado. Buscando los sismos de la zona…' : 'Guardado. La consulta queda apagada.';
    // El servidor vuelve a bajar la semana con la zona nueva: tarda unos
    // segundos. Se pregunta dos veces por si la primera llega antes.
    for (const espera of [1500, 6000]) {
      setTimeout(async () => {
        await cargar();
        if (espera > 2000) {
          msg.textContent = 'Guardado.';
          if (S.zona && S.activo) irA(vistaZona(), 700);
          despertar();
        }
      }, espera);
    }
  }

  // ─── Ratón y botones ──────────────────────────────────────────────
  function bajoElRaton(px, py) {
    let mejor = null, dMejor = 1e9;
    for (const p of enPantalla) {
      const d = Math.hypot(p.x - px, p.y - py);
      if (d <= p.r + 5 && d < dMejor) { mejor = p; dMejor = d; }
    }
    return mejor;
  }
  function posicion(e) {
    const r = caja.getBoundingClientRect();
    return [e.clientX - r.left, e.clientY - r.top];
  }
  const tip = $('sm-tip');
  function mostrarTip(p) {
    if (!p) { tip.classList.remove('on'); return; }
    tip.textContent = `M ${p.s.mag.toFixed(1)} · ${p.s.lugar} · ${hace(horaServidor() - p.s.t)}`;
    const x = limita(p.x, 90, w - 90);
    tip.style.transform = `translate(${x}px, ${p.y - p.r - 10}px) translate(-50%, -100%)`;
    tip.classList.add('on');
  }

  let arrastre = null;
  cvC.addEventListener('pointerdown', (e) => {
    if (e.button !== 0) return;
    const [px, py] = posicion(e);
    arrastre = { px, py, cx: V.cx, cy: V.cy, movido: false, tactil: e.pointerType === 'touch' };
    // Con el dedo NO se arrastra el mapa: el gesto es para desplazar la
    // página. En el teléfono se mueve con los botones.
    if (!arrastre.tactil) cvC.setPointerCapture(e.pointerId);
  });
  cvC.addEventListener('pointermove', (e) => {
    const [px, py] = posicion(e);
    if (arrastre && !arrastre.tactil) {
      const dx = px - arrastre.px, dy = py - arrastre.py;
      if (!arrastre.movido && Math.hypot(dx, dy) < 4) return;
      arrastre.movido = true;
      vuelo = null;
      V.cx = arrastre.cx - dx / V.k;
      V.cy = arrastre.cy - dy / V.k;
      ajustarVista();
      caja.classList.add('arrastrando');
      mostrarTip(null);
      despertar();
      return;
    }
    const p = bajoElRaton(px, py);
    cvC.style.cursor = p ? 'pointer' : '';
    mostrarTip(p);
  });
  const soltar = (e) => {
    if (!arrastre) return;
    const a = arrastre;
    arrastre = null;
    caja.classList.remove('arrastrando');
    if (a.movido || e.type === 'pointercancel') return;
    const [px, py] = posicion(e);
    const p = bajoElRaton(px, py);
    elegir(p ? p.s.id : null);
  };
  cvC.addEventListener('pointerup', soltar);
  cvC.addEventListener('pointercancel', soltar);
  cvC.addEventListener('pointerleave', () => mostrarTip(null));
  cvC.addEventListener('wheel', (e) => {
    // Con el mapa ya alejado del todo, la rueda vuelve a desplazar la página.
    if (e.deltaY > 0 && V.k <= kMin * 1.001) return;
    e.preventDefault();
    const [px, py] = posicion(e);
    acercar(Math.exp(-e.deltaY * 0.0016), px, py);
    mostrarTip(null);
    despertar();
  }, { passive: false });
  cvC.addEventListener('dblclick', (e) => {
    const [px, py] = posicion(e);
    irA({ k: V.k * 2, cx: V.cx + (px - w / 2) / V.k, cy: V.cy + (py - h / 2) / V.k }, 300);
    despertar();
  });

  const pulsar = (id, fn) => { const b = $(id); if (b) b.addEventListener('click', fn); };
  pulsar('sm-mas', () => { irA({ k: V.k * 1.8, cx: V.cx, cy: V.cy }, 250); despertar(); });
  pulsar('sm-menos', () => { irA({ k: Math.max(kMin, V.k / 1.8), cx: V.cx, cy: V.cy }, 250); despertar(); });
  pulsar('sm-mundo', () => { irA(vistaMundo(), 600); despertar(); });
  pulsar('sm-zona', () => { irA(vistaZona(), 600); despertar(); });
  pulsar('sm-repasar', () => { if (S.repaso) pararRepaso(); else empezarRepaso(); });
  pulsar('sm-actualizar', async () => {
    if (sinServidor) return;
    $('sm-estado-txt').textContent = 'Consultando las fuentes…';
    try { await fetch('/api/sismos/refresh', { method: 'POST' }); } catch (e) { /* lo dirá el estado */ }
    setTimeout(cargar, 2500);
  });
  pulsar('sm-guardar', guardarZona);

  function segmentos(id, atributo, alElegir) {
    const grupo = $(id);
    if (!grupo) return;
    grupo.addEventListener('click', (e) => {
      const b = e.target.closest('button');
      if (!b) return;
      grupo.querySelectorAll('button').forEach((x) => x.classList.toggle('on', x === b));
      alElegir(parseFloat(b.getAttribute(atributo)));
    });
  }
  segmentos('sm-periodo', 'data-s', (seg) => { S.periodo = seg; if (S.repaso) pararRepaso(); filtrar(); });
  segmentos('sm-mag', 'data-m', (m) => { S.minMag = m; filtrar(); });

  $('sm-lista').addEventListener('click', (e) => {
    const b = e.target.closest('.sm-item');
    if (b) elegir(b.dataset.id, true);
  });
  for (const id of ['sm-activo', 'sm-zona-sel', 'sm-radio']) {
    const c = $(id);
    if (c) c.addEventListener('input', () => {
      if (rellenando) return;
      S.formularioTocado = true;
      if (id === 'sm-radio') $('sm-radio-val').textContent = c.value + ' km';
    });
  }
  if ($('sm-zona-sel')) $('sm-zona-sel').addEventListener('change', () => { if (!rellenando) S.formularioTocado = true; });

  if (window.ResizeObserver) {
    new ResizeObserver(() => { if (S.visible && medir()) despertar(); }).observe(caja);
  } else {
    window.addEventListener('resize', () => { if (S.visible && medir()) despertar(); });
  }

  // Las opciones de «Dónde está MECH», ya al cargar: así app.js las
  // encuentra cuando convierte los desplegables en menús.
  rellenarFormulario();

  // ─── Lo que usa app.js ────────────────────────────────────────────
  function mostrar(si) {
    if (si === S.visible) return;
    S.visible = si;
    temporizadores.forEach(clearInterval);
    temporizadores = [];
    if (!si) {
      if (S.repaso) pararRepaso();
      if (raf) { cancelAnimationFrame(raf); raf = 0; }
      mostrarTip(null);
      return;
    }
    marcarMenu(false);
    pedirMapa().then(despertar);
    // La vista acaba de hacerse visible: se mide en el siguiente fotograma,
    // cuando ya tiene tamaño.
    requestAnimationFrame(() => { medir(); despertar(); });
    cargar();
    // Red de seguridad además del WebSocket: la lista entera cada minuto
    // (trae también las magnitudes que las redes corrigen después).
    temporizadores.push(setInterval(cargar, 60000));
    // «hace 3 min» envejece solo.
    temporizadores.push(setInterval(() => { pintarEstado(); }, 5000));
    temporizadores.push(setInterval(() => { if (!S.repaso) filtrar(); pintarFicha(); }, 30000));
  }

  window.Sismos = { mostrar, evento };
})();
