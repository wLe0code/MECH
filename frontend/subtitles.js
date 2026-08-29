/* MECH · Subtítulos de la narración (estilo cine).
 *
 * Lo usan la pantalla de proyección (/projector) y la vista VR
 * (/projector/vr). El backend manda la línea que toca ver AHORA:
 *
 *     {type: "subtitle", text: "Verona amanece dividida.", lang: "es"}
 *
 * y también la deja en /api/state como `current_subtitle` (la vista VR del
 * teléfono se alimenta del sondeo HTTP cuando el WebSocket no conecta).
 *
 * OJO — el reparto de líneas y su TIEMPO los decide el backend
 * (backend/subtitles.py), no esta página: es el único que sabe cuánto dura
 * de verdad el audio de ElevenLabs y dónde hace pausas MECH. Antes se
 * estimaba aquí a ~15 caracteres por segundo y los subtítulos se
 * adelantaban en cada pausa. NO devolver esa lógica al navegador.
 *
 * El idioma no necesita traducción: el texto YA viene en el idioma activo
 * (español, o inglés si lo despertaron con "wake up MECH").
 */
window.MechSubs = (function () {
  /**
   * @param {Element[]} targets elementos donde se escribe el texto (dos en
   *   VR, uno por ojo). Se ocultan solos con CSS al quedar vacíos (:empty).
   */
  function create(targets) {
    const destinos = (targets || []).filter(Boolean);
    let actual = null;

    return {
      /** Pinta la línea actual (o la borra si llega vacía/null). */
      set(text, idioma) {
        const limpio = (text || '').trim();
        if (limpio === (actual || '')) return;  // ya está en pantalla
        actual = limpio;
        destinos.forEach((el) => {
          el.textContent = limpio;
          if (idioma) el.setAttribute('lang', idioma);
        });
      },
      clear() { this.set('', null); },
    };
  }

  return { create };
})();
