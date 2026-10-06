# HANDOFF — MECH

Documento de traspaso entre sesiones de Claude Code. **Léelo completo** antes
de tocar nada. Contexto de fondo (arquitectura/hardware/decisiones): **CLAUDE.md**
en la raíz — este handoff no lo reemplaza, lo complementa con el estado *vivo*.
CLAUDE.md está muy actualizado; si hay conflicto, gana CLAUDE.md.

**Última actualización: 6 oct 2026 (segunda sesión del día).** Lo del 5 oct
(§2.quinquies) se subió el 6 oct en dos commits encima de `62f3ebb`: «Panel
con estética nueva…» y «Cinco idiomas más…». ⚠️ **Subido, pero SIN probar en
la Pi.** Después, el mismo 6 oct (§2.sexies): **saludo en español** y **cada
comando solo en el idioma del despertar**. Subido el mismo día en un commit
encima de `90b86d3` («Saludo en español y cada comando solo en el idioma del
despertar»). ⚠️ **Subido, pero SIN probar en la Pi.**

> ⚠️ **Antes de leer nada más: `git fetch` y `git status`.** La sesión del
> 6 oct empezó leyendo este handoff en una copia local que estaba **2
> commits atrasada** (todavía decía «cuatro idiomas») y trabajó media sesión
> sobre código viejo hasta que el equipo avisó. Si `git status` dice
> «behind», primero `git pull` y volver a leer.

---

## 0. En un minuto

1. **El código es el del commit `c0e0310` («trasluce mech») + lo que el
   equipo pidió después** (§2.bis). El 23 sep se REVIRTIÓ todo lo que había
   entre medias — ver §2.ter antes de proponer nada «nuevo» que en realidad
   ya se quitó.
2. **Probado en la Pi y funcionando (23 sep):** la reversión, el saludo de
   3 rotaciones y la relatividad en la biblioteca.
3. **Hecho pero SIN probar en el robot** (§4, es lo primero que toca):
   controles del panel (sobre todo LATERAL), trivia estilo Kahoot, recorte
   automático de los videos de la relatividad, y el arreglo de «regresa a
   proyectar» (Movilidad **v4**).
4. **Preguntas sin contestar del equipo** (§2.quater), entre ellas qué
   hacer con el **modo de alerta de sismos** (investigado, sin implementar).
5. **Otra sesión de Claude trabaja en `web/` en paralelo.** `git fetch`
   antes de subir y commitear por rutas (§2).
6. **5 oct, subido el 6 oct y sin probar en la Pi** (§2.quinquies): cinco
   idiomas más (alemán, italiano, japonés, ruso, mandarín) y la estética
   nueva del panel (fondo grafito, acento cian; mismos controles).
7. **6 oct, subido y sin probar en la Pi** (§2.sexies): el saludo
   por cámara sale en **español**, y los comandos solo valen en el idioma
   con el que se despertó a MECH («hey MECH» ya no corta a un MECH despierto
   en español, ni «oye MECH» a uno despierto en inglés).

---

## 1. Objetivo del proyecto (MECH)

Robot interactivo para la **WRO 2026**. En un stand, narra obras con
**voz + proyección inmersiva + movimiento físico**, reaccionando a quien se
acerca y le habla. Claude devuelve un Plan estructurado; Python lo ejecuta
(STT local con faster-whisper, TTS de ElevenLabs, videos pre-renderizados o
imágenes de Gemini, Arduino para motores y servos).

- Obras en la biblioteca: `don_quijote`, `campana_1856`, `jimenez_deredia`,
  `malpais`, `isidro_con_wong` (4 segmentos c/u), `isaac_newton` (5),
  `relatividad` (**7**), `crispr` (**5**) y el slot `marketing` (12
  espacios, con audio propio, no pasa por Claude).
- Habla nueve idiomas (es/en/fr/pt y, desde el 5 oct, de/it/ja/ru/zh; lo
  decide la frase con que lo despiertan), hace de traductor por turnos y,
  desde el 25 sep, ofrece una **trivia** al terminar una obra.
- El equipo ya es **campeón nacional WRO 2026 Future Innovators**. En la web
  la generación actual se llama MECH-3; en el código y la voz es «MECH».

---

## 2. Estado del repo

- **Rama:** `main` = `origin/main` (comprobado el 6 oct, tras subir los dos
  commits del 5 oct). Todo pusheado salvo este handoff si se acaba de editar.
- Remoto: `https://github.com/wLe0code/MECH.git`
- Sin trackear y **NO se commitean**: `.agents/`, `skills-lock.json`. Tampoco
  `windows/config.txt` (tiene la IP local del usuario) ni
  `windows/dist/MECH Panel.exe` (se construye, no va a git).
- Dev en **Windows 11** (OneDrive sincroniza el repo); el robot corre en
  **Raspberry Pi 5** (hostname `mech`, ej. `http://mech:8000`). El Arduino se
  flashea desde el laptop.
- **Python de la Pi: 3.13** (¡no 3.11!). Importa para dependencias — ver §6.
- **En la laptop NO hay `fastapi` ni `ffmpeg` instalados.** Para simular el
  servidor hace falta un stub mínimo de FastAPI; el recorte de videos se
  probó con un ffmpeg simulado.
- **No hay suite de tests ni linter.** Chequeo rápido sin hardware:
  `python -m py_compile backend/*.py` y `node --check frontend/app.js`.
  Lo que sí hay, y conviene correr al tocar esas partes:
  - `python scripts/probar_saludo.py` — cuenta las órdenes del saludo (3
    llegadas arriba, el izquierdo quieto, nunca por debajo de 90).
  - `python scripts/probar_trivia.py` — cómo se entienden las respuestas
    (tiene que dar 50/50).
  - `python scripts/probar_idiomas.py` — los nueve idiomas: despertar,
    órdenes, colisiones entre idiomas, traductor, trivia, subtítulos y
    tablas (tiene que decir «TODO BIEN»). Mide las colisiones con las listas
    de todos los idiomas JUNTAS (apaga `VOICE_STRICT_LANGUAGE` a propósito).
  - `python scripts/probar_comandos_idioma.py` — la regla del 6 oct: cada
    idioma con sus comandos y sin los ajenos, el idioma fijo estando
    despierto, el saludo, y el bucle de voz real con micrófono/Whisper/voz
    de mentira (tiene que decir «TODO BIEN»).
  - ⚠️ **En esta laptop el único Python es el de Spyder, 3.8.10**
    (`%LOCALAPPDATA%\Programs\Spyder\Python\python.exe`; `python` a secas es
    el alias de la Microsoft Store y no corre nada). No tiene `dotenv` ni
    `fastapi`, y `voice_phrases.py` usa `str.removesuffix` (3.9+; en la Pi
    hay 3.13): `probar_idiomas.py` y `probar_trivia.py` no arrancan tal cual
    aquí. Se corrieron con un envoltorio que simula `dotenv` y carga
    `voice_phrases` con esa llamada escrita a la antigua. No «arregles» el
    `removesuffix` del repo por esto. Tampoco hay `node`.
  - Simulaciones con el código real: `MechApp.__new__` + stubs (la cabecera
    de `scripts/probar_saludo.py` muestra cómo). En Windows, correrlas con
    `PYTHONIOENCODING=utf-8` o los `print` con tildes revientan (cp1252).
- **Trabajo en paralelo:** hay otra sesión de Claude tocando `web/` (subió
  `d52f0d0`: salón de trofeos, evolución hasta MECH-5, figuras 26–45). Antes
  de subir: `git fetch`. Para no arrastrar cambios ajenos:
  `git commit --only -- <rutas>`. **Nunca force-push.**

### 2.bis Lo hecho del 23 al 26 sep (commit por commit)

| Commit | Qué |
|---|---|
| `068b0e4` (23 sep) | **Reversión a `c0e0310`** conservando solo `MECH Panel.exe`. Saludo nuevo. Relatividad en la biblioteca. **Probado en la Pi: funciona.** |
| `a99a08b` (23 sep) | Controles del panel, `docs/USO.md` reescrita, botón «Biblioteca de videos» en la app, guiones de CRISPR, recorte automático de la relatividad. |
| `0d28d6c` (25 sep) | **Trivia** de vuelta, con pantalla estilo Kahoot. |
| `3a10c0b` (26 sep) | Obra `crispr` en la biblioteca (5 segmentos, 18 `facts`). |
| `d52f0d0` (26 sep) | Web (otra sesión): trofeos, evolución, figuras del documento de California. |
| `7bf0dba` (26 sep) | Relatividad pasa de 8 a **7 segmentos**. |
| `62f3ebb` (26 sep) | «Regresa a proyectar» que no giraba → Movilidad **v4**. |

**Saludo** (`gestures.py`, `mech_app._greeting_blocked`): el brazo DERECHO
sube hacia adelante y llega arriba **exactamente 3 veces**
(`ARM_WAVE_REPEATS=3`, `ARM_WAVE_BOTH=false`, `ARM_INVERT_R=true`), solo en
**reposo** (`GREETING_ONLY_DORMANT`), **nunca mientras presenta** (contador
`_presenting` que cubre `execute_plan`, `play_playlist` y la trivia) y la
frase salía en **inglés** (`GREETING_LANGUAGE=en`, que NO cambia el idioma de
MECH) — ⚠️ **desde el 6 oct sale en español**, ver §2.sexies. El botón
«SALUDAR AHORA» respeta las mismas reglas.

**Controles del panel**: AVANZAR iba hacia atrás → `DRIVE_INVERT_FORWARD`
(default true, en `arduino_link.move()`, vale para TODO menos el comando
crudo). Los botones se intercambiaron en `frontend/index.html`: **GIRO manda
`vy`** y **LATERAL manda `w`**. El código de maniobras no cambió (ya usaba
`vy` para girar).

**Recorte automático** (`video_library.trim_uploaded`, campo `trim` de
`WORKS`): al subir un video de la relatividad, ffmpeg conserva seg 1 → los
primeros 20 s, seg 2 → los primeros 10 s, seg 3–7 → los **últimos** 10 s. El
original queda en `<slug>/originales/`. Sin ffmpeg o si falla, se usa el
video entero y el panel avisa. Solo afecta a lo que se suba DESPUÉS del
cambio (lo ya subido hay que volver a subirlo). `/library` marca esos
segmentos con ✂.

**Trivia** (`backend/trivia.py` = estado, `mech_app` = voz y proyección,
`frontend/trivia.js` = pantalla): al terminar una obra `immersive` ENTERA y
sin interrupción, MECH pregunta «¿Te gustaría realizar una trivia para
comprobar tu conocimiento?» en el idioma activo. Opción múltiple A/B/C, se
contesta hablando (letra, orden o texto). Acierto → confeti; fallo → «No has
acertado. La respuesta correcta es la B: …». Las preguntas las escribe
Claude en el momento (`llm.make_quiz`) con el guion narrado + los `facts`.
Detalle completo en CLAUDE.md → «Modo TRIVIA».

