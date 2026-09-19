# Cómo oye MECH — y cómo hacerlo oír mejor

Documento de referencia sobre la cadena de audio: qué hacen los teléfonos
para entender tan bien la voz, qué de eso hace MECH hoy, y qué queda.

Escrito en sep 2026 a raíz de la pregunta del equipo: *"¿por qué Google o
Siri entienden tan bien y MECH no? Los micrófonos son buenos."*

---

## 1. La respuesta corta

**Casi nunca es el micrófono.** Un teléfono no oye mejor porque su cápsula sea
mejor — de hecho la del Steren MIC-9010 de MECH, al ir **pegada a la boca**,
recoge mejor señal que un teléfono a un metro de distancia.

Lo que hace un teléfono es **procesar el audio antes de reconocerlo**. Entre
que el sonido entra por la cápsula y llega al reconocedor, pasa por media
docena de etapas. Ese es el truco entero.

---

## 2. Qué hace un teléfono, etapa por etapa

| Etapa | Qué hace | ¿La necesita MECH? |
|---|---|---|
| **Array de micrófonos + beamforming** | 2-4 micrófonos separados unos centímetros. Comparando cuándo llega el sonido a cada uno, se calcula de qué dirección viene y se atenúa todo lo demás. | **No.** Es para micrófonos lejanos. El de MECH es de solapa: ya está a 15 cm de la boca, que es una ventaja *mayor* que cualquier beamforming. |
| **Cancelación de eco (AEC)** | El teléfono sabe exactamente qué está mandando al altavoz, así que puede restarlo de lo que entra por el micrófono. Por eso podés interrumpir a Siri mientras habla. | **Sí, sería útil.** Es la solución "de verdad" al problema de que MECH se oiga a sí mismo. Pendiente (§5). |
| **Supresión de ruido** | Una red neuronal separa voz de no-voz y atenúa lo segundo (ventilador, murmullo, tecleo). | **Sería útil** en un stand ruidoso. Pendiente (§5). |
| **Control automático de ganancia (AGC)** | Sube o baja el volumen para que la voz llegue siempre al mismo nivel, hable quien hable y desde donde hable. | **Sí — ya implementado** (§3). |
| **Filtro pasa-altos** | Corta por debajo de ~80 Hz: continua, zumbido de red, roce de ropa, golpes de mesa. | **Sí — ya implementado** (§3). |
| **Remuestreo con anti-aliasing** | Baja a los 16 kHz que quiere el reconocedor, filtrando primero para que los agudos no se "plieguen" sobre la voz. | **Sí — ya implementado** (§3). |
| **Detector de voz neuronal (VAD)** | Un modelito decide qué es voz humana y qué no, mucho mejor que un umbral de energía. | **Sería útil.** MECH usa webrtcvad (2011) + energía. Pendiente (§5). |
| **Chip dedicado siempre encendido** | Un DSP de bajísimo consumo escucha la palabra clave sin despertar el procesador. | **No aplica.** La Pi está enchufada. |

---

## 3. Lo que MECH ya hace (sep 2026)

Todo vive en [`backend/stt.py`](../backend/stt.py), en
`prepare_for_whisper()`, y se aplica en este orden:

```
micrófono 48 kHz → pasa-altos → remuestreo a 16 kHz → nivel → Whisper
```

El orden importa: si se normalizara antes de quitar el retumbe, el
normalizador contaría esa energía como si fuera voz.

### 3.1 Pasa-altos (`AUDIO_HIGHPASS_HZ`, 80 Hz)

Resta una media móvil, que es un pasa-altos suave. Suave **a propósito**: un
filtro agresivo se comería los graves de una voz masculina.

- Continua: **eliminada** (0.08 → 0.000002 medido).
- Retumbe de 30 Hz: **−13 dB**.
- Banda de la voz: conserva el **89 %**; los graves de voz masculina
  (150-300 Hz), el **81 %**.

**Esto arregla un problema que el equipo ya había peleado a mano.** El piso
de ruido del detector se mide con el RMS de cada frame; si el receptor USB
mete offset de continua, ese offset cuenta como "ruido ambiente", el piso
sube y MECH se queda sordo para el "ok MECH". Ahora `_frame_rms()` resta la
media antes de medir. Medido:

