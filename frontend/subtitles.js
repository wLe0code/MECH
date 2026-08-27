/* MECH · Subtítulos de la narración (estilo cine).
 *
 * Lo usan la pantalla de proyección (/projector) y la vista VR
 * (/projector/vr). El backend manda el guion que acaba de escribir Claude:
 *
 *     {type: "subtitle", text: "...", lang: "es"|"en"}
 *
 * y también lo deja en /api/state como `current_subtitle` (la vista VR del
 * teléfono se alimenta del sondeo HTTP cuando el WebSocket no conecta).
 *
 * El texto llega COMPLETO por segmento (2-4 frases). Para que se lea como en
 * el cine lo partimos en trozos cortos y los pasamos solos, estimando la
 * duración por la cantidad de caracteres (el TTS habla a ~15 car/s). El
 * último trozo se queda en pantalla hasta que llegue otro subtítulo o el
 * backend lo borre — así nunca se ve la pantalla "muda" mientras MECH habla.
 *
 * El idioma no necesita traducción: el texto YA viene en el idioma activo
 * (español, o inglés si lo despertaron con "wake up MECH").
 */
window.MechSubs = (function () {
  const CHARS_PER_SEC = 15;   // ritmo aproximado del TTS
  const MAX_CHARS = 90;       // ~2 líneas en la pantalla del proyector
  const MIN_MS = 1200;        // ningún trozo parpadea
  const MAX_MS = 9000;

  /** Reparte una frase en líneas de como mucho `ancho` caracteres. */
  function llenar(frase, ancho) {
    const out = [];
    let linea = '';
    for (const palabra of frase.split(' ')) {
      if (linea && (linea + ' ' + palabra).length > ancho) {
        out.push(linea);
        linea = palabra;
      } else {
        linea = linea ? linea + ' ' + palabra : palabra;
      }
    }
    if (linea) out.push(linea);
    return out;
  }

  /** Parte una frase larga en trozos PAREJOS (sin colas de dos palabras).
   *  Empieza por el ancho ideal y lo va soltando hasta que salen tantos
   *  trozos como hacen falta y no uno más. */
  function partirLargo(frase, max) {
    const partes = Math.ceil(frase.length / max);
    const objetivo = Math.ceil(frase.length / partes);
    for (let ancho = objetivo; ancho <= max; ancho += 4) {
      const out = llenar(frase, ancho);
      if (out.length <= partes) return out;
    }
    return llenar(frase, max);
  }

  /** Parte el guion en trozos cortos, respetando frases.
   *  `max` = caracteres por trozo (la vista VR usa menos: cada ojo es
   *  media pantalla y ahí un trozo largo se volvería un párrafo). */
  function split(text, max) {
    const MAX = max || MAX_CHARS;
    const frases = String(text)
      .replace(/\s+/g, ' ')
      .trim()
      .split(/(?<=[.!?…:;])\s+/);
    const trozos = [];
    let actual = '';

    const empujar = () => { if (actual.trim()) trozos.push(actual.trim()); actual = ''; };

    for (const frase of frases) {
      if (!frase) continue;
      if (frase.length > MAX) {
        // Frase muy larga: la cortamos en trozos parejos por palabras.
        empujar();
        partirLargo(frase, MAX).forEach((t) => trozos.push(t));
      } else if ((actual + ' ' + frase).trim().length > MAX) {
        empujar();
        actual = frase;
      } else {
        actual = (actual ? actual + ' ' : '') + frase;
      }
    }
    empujar();
    return trozos.length ? trozos : [String(text).trim()];
  }

  /**
   * Crea un controlador de subtítulos.
   * @param {Element[]} targets elementos donde se escribe el texto (dos en VR,
   *   uno por ojo). Se ocultan solos con CSS cuando quedan vacíos (:empty).
   * @param {{maxChars?: number}} [opciones] ancho del trozo en caracteres.
   */
  function create(targets, opciones) {
    const destinos = (targets || []).filter(Boolean);
    const maxChars = (opciones && opciones.maxChars) || MAX_CHARS;
    let completo = null;   // el guion que estamos mostrando (para no reiniciar)
    let trozos = [];
    let indice = 0;
    let timer = null;

    function pintar(texto, idioma) {
      destinos.forEach((el) => {
        el.textContent = texto || '';
        if (idioma) el.setAttribute('lang', idioma);
      });
    }

    function avanzar(idioma) {
      const texto = trozos[indice];
      pintar(texto, idioma);
      indice += 1;
      if (indice >= trozos.length) return;  // el último se queda fijo
      const ms = Math.min(MAX_MS, Math.max(MIN_MS, (texto.length / CHARS_PER_SEC) * 1000));
      timer = setTimeout(() => avanzar(idioma), ms);
    }

    return {
      /** Muestra un guion nuevo (o lo borra si llega vacío/null). */
      set(text, idioma) {
        const limpio = (text || '').trim();
        if (limpio === (completo || '')) return;  // ya lo estamos mostrando
        clearTimeout(timer);
        completo = limpio;
        if (!limpio) { pintar('', idioma); return; }
        trozos = split(limpio, maxChars);
        indice = 0;
        avanzar(idioma);
      },
      clear() { this.set('', null); },
    };
  }

  return { create, split };
})();
