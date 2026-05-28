# video_library/

Esta carpeta contiene los **videos pre-renderizados** de las obras culturales que
MECH puede contar (Opción B de la arquitectura).

## Para qué

Generar video con IA en vivo (Kling, Veo, Runway) tarda **30 s – 2 min** por clip y
cuesta varios dólares por historia. Eso rompe la experiencia interactiva del stand
(el usuario se aburre y se va). En cambio, los videos se generan **una sola vez,
antes del evento**, en otra máquina sin presión de tiempo, y MECH solo los reproduce.

## Estructura

```
backend/video_library/
    romeo_julieta/
        seg01.mp4
        seg02.mp4
        seg03.mp4
        seg04.mp4
        seg05.mp4
    shrek/
        seg01.mp4
        ...
    la_odisea/
        ...
    don_quijote/
        ...
```

- El **slug** del subdirectorio (`romeo_julieta`, etc.) debe coincidir EXACTO con el
  slug definido en [`backend/video_library.py`](../video_library.py).
- Los archivos siguen la convención `seg{NN:02d}.mp4` con número 1-indexado.
- El número de segmentos por obra (`segments` en el manifest) debe coincidir con
  los archivos presentes.

## Cómo subir videos

### Opción A — UI web (más fácil)

1. Arranca el servidor: `python -m backend.server`
2. Abre `http://<ip-de-la-pi>:8000/library`
3. Verás un card por cada obra, con un botón por segmento. Click → escoger archivo
   → se sube y se valida que esté disponible.

### Opción B — SCP / copiar a mano

```bash
# Desde tu compu (donde generaste el video):
scp Romeo_escena01.mp4 pi@<ip-de-la-pi>:~/MECH/backend/video_library/romeo_julieta/seg01.mp4
```

### Opción C — curl

```bash
curl -F "file=@Romeo_escena01.mp4" \
     http://<ip-de-la-pi>:8000/api/library/romeo_julieta/1
```

## Cómo añadir una obra nueva

1. Edita [`video_library.py`](../video_library.py) y añade una entrada nueva a
   `WORKS` con su `title`, `author`, `synopsis` y número de `segments`.
2. Crea el subdirectorio: `mkdir -p backend/video_library/<slug>/`
3. Sube los videos (opción A, B o C arriba).
4. Reinicia el servidor — la lista de obras disponibles se inyecta al system
   prompt de Claude al arranque.

## Recomendaciones técnicas para los videos

- **Resolución:** 1080p (1920×1080) o menor. La Raspberry Pi reproduce mejor
  con codecs H.264 estándar.
- **Duración:** 5–15 segundos por segmento. MECH los reproduce en bucle mientras
  narra (la narración dura ~20–30 s, así que el video se va a repetir 2–6 veces).
- **Sin audio:** los videos se silencian por código (`<video muted>`). Si tienen
  música o voz, no se va a oír — y aunque se oyera, chocaría con el TTS del robot.
- **Codec:** H.264 (mp4) es lo más compatible. Algunos modelos exportan WebM o
  ProRes; convierte primero:
  ```bash
  ffmpeg -i original.webm -c:v libx264 -crf 23 -preset slow -an seg01.mp4
  ```
- **Estilo cinematográfico:** prompts dramáticos, iluminación marcada, encuadre
  cerrado. El video se proyecta y la voz lo acompaña — quieres ambiente, no
  documental.

## Fallback automático

Si **falta** algún segmento de una obra, esa obra **no aparece** en la lista que
ve Claude. Si el usuario la pide igual, Claude responde con `image_prompt` y se
generan imágenes con NanoBanana en vivo. Es decir: la biblioteca incompleta no
rompe el robot; solo significa que esa obra usa el flujo viejo.

## Ignorar de git

Los videos son archivos grandes — añade esta carpeta a `.gitignore` (o solo el
contenido):

```
backend/video_library/*/
!backend/video_library/README.md
```