```
continua pura de 3000/32768 = 0.092  ->  RMS 0.00000   (antes: 0.092)
tono de 300 Hz de esa amplitud       ->  RMS 0.06473   (sí se oye)
voz + continua                       ->  RMS 0.06473   (= igual que solo voz)
```

### 3.2 Remuestreo con anti-aliasing

⚠️ **Esto era un defecto real.** El código bajaba de 48 kHz a 16 kHz
promediando bloques de 3 muestras. Eso es un filtro pobrísimo: todo lo que
esté por encima de 8 kHz **se pliega hacia abajo** y reaparece dentro de la
banda de la voz.

Medido (tono puro que no cabe en 16 kHz, cuánto sobrevive):

| Entrada | Reaparece a | caja (antes) | FIR (ahora) |
|---|---|---|---|
| 8.5 kHz | 7.5 kHz | −7 dB | −18 dB |
| 10 kHz | 6 kHz | −9 dB | **−48 dB** |
| 12 kHz | 4 kHz | −13 dB | **−52 dB** |
| 15 kHz | 1 kHz | −25 dB | **−56 dB** |

Con ruido de banda alta realista (lo que produce una fuente conmutada, un
proyector o el siseo de una sala), la mejora medida es de **16 a 47 dB menos
de basura** dentro de la banda útil.

Y de paso conserva mejor los agudos que SÍ importan (las consonantes):

```
4000 Hz:  caja -0.81 dB  ->  FIR +0.00 dB
6000 Hz:  caja -1.89 dB  ->  FIR +0.01 dB
```

Cuesta ~15 ms por cada 3 s de audio en un laptop (~60 ms en la Pi), nada al
lado de los segundos que tarda Whisper.

⚠️ **Solo aplica si se captura a más de 16 kHz.** Si el `.env` tiene
`AUDIO_SAMPLE_RATE=16000` no hay remuestreo y esta mejora no hace nada. En la
Pi debe estar en **48000** (el Steren no abre a 16000).

### 3.3 Nivel automático (`AUDIO_TARGET_DBFS`, −16 dBFS)

El "AGC" del teléfono, en versión simple. Whisper se entrenó con audio a un
nivel razonable y transcribe peor lo que entra bajito — y en un stand cada
visitante habla a distinta distancia y volumen.

- Se mide sobre el **percentil 90** de la envolvente, no sobre el total: si
  se midiera el total, una frase con pausas largas quedaría sobreamplificada.
- Tope de ganancia **×8**: amplificar un susurro ×30 solo subiría el ruido de
  sala y le regalaría alucinaciones a Whisper.
- Nunca satura (se topa a 0.97 de pico) y **no toca el silencio**.

Medido:

```
muy bajito (visitante lejos)   -49.2 -> -31.2 dBFS   (topado en x8)
normal                         -33.3 -> -16.0 dBFS
fuerte (casi saturando)        -14.2 -> -16.0 dBFS   (lo BAJA)
```

### 3.4 `WHISPER_BEAM_SIZE` (5)

Cuántas hipótesis explora el decodificador. Estaba fijo en 1 ("más rápido");
5 es el default de faster-whisper y acierta bastante más en frases cortas con
ruido, a cambio de unas décimas.

**El modelo de interrupciones sigue en 1** (`WHISPER_INTERRUPT_BEAM_SIZE`):
ahí manda el retardo, porque MECH sigue hablando mientras tanto, y solo hay
que reconocer dos palabras conocidas.

### 3.5 Dónde se ajusta todo

Ajustes del panel, **en vivo y sin reiniciar**:

| Slider | Clave | Cuándo tocarlo |
|---|---|---|
| Quita retumbe | `AUDIO_HIGHPASS_HZ` | Subir si hay zumbido o roce de ropa; 0 lo apaga |
| Nivel de voz | `AUDIO_TARGET_DBFS` | Si la voz entra muy bajita; 0 lo apaga |
| Precisión STT | `WHISPER_BEAM_SIZE` | Bajar a 1 si la respuesta se siente lenta |

---

## 4. Cómo medirlo sin hardware

