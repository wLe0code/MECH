# Assets del STAND

PNG con **fondo transparente**, alta resolución, listos para colocar sobre el
fondo negro del stand. Se regeneran con:

```bash
cd branding/scripts
python stand_assets.py
```

## Qué es cada archivo

| Archivo | Para qué | Tamaño |
|---|---|---|
| `frase-en.png` | **El lema**, dos líneas. Va justo debajo de las tarjetas M·E·C·H | 3600 × 799 |
| `frase-es.png` | El mismo lema en español | 3600 × 580 |
| `frase-en-1linea.png` | Variante de una sola línea, para espacios anchos | 4200 × 275 |
| `divisor.png` | Franja de píxeles de la marca. Separa sin meter ruido | 3000 × 29 |
| `datos-en.png` | Tres cifras clave (+40 %, 8 h, 100 %) | 3400 × 402 |
| `datos-es.png` | Las mismas cifras en español | 3400 × 402 |
| `guia-colocacion.png` | Referencia de cómo queda todo montado | 1000 × 2080 |
| `patrocinadores-azul.png` | **Barra de patrocinadores** estilo web, fondo claro azulado + glow tenue (recomendada) | 6033 × 764 |
| `patrocinadores-blanco.png` | La misma barra con el fondo claro neutro de la web | 6002 × 606 |
| `patrocinadores-azul-sin-fade.png` | Pastilla completa, sin desvanecer los extremos | 6164 × 764 |

## Orden recomendado (de arriba a abajo)

```
tarjetas M · E · C · H
<< If it's immersive, it is MECH. >>
frase-en.png            ← el lema
divisor.png             ← respiro
datos-en.png            ← opcional, si sobra espacio
render del robot
```

Deja **aire** entre bloques (mínimo la altura del divisor ×2). Si el espacio
queda justo, quita `datos-en.png` antes que reducir el lema: el lema es lo
que la gente lee de lejos.

## De dónde salen las cifras

- **+40 %** — retención de interés ante un robot humanoide
  (Fuentes-Moraleda et al., 2021, Univ. Rey Juan Carlos).
- **8 h** — autonomía de la batería, un día escolar completo.
- **100 %** — la voz se pasa a texto en el propio robot (faster-whisper
  local), sin internet.

## Barra de patrocinadores

Se regenera con `python barra_patrocinadores.py` (desde `branding/scripts`).
Toma los logos **originales** de `branding/patrocinadores/` a su resolución
nativa (los de la web están a 220 px y se verían borrosos en grande). Los seis
salen **una sola vez**, con el mismo aire entre todos y fuera de la franja que
se desvanece: en una pieza impresa, un logo repetido o cortado en el borde
parece un error. Para añadir un patrocinador: su logo en
`branding/patrocinadores/` y su nombre de archivo en `ORDEN` del script.

El fondo es **claro a propósito**: AdmisiónCR y Team STEAM son azul marino y
en una barra oscura desaparecerían.