**«Regresa a proyectar»** — tenía tres causas:
1. Girarlo a mano desde el panel no le decía a MECH que ya no miraba a la
   proyección → estado nuevo `state["facing"] = "manual"` («no lo sé»),
   que ponen los botones GIRO/LATERAL, el comando crudo con giro y «PROBAR
   MEDIA VUELTA» (`maneuvers.mark_manual`). En "manual" las órdenes
   explícitas obedecen siempre; lo automático (volver solo antes de narrar)
   solo gira con `"outward"`.
2. «Vuelve a la proyección» no se entendía → frases nuevas en
   `VOICE_PROJECT_PHRASES`.
3. En inglés «go back to projecting» casaba con «go back» y RETROCEDÍA →
   en `handle_movement_command` el giro se comprueba ANTES que
   avanzar/retroceder. **No cambies ese orden.**

**App de Windows**: cuarto botón «Biblioteca de videos (en el navegador)»,
que abre `/library` en una pestaña normal. El `.exe` se reconstruye con
`windows\construir_exe.ps1`; si la app está abierta da «Acceso denegado» —
pedirle al usuario que la cierre, no cerrarla por él.

### 2.ter La REVERSIÓN del 23 sep — qué NO volver a meter

El equipo pidió volver a `c0e0310` porque «así estaba perfecto». **Se quitó
a propósito** y no vuelve salvo pedido explícito:

- Todo lo de los **parlantes alámbricos Logitech S150** (`TTS_GAIN_DB`,
  `TTS_NORMALIZE`, `pi/volumen-max.sh`). **Ya no se usan esos parlantes.**
- El gesto «67» por cámara y el traductor **continuo** (el de turnos sigue).
- El arreglo del reposo con redes extra, la medición del micrófono al
  arrancar, la fase `loading`, los reintentos de cámara/micrófono.
- Los 4 commits «Conexiones a prueba de todo»: el micrófono en un proceso
  aparte (`_mic_worker.py`), `wav_play.py`, la detección de «8 s sin datos»,
  la carpeta `tests/` y `LEEME-ARREGLOS.md`.

Esos commits **siguen en el historial de git** (el usuario eligió subida
normal, sin reescribir historia), pero su contenido no está en el árbol. Si
`git log` los muestra, no significa que estén activos.

Lo que se recuperó DESPUÉS, a pedido: la **trivia** (25 sep) y
`docs/USO.md` (reescrita desde cero el 23 sep con lo que sí existe).

### 2.quinquies Lo hecho el 5 oct (subido el 6 oct, SIN probar en la Pi)

Tres pedidos del equipo en un solo mensaje. Detalle completo en CLAUDE.md
(«Idiomas que no usan letras latinas» y «Estética del panel»).

**1. Cinco idiomas más: alemán, italiano, japonés, ruso y mandarín.** Los
cinco caben en la voz (`eleven_multilingual_v2`) y en Whisper. Mismo
mecanismo: solo se activan despertándolo en ese idioma.

| Frase | Idioma |
|---|---|
| «guten Tag MECH» · «wach auf MECH» | alemán |
| «ciao MECH» · «buongiorno MECH» | italiano |
| «こんにちは MECH» · «起きて MECH» | japonés |
| «привет MECH» · «проснись MECH» | ruso |
| «你好 MECH» · «醒醒 MECH» | mandarín |

- Archivos: `config.py` (sección nueva «Idiomas añadidos en oct 2026», 14
  listas por idioma + `VOICE_NAME_ALIASES` + `WAKE_<IDIOMA>_ENABLED`),
  `lang.py`, `voice_phrases.py`, `subtitles.py`, `stt.py`, `maneuvers.py`,
  `server.py`, `preflight.py`, `.env.example`, `frontend/index.html`,
  `app.js`, `trivia.js`, `docs/USO.md` y `scripts/probar_idiomas.py` (nuevo).
- **Lo difícil fueron japonés, ruso y chino**: no usan letras latinas, dos
  de ellos van sin espacios y Whisper escribe «MECH» como le suena. Se tocó
  el matcher (`_contiene`, `normalize`, alias del nombre), los subtítulos
  (miden ancho, cortan en comas) y la trivia. **Para texto latino el
  matcher no cambió**: comparado con el de HEAD, `normalize` y
  `_word_matches` dan lo mismo (181 476 pares) y los subtítulos también (334
  guiones). Sobre 1463 frases, con los idiomas nuevos encendidos cambian 14,
  ninguna en despertar/dormir/moverse: «cierto» y «já sei» cuentan como sí,
  «un momento MECH» y «acepta MECH» interrumpen (detalle en CLAUDE.md).
- Verificado sin hardware: `probar_idiomas.py` entero, `probar_trivia.py`
  50/50, y una simulación con `mech_app` + el bucle de voz de `server.py`
  reales (stub de FastAPI): despertar/dormir, órdenes de movimiento,
  traductor en los dos sentidos y trivia en los cinco idiomas.
- **NO verificado** (hace falta la Pi y el micrófono): cómo transcribe
  Whisper `base` cada idioma, y sobre todo **cómo escribe el nombre «MECH»**
  en japonés/ruso/chino. Si no despierta, el panel dice «Oí en japonés: '…'»
  y se añade esa forma a `VOICE_NAME_ALIASES` en el `.env`.
- La Pi necesita `sudo apt install fonts-noto-cjk` para que japonés y chino
  se lean en la proyección (el preflight lo avisa, §11).
- Línea de arranque: `Idiomas: español · inglés · … · mandarín`.

**2. Estética nueva del panel.** «Que el fondo no sea ese violeta, algo más
chiva», con la skill `emil-design-eng`. `frontend/styles.css` reescrita
entera: fondo grafito neutro con rejilla de puntos, un solo acento cian
(sustituye al morado), botones del Arduino como teclas, casillas como
palanquitas, deslizadores alineados. **Mismos controles**: el HTML solo
cambió por los idiomas. `library.html` hereda la paleta. No se tocaron la
proyección, la trivia (morada a propósito, estilo Kahoot) ni la app de
Windows. Verificado en el navegador (vista Voz, Arduino, Ajustes, Stand,
Sensores, Firmware, Inmersivo, biblioteca; escritorio y móvil a 375 px) con
un servidor estático de mentira — **no con el backend real**. Tras el
`git pull` en la Pi: **Ctrl+Shift+R** en el panel.

**2 bis. «Deja de traducir» con el turno ya terminado** (bug de antes,
encontrado de paso y arreglado el mismo día a pedido del equipo). La orden
solo se miraba en medio de un turno; con el turno terminado se iba a Claude
y el par de idiomas no se olvidaba. Además «deja de traducir, MECH» casaba
con «traduce MECH» y arrancaba otro turno. Ahora
`mech_app.handle_text_command()` mira salir ANTES que entrar. Si no hay nada
que olvidar se calla (así su propio eco, «Listo, dejo de traducir», muere en
silencio en vez de ir a Claude); para que eso valga en los nueve idiomas se
retocó la confirmación en japonés, ruso y chino. Simulado con `mech_app` y
el bucle de voz reales (70 comprobaciones): 14 formas de decirlo en 9
idiomas, con y sin «MECH», a mitad de turno, sin par, el eco en cada idioma,
y que «traduce MECH» y las preguntas normales siguen igual. **Probar en la
Pi:** traducir una frase → «deja de traducir» → el badge del panel pasa de
`LISTO · ES ↔ FR` a `APAGADO`, y el siguiente «traduce MECH» vuelve a
preguntar los idiomas.

**3. Modo de alerta de sismos: SOLO investigado, nada implementado.** Lo que
se le explicó al equipo:

- Avisar «30 s antes» solo es posible si el sismo es lejano (la alerta le
  gana a la onda porque viaja por internet). Cerca del epicentro no hay
  aviso que valga, y nadie PREDICE sismos.
- **Costa Rica**: existe (OVSICORI-UNA, proyecto ATTAC con ETH Zúrich), pero
  las alertas se reparten por su app «OVSICORI-UNA Alerta Terremotos» (y
  pruebas por TV digital). **No se encontró ninguna API pública**: habría
  que escribirle al OVSICORI y pedir acceso. Ojo: desde 2024 el propio
  OVSICORI dice que la alerta a veces llega tarde al teléfono.
- **California** (ShakeAlert, USGS): hace falta una licencia de socio técnico
  (acuerdo con el USGS). No es una API key que se saque en una tarde.
- **Japón y China**: Wolfx (`wss://ws-api.wolfx.jp/jma_eew` y otros) da las
  alertas oficiales gratis y **sin clave**, pero es un servicio no oficial y
  solo sirve si el robot está allí.
- **Sin clave y mundial, pero DESPUÉS del sismo**: USGS
  (`earthquake.usgs.gov/.../all_hour.geojson`, se actualiza cada minuto) y
  EMSC (`wss://www.seismicportal.eu/standing_order/websocket`). Sirven para
  «acaba de temblar en X», no para avisar antes.
- Propuesta que quedó sobre la mesa: un modo «aviso de sismo» con la fuente
  como configuración, arrancando con USGS/EMSC (sin clave) y dejando el
  hueco para OVSICORI si dan acceso. **Falta que el equipo decida.**

### 2.sexies Lo hecho el 6 oct (subido el 6 oct, SIN probar en la Pi)

Dos pedidos del equipo en un mensaje. Subido en un commit encima de
`90b86d3` (el equipo dijo «sí, déjalo para que yo solo tenga que hacer el git
pull»). Archivos: `config.py`,
`voice_phrases.py`, `server.py`, `preflight.py`, `mech_app.py` e
`interrupt_listener.py` (solo comentarios), `.env.example`,
`frontend/index.html`, `frontend/app.js`, `docs/USO.md`, `CLAUDE.md`,
`scripts/probar_idiomas.py` (una línea) y `scripts/probar_comandos_idioma.py`
(nuevo).

**1. El saludo por cámara sale en español** (`GREETING_LANGUAGE`, default
`es`; en septiembre el equipo lo había pedido en inglés). Todo lo demás del
saludo sigue igual (brazo derecho, 3 llegadas arriba, solo en reposo).

- ⚠️ **En la Pi hay que cambiarlo también en el panel**: «Guardar y aplicar»
  escribe todas las perillas en el `.env`, así que casi seguro tiene
  `GREETING_LANGUAGE=en` guardado y eso gana al código. Ajustes → «Idioma
  del saludo» → ESPAÑOL → «Guardar y aplicar» (en vivo, sin reiniciar). El
  preflight lo avisa y la línea de arranque lo delata (abajo).