El script de simulación fabrica voz sintética y le suma la basura de un stand
(siseo de agudos, retumbe, continua) para comparar la cadena vieja con la
nueva. No necesita micrófono ni Whisper. Cubre: aliasing, que la voz no se
toque, el pasa-altos, el AGC en tres niveles, que no amplifique el silencio,
la cadena completa, el caso de captura ya a 16 kHz, el RMS sin continua y que
todo se pueda apagar desde config.

---

## 4.bis La SALIDA: que se oiga con un parlante pequeño

Todo lo de arriba es cómo MECH **oye**. Esto es cómo se le **oye a él**.

El equipo pasó de un **JBL Charge 5** (~30 W) a unos **Logitech S150**
(**1,2 W por canal**). Son ~25 veces menos potencia: hay un límite físico que
el software no puede saltarse. Lo que sí se puede es entregarle al parlante
la señal más fuerte posible sin romperla.

`tts._subir_volumen()` se aplica a TODO lo que suena (voz y chime), justo
antes de escribir el WAV — así funciona igual con `pw-play`, `paplay` o
`ffplay`. Dos pasos:

### `TTS_NORMALIZE` (default true) — gratis, +8 dB

Escala cada frase para que su pico quede casi en el máximo. ElevenLabs no
entrega el audio a tope, así que aquí hay margen regalado. **Medido: +8,1 dB
de volumen con 0 % de distorsión** — solo multiplica, no deforma nada.

### `TTS_GAIN_DB` (default 0) — empuje con limitador

Más decibelios encima. Como ya no cabe más señal, subir de golpe recortaría
los picos en seco y la voz sonaría rota. En vez de eso hay un **limitador
suave**: por debajo de 0.70 no se toca nada y los picos se redondean con
`tanh`. Eso sube el volumen **percibido** (la energía media) sin el crujido
del recorte duro. Medido:

| `TTS_GAIN_DB` | Volumen total | Distorsión |
|---|---|---|
| 0 (solo nivelar) | +8,1 dB | 0 % |
| **+6** | **+13,2 dB** | 1 % |
| +9 | +14,9 dB | 3,5 % |
| +12 | +16,2 dB | 7 % |
| +18 | +17,7 dB | 14 % |

**Recomendado para los S150: +6.** Por encima de +12 la voz empieza a sonar
apretada y se gana poco — la curva se aplana porque el limitador ya está
trabajando todo el rato.

Los dos se ajustan **en vivo** desde Ajustes («Volumen voz» y «Nivelar voz»),
así que en el stand se sube hasta donde suene bien y ya.

### ⚠️ Antes que nada: el volumen del sistema

El software no puede compensar un mezclador al 40 %. En la Pi:

```bash
wpctl set-volume @DEFAULT_AUDIO_SINK@ 1.0    # PipeWire (Bookworm)
alsamixer                                    # o a mano, tecla F6 para elegir
```

Y los S150 tienen **3 botones** en el frente del parlante derecho: `−`,
**mute** y `+` (no una rueda). Que no esté en mute, y darle varias veces al
`+`. Eso suele ser el mayor salto de todos, y es gratis.

⚠️ Ojo: en el S150 esos botones son **digitales**, no un potenciómetro. Si
lo que mandan al sistema son teclas de volumen, están tocando la MISMA
etapa que `wpctl` — y entonces `volumen-max.sh` ya la deja arriba. Para
saberlo, `pi/volumen-max.sh` con doble click lista todas las etapas que
encuentra y su nivel.

### Si aún así no alcanza

Es un problema de hardware, no de software. Un parlante **amplificado**
(activo, con su propia fuente) de 10-20 W resuelve de verdad; los S150 se
alimentan por USB y por eso son tan flojos.

Ojo también con `BACKGROUND_MUSIC_VOLUME` (18): si subís la voz, quizá haya
que bajar la música para que no compita.

---

## 5. Lo que FALTA (por orden de impacto esperado)

Ninguna de estas está hecha. Todas necesitan una decisión del equipo porque
añaden una dependencia o cuestan CPU en la Pi.

### 5.1 Detector de voz neuronal (Silero VAD) — el más prometedor

MECH usa **webrtcvad**, de 2011, que decide "esto es voz" con un modelo
estadístico simple. Se dispara con cualquier ruido de banda ancha: una silla
arrastrada, un aplauso, un golpe en la mesa. Por eso hizo falta añadirle
encima un umbral de energía y un piso de ruido adaptativo — toda esa
complejidad de `record_until_silence()` existe para compensarlo.