- **Guarda del eco** (`server.py`, bucle de voz): el saludo en español lleva
  un «MECH» dentro, así que su eco no puede colarse como un despertar. La
  ventana `mech_app.greeting_until` se compara ahora con el momento en que
  se GRABÓ el audio (`inicio_audio`), no con la hora de después de
  transcribir: Whisper tarda 1-2 s en la Pi y con el reloj de después la
  ventana ya estaba cerrada (con el saludo en inglés no se notaba: transcrito
  en español no se parece a nada). Simulado: quitando el cambio, la prueba
  falla.

**2. Cada comando, solo en el idioma en que despertó** («que el "oye MECH"
tenga que decirse en el idioma en el que despertó para funcionar»).

- `voice_phrases._frases_activas()` sustituye a `_todos_los_idiomas()`: de
  cada lista `VOICE_*_PHRASES` mira solo la del idioma ACTIVO. Vale para
  interrumpir, dormir, moverse, marketing, traductor, trivia y sí/no. Las de
  DESPERTAR no cambian: en reposo se miran las nueve (eligen el idioma).
- **El idioma queda fijo hasta que se duerme** (decisión mía; el equipo la
  confirmó el 6 oct: «prefiero que la frase se tenga que decir en cada
  idioma dependiendo del que despierta, justo como lo hiciste»): antes,
  decir la frase de despertar de OTRO idioma estando
  despierto lo cambiaba. Ya no (`voice_phrases.wake_language_awake()`); esa
  frase sigue hacia Claude como cualquier otra. Motivo: «oye MECH» está
  también en la lista de despertar española, así que dicho a un MECH en
  inglés lo pasaba a español — justo el ejemplo que puso el equipo. De paso
  se va un fallo real: «OK MECH, tell me about…» en inglés casaba con el
  «ok MECH» español. **Si el equipo quiere recuperar el cambio de idioma a
  media charla, es esa función.**
- **Interruptor**: `VOICE_STRICT_LANGUAGE` (default true), en vivo desde
  Ajustes → «Idioma de los comandos». Apagado vuelve TODO lo de antes (las
  nueve listas a la vez y el cambio de idioma despierto).
- «ok» se añadió a las listas de sí de los ocho idiomas que no lo tenían
  (antes lo heredaban de la española).
- La separación es **por lista**, no perfecta: palabras casi iguales entre
  idiomas siguen valiendo en los dos («ok», «no», «avanza»/«avance»,
  «traduce»/«traduz»/«traduci», «perdón»/«pardon», «claro»/«klar»).
  `probar_comandos_idioma.py` las lista (punto 2 bis). No es un fallo.
- NO se tocó lo que no es un comando: respuestas de la trivia
  (`parse_answer`), números de «avanza diez segundos», nombres de idioma del
  traductor.
- Panel: el banner de «MECH está hablando» dice la frase que lo corta EN ESE
  idioma (`LANGS[...].corta` en `app.js`).
- Si MECH queda despierto en un idioma por error y nadie sabe dormirlo en
  ese idioma: chip **ES** de la vista Voz (no hay botón de «dormir» en el
  panel).
- Línea nueva al arrancar: `Comandos: solo en el idioma con el que se
  despertó a MECH · saludo en español`. Si dice «saludo en inglés», es el
  `.env` de la Pi.

Verificado sin hardware: `probar_comandos_idioma.py` (137 comprobaciones:
las 704 frases de las listas en su idioma, una frase de bandera por comando
en los nueve idiomas contra las de los otros ocho, el bucle de voz real en
los nueve), `probar_idiomas.py` (281), `probar_trivia.py` (50/50) y
`probar_saludo.py`. El panel se abrió en el navegador con un servidor de
mentira: los nueve chips, la pista correcta al narrar en cada idioma, el
interruptor nuevo y lo que manda «Guardar y aplicar». **NO verificado**: nada
con micrófono — sobre todo cómo escribe Whisper «hey MECH», «warte MECH»,
«ねえ MECH», etc. estando ya en ese idioma (§4).

### 2.quater Preguntas abiertas con el equipo

Ninguna bloquea nada, pero conviene cerrarlas en la próxima sesión:

0. **Alerta de sismos** (§2.quinquies, punto 3): ¿se implementa? ¿con qué
   fuente? ¿para dónde (Costa Rica, Puerto Rico, California)?

1. **«Parlante alámbrico» en `web/evolucion.html`** (y en `web/js/i18n.js`)
   figura como novedad de MECH-4, y el equipo dijo que ya no usa parlantes
   alámbricos. Lo escribió la otra sesión a partir del documento de
   California. Se avisó; no hubo respuesta. No tocarlo sin preguntar.
2. **Segmentos 1 y 2 de la relatividad**: el equipo dijo «1 será de 20
   segundos, 2 será de 10 s». Se interpretó como los **primeros** 20 s / 10 s
   (y los últimos 10 s solo para 3–7, que sí lo dijeron expreso). Si querían
   otra parte del video, es cambiar `"inicio"` por `"final"` en `trim`.
3. **Datos de CRISPR**: los 18 `facts` y `docs/GUIONES_CRISPR.md` se
   escribieron **sin búsqueda web** (a diferencia de las otras obras). Son
   datos conocidos y conservadores, pero conviene que el equipo los repase
   contra las fuentes listadas antes de presentarlos.

---

## 3.pre Cómo leer el historial que sigue (§3 a §3.decies)

Las secciones de abajo son el historial tal como estaba en `c0e0310`. Siguen
siendo válidas como explicación del **porqué** de cada pieza, con estas
salvedades:

- **Saludo**: donde diga «dos brazos» o cuente las repeticiones de otra
  manera, manda §2.bis (solo el derecho, 3 llegadas arriba) y, para el
  idioma, §2.sexies (**en español** desde el 6 oct).
- **Idiomas**: donde diga que las órdenes «se aceptan todas siempre, sin
  mirar el idioma activo» o que la frase de despertar de otro idioma cambia
  el idioma estando despierto, manda §2.sexies: desde el 6 oct cada comando
  vale solo en el idioma del despertar y el idioma queda fijo hasta dormirse.
- **Botones del panel**: cuando §3.quinquies dice «el mismo movimiento del
  botón LATERAL», habla del botón de ENTONCES (`vy`). Hoy ese movimiento
  está en el botón **GIRO**. La maniobra sigue siendo un tramo de `vy`.
- **`TURN_180_SECONDS`**: el default hoy es **4.8 s**. Se calibra en el
  robot, en vivo desde Ajustes.
- **`state["facing"]`** tiene un tercer valor, `"manual"`.
- La línea de arranque a buscar hoy es **«Movilidad v4 (sep 2026)»**.

Índice: §3 inglés, subtítulos e interrupción · §3.bis movilidad y giro de
180° · §3.ter marketing · §3.quater y §3.quinquies sincronía de la VR y giro
solo lateral · §3.sexies preflight y panel sin internet · §3.septies francés
y portugués · §3.octies traductor · §3.nonies saludo solo en reposo y una
vez por visitante · §3.decies cadena de audio.

---

## 3. Lo último que se hizo (ago 2026, todo pusheado)

### 🇬🇧 Modo inglés bajo demanda
- Módulo **`backend/lang.py`**: idioma activo (`es` por defecto), frases fijas
  de los dos idiomas y la instrucción de idioma que se le añade a Claude.
- **Se activa SOLO con «wake up MECH»**; con «ok MECH» / «despierta MECH»
  sigue en español. Al dormirse **vuelve a español solo**. Estando despierto,
  decir la frase del otro idioma cambia el idioma.
- Cambian: Whisper (`language="en"`), la narración de Claude (bloque de idioma
  APARTE en el system prompt para no romper el caché), las frases fijas y los
  subtítulos. El TTS ya era multilingüe.
- **Truco**: en reposo se escucha en español, así que «wake up MECH» puede
  salir deformado → si la transcripción no da wake, se **re-transcribe el mismo
  audio en inglés** antes de descartarlo. Hay variantes fonéticas en la lista.
- Chips **ES / EN** en la vista Voz (`POST /api/language/{es|en}`) para probar
  sin micrófono. `.env`: `WAKE_ENGLISH_ENABLED`, `VOICE_WAKE_PHRASES_EN`,
  `VOICE_SLEEP_PHRASES_EN`.

### 💬 Subtítulos en la proyección
- Estilo cine, abajo, en `/projector` y en `/projector/vr` (uno por ojo, con la
  separación de la calibración VR). Haya video, imagen o pantalla vacía, y en
  el idioma activo.
- **El ritmo lo manda el BACKEND**, no el navegador: `tts` pide el audio a
  ElevenLabs **con marcas de tiempo por carácter** y `backend/subtitles.py`
  calcula en qué segundo va cada línea; un hilo las publica a su hora. Antes se
  estimaban en el navegador a ~15 car/s y se adelantaban en cada pausa.
  `frontend/subtitles.js` quedó como pintor tonto — **no devolver el pacing al
  navegador**. Sin marcas de tiempo, cae a reparto proporcional a la duración
  real del audio.
- `mech_app.set_subtitle()` emite el evento WS `subtitle` **y** deja
  `state["current_subtitle"]`: eso último es lo que hace que se vean en el
  teléfono (que se alimenta del sondeo HTTP). Toggle: Ajustes → "Subtítulos".

### ✋ Interrupción por voz mientras narra ("oye MECH" / "hey MECH")
Lo más iterado de la sesión: se probó 4 veces en el robot y cada prueba destapó
una causa distinta. Estado final:

- `backend/interrupt_listener.py`: hilo que escucha durante TODO el plan y
  **solo** reacciona a `VOICE_INTERRUPT_PHRASES(_EN)`. Graba y transcribe **en
  paralelo** (cola de 1 clip, se queda con el más reciente) — antes el
  micrófono se cerraba 1-2 s en cada transcripción y ahí se perdían las frases.
  **No volver a hacerlo secuencial.**
- Al oírla, `mech_app.stop_presentation()` para TODO: voz, música, subtítulos,
  **la proyección** y las ruedas (brazos a reposo). Luego **pregunta** «Claro,
  ¿de qué quieres que hable?» y suena el **chime** de "puedes hablar".
- «oye MECH, cuéntame de Malpaís» → guarda la petición en
  `mech_app.pending_command` y el bucle de voz la atiende enseguida, sin
  preguntar ni chime.

**Las cuatro causas encontradas** (por si algo vuelve a fallar):

1. *No respondía*: si la narración se lanzaba desde el PANEL, el bucle de voz
   tenía el micrófono abierto y el listener no podía abrirlo → ahora el bucle
   lo cede (`mech_app.mic_release`).
2. *"Le cuesta y tarda en callarse"*: grabar y transcribir en serie + silencio
   de fin de frase de 1.2 s. Ahora van en paralelo,
   `INTERRUPT_SILENCE_TIMEOUT=0.6` y `tts.request_stop()` mata el reproductor
   si no muere en 250 ms.
3. *"Se buguea el audio"*: `_on_interrupt` no era idempotente (un segundo
   disparo cortaba la pregunta a media palabra), se hablaba encima del rastro
   del parlante (ahora 0.4 s de pausa) y la música no se mataba de verdad.
4. *"Va muy lagueado, todo descoordinado"*: **MECH se transcribía a sí mismo
   sin parar** y la Pi no daba abasto. El piso de ruido normal baja rápido y se
   queda en los silencios, así que los picos de su propia voz lo superaban
   siempre (subir el umbral NO bastaba — comprobado simulando el micrófono).
   Ahora, solo al narrar, `stt.record_until_silence(floor_average=True)` pone
   el piso **al nivel del parlante** (calibra ~1 s sin poder disparar y luego
   ignora los picos) con `INTERRUPT_ENERGY_FACTOR=4.0`. En simulación con audio
   continuo: de 5 transcripciones a 2 en 15 s, sin perder al visitante.
   Además el listener ya no manda el nivel del mic al panel (eran ~8 eventos/s
   por WS) y usa un Whisper aparte con 2 hilos de CPU.

**Diagnóstico que quedó montado** (útil en el evento):
- El panel loguea **todo lo que oye mientras narra**: `Oí mientras narraba: '...'`.
- Al cortar registra **"Corto la narración (X s desde que terminaste de
  hablar)"** y **"Voz cortada en N ms"**. Con esos dos números se sabe si falta
  afinar la detección o si lo que queda es el buffer del parlante Bluetooth.
- Botón **«Interrumpir narración»** en la vista Voz (`POST /api/voice/interrupt`):
  corta sin micrófono. Si por ahí SÍ corta, el mecanismo está bien y el
  problema es de audio.

**Ajustes en vivo para el evento** (Ajustes del panel):
| Ajuste | Clave | Cuándo tocarlo |
|---|---|---|
| Umbral ruido | `VAD_ENERGY_FACTOR` | No despierta / graba fantasmas |
| **Umbral al narrar** | `INTERRUPT_ENERGY_FACTOR` | Se transcribe a sí mismo (subir) / no te oye al interrumpir (bajar) |
| Interrumpir | `VOICE_INTERRUPT_ENABLED` | Si se corta solo en el evento |
| Subtítulos | `SUBTITLES_ENABLED` | — |

---

## 3.bis Movilidad (sep 2026) — lo último, SIN probar en el robot

El usuario notó que MECH había perdido movimiento («como que le quitaste esas
capacidades cuando logramos el VR, por ejemplo el saludo cuando pasa en la
cámara») y pidió tres cosas más. Todo implementado y validado en simulación
(scripts con stubs, ~70 comprobaciones), **nada probado en el robot todavía**.

### El saludo por cámara: qué estaba mal de verdad

No se había borrado. `on_user_detected` movía el brazo **antes** del cooldown,
así que:
- el brazo se disparaba en CADA detección (también dentro del cooldown),
- la voz solo cada 60 s,
- y como la visión se **pausa** mientras narra (commit `c446563`, del tiempo
  del VR), al terminar cada narración "redetectaba" a la misma persona y el
  brazo se movía **solo, en silencio**.

Ahora gesto y voz van juntos bajo el mismo cooldown (`GREETING_COOLDOWN`,
45 s, ajustable). Y hay un botón **«SALUDAR AHORA»** en la vista Arduino
(`POST /api/move/greet`) para probarlo sin depender de la cámara.

### Lo nuevo

1. **«mira hacia afuera» / «regresa a proyectar»** → `backend/maneuvers.py`.
   Giro de 180° = tramo **lateral** (apartarse de la mesa) + **rotación**; la
   vuelta es el mismo recorrido invertido, así que termina donde empezó.
   No pasa por Claude (instantáneo, sin gastar API). Al girar hacia afuera
   saluda con el brazo y lo dice. `state["facing"]` se ve en el panel, y
   `execute_plan` se da vuelta solo si le piden una historia estando de
   espaldas.
2. **Saludo más lento** — `ARM_WAVE_SECONDS` (2.2 s de subida y de bajada,
   antes 1.3 fijos).
3. **Brazos mínimos al proyectar** — `gestures.perform_talking()`: UN solo
   brazo, máx. 115° (reposo 90), lento, **sin ruedas**; `neutral` no manda
   nada. Los planes `mode="movement"` («saluda al público») conservan el
   gesto completo. Se revierte con `NARRATION_GESTURE_MODE=full`.

### Segunda pasada (probado en el robot: "no se mueve")

Se probó en el robot y **las ruedas no se movían**. Dos causas, las dos reales:

1. **`MODE:LISTEN` frena los motores.** En el firmware, `applyMode()` llama a
   `stopAllMotors()` para LISTEN/SPEAK/STOP — y el bucle de voz mandaba
   `MODE:LISTEN` en CADA vuelta (cada 0.3 s mientras narra). Cualquier
   movimiento moría a los ~300 ms. **Esto afectaba también a
   `return_to_start()`, que probablemente nunca funcionó con el bucle de voz
   encendido.** Arreglado en tres capas: `set_mode` ya no reenvía el modo que
   ya está puesto, el `MODE:LISTEN` del bucle se movió a justo antes de
   grabar, y `mech_app.wheels_busy` bloquea al bucle mientras las ruedas se
   mueven (y pone el Arduino en AUTO, el único modo que no frena).
2. **Iba a media potencia.** `TURN_180_SPEED` era 55, y el firmware escala
   `v * 255 / 100` → PWM 140/255. Con estos motores y el L298N eso zumba y no
   arranca. Ahora el default es **100** (PWM 255) y cada tramo empieza con un
   pulso a fondo (`MOTOR_KICK_SECONDS`).

La **distribución de ruedas sí era la correcta**: el giro usa el patrón
diagonal y el lateral el delantero/trasero, que es justo lo que el equipo
calibró en julio. Se comprobó reproduciendo `driveOmni()` en la simulación.

**El saludo también se agrandó**: llegaba a 170° con UN vaivén de 20°; ahora
llega a 180° y agita 65° tres veces (`ARM_WAVE_HIGH`/`SWING`/`REPEATS`).

### Tercera pasada: "solo sale ACK:ARM"

El equipo probó y **la orden no producía ningún comando de ruedas, solo
`ACK:ARM`**. Ese síntoma es exactamente lo que hace el CÓDIGO VIEJO: sin el
intercept de `handle_movement_command`, «mira hacia afuera» se la come Claude
como un plan `mode="movement"` → gesto `wave` → solo comandos `ARM`. Se
comprobó que el matcher reconoce todas las variantes reales de Whisper
("Mira/Mire/Mirá hacia afuera/fuera", con y sin "MECH" delante), y que por la
ruta real la maniobra emite `MOVE:0:100:0 · STOP · MOVE:0:0:100 · STOP` ANTES
del `ARM`. O sea: la Pi tenía `git pull` pero **sin reiniciar el server**.

Para que no vuelva a pasar a ciegas:
- El server loguea al arrancar **`Movilidad v2 (sep 2026): ...`** con los
  parámetros del giro. Si esa línea no sale, está corriendo código viejo.
  (`MOVILIDAD_VERSION` en server.py — subirla al tocar movimiento.)
- Cada tramo loguea **`Ruedas: MOVE:x:y:z durante N s`** en el panel, y avisa
  con `warn` si un tramo quedó en 0 s.

También en esta pasada:
- **Potencia 100 en TODO lo que mueve ruedas** (antes solo el giro): visión
  al acercarse, `return_to_start`, balanceo de gestos y los botones del
  panel. Los brazos siguen suaves.
- **El saludo usa los DOS brazos** (`ARM_WAVE_BOTH`) y **ya no lo encoge un
  `.env` con `ARM_GESTURE_MODE=subtle`** — eso dejaba el saludo de bienvenida
  en un vaivén de 12°, que es probablemente por qué "movía muy poco los
  brazos al ver a alguien". **Vale la pena revisar esa clave en el `.env` de
  la Pi.**
- `mech_app.log()` ya no puede tumbar una maniobra: un carácter que la
  consola no sepa pintar reventaba el `print` y se perdía el movimiento
  entero (pasa en Windows/cp1252, no en la Pi).

### ⚠️ Lo que HAY QUE CALIBRAR en el robot

**El giro se mide por TIEMPO (no hay encoders).** Con el robot en el suelo
donde vaya a trabajar:

0. **Primero, sin el bucle de voz**: apagá la voz desde el panel y probá
   `MOVE:0:0:100` en Arduino → comando crudo. Si ahí gira y con la voz
   encendida no, quedó algún resto del bug de `MODE:LISTEN`.
1. Panel → **Arduino** → «MIRA HACIA AFUERA». Ahora es un tramo lateral
   sostenido; si gira al revés, activá «Sentido» en Ajustes.
2. Panel → **Ajustes** → «GIRO DE 180° — CALIBRACIÓN» → subir/bajar **Giro**
   (segundos) hasta que quede justo de espaldas. Se aplica en vivo.
3. **Lateral** = cuánto se aparta antes de rotar. Ponlo en 0 s si no hace
   falta o si el espacio es justo.
4. Si gira hacia el lado equivocado, se voltea el signo de `w` en
   `driveOmni()` del `.ino` — **no** en `maneuvers.py`.

Ajustes nuevos, todos en vivo: `TURN_180_SECONDS`, `TURN_180_SPEED`,
`TURN_LATERAL_SECONDS`, `TURN_LATERAL_SPEED`, `MOTOR_KICK_SECONDS`,
`ARM_WAVE_SECONDS`, `ARM_WAVE_HIGH`, `ARM_WAVE_SWING`, `ARM_WAVE_REPEATS`,
`GREETING_COOLDOWN`, `NARRATION_GESTURE_MODE`.

**Si aun así no se mueve, es eléctrico** (§5: los motores y ruedas son de mal
material y hay un cambio de compra pendiente). A potencia 100 y con el bucle
de voz apagado, si `MOVE:0:0:100` no mueve nada, el problema ya no está en
este código: batería, L298N o los propios motores.