**Silero VAD** es un modelito neuronal (~2 MB) que distingue voz humana de
ruido mucho mejor. faster-whisper ya lo trae dentro (`vad_filter=True`), pero
requiere el paquete **`onnxruntime`**.

- **Coste:** una dependencia más en la Pi (Python 3.13, aarch64 — hay que
  comprobar que haya wheel). CPU: mínima, el modelo es diminuto.
- **Dónde daría el salto:** reemplazando a webrtcvad en el bucle en vivo, no
  en `vad_filter` (MECH ya recorta el audio antes de llamar a Whisper, así
  que ahí no aportaría).
- **Riesgo:** medio. Toca el bucle de grabación, que es lo más delicado del
  proyecto y lo que más se ha iterado en el robot real.

### 5.2 Modelo `small` en vez de `base`

Es el salto de precisión más grande que existe para Whisper multilingüe, y no
necesita ninguna dependencia nueva: solo cambiar `WHISPER_MODEL=small` y
descargarlo una vez.

- **Coste:** ~2.5× más lento y ~3× más RAM. En una Pi 5 de 8 GB la RAM sobra;
  el tiempo hay que **medirlo en el robot** antes de decidir.
- **Prueba sugerida:** poner `small`, decirle diez frases y comparar el
  retardo con el de hoy. Si se siente lento, volver a `base` y bajar
  `WHISPER_BEAM_SIZE` a 1.

### 5.3 Cancelación de eco (AEC)

La solución "de teléfono" al problema de que MECH se oiga a sí mismo, que en
este proyecto se ha atacado tres veces por otros caminos (umbral alto al
narrar, esperas de drenaje, modo traductor por turnos).

- **Coste:** alto. Hay que capturar la señal que va al parlante como
  referencia y correr un filtro adaptativo. Con un parlante **Bluetooth** es
  aún peor: el retardo es variable y desconocido, y eso es justo lo que un
  AEC necesita saber.
- **Recomendación:** no vale la pena para el evento. Si algún día se cambia a
  un parlante por cable, se puede reconsiderar.

### 5.4 Supresión de ruido (RNNoise / `noisereduce`)

Atenúa el ruido estacionario (murmullo, ventilador, proyector).

- **Coste:** una dependencia más y CPU por frase.
- **Ojo:** la propia documentación de Whisper avisa de que **sobre-procesar
  audio limpio empeora la transcripción**. Con un micrófono de solapa el
  audio ya entra bastante limpio, así que esto puede restar en vez de sumar.
  Probar antes de adoptar.

---

## 6. Qué probar en la Pi

1. **Confirmar `AUDIO_SAMPLE_RATE=48000`** en el `.env` de la Pi. Con 16000
   la mejora del remuestreo no hace nada.
2. Decirle diez frases variadas (cerca, lejos, bajito, con ruido de fondo) y
   comparar la transcripción con la de antes.
3. Mirar si el **"ok MECH" despierta más fácil**: el arreglo del RMS debería
   bajar el piso de ruido. Si ahora dispara solo, subir el "Umbral ruido".
4. Cronometrar el retardo con `WHISPER_BEAM_SIZE=5` y con 1.
5. Si sobra tiempo, probar `WHISPER_MODEL=small` (§5.2).

---

## 7. Fuentes

- [How noise removal improves Whisper accuracy](https://dev.to/stevecase430/clean-audio-before-whisper-how-noise-removal-improves-transcription-accuracy-with-code-pko)
- [Build a reliable AI transcription pipeline](https://dev.to/toshiusklay/build-a-reliable-ai-transcription-pipeline-a-developers-field-guide-31ba)
- [Whisper accuracy issues: improvement guide](https://gigagpu.com/fix-whisper-transcription-accuracy/)
- [faster-whisper — VAD (Silero) y `vad_filter`](https://github.com/SYSTRAN/faster-whisper)
- [faster-whisper `vad.py` (dependencia de onnxruntime)](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/vad.py)
- [reSpeaker XVF3000 — AEC, beamforming, AGC en hardware](https://wiki.seeedstudio.com/ReSpeaker_Mic_Array_v2.0/)
- [Loudspeaker beamforming to enhance speech recognition](https://arxiv.org/pdf/2501.08104)