> Recordatorio del §5: los **servos de los brazos** todavía no se habían
> movido en el robot (respondían `ACK:ARM` pero quietos) — eso es eléctrico.
> Si el saludo no se ve, revisar primero la alimentación de 5–6 V y la tierra
> común, no este código.

---

## 3.ter Slot de MARKETING (sep 2026) — sin probar en la Pi

Pedido del equipo: un slot de videos promocionales que **proyecte aunque no
tenga los 5**, se dispare con «proyecta marketing» y **conserve su audio**.

Está en `WORKS` como `marketing` con la marca **`promo: True`**, que es lo que
lo hace comportarse al revés que una obra cultural:

| | Obra cultural | Slot `marketing` |
|---|---|---|
| Cómo se pide | lo decide Claude | «proyecta marketing» (orden directa, sin Claude) |
| Reproducción | clip corto en bucle bajo la narración | video **entero**, uno tras otro |
| Audio | **mudo** (MECH narra encima) | **su propio audio** — MECH se calla |
| Si faltan archivos | la obra no se ofrece | **proyecta con los que haya** |

- **12 espacios, ninguno obligatorio.** Con uno solo ya proyecta, y los huecos
  del medio se saltan (si están el 1, el 3 y el 7, reproduce esos tres).
- **No se le ofrece a Claude** (`system_prompt_section` filtra los promo): si
  lo viera, lo narraría como una obra y taparía el audio del video.
- Se corta con «oye MECH», con el botón «Cortar» de `/library` o con el paro.
- **El final lo marca la PANTALLA, no el backend.** Python no sabe cuánto dura
  cada mp4: `projector.html` avanza con el evento `ended` de cada `<video>` y
  avisa con `POST /api/playlist/ended`. `MARKETING_MAX_SECONDS` es solo el
  tope por si no hay ninguna pantalla abierta.
- Subida en `/library`: la tarjeta de Marketing tiene su propio aviso y los
  botones «Proyectar ahora» / «Cortar».

### ⚠️ Para que se OIGA hay que abrir Chromium distinto

Los navegadores no dejan reproducir con sonido sin un gesto del usuario:

```bash
chromium --kiosk --autoplay-policy=no-user-gesture-required http://localhost:8000/projector
```

Sin esa opción el video **se ve pero mudo**, y la pantalla muestra «Toca la
pantalla para activar el sonido» (un toque lo activa y reinicia el video en
curso). Conviene actualizar el lanzador de la Pi con ese flag. En el visor VR
los videos van siempre mudos a propósito: el sonido sale por el parlante.

Y al convertir los mp4, **NO uses `-an`** (eso quita el audio):

```bash
ffmpeg -i original.mov -c:v libx264 -crf 23 -c:a aac -b:a 192k seg01.mp4
```

---

## 3.quater Sincronía de la VR y saludo más corto (sep 2026)

Dos arreglos pedidos tras probar el robot (ya se mueve bien):

**1. El video de la VR no iba sincronizado con el audio.** El audio sale por
el parlante de la Pi, al ritmo de `/projector`; el visor del teléfono
empezaba el video DESDE CERO cada vez que se entraba. Ahora `/projector`
reporta por qué segundo va (`POST /api/playback`, cada 2 s y al cambiar de
archivo) y el visor salta a ese punto.

Detalle que importa: se manda la posición **+ la antigüedad del dato**
(`age`), NO una hora absoluta — el reloj del teléfono no tiene por qué
coincidir con el de la Pi. El visor solo suma `position + age`. `/api/state`
recalcula `age` al responder, que es de donde se alimenta el sondeo del
móvil. Tolerancia de 0.6 s y máximo un salto cada 1.5 s, porque buscar
posición en un móvil parpadea. Con clips en bucle se usa el módulo de la
duración. En la playlist promo el visor sigue además el `index` que reporta
la pantalla, en vez de asumir que va por el primer archivo.

Si vuelve a salir descuadrado: revisar que `/projector` esté abierto (es
quien reporta) y que `state["playback"]` traiga datos. Sin reporte el visor
no se rompe, solo pierde la sincronía.

**2. El saludo daba demasiadas vueltas.** `ARM_WAVE_REPEATS` ahora cuenta las
subidas TOTALES (contando la inicial), que es lo que uno ve: antes el valor 3
producía 4 subidas. Con el default 3 hace "sube, agita, agita, baja". Mínimo
2, tanto en el código como en el slider del panel.

---

## 3.quinquies Segunda pasada del giro y de la VR (sep 2026)

Tras probarlo en el robot:

**1. El giro hacía "un movimiento raro y muy corto".** Ahora la media vuelta
es **UN SOLO tramo LATERAL** — literalmente el mismo movimiento del botón
«LATERAL» del panel — sostenido hasta que queda de espaldas. **Se quitó el
tramo de rotación (`w`)**: con estas ruedas ese patrón no gira bien. Encaja
con lo que ya sabíamos: la cinemática de este robot está calibrada a mano y
no coincide con la mecanum de libro.
- Solo hay que calibrar **una** cosa: los segundos (Ajustes → «Media vuelta»).
- Si gira hacia el lado contrario: **`TURN_180_INVERT`**, en vivo, sin tocar
  el firmware.
- Los sliders «Lateral» y «Vel. lateral» desaparecieron del panel (ya no
  existe ese tramo); las claves siguen en config para no romper `.env`.

**2. Los brazos al girar hacia afuera van a medio gas.** `gestures.wave_outward()`:
145°, vaivén de 30°, UN brazo. Quedan tres tamaños bien diferenciados:
bienvenida por cámara (180°, 65°, dos brazos) > girar hacia afuera (145°, 30°,
un brazo) > al narrar (115°, un brazo).

**3. La VR se sincronizaba solo al entrar.** Al salir de la página el móvil
PAUSA el video, y al volver arrancaba desde cero (se notaba sobre todo en
marketing: videos largos y sin bucle). Tres arreglos:
- **Corrección continua**: un tic cada segundo, no solo al cargar el video.
- **`visibilitychange` / `pageshow` / `focus`** fuerzan un reenganche
  inmediato saltándose el antirrebote.
- El reporte se guarda **con la hora local en que llegó**, y el objetivo se
  recalcula como `position + age + (ahora − llegada)`. Sin eso, reusar el
  mismo reporte apuntaba a un punto cada vez más viejo.

⚠️ Y un detalle que es fácil volver a romper: **`play()` sobre un video
TERMINADO lo reinicia desde cero**. Todos los `play()` de reanudación llevan
`if (v.paused && !v.ended)`. Si alguien "arregla" que el video se quede
pausado sin esa guarda, vuelve el bug del video que empieza de nuevo.

---

## 3.sexies Listo para la competencia (sep 2026)

**1. El giro se quedaba corto.** Calibrado en tres pasadas sobre el robot:
2.0 s daba ~80° ("un poquito menos de la mitad"), 4.5 s daba 165-170°, y el
default quedó en **4.8 s**. El slider llega a 14 s.
La regla para reajustarlo: si con S segundos gira X grados, los que necesitás
son **S × 180 / X**. Botón nuevo **«PROBAR MEDIA VUELTA»** en la vista Arduino: repite el
tramo *sin* cambiar la orientación guardada, para poder calibrar pulsando
varias veces seguidas (con «mira hacia afuera» había que alternar con
«regresa a proyectar» y se acumulaba el error de los dos tramos).

**2. Chequeo previo:** `python -m backend.preflight` (o `--sin-red`).
Verifica de una pasada dependencias, Whisper cargando **del disco**, claves,
micrófono (lo abre de verdad), reproductores de audio, Arduino, biblioteca,
frontend offline y las claves del `.env` que tapan defaults. **Correrlo con
el server apagado.**

**3. El panel ya no depende de internet.** Los iconos venían de un CDN y las
fuentes de Google Fonts: sin wifi, los botones que son **solo icono** (subir
video, borrar) salían **EN BLANCO**. Ahora todo en `frontend/vendor/`.
De paso: `ti-brand-arduino` no existe en Tabler, así que esos tres iconos ya
estaban rotos incluso con internet.

**4. «Proyecta marketing» terminaba en menos de un segundo.** No era el
backend: el `<video>` de la pantalla dispara `error` con los archivos que no
sabe decodificar y se salta al siguiente — con todos fallando, la playlist
acaba en milisegundos. **Chromium no lee H.265/HEVC**, aunque el archivo se
vea perfecto en VLC o en el móvil.

Ahora la pantalla **reporta qué archivos falló** (`played` y `failed` en
`/api/playlist/ended`) y el panel lo dice con nombre y motivo, más el comando
de ffmpeg para reconvertir. También avisa si termina en menos de 3 s aunque
no haya reportes. Y `python -m backend.preflight` lo detecta ANTES, con
ffprobe: marca cualquier video de la biblioteca cuyo codec no lea el
navegador.

Reconversión:
```bash
ffmpeg -i original.mp4 -c:v libx264 -crf 23 -c:a aac -b:a 192k seg01.mp4
```

**5. Todo valor de movimiento es CONFIGURACIÓN** (pedido explícito). Nada
hardcodeado: clave en `config.py` + `_LIVE_KEYS` + slider en Ajustes, para
poder recalibrar EN EL EVENTO sin tocar código ni reiniciar. Lo último que
entró así: **«avanza diez segundos» / «retrocede cinco segundos»**
(`maneuvers.advance`), con el número hablado opcional — sin él usa Ajustes →
"Avanzar", y siempre topa en `ADVANCE_MAX_SECONDS`.

Valores actuales tras calibrar en el robot: giro **4.8 s**, brazos **2**
subidas (saludo y giro hacia afuera comparten esa perilla), avanzar **10 s**.

### Qué se cae si no hay wifi (lo dice el preflight)

**Sigue funcionando:** micrófono y Whisper (local), «ok MECH», «mira hacia
afuera», «proyecta marketing» y los videos de biblioteca **con su audio**,
saludo por cámara, motores, panel, proyector y VR.

**No funciona:** narrar una obra (el guion lo escribe Claude) y hablar (la voz
la genera ElevenLabs). No hay sustituto local. **Plan B: hotspot del celular.**
Si tampoco hay datos, lo que queda en pie es la proyección de marketing y los
videos de biblioteca, que son archivos locales.

---

## 3.septies Francés y portugués (sep 2026) — sin probar en la Pi

Pedido del equipo: los mismos idiomas que ya tenía en inglés, ahora también en
**francés** y **portugués**. Mecanismo idéntico al del inglés (§3), solo que
generalizado de 2 a 4 idiomas.

**El idioma lo decide la frase con que se le despierta**, igual que antes:

| Frase | Idioma |
|---|---|
| «ok MECH» · «despierta MECH» | español |
| «wake up MECH» | inglés |
| «bonjour MECH» · «salut MECH» · «réveille MECH» | francés |
| «bom dia MECH» · «boa tarde MECH» · «acorda MECH» | portugués |

Al dormirse **vuelve solo a español**, como siempre. En el panel (vista Voz)
hay ahora cuatro chips ES / EN / FR / PT para probarlo sin micrófono.

Qué se tradujo a los cuatro idiomas:
- las frases fijas de `backend/lang.py` (saludo, despedida, bienvenida, error,
  interrupción, playlist vacía, cambio de idioma),
- las frases del giro (`maneuvers._SAY`),
- las órdenes de movimiento, la de marketing y las de interrumpir/dormir
  (`VOICE_*_PHRASES_FR` / `_PT` en `config.py`) — **se aceptan todas siempre**,
  sin mirar el idioma activo (⚠️ ya no: desde el 6 oct solo las del idioma
  activo, §2.sexies),
- el `initial_prompt` de Whisper y la directiva de idioma que se le manda a
  Claude.

### Dos decisiones que importan

**1. El reintento del despertar ya NO va idioma por idioma.** Antes, si la
transcripción en español no daba wake, se re-transcribía el mismo audio en
inglés. Con cuatro idiomas eso serían 3 pasadas de Whisper por CADA ruido que
entre: la Pi quedaría ~10 s sin escuchar. Ahora se re-transcribe **una sola
vez con detección automática de idioma** (`stt.transcribe_any`) y el texto se
compara contra las listas de los cuatro. Mismo costo que antes.
**No lo vuelvas a hacer idioma por idioma.**

**2. Las frases se eligieron para NO chocar entre idiomas.** El matcher de
`voice_phrases` tolera UNA letra de error en palabras de 4+ letras y hace
substring en las cortas, así que:
- ❌ «desperta MECH» (pt) — cae en «despierta MECH» (es), despertaría en el
  idioma equivocado. Por eso el portugués usa **«acorda»** y **«bom dia»**.
- ❌ «olá MECH» (pt) — «ola» está dentro de «hola», así que «hola MECH»
  despertaría en portugués.
- ❌ «dors MECH» (fr, dormir) — «dors» está a una letra de «dos», y
  «avanza dos segundos, MECH» habría dormido al robot. El francés usa
  «au revoir», «bonne nuit», «arrête d'écouter».

Si vas a añadir una frase, pruébala contra las listas de los otros tres.

### Cómo comprobar que la Pi corre esto

Al arrancar, el server loguea una línea nueva:

```
Idiomas: español · inglés · francés · portugués — «ok MECH» (es) · ...
```

Si esa línea no sale (o solo dice «español · inglés»), hicieron `git pull`
pero **no reiniciaron el server** — o alguien apagó un idioma en el `.env`
(`WAKE_FRENCH_ENABLED` / `WAKE_PORTUGUESE_ENABLED`).

### Qué falta probar

1. Despertar en los cuatro idiomas y comprobar que narra, subtitula y
   responde en el idioma correcto.
2. Que «ok MECH» y «hola MECH» **no** despierten en portugués, y que
   «avanza dos segundos MECH» **no** lo duerma (son las colisiones que se
   cerraron a mano; en simulación pasan, falta el micrófono real).
3. Cuánto tarda el reintento con detección automática en la Pi. Si se nota
   lento al despertar, la palanca es `WHISPER_MODEL` (o apagar los idiomas
   que no se vayan a usar en el evento).
4. Que las voces de ElevenLabs suenen bien en francés y portugués
   (`eleven_multilingual_v2` los cubre, pero la voz configurada tiene acento
   español y puede sonar raro).

Validado en simulación: ~100 comprobaciones sin hardware (despertar en los 4
idiomas, no-despertar con frases del stand, reposo, interrupción, las 5
órdenes de movimiento en los 4 idiomas, números hablados, tablas de `lang.py`
y de `maneuvers._SAY`). El panel se verificó en el navegador: los 4 chips
caben en una línea y el cambio de idioma marca el chip correcto.

---

## 3.octies Modo TRADUCTOR (sep 2026) — sin probar en la Pi

Pedido del equipo: que MECH sirva para que dos personas que no hablan el mismo
idioma se entiendan en el stand. Aprovecha los cuatro idiomas de §3.septies.

**Funciona POR TURNOS: un «traduce MECH» = UNA frase traducida.**

```
«ok MECH»                → despierta
«traduce MECH»           → arranca un turno
MECH: «¿De qué idioma a qué idioma traduzco?»          (+ chime)
«de español a francés»
MECH: «Listo, traduzco entre español y francés. ¿Qué quieres que traduzca?»
«Buenos días, ¿cómo está?»
MECH: «Bonjour, comment allez-vous ?»    → y SE CALLA

«traduce MECH»           → otro turno; ya sabe el par, va al grano
MECH: «¿Qué quieres que traduzca?»                     (+ chime)
«Très bien, merci»       (el otro, en francés)
MECH: «Muy bien, gracias.»               → y se calla otra vez

«deja de traducir»       → olvida el par
```

Módulo nuevo: [`backend/translator.py`](backend/translator.py) (solo el
estado) + `llm.translate()` + la rama del bucle de voz en `server.py`.

### Por qué por turnos (esto es lo importante)

La **primera versión escuchaba en bucle** y tenía un problema grave: MECH
habla en cada frase, el micrófono capta su propio parlante, traduce su
traducción, y la de esa — **sin fin**. Se intentó tapar con una espera y una
guarda de texto, pero el equipo propuso lo que de verdad lo resuelve: que
MECH escuche **solo cuando acaba de preguntar**, traduzca UNA frase y se
calle. Así el micrófono nunca está abierto justo después de que él hable.

⚠️ **No lo vuelvas a hacer continuo** sin resolver el eco de otra manera.

Queda **un** hueco de eco: entre la pregunta de MECH y la frase del
visitante. Lo tapan `TRANSLATOR_DRAIN_SECONDS` (0.8 s tras hablar, por el
buffer del parlante Bluetooth) y `translator.looks_like_own_echo()`. Y si aun
así entra, MECH **no pierde el turno**: vuelve a pedir la frase.

### Otras decisiones

**1. El par de idiomas se RECUERDA** entre turnos — repetirlo en cada frase
sería insufrible. Se cambia nombrándolo en el propio comando («traduce MECH
del inglés al portugués», «traduce MECH al francés» → origen = el idioma
activo de MECH) y se olvida con «deja de traducir», al dormirlo o con el paro.

**2. Traduce en los DOS sentidos.** Whisper detecta en cuál de los dos
idiomas del par se dijo la frase (`stt.transcribe_any`, el mismo de
§3.septies) y MECH la pasa al otro. Si detecta un idioma que no es del par,
re-transcribe forzando el de ORIGEN. Se puede fijar el sentido con
`TRANSLATOR_AUTO_DETECT=false` — recomendable **si el par es
español/portugués**, que Whisper confunde en frases muy cortas.

**3. No pasa por el prompt grande de MECH.** `llm.translate()` es una llamada
corta (system de ~700 caracteres, sin caché ni structured output). Con el
prompt de siempre (obras, gestos, biblioteca) cada frase tardaría de más, y
en una conversación la latencia es todo. Si en el evento se nota lento,
`CLAUDE_TRANSLATE_MODEL` permite poner un modelo más rápido sin tocar nada.

**4. Dentro de un turno no se obedecen órdenes.** Solo «deja de traducir»,
dormirlo y repetir «traduce MECH». Es a propósito: un intérprete no ejecuta
lo que está traduciendo (si no, traducir la frase «mira hacia afuera»
giraría el robot).

**5. Si la traducción falla** (API caída, respuesta vacía), tampoco pierde el
turno: lo dice y vuelve a pedir la frase.

### En el panel

Tarjeta TRADUCTOR nueva en la vista Voz: dos selectores de idioma, «Traducir
una» (un turno con ese par, sin preguntar idiomas) y «Olvidar». El badge
muestra la etapa:

| Badge | Qué significa |
|---|---|
| `APAGADO` | nada en curso, sin par recordado |
| `ESPERANDO IDIOMAS` | preguntó de qué idioma a qué idioma |
| `ESCUCHANDO · ESPAÑOL ↔ FRANCÉS` | esperando LA frase a traducir |
| `LISTO · ESPAÑOL ↔ FRANCÉS` | callado, con el par recordado |

La flecha dice el modo: `↔` bidireccional, `→` sentido fijo.
Endpoints: `POST /api/translate/start?src=&dst=` y `POST /api/translate/stop`.

### Qué falta probar

1. El ciclo entero: «traduce MECH» → par → frase → traducción → **se calla** →
   «traduce MECH» otra vez y que NO vuelva a preguntar los idiomas.
2. **Que no traduzca su propia pregunta.** Es lo que más puede fallar. Si
   pasa, subí `TRANSLATOR_DRAIN_SECONDS` y el "Umbral ruido" de Ajustes.
3. El sentido automático con dos personas de verdad. Si se equivoca mucho,
   `TRANSLATOR_AUTO_DETECT=false`.
4. Cuánto tarda cada traducción en la Pi (Whisper + Claude + ElevenLabs). Si
   se hace pesado, la palanca es `CLAUDE_TRANSLATE_MODEL`.
5. Que «traduce MECH» no se dispare con preguntas normales del stand (las
   frases piden dos palabras justo por eso) y que «¿cómo se traduce Quijote
   al francés?» siga yendo a Claude.
6. Los subtítulos de la traducción en `/projector` y en la VR.

Validado en simulación: 10 bloques con micrófono, Whisper, ElevenLabs y
Claude simulados — los dos turnos seguidos, par recordado, par dicho en el
comando, par a medias, guarda anti-eco, fallo de traducción, «deja de
traducir», dormirse, paro y el estado del panel en cada etapa. El panel se
verificó en el navegador con las cinco etapas del badge.

---

## 3.nonies Saludo por cámara SOLO en reposo (sep 2026)

Pedido del equipo: el saludo de la cámara interrumpía presentaciones y
conversaciones. Ahora **solo se dispara con MECH en reposo**.

| MECH está… | ¿Saluda al ver a alguien? |
|---|---|
| en reposo (esperando «ok MECH») | **sí** — es justo lo que se quiere |
| despierto, esperando comando | no |
| grabando / transcribiendo / pensando / narrando | no |
| traduciendo | no (está despierto) |

### Y además: saluda UNA VEZ por visitante

El equipo reportó que MECH **repetía el saludo cada minuto aunque ya no
hubiera nadie**. La causa: `vision.LOST_AFTER_S` son 1.5 s, así que cualquier
parpadeo del detector (una cabeza que gira, un falso positivo con la luz de
la proyección) contaba como "se fue y volvió" = llegada nueva. Lo único que
lo frenaba era el cooldown de 45 s — de ahí la periodicidad.

Ahora hace falta una **ausencia de verdad**: la cámara tiene que quedarse sin
nadie `GREETING_REARM_SECONDS` (20 s) **seguidos**. El reloj se REINICIA en
cada pérdida, así que un detector que parpadea no lo completa nunca.
Verificado en simulación: 10 min de parpadeo continuo -> 1 solo saludo;
cámara vacía 25 s y llega otro -> sí saluda.

⚠️ Efecto secundario a saber: si la cámara tiene un falso positivo
PERMANENTE (un póster, un reflejo), MECH creerá que nunca se fue nadie y no
volverá a saludar. Ahí el problema es la cámara.

- Clave: **`GREETING_ONLY_DORMANT`** (default true), **en vivo** desde
  Ajustes → «Saludar por cámara solo en reposo». Poniéndola en false vuelve
  el comportamiento viejo, pero **ni así habla encima de una narración**.
- El botón **«SALUDAR AHORA»** (vista Arduino) se salta la regla Y el
  cooldown: es para probar el saludo sin tener que dormir a MECH. Lo único
  que respeta es no hablar encima de una narración o de una grabación.
- El aviso del panel («No saludo: MECH está despierto») sale **como mucho una
  vez por minuto**: la visión detecta a ~10 fps y si no lo llenaría de logs
  iguales.
- También se añadió `listening` a las fases que bloquean el saludo: antes
  MECH podía saludar **encima de alguien a quien estaba grabando**.

Código: `mech_app.on_user_detected()` (la puerta), `_perform_greeting()` (el
saludo en sí) y `greet_now()` (el botón). Validado en simulación: 6 bloques
(reposo, las 5 fases despierto, throttle del aviso, regla apagada, cooldown y
el botón del panel).

---

## 3.decies Cadena de audio: que MECH entienda mejor (sep 2026)

Pregunta del equipo: *"¿por qué Google o Siri entienden tan bien y MECH no?
Los micrófonos son buenos."* La investigación completa está en
**[`docs/AUDIO.md`](docs/AUDIO.md)**; aquí va el resumen.

**No es el micrófono.** El de MECH es de solapa: va a 15 cm de la boca, que
es mejor punto de partida que un teléfono a un metro. Lo que hace un teléfono
es **procesar el audio antes de reconocerlo** (pasa-altos, cancelación de
eco, supresión de ruido, AGC, remuestreo limpio, VAD neuronal). MECH hacía
casi nada de eso.

### Lo que se implementó (sin dependencias nuevas)

`stt.prepare_for_whisper()`: pasa-altos → remuestreo a 16 kHz **con
anti-aliasing** → nivel objetivo.

⚠️ **Había un defecto real en el remuestreo.** Bajaba de 48 kHz a 16 kHz
promediando bloques de 3 muestras, que es un filtro pobrísimo: los agudos de
8-16 kHz **se pliegan** dentro de la banda de la voz. Medido con tonos puros:

| Entrada | Reaparece a | antes | ahora |
|---|---|---|---|
| 8.5 kHz | 7.5 kHz | −7 dB | −18 dB |
| 10 kHz | 6 kHz | −9 dB | **−48 dB** |
| 12 kHz | 4 kHz | −13 dB | **−52 dB** |

Con ruido realista de banda alta (fuente conmutada, proyector, siseo de
sala): **16 a 47 dB menos de basura** dentro de la banda útil. Y de paso
conserva mejor las consonantes (a 6 kHz: −1.9 dB antes, 0 dB ahora).

⚠️ **Solo aplica si se captura por encima de 16 kHz.** Si el `.env` de la Pi
tiene `AUDIO_SAMPLE_RATE=16000`, no hay remuestreo y esto no hace nada.
**Hay que confirmar que en la Pi esté en 48000** (el del laptop está en
16000, por eso el script de prueba lo fija a mano).

**Y otro arreglo que puede importar más todavía:** `_frame_rms()` ahora resta
la continua antes de medir. Si el receptor USB mete offset de continua, ese
offset contaba como "ruido ambiente", el piso subía y MECH se quedaba sordo
para el "ok MECH" — que es justo el problema que el equipo peleó a mano en la
olimpiada subiendo el umbral. Medido: una continua pura pasa de marcar
RMS 0.092 a marcar 0.00000, y la voz real sigue marcando igual.

También: **nivel automático** (el "AGC" del teléfono, `-16 dBFS`, con tope de
ganancia ×8 y sin saturar nunca) y **`WHISPER_BEAM_SIZE=5`** en vez de 1 (el
de las interrupciones sigue en 1: ahí manda el retardo).

Tres sliders nuevos en Ajustes, en vivo: **Quita retumbe**, **Nivel de voz**
y **Precisión STT**.

### Lo que NO se hizo (hace falta decisión del equipo)

Ordenado por impacto esperado; el detalle y los costes están en `docs/AUDIO.md`:

1. **Silero VAD** en lugar de webrtcvad (de 2011, se dispara con cualquier
   ruido de banda ancha). Es lo más prometedor. Necesita `onnxruntime` y toca
   el bucle de grabación, que es la parte más delicada del proyecto.
2. **`WHISPER_MODEL=small`** en vez de `base`: el mayor salto de precisión
   posible y **sin dependencias**, pero ~2.5× más lento. **Hay que medirlo en
   la Pi.**
3. **Cancelación de eco (AEC)**: la solución "de teléfono" al eco del
   parlante. Con parlante Bluetooth (retardo variable) es muy difícil; no
   vale la pena para el evento.
4. **Supresión de ruido**: ojo, la documentación de Whisper avisa de que
   sobre-procesar audio limpio **empeora** la transcripción. Con micrófono de
   solapa puede restar en vez de sumar.

### Qué probar

1. **Confirmar `AUDIO_SAMPLE_RATE=48000`** en el `.env` de la Pi.
2. Diez frases variadas (cerca, lejos, bajito, con ruido) y comparar.
3. ¿El «ok MECH» despierta más fácil? Si ahora dispara solo, subir el
   "Umbral ruido".
4. Cronometrar el retardo con `WHISPER_BEAM_SIZE=5` y con 1.

Validado en simulación: 9 bloques con señales sintéticas (aliasing medido en
tres tipos de ruido, que la voz no se toque, pasa-altos, AGC en tres niveles,
que no amplifique el silencio, cadena completa, captura ya a 16 kHz, RMS sin
continua y que todo se pueda apagar desde config).

---


## 4. ⚠️ Lo PRIMERO que hay que hacer: probar en la Pi

En la Pi: icono **«Iniciar MECH»** (hace `git pull` y reinicia el server).
Al arrancar tienen que salir estas líneas; si falta alguna, la Pi corre
código viejo:

- `Comandos: solo en el idioma con el que se despertó a MECH · saludo en
  español` (lo del 6 oct; si dice «saludo en inglés», ver el punto 00.1)
- `Movilidad v4 (sep 2026): ...`
- `Trivia: 3 preguntas por partida…`
- `Idiomas: español · inglés · francés · portugués · alemán · italiano ·
  japonés · ruso · mandarín` (si solo salen cuatro, falta el código del
  5 oct)

Y en el navegador del panel, **Ctrl+Shift+R** (si no, se queda el `app.js`
viejo en caché y los botones nuevos no aparecen).

### 00) Lo del 6 oct (§2.sexies; ya subido, sin probar)

1. **Saludo en español**: panel → Ajustes → «Idioma del saludo» → ESPAÑOL →
   «Guardar y aplicar» (el `.env` de la Pi lo tiene en inglés). Luego, con
   MECH en reposo, vista Arduino → «SALUDAR AHORA»: tiene que decir «¡Hola!
   Soy MECH. Un gusto verte hoy aquí».
   - **Que no se despierte solo al saludar.** Si tras el saludo dice «Hola,
     ya te escucho», el eco se coló: anotar qué sale en el log justo antes.
2. **Cada comando en su idioma**, con dos idiomas basta (español e inglés):
   - «ok MECH» → pedir una obra → a media narración decir «hey MECH»: NO
     debe cortarse. Decir «oye MECH»: sí.
   - Dormirlo, «wake up MECH» → pedir algo → «oye MECH»: NO debe cortarse.
     «hey MECH»: sí. El banner del panel dice cuál toca.
   - Despierto en inglés: «para de escuchar» NO lo duerme, «stop listening»
     sí. Despierto en español: «wake up MECH» NO lo pasa a inglés.
   - ⚠️ Lo que no se pudo simular: cómo escribe Whisper «hey MECH» cuando
     transcribe en inglés (¿«Hey, Mac»?). Si «hey MECH» no corta, mirar en
     el panel `Oí mientras narraba: '…'` y añadir esa forma a
     `VOICE_INTERRUPT_PHRASES_EN`. Lo mismo en cada idioma.
3. Si en el evento estorba: Ajustes → «Idioma de los comandos», apagado, y
   vuelve lo de antes sin reiniciar.

### 0) Lo del 5 oct (ya subido; sin probar)

1. **Panel**: abrirlo y dar **Ctrl+Shift+R**. Tiene que verse negro grafito
   con el acento cian, no violeta. Repasar que TODOS los botones siguen
   donde estaban y hacen lo mismo (sobre todo mantener apretado AVANZAR /
   GIRO en la vista Arduino, y las palanquitas de Ajustes → «Guardar y
   aplicar»).
2. **Fuente para japonés y chino**: `sudo apt install fonts-noto-cjk` en la
   Pi, y `python -m backend.preflight` (§11 tiene que dar OK).
3. **Despertar en cada idioma nuevo**: «guten Tag MECH», «ciao MECH»,
   «こんにちは MECH», «привет MECH», «你好 MECH». El log debe decir «MECH
   despierto (<idioma>)» y contestar en ese idioma.
   - Si en japonés/ruso/chino NO despierta: mirar el panel, sale «Oí en
     <idioma>: '…'». Copiar cómo escribió el nombre a `VOICE_NAME_ALIASES`
     del `.env` y reiniciar. Si ni siquiera detecta el idioma, probar
     `WHISPER_MODEL=small`.
   - Comprobar que «hello MECH» y «hola MECH» **no** lo despiertan.
4. **Una obra en japonés o chino**: que narre, que los subtítulos se lean
   (no cuadritos) y que cambien de línea en sitios razonables.
5. **Chips del panel** (vista Voz): los nueve cambian el idioma sin
   micrófono. Útil para separar «no me entiende» de «no funciona».
6. Cuánto tarda en despertar ahora. Con nueve idiomas el reintento sigue
   siendo UNA pasada de Whisper, así que no debería notarse; si se nota,
   apagar en el `.env` los idiomas que no se vayan a usar.

### A) Lo nuevo del 23–26 sep (sin probar)

1. **Controles del panel** (vista Arduino):
   - AVANZAR va hacia adelante y RETROCEDER hacia atrás. Si no: Ajustes →
     «Adelante/atrás invertido».
   - Los dos botones **GIRO** giran sobre sí mismo.
   - Los dos **LATERAL** — *esto es lo que no se sabe*: ¿se desplaza de lado
     de verdad con `w`? Si no se mueve o hace algo raro, anotar exactamente
     qué hace. Si izquierda y derecha salen cambiadas (en GIRO o en
     LATERAL), es cambiar el signo en ese botón de `frontend/index.html`.
2. **«Regresa a proyectar»**: girarlo con un botón GIRO → la vista Arduino
   debe decir «NO LO SÉ (lo giraste a mano)» → decir «regresa a proyectar»
   (o «vuelve a la proyección») → tiene que girar. Y el camino normal: «mira
   hacia afuera» → gira y saluda → «regresa a proyectar» → vuelve.
3. **Trivia**: pedir una obra y dejarla terminar ENTERA → debe ofrecer la
   trivia → «sí» → pantalla de carga → pregunta con fichas de colores.
   Contestar de las tres formas («la A», «la segunda», el texto). Probar un
   acierto (confeti) y un fallo (dice la correcta). Probar «no sé» dos
   veces: debe revelar y seguir.
   - Sin micrófono: tarjeta TRIVIA de la vista Voz («Empezar trivia» y un
     botón por opción). Si por ahí funciona y hablando no, el problema es de
     audio, no del juego.
   - Si MECH se contesta a sí mismo (el micrófono oye su propio parlante):
     subir `TRIVIA_DRAIN_SECONDS`.
   - Es la primera vez que `llm.make_quiz` llama a Claude **de verdad** (en
     la laptop se simuló). Si falla, el panel muestra el error exacto.
4. **Recorte de la relatividad**: primero `ffmpeg -version` en la Pi (si no
   está: `sudo apt install ffmpeg`). Subir un video al segmento 3 en
   `/library` → el panel debe decir que lo recortó a los últimos 10 s, y el
   original queda en `backend/video_library/relatividad/originales/`.
5. **Saludo**: ya se probó el 23 sep. Solo repasar si el brazo va hacia
   adelante; si va hacia atrás: Ajustes → «Sentido brazos».
6. **Botón «Biblioteca de videos»** de `MECH Panel.exe`: abre `/library` en
   el navegador de siempre.

### B) Heredado de antes de la reversión (seguía sin probar)

1. **Interrumpir**: ponerlo a narrar algo largo y decirle «oye MECH».
   - ¿El audio sale limpio, sin entrecortarse?
   - ¿Cuánto marca el log en «Corto la narración (X s…)» y «Voz cortada en N ms»?
   - Si en el log aparece `Oí mientras narraba:` con texto de su PROPIA
     narración → subir "Umbral al narrar".
   - Si no reacciona → bajarlo, y probar el botón «Interrumpir narración» para
     descartar que sea el micrófono.
2. **Idiomas**: «wake up MECH» → inglés, «bonjour MECH» → francés,
   «bom dia MECH» → portugués (log: "MECH despierto (<idioma>)"). Debe
   narrar y subtitular en ese idioma y volver a español al dormirse. Ver
   §3.septies para las trampas que hay que descartar.
3. **Traductor (§3.octies)**: «traduce MECH» → «de español a inglés» → una
   frase → debe repetirla en inglés y **callarse**. Repetir «traduce MECH»:
   NO debe volver a preguntar los idiomas. Si traduce su propia PREGUNTA
   (eco del parlante): subir `TRANSLATOR_DRAIN_SECONDS`.
4. **Giro de 180°**: calibrar `TURN_180_SECONDS` en Ajustes (§3.bis). Es lo
   que más tiempo lleva, y hay que repetirlo si cambian batería, suelo o
   ruedas.
5. **Marketing (§3.ter)**: subir un par de videos en `/library` →
   «Proyectar ahora» → ¿se ven enteros, uno tras otro, **y se oyen**? Si se
   ven mudos, es el flag de autoplay de Chromium (el icono «Proyectar MECH»
   ya lo lleva).
6. **VR sincronizada (§3.quater y §3.quinquies)**: con marketing
   proyectando, ENTRAR al visor (tiene que aparecer por donde va el audio),
   SALIR de la página y VOLVER — no debe empezar de nuevo.
7. **Audio (§3.decies)**: confirmar `AUDIO_SAMPLE_RATE=48000` en el `.env`
   de la Pi. Si ahora dispara solo, subir el "Umbral ruido".
8. Vigilar la **CPU de la Pi** mientras narra (`htop`): si sigue alta, la
   siguiente palanca es `WHISPER_INTERRUPT_MODEL=tiny`.

Antes del evento, con el server apagado: `python -m backend.preflight`
(avisa, entre otras cosas, si el `.env` de la Pi tapa el saludo de 3
rotaciones o las frases de la trivia).

---

## 5. Frentes ABIERTOS

### A) Motores y ruedas
Los motores y ruedas se **cambiaron en septiembre**; por eso AVANZAR iba
hacia atrás y los laterales giraban (§2.bis). En vez de reflashear o
recablear se corrigió por software. Lo que queda:
- **Confirmar qué hace `w`** con las ruedas nuevas (punto A.1 de §4). De eso
  depende que los botones LATERAL sirvan para algo.
- Si algún día se remontan las ruedas en X (mecanum de libro), habría que
  recalibrar `driveOmni()` en el firmware. **No lo propongas**: el equipo
  decidió no remontarlas y todo el movimiento autónomo es adelante/atrás.
- Sin encoders: todo giro va por TIEMPO.

### B) Pendientes menores
- **Generar y subir los videos** de `relatividad` (7), `crispr` (5) e
  `isaac_newton` (5). Los guiones están en `docs/GUIONES_*.md`. Mientras
  falte un solo segmento, esa obra no se ofrece a Claude y MECH cae a
  imágenes de Gemini.
- **Fotos reales del robot** a `web/assets/robot-01.jpg` / `robot-02.jpg`
  (preguntar antes: la otra sesión rehízo la web y puede que ya no hagan
  falta).
- **Servos de los brazos**: si responden `ACK:ARM` pero no se mueven, es
  ELÉCTRICO (alimentación 5–6 V externa / tierra común / interruptor), no
  código.
- El aro de LEDs sigue **en pausa** (`MECH_LEDS 0`).

---

## 6. Gotchas que cuestan tiempo si no se saben

- **Dependencias de la Pi con Python 3.13:** `pip install -r backend/requirements.txt`.
  Visión: `pip install "opencv-python-headless<5"` (NO la 5, NO mediapipe en
  3.13; corre con el detector Haar). Ver `backend/requirements-vision.txt`.
- **El `.env` de la Pi TAPA los defaults del código**, y «Guardar y aplicar»
  del panel escribe ahí TODAS las perillas. Si un cambio de default «no
  llega» (el saludo sigue con 2 repeticiones, una frase nueva no funciona),
  mirar primero el `.env`. El preflight lista las claves que tapan.
- **`git pull` en la Pi + reiniciar el server** para aplicar cambios: icono
  «Iniciar MECH» (ver `pi/README.md`). El frontend NO necesita reinicio,
  pero sí **Ctrl+Shift+R** en el navegador. El firmware se flashea aparte.
- **El comando crudo del panel NO pasa por `DRIVE_INVERT_FORWARD`**:
  `MOVE:100:0:0` a mano puede ir al revés que el botón AVANZAR. No es un bug.
- **Iconos del panel**: solo existen los del subconjunto local
  (`frontend/vendor/mech-icons.css`). `ti-help-circle` NO está — por eso la
  trivia usa `ti-bulb`. Un icono que falta deja el botón en blanco; se
  regenera con `python scripts/mkicons.py`.
- **`frontend/trivia.js`**: al revelar la respuesta NO se repite la
  animación de entrada (`.mt-wrap.reveal`), y la banda del veredicto va en
  el flujo, no encima. Las dos cosas se rompieron una vez; no las «limpies».
- **Recorte de videos**: necesita `ffmpeg` y `ffprobe` en la Pi. Re-codifica
  a H.264 (copiando solo se puede cortar en fotogramas clave), así que
  tarda unos segundos por video.
- **VR en el teléfono:** recargar con caché limpia. El sondeo HTTP (no el
  WS) es lo que la hace funcionar en el móvil — **no quitarlo**.
- **El parlante es Bluetooth**: tiene buffer propio. Un rastro de voz de
  décimas DESPUÉS de cortar no se puede arreglar por software.
- **Escribir scripts de prueba**: los heredoc de bash con comillas y tildes
  fallan en esta máquina; mejor escribir el `.py` en el scratchpad y
  ejecutarlo.
- **`git push` solo cuando el usuario lo pida.** Commits en español,
  `Co-Authored-By: Claude ...`. Commitear por rutas
  (`git commit --only -- <rutas>`) para no arrastrar lo de la otra sesión.
- **Este `handoff.md` SÍ se commitea** (va en los commits desde sep 2026).

---

## 7. Cómo trabajar con este usuario

- Estudiante, **no** programador pro, en **español**. Explicaciones paso a paso,
  cambios chicos y revisables.
- **Ritmo de la sesión pasada**: pide el cambio → se hace y se verifica →
  se le explica qué probar → dice «sí, súbelo a GitHub» → push. Preguntar
  SIEMPRE antes de subir; no asumir que el «sí» anterior vale para el
  siguiente cambio.
- **Todo valor de movimiento va como configuración en vivo** (clave en
  `config.py` + `_LIVE_KEYS` y `/api/config` en `server.py` + control en
  Ajustes), nunca hardcodeado.
- Cuando algo falla en su consola/hardware, pedir el mensaje u observación
  **exacta** antes de adivinar.
- **Antes de dar por bueno un arreglo, simularlo con el código real.** El
  arreglo de «regresa a proyectar» destapó la tercera causa (el «go back»
  en inglés) solo al simular las frases una por una.
- **Decir claro qué se probó y qué no.** Casi nada de esta tanda se pudo
  probar en el robot; el usuario lo prueba en la Pi y vuelve con el
  resultado.
- **Hardware pieza por pieza** (flashear → 1 motor → …). Muchos problemas
  fueron eléctricos (batería débil, tierra común, voltaje), no de código.
- Al terminar cambios grandes, **actualizar este `handoff.md` y `CLAUDE.md`**.
