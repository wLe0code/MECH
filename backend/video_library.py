"""Biblioteca de videos pre-renderizados (Opción B de la arquitectura).

Para WRO 2026 evitamos generar video en vivo (latencia 30s–2min con
Kling/Veo/Runway mata la demo interactiva). En su lugar, los videos de
las obras culturales se generan UNA VEZ antes del evento (en otra
máquina, sin presión de latencia) y se guardan como .mp4 en
``VIDEO_LIBRARY_DIR``. MECH los reproduce en bucle mientras narra.

Estructura en disco esperada:

.. code-block:: text

    backend/video_library/
        romeo_julieta/
            seg01.mp4
            seg02.mp4
            ...
        shrek/
            seg01.mp4
            ...

El "slug" del subdirectorio es lo que Claude usa para referirse a la
obra en el `Plan`. Los archivos siguen el patrón ``seg{NN:02d}.mp4``.

Si una obra NO está en la biblioteca o le faltan segmentos, MECH cae al
flujo original de NanoBanana (generación de imagen en vivo) para no
romper preguntas espontáneas del usuario.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import TypedDict

import config


class WorkMeta(TypedDict, total=False):
    title: str
    author: str
    synopsis: str
    segments: int
    # Opcional: True si esta exposición admite música de fondo bajo la
    # narración (se sube un sample a video_library/<slug>/music.<ext>).
    music: bool
    # Opcional: lista de datos VERIFICADOS (fechas, nombres, hechos). Se
    # inyectan al system prompt para que Claude no los invente/alucine.
    # Solo poné aquí cosas que sepas ciertas; MECH tratará esto como verdad.
    facts: list[str]
    # Opcional: URLs de donde se verificaron los facts. Documentación para
    # humanos — NO se inyectan al prompt (no gastan tokens). Si corregís o
    # añadís un fact, anotá aquí de dónde lo sacaste.
    sources: list[str]
    # Opcional: True = "slot abierto" tipo MARKETING. Se comporta distinto a
    # una obra normal en cuatro cosas:
    #   1. `segments` es un MÁXIMO de espacios, no una cantidad exigida: se
    #      proyecta con los videos que haya, aunque falten (y aunque haya
    #      huecos en el medio).
    #   2. Los videos se reproducen ENTEROS y en fila (playlist), no en bucle
    #      bajo la narración de MECH.
    #   3. Suenan CON SU PROPIO AUDIO. MECH no narra encima.
    #   4. NO se le ofrece a Claude: se dispara con una orden directa
    #      ("proyecta marketing"), sin pasar por el modelo.
    promo: bool
    # Opcional: RECORTE automático al subir un video, por segmento.
    # {segmento: ("inicio" | "final", segundos)} = se conservan los primeros
    # o los últimos N segundos. Lo hace `trim_uploaded()` con ffmpeg justo
    # después de subirlo; el archivo ORIGINAL se guarda en
    # <slug>/originales/ por si hay que recortarlo distinto. Los segmentos que
    # no aparecen aquí se usan tal cual. Las imágenes nunca se recortan.
    trim: dict[int, tuple[str, float]]


# Catálogo de obras con video pre-renderizado.
#
# Para añadir una obra nueva:
#   1. Crea la entrada aquí con el slug que prefieras.
#   2. Crea el subdirectorio backend/video_library/<slug>/.
#   3. Sube los archivos seg01.mp4, seg02.mp4, ... según `segments`.
#   4. Reinicia el servidor (el system prompt se recompone al arrancar).
WORKS: dict[str, WorkMeta] = {
    # --- Slot abierto de MARKETING (promo) ---------------------------------
    # No es una obra cultural: es el material promocional del equipo. Se
    # proyecta entero y con su propio audio cuando alguien dice
    # "proyecta marketing". Ver `promo` en WorkMeta.
    "marketing": {
        "title": "Marketing",
        "author": "Equipo MECH",
        "synopsis": (
            "Videos promocionales del proyecto. Se proyectan enteros, en "
            "orden y con su propio audio, uno tras otro. No hace falta "
            "llenar todos los espacios: se reproduce lo que haya."
        ),
        # MÁXIMO de espacios disponibles (no hay que llenarlos todos).
        "segments": 12,
        "promo": True,
    },
    "don_quijote": {
        "title": "Don Quijote de la Mancha",
        "author": "Miguel de Cervantes",
        "synopsis": (
            "Un hidalgo enloquecido por las novelas de caballería sale junto "
            "a Sancho Panza a buscar aventuras imposibles."
        ),
        "facts": [
            "La primera parte se publicó en 1605 y la segunda en 1615.",
            "Miguel de Cervantes nació en Alcalá de Henares en 1547 y murió "
            "en Madrid en 1616 (un año después de publicar la segunda parte).",
            "El protagonista es el hidalgo Alonso Quijano (don Quijote); su "
            "escudero es Sancho Panza, su caballo Rocinante y su amada "
            "idealizada Dulcinea del Toboso.",
            "Es considerada la primera novela moderna y una de las obras "
            "cumbre de la literatura universal.",
        ],
        "sources": [
            "https://www.britannica.com/topic/Don-Quixote-novel",
            "https://en.wikipedia.org/wiki/Don_Quixote",
            "https://www.britannica.com/biography/Miguel-de-Cervantes",
        ],
        "segments": 4,
    },
    "campana_1856": {
        "title": "Campaña Nacional de 1856",
        "author": "Historia de Costa Rica",
        "synopsis": (
            "Costa Rica y Centroamérica se unen para expulsar al filibustero "
            "William Walker. Gesta del héroe Juan Santamaría, que incendia el "
            "mesón en la Batalla de Rivas."
        ),
        "facts": [
            "La Campaña Nacional fue de marzo de 1856 a mayo de 1857; el "
            "presidente de Costa Rica era Juan Rafael Mora Porras.",
            "La Batalla de Santa Rosa fue el 20 de marzo de 1856, en "
            "Guanacaste; la Batalla de Rivas fue el 11 de abril de 1856, en "
            "Nicaragua.",
            "Juan Santamaría, joven soldado y tambor de Alajuela, incendió el "
            "Mesón de Guerra en Rivas y murió en esa gesta; el 11 de abril es "
            "feriado nacional en Costa Rica en su honor.",
            "William Walker era un filibustero estadounidense que había "
            "ocupado Nicaragua desde 1855; se rindió el 1 de mayo de 1857.",
        ],
        "sources": [
            "https://es.wikipedia.org/wiki/Campa%C3%B1a_Nacional_de_1856-1857",
            "https://museojuansantamaria.go.cr/campana-nacional/",
        ],
        "segments": 4,
    },
    "jimenez_deredia": {
        "title": "Esculturas de Jiménez Deredia",
        "author": "Jorge Jiménez Deredia (escultor costarricense)",
        "synopsis": (
            "Exposición de la obra del escultor costarricense Jorge Jiménez "
            "Deredia, célebre por sus esferas y figuras en mármol y bronce. "
            "Su serie 'Génesis' fusiona el simbolismo de las esferas "
            "precolombinas de Costa Rica con temas universales de "
            "transformación, gestación y vida."
        ),
        "facts": [
            "Jorge Jiménez Deredia nació en Heredia, Costa Rica, el 4 de "
            "octubre de 1954; su nombre artístico 'Deredia' viene de "
            "'de Heredia'.",
            "Vive y trabaja en Italia desde 1976; se formó en la Academia de "
            "Bellas Artes de Carrara y estudió arquitectura en Florencia.",
            "Es el PRIMER escultor latinoamericano con una obra en la "
            "Basílica de San Pedro del Vaticano: la estatua de San Marcelino "
            "Champagnat, develada el 20 de septiembre del año 2000 ante Juan "
            "Pablo II.",
            "Su obra está inspirada en las esferas de piedra precolombinas "
            "de Costa Rica; su serie más conocida es 'Génesis'. Es ESCULTOR "
            "(mármol y bronce), no pintor.",
        ],
        "sources": [
            "https://es.wikipedia.org/wiki/Jorge_Jim%C3%A9nez_Deredia",
            "https://www.deredia.com/en/bioagrafia",
        ],
        "segments": 4,  # 3 videos reales + 1 imagen de una obra (cada slot acepta video o imagen)
    },
    "malpais": {
        "title": "Música de Malpaís",
        "author": "Malpaís (banda costarricense)",
        "synopsis": (
            "Exposición sobre Malpaís, banda costarricense fundada por Fidel "
            "Gamboa, ícono de la identidad nacional. Su música fusiona "
            "folclor y rock, evocando los paisajes, la nostalgia y el alma de "
            "Costa Rica."
        ),
        "facts": [
            "Fidel Gamboa fue MÚSICO, compositor, arreglista y cantante "
            "costarricense; NO fue médico ni tuvo otra profesión.",
            "Fidel Gamboa nació en Nicoya el 6 de agosto de 1961 y murió en "
            "Escazú el 28 de agosto de 2011, a los 50 años, por un infarto "
            "(NO murió en 2018).",
            "Malpaís se formó en 1999; entre sus fundadores están los "
            "hermanos Fidel y Jaime Gamboa, junto a músicos como Manuel "
            "Obregón.",
            "Su primer disco se llama 'Uno' y salió en 2002.",
            "Tras la muerte de Fidel, la banda decidió continuar en honor a "
            "su legado.",
            "Su música mezcla folclor costarricense (sobre todo guanacasteco) "
            "con rock, jazz y trova.",
        ],
        "sources": [
            "https://es.wikipedia.org/wiki/Fidel_Gamboa",
            "https://es.wikipedia.org/wiki/Malpa%C3%ADs_(banda)",
            "https://www.grupomalpais.com/pages/historia",
        ],
        "segments": 4,
        "music": True,  # admite sample de música de fondo bajo la narración
    },
    "isaac_newton": {
        "title": "Isaac Newton",
        "author": "Isaac Newton (1642-1727), físico y matemático inglés",
        "synopsis": (
            "Vida, logros y contexto de Isaac Newton: el niño de Woolsthorpe "
            "que quedó huérfano de padre antes de nacer, el joven que durante "
            "la peste de 1665 formuló el cálculo, descompuso la luz y "
            "concibió la gravitación universal, el autor de los 'Principia' "
            "que explicó con las mismas leyes la caída de una manzana y el "
            "giro de los planetas, y el hombre que terminó dirigiendo la Casa "
            "de la Moneda y enterrado entre reyes en la Abadía de "
            "Westminster."
        ),
        "facts": [
            "Isaac Newton nació el 25 de diciembre de 1642 según el "
            "calendario juliano que usaba Inglaterra entonces, que equivale "
            "al 4 de enero de 1643 del calendario actual. Murió el 20 de "
            "marzo de 1727 (juliano), o 31 de marzo de 1727 en el actual. "
            "Las dos fechas son correctas: depende del calendario.",
            "Nació en Woolsthorpe Manor, en Lincolnshire, Inglaterra. Su "
            "padre murió unos meses ANTES de que él naciera, y su madre lo "
            "dejó al cuidado de su abuela cuando se volvió a casar.",
            "Estudió en el Trinity College de Cambridge, donde ingresó en "
            "1661.",
            "Entre 1665 y 1667 la Universidad de Cambridge cerró por la Gran "
            "Peste y Newton volvió a Woolsthorpe. En ese retiro forzado "
            "sentó las bases del cálculo, de su teoría de la luz y de la "
            "gravitación universal. Ese periodo se conoce como su 'annus "
            "mirabilis' (año maravilloso).",
            "Lo de la manzana lo contó el propio Newton en su vejez: vio "
            "caer una manzana y se preguntó por qué caía siempre hacia el "
            "centro de la Tierra. NO le cayó en la cabeza — eso es un adorno "
            "posterior.",
            "Con un prisma demostró que la luz blanca no es simple: está "
            "compuesta por los colores del arcoíris, y el prisma los separa "
            "en vez de teñirla. Lo publicó en 'Opticks' (1704).",
            "Construyó el primer telescopio reflector práctico, que usa un "
            "espejo en lugar de lentes. Los grandes telescopios de hoy "
            "siguen ese principio.",
            "Fue profesor lucasiano de matemáticas en Cambridge desde 1669.",
            "Su obra cumbre es 'Philosophiae Naturalis Principia "
            "Mathematica' (los 'Principia'), publicada en 1687 gracias al "
            "empeño y al dinero del astrónomo Edmond Halley. Ahí enuncia las "
            "tres leyes del movimiento y la ley de gravitación universal.",
            "La idea revolucionaria de los 'Principia' es que las MISMAS "
            "leyes explican la caída de una manzana y el giro de la Luna "
            "alrededor de la Tierra: el cielo y la Tierra obedecen la misma "
            "física.",
            "En 1696 entró en la Real Casa de la Moneda como Warden "
            "(guardián) y en 1699 llegó a Master (director), cargo que "
            "mantuvo hasta su muerte. Persiguió a los falsificadores de "
            "moneda en persona.",
            "Fue presidente de la Royal Society desde 1703 hasta su muerte.",
            "La reina Ana lo nombró caballero (Sir Isaac Newton) en abril de "
            "1705, durante una visita real al Trinity College.",
            "Mantuvo una agria disputa con Gottfried Leibniz sobre quién "
            "inventó primero el cálculo. Hoy se acepta que lo desarrollaron "
            "de forma independiente, y la notación que usamos en clase es la "
            "de Leibniz.",
            "Dedicó muchísimo tiempo a la alquimia y a estudios religiosos y "
            "de cronología bíblica: escribió más sobre eso que sobre física.",
            "Nunca se casó. Murió en Kensington y está enterrado en la "
            "Abadía de Westminster, un honor reservado a reyes y grandes "
            "figuras de Inglaterra.",
            "La frase 'si he visto más lejos, es por estar de pie sobre "
            "hombros de gigantes' es suya, de una carta a Robert Hooke "
            "en 1675.",
        ],
        "sources": [
            "https://en.wikipedia.org/wiki/Isaac_Newton",
            "https://www.britannica.com/biography/Isaac-Newton",
            "https://www.newton.ac.uk/about/isaac-newton/isaac-newtons-life/",
            "https://www.westminster-abbey.org/abbey-commemorations/commemorations/sir-isaac-newton",
            "https://www.royalsocietypublishing.org/doi/10.1098/rsnr.1998.0053",
        ],
        "segments": 5,
    },
    "isidro_con_wong": {
        "title": "Cuadros de Isidro Con Wong",
        "author": "Isidro Con Wong (pintor costarricense)",
        "synopsis": (
            "Exposición de la pintura de Isidro Con Wong, pionero "
            "costarricense del realismo mágico. Famoso por sus toros rojos, "
            "soles y lunas que retratan la mística rural y el campo de Costa "
            "Rica con color vibrante."
        ),
        "facts": [
            "Isidro Con Wong nació en Puntarenas el 25 de febrero de 1931 y "
            "FALLECIÓ el 1 de septiembre de 2024, a los 93 años (no hablar "
            "de él como si estuviera vivo).",
            "Fue hijo de inmigrantes chinos de la provincia de Cantón "
            "(Zhongshan); parte de su educación temprana fue en China.",
            "Antes de dedicarse al arte fue agricultor, pescador y ganadero "
            "en Paquera y el Golfo de Nicoya; se dedicó de lleno al arte a "
            "partir de los 40 años.",
            "Su estilo se conoce como realismo mágico; las vacas y toros de "
            "sus fincas y los paisajes de Puntarenas son motivos centrales.",
            "Además de pintor fue escultor (bronce y madera).",
        ],
        "sources": [
            "https://es.wikipedia.org/wiki/Isidro_Con_Wong",
            "https://isidroconwong.com/historia/",
            "https://www.larepublica.net/noticia/isidro-con-wong-maestro-del-realismo-magico-y-escultor-costarricense-fallece-a-los-93-anos",
        ],
        "segments": 4,  # 3 videos reales + 1 imagen de una obra (cada slot acepta video o imagen)
    },
    "relatividad": {
        "title": "La teoría de la relatividad",
        "author": "Albert Einstein (1879-1955), físico alemán",
        "synopsis": (
            "La relatividad contada en el orden en que se descubrió: el "
            "misterio de la luz que el éter no explicaba, el empleado de la "
            "oficina de patentes de Berna que en 1905 publicó cuatro "
            "artículos que cambiaron la física, el tiempo que se estira y el "
            "espacio que se encoge según las transformaciones de Lorentz, la "
            "equivalencia entre masa y energía, el 'pensamiento más feliz' "
            "que llevó a entender la gravedad como espacio-tiempo curvo, el "
            "eclipse de 1919 que lo comprobó y lo hizo mundialmente famoso, "
            "y todo lo que hoy depende de ella: el GPS, las ondas "
            "gravitacionales y la primera imagen de un agujero negro."
        ),
        # OCHO segmentos, uno por escena del guion (docs/GUIONES_RELATIVIDAD.md).
        # Ocho es justo el máximo de segmentos que admite un plan de Claude.
        "segments": 8,
        # Duraciones que pidió el equipo (23 sep 2026): el 1 dura 20 s y el 2
        # dura 10 s; del 3 al 7 los videos traen más de lo necesario y solo
        # se conservan sus ÚLTIMOS 10 s. El 8 se usa entero.
        "trim": {
            1: ("inicio", 20),
            2: ("inicio", 10),
            3: ("final", 10),
            4: ("final", 10),
            5: ("final", 10),
            6: ("final", 10),
            7: ("final", 10),
        },
        "facts": [
            "Los OCHO videos van en este orden, uno por segmento de "
            "narración: 1) el misterio de la luz y el éter (Maxwell, "
            "Michelson-Morley, 1865-1887); 2) Einstein en la oficina de "
            "patentes (1895-1905); 3) el tiempo no es igual para todos, la "
            "relatividad especial (1905); 4) las transformaciones de Lorentz, "
            "con sus fórmulas en una pizarra; 5) E=mc² (1905); 6) la gravedad "
            "es espacio curvo, la relatividad general (1907-1915); 7) el "
            "eclipse de 1919; 8) la relatividad hoy: GPS, ondas "
            "gravitacionales y la foto del agujero negro. Narra cada tramo "
            "sobre su video.",
            "Albert Einstein nació el 14 de marzo de 1879 en Ulm, Alemania, "
            "y murió el 18 de abril de 1955 en Princeton, Estados Unidos.",
            "James Clerk Maxwell publicó su teoría del campo "
            "electromagnético en 1865: de ella se deduce que la luz es una "
            "onda electromagnética que viaja a unos 300 000 km/s.",
            "El experimento de Michelson y Morley (1887, en Cleveland, "
            "Estados Unidos) buscaba el movimiento de la Tierra a través del "
            "éter y NO lo encontró. Es el 'resultado nulo' más famoso de la "
            "historia de la física.",
            "Hendrik Lorentz y Henri Poincaré ya habían desarrollado parte "
            "de las matemáticas de la relatividad especial. Lo NUEVO de "
            "Einstein fue la interpretación: el tiempo y el espacio mismos "
            "son relativos, y el éter sobra.",
            "Las transformaciones de Lorentz giran alrededor del factor de "
            "Lorentz: gamma = 1 dividido entre la raíz cuadrada de "
            "(1 menos v al cuadrado sobre c al cuadrado). A velocidades "
            "normales gamma vale prácticamente 1 y no se nota nada; cuando v "
            "se acerca a c, gamma se dispara. Lorentz las publicó en su "
            "forma moderna en 1904 y Einstein las dedujo en 1905 a partir de "
            "sus dos postulados. El nombre se lo puso Poincaré.",
            "De gamma salen las dos consecuencias famosas: la dilatación del "
            "tiempo (un reloj en movimiento avanza más lento) y la "
            "contracción de la longitud (un objeto en movimiento se acorta "
            "en la dirección en que viaja). Las ecuaciones de Newton son el "
            "caso particular de estas cuando la velocidad es mucho menor que "
            "la de la luz.",
            "Einstein trabajó en la Oficina de Patentes de Berna desde 1902 "
            "como experto técnico de tercera clase. Allí escribió los "
            "artículos de 1905.",
            "1905 es su 'año milagroso': cuatro artículos — el efecto "
            "fotoeléctrico, el movimiento browniano, la relatividad especial "
            "('Sobre la electrodinámica de los cuerpos en movimiento') y el "
            "de la equivalencia entre masa y energía, de donde sale E=mc².",
            "El Premio Nobel de Física de 1921 (entregado en 1922) se lo "
            "dieron por el EFECTO FOTOELÉCTRICO, **no** por la relatividad.",
            "El Sol convierte unos cuatro millones de toneladas de su masa "
            "en energía cada segundo. Eso es E=mc² en acción.",
            "Hermann Minkowski, que había sido profesor de Einstein, propuso "
            "en 1908 unir espacio y tiempo en una sola cosa: el "
            "espacio-tiempo.",
            "El 'pensamiento más feliz de su vida' (1907): una persona en "
            "caída libre no siente su propio peso. De ahí sale el principio "
            "de equivalencia entre gravedad y aceleración.",
            "Su amigo el matemático Marcel Grossmann le enseñó la geometría "
            "de Riemann, la herramienta que necesitaba para describir el "
            "espacio curvo. Publicaron juntos un primer intento en 1913.",
            "Las ecuaciones finales de la relatividad general las presentó "
            "ante la Academia Prusiana de Ciencias en noviembre de 1915. El "
            "matemático David Hilbert trabajaba en lo mismo al mismo tiempo.",
            "Con la relatividad general explicó por fin una anomalía en la "
            "órbita de Mercurio que la física de Newton no podía explicar "
            "(unos 43 segundos de arco por siglo).",
            "En 1916 Karl Schwarzschild, mientras servía en el frente de la "
            "Primera Guerra Mundial, encontró la primera solución exacta de "
            "las ecuaciones: la que describe lo que hoy llamamos un agujero "
            "negro.",
            "Eclipse del 29 de mayo de 1919: una expedición dirigida por "
            "Arthur Eddington fue a la isla de Príncipe (frente a África) y "
            "otra a Sobral (Brasil). Los resultados se anunciaron en Londres "
            "el 6 de noviembre de 1919 y convirtieron a Einstein en una "
            "celebridad mundial.",
            "GPS: los relojes de los satélites se adelantan unos 38 "
            "microsegundos al día respecto a los de la Tierra. Sin "
            "corregirlo, el error de posición crecería varios kilómetros por "
            "día.",
            "Ondas gravitacionales: Einstein las predijo en 1916 y el "
            "observatorio LIGO las detectó por primera vez el 14 de "
            "septiembre de 2015 (anunciado en febrero de 2016), producidas "
            "por la fusión de dos agujeros negros. Premio Nobel de Física "
            "2017.",
            "La primera imagen de un agujero negro (el del centro de la "
            "galaxia M87) la publicó el Event Horizon Telescope el 10 de "
            "abril de 2019.",
            "OJO con Mileva Marić, compañera de estudios y primera esposa "
            "de Einstein: se menciona a veces como coautora de la relatividad. "
            "Es un debate histórico SIN pruebas concluyentes: si alguien "
            "pregunta, di que se discute — no lo afirmes ni lo niegues.",
        ],
        "sources": [
            "https://en.wikipedia.org/wiki/Albert_Einstein",
            "https://en.wikipedia.org/wiki/Lorentz_transformation",
            "https://en.wikipedia.org/wiki/Michelson%E2%80%93Morley_experiment",
            "https://en.wikipedia.org/wiki/Eddington_experiment",
            "https://www.nobelprize.org/prizes/physics/1921/einstein/facts/",
            "https://www.ligo.caltech.edu/page/detection-companion-papers",
            "https://eventhorizontelescope.org/blog/astronomers-capture-first-image-black-hole",
            "https://www.gps.gov/systems/gps/performance/accuracy/",
        ],
    },
    "crispr": {
        "title": "CRISPR y Cas9: las tijeras genéticas",
        "author": "Emmanuelle Charpentier y Jennifer Doudna (Nobel de Química 2020)",
        "synopsis": (
            "CRISPR contado en el orden en que se descubrió: unas repeticiones "
            "raras en el ADN de las bacterias que resultaron ser una memoria "
            "contra los virus, la proteína Cas9 que Charpentier y Doudna "
            "convirtieron en unas tijeras genéticas programables en 2012, "
            "cómo busca y corta una secuencia exacta del ADN, el primer "
            "tratamiento aprobado para la anemia falciforme y la gran "
            "pregunta ética de editar embriones humanos."
        ),
        # CINCO segmentos, uno por escena del guion (docs/GUIONES_CRISPR.md).
        "segments": 5,
        "facts": [
            "Los CINCO videos van en este orden, uno por segmento de "
            "narración: 1) el misterio en el ADN de las bacterias y su "
            "sistema inmune (1987-2007); 2) las tijeras genéticas: "
            "Charpentier, Doudna y Cas9 (2011-2012); 3) cómo funciona: la "
            "guía busca la secuencia, Cas9 corta y la célula repara; 4) del "
            "laboratorio al hospital (2013-2023); 5) la gran pregunta ética "
            "(2018-hoy). Narra cada tramo sobre su video.",
            "CRISPR son las siglas en inglés de 'repeticiones palindrómicas "
            "cortas agrupadas y regularmente espaciadas'. Cas significa "
            "'asociada a CRISPR': son las proteínas que trabajan con esas "
            "repeticiones.",
            "En 1987 el equipo de Yoshizumi Ishino, en la Universidad de "
            "Osaka (Japón), describió por primera vez esas repeticiones raras "
            "en el ADN de la bacteria Escherichia coli. No supieron para qué "
            "servían.",
            "Francisco Mojica, de la Universidad de Alicante (España), estudió "
            "esas repeticiones desde 1993 en microbios de las salinas de "
            "Santa Pola. El nombre CRISPR lo acordaron Mojica y el holandés "
            "Ruud Jansen, y se publicó por primera vez en 2002.",
            "En 2005 Mojica publicó que los fragmentos entre las repeticiones "
            "coinciden con ADN de virus, y propuso que son una memoria "
            "inmunitaria de las bacterias. Otros dos grupos llegaron a la "
            "misma idea ese año.",
            "En 2007 Rodolphe Barrangou y Philippe Horvath, de la empresa "
            "Danisco, demostraron con la bacteria que se usa para hacer yogur "
            "y queso que CRISPR la protege de verdad contra los virus.",
            "En 2011 el grupo de la francesa Emmanuelle Charpentier describió "
            "el ARN llamado tracrRNA, una pieza clave del sistema. Ese mismo "
            "año Charpentier y la estadounidense Jennifer Doudna (Universidad "
            "de California en Berkeley) se conocieron en un congreso en "
            "Puerto Rico.",
            "En junio de 2012 Doudna, Charpentier y su equipo publicaron en "
            "la revista Science que Cas9 se puede programar con un ARN guía "
            "para cortar el ADN en el sitio que uno elija.",
            "La Cas9 más usada viene de la bacteria Streptococcus pyogenes. "
            "La guía lleva unas 20 letras genéticas que buscan su pareja en "
            "el ADN, y Cas9 corta las dos hebras.",
            "Después del corte la célula repara el ADN. Si lo repara 'a lo "
            "rápido' suele meter pequeños errores y el gen queda apagado; si "
            "se le da una copia corregida como molde, puede usarla para "
            "arreglar el gen.",
            "En enero de 2013 los equipos de Feng Zhang (Instituto Broad) y "
            "George Church (Harvard) publicaron edición con CRISPR en células "
            "humanas.",
            "El 7 de octubre de 2020 Emmanuelle Charpentier y Jennifer Doudna "
            "ganaron el Premio Nobel de Química 'por el desarrollo de un "
            "método para la edición del genoma'. Fue la primera vez que dos "
            "mujeres compartían, solas, un Nobel de ciencias.",
            "En julio de 2019 Victoria Gray, de Mississippi, fue la primera "
            "persona de Estados Unidos tratada con CRISPR para la anemia "
            "falciforme, dentro de un ensayo clínico.",
            "Casgevy es el primer tratamiento con CRISPR aprobado: el Reino "
            "Unido lo autorizó el 16 de noviembre de 2023 y Estados Unidos el "
            "8 de diciembre de 2023, para la anemia falciforme. Se extraen "
            "células madre de la sangre del paciente, se editan en el "
            "laboratorio y se le devuelven.",
            "En noviembre de 2018 el científico chino He Jiankui anunció el "
            "nacimiento de dos gemelas con un gen editado antes de nacer. Lo "
            "condenó la comunidad científica mundial y en diciembre de 2019 "
            "un tribunal chino lo sentenció a tres años de cárcel.",
            "La diferencia clave de la ética: editar células del cuerpo de un "
            "paciente no se hereda; editar embriones o células reproductoras "
            "sí pasa a los hijos, y eso está prohibido o muy restringido en "
            "muchos países.",
            "NO digas que Mojica ganó el Nobel (no lo ganó, aunque su trabajo "
            "fue fundamental) ni que CRISPR 'cura cualquier enfermedad "
            "genética': hoy hay un tratamiento aprobado y muchos ensayos en "
            "marcha.",
            "NO digas que Doudna y Charpentier 'inventaron CRISPR': CRISPR "
            "existe en las bacterias desde hace muchísimo tiempo. Lo que "
            "ellas hicieron fue convertirlo en una herramienta programable.",
        ],
        "sources": [
            "https://www.nobelprize.org/prizes/chemistry/2020/press-release/",
            "https://www.science.org/doi/10.1126/science.1225829",
            "https://www.science.org/doi/10.1126/science.1138140",
            "https://en.wikipedia.org/wiki/Francisco_Mojica",
            "https://en.wikipedia.org/wiki/CRISPR",
            "https://www.fda.gov/news-events/press-announcements/fda-approves-first-gene-therapies-treat-patients-sickle-cell-disease",
            "https://www.gov.uk/government/news/mhra-authorises-world-first-gene-therapy-that-aims-to-cure-sickle-cell-disease-and-transfusion-dependent-thalassemia",
            "https://en.wikipedia.org/wiki/He_Jiankui_affair",
        ],
    },
}


# ---------------------------------------------------------------------------
# Rutas y disponibilidad
# ---------------------------------------------------------------------------


# Un segmento puede ser un VIDEO (clip que loopea) o una IMAGEN (foto fija de
# una obra). Se acepta cualquiera de estas extensiones; el nombre base es
# seg01, seg02, ... y la extensión define el tipo.
_SEG_VIDEO_EXTS = (".mp4", ".webm", ".mov", ".m4v", ".mkv")
_SEG_IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")
_SEG_EXTS = _SEG_VIDEO_EXTS + _SEG_IMAGE_EXTS


def segment_filename(segment: int) -> str:
    """Nombre por defecto (mp4) — solo para logs/mensajes."""
    return f"seg{segment:02d}.mp4"


def segment_basename(segment: int) -> str:
    """Base sin extensión: seg01, seg02, ..."""
    return f"seg{segment:02d}"


def segment_file(slug: str, segment: int) -> Path | None:
    """Ruta del archivo del segmento si existe (video o imagen), o None."""
    folder = config.VIDEO_LIBRARY_DIR / slug
    base = segment_basename(segment)
    for ext in _SEG_EXTS:
        p = folder / f"{base}{ext}"
        if p.exists():
            return p
    return None


# ---------------------------------------------------------------------------
# Recorte automático al subir (campo `trim` de la obra)
# ---------------------------------------------------------------------------


def trim_rule(slug: str, segment: int) -> tuple[str, float] | None:
    """("inicio"|"final", segundos) si ese segmento se recorta al subirlo."""
    regla = WORKS.get(slug, {}).get("trim", {}).get(segment)
    if not regla:
        return None
    lado, segundos = regla
    return (lado, float(segundos))


def trim_label(slug: str, segment: int) -> str | None:
    """Texto corto para la página /library: "últimos 10 s", "primeros 20 s"."""
    regla = trim_rule(slug, segment)
    if regla is None:
        return None
    lado, segundos = regla
    cuales = "últimos" if lado == "final" else "primeros"
    return f"{cuales} {segundos:g} s"


def _duracion(path: Path) -> float | None:
    """Duración en segundos según ffprobe, o None si no se pudo saber."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=30,
        )
        return float(r.stdout.strip())
    except Exception:
        return None


def trim_uploaded(slug: str, segment: int, path: Path) -> tuple[Path, str | None]:
    """Recorta un video recién subido según el `trim` de su obra.

    Devuelve (ruta final del segmento, mensaje para el panel o None si no
    había nada que hacer). NUNCA pierde el video: si no hay ffmpeg o el
    recorte falla, se queda el archivo entero tal cual se subió y el mensaje
    lo dice.

    El original se mueve a `<slug>/originales/` y el recortado se escribe
    como `segNN.mp4` en H.264 (lo que mejor lee el navegador de la
    proyección). Se re-codifica en vez de copiar: copiando, ffmpeg solo puede
    cortar en los fotogramas clave y "los últimos 10 s" saldrían en 12 o 13.
    """
    regla = trim_rule(slug, segment)
    if regla is None or not segment_is_video(path):
        return path, None
    lado, segundos = regla
    etiqueta = trim_label(slug, segment)
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        return path, (
            f"No recorté {path.name} a los {etiqueta}: falta ffmpeg en la Pi "
            f"(sudo apt install ffmpeg). Se usa el video entero."
        )

    total = _duracion(path)
    if total is not None and total <= segundos + 0.3:
        return path, f"{path.name} ya dura {total:.1f} s: no hace falta recortarlo."

    originales = path.parent / "originales"
    originales.mkdir(exist_ok=True)
    original = originales / path.name
    if original.exists():
        original.unlink()
    shutil.move(str(path), str(original))

    destino = path.parent / f"{segment_basename(segment)}.mp4"
    cmd = ["ffmpeg", "-y", "-v", "error"]
    if lado == "final":
        cmd += ["-sseof", f"-{segundos:g}", "-i", str(original)]
    else:
        cmd += ["-i", str(original), "-t", f"{segundos:g}"]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    # Las obras van MUDAS (encima habla MECH); los slots promo llevan su audio.
    cmd += (["-c:a", "aac", "-b:a", "160k"] if is_promo(slug) else ["-an"])
    cmd.append(str(destino))
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        ok = r.returncode == 0 and destino.exists() and destino.stat().st_size > 0
        error = (r.stderr or "").strip().splitlines()[-1:] if not ok else []
    except Exception as e:
        ok, error = False, [str(e)]

    if not ok:
        # Volvemos a dejar el original donde estaba: mejor entero que nada.
        if destino.exists():
            destino.unlink()
        shutil.move(str(original), str(path))
        return path, (
            f"No pude recortar {path.name} ({' '.join(error) or 'error de ffmpeg'}). "
            f"Se usa el video entero."
        )
    return destino, (
        f"{destino.name} recortado a los {etiqueta}"
        + (f" (el original duraba {total:.1f} s)" if total else "")
        + f". El original quedó en {slug}/originales/."
    )


def remove_original(slug: str, segment: int) -> None:
    """Borra el original guardado de un segmento (al borrar el segmento)."""
    carpeta = config.VIDEO_LIBRARY_DIR / slug / "originales"
    for ext in _SEG_VIDEO_EXTS:
        p = carpeta / f"{segment_basename(segment)}{ext}"
        if p.exists():
            p.unlink()


def segment_path(slug: str, segment: int) -> Path:
    """Ruta por defecto (.mp4) — para guardar cuando no se sabe la extensión."""
    return config.VIDEO_LIBRARY_DIR / slug / segment_filename(segment)


def segment_url(slug: str, segment: int) -> str | None:
    """URL relativa del segmento existente (o None si no hay archivo)."""
    p = segment_file(slug, segment)
    return f"/videos/{slug}/{p.name}" if p else None


def segment_is_video(path: Path) -> bool:
    return path.suffix.lower() in _SEG_VIDEO_EXTS


def segment_kind(slug: str, segment: int) -> str | None:
    """'video' | 'image' | None según el archivo del segmento."""
    p = segment_file(slug, segment)
    if p is None:
        return None
    return "video" if segment_is_video(p) else "image"


def segment_exists(slug: str, segment: int) -> bool:
    return segment_file(slug, segment) is not None


# --- Música de fondo (solo obras con "music": True, ej. Malpaís) ------------

# Extensiones de audio aceptadas para el sample de música de fondo.
# (ffplay reproduce todas; incluimos las que salen de descargas comunes.)
_MUSIC_EXTS = (
    ".mp3", ".ogg", ".wav", ".m4a", ".aac", ".flac",
    ".opus", ".weba", ".webm", ".aiff", ".aif", ".wma",
)


def background_audio_path(slug: str):
    """Ruta al sample de música de fondo de la obra, o None si no hay.

    El archivo se llama music.<ext> dentro de la carpeta de la obra.
    """
    folder = config.VIDEO_LIBRARY_DIR / slug
    for ext in _MUSIC_EXTS:
        p = folder / f"music{ext}"
        if p.exists():
            return p
    return None


def background_audio_exists(slug: str) -> bool:
    return background_audio_path(slug) is not None


def background_audio_url(slug: str) -> str | None:
    p = background_audio_path(slug)
    return f"/videos/{slug}/{p.name}" if p else None


def supports_music(slug: str) -> bool:
    """True si la obra está marcada como que admite música de fondo."""
    return bool(WORKS.get(slug, {}).get("music"))


def is_promo(slug: str) -> bool:
    """True si es un slot abierto tipo marketing (ver `promo` en WorkMeta)."""
    return bool(WORKS.get(slug, {}).get("promo"))


def work_is_complete(slug: str) -> bool:
    """¿Está lista para proyectarse?

    Obra normal: TODOS los segmentos definidos tienen que estar en disco (si
    falta uno, la narración quedaría con un hueco visual).

    Slot promo (marketing): basta con que haya AL MENOS UN video. `segments`
    ahí es un máximo de espacios, no una cantidad exigida — el equipo pidió
    expresamente que proyecte aunque no estén los 5.
    """
    meta = WORKS.get(slug)
    if meta is None:
        return False
    if meta.get("promo"):
        return any(segment_exists(slug, i) for i in range(1, meta["segments"] + 1))
    return all(segment_exists(slug, i) for i in range(1, meta["segments"] + 1))


def playlist(slug: str) -> list[dict]:
    """Los archivos presentes de un slot, EN ORDEN y saltándose los huecos.

    Es lo que se reproduce en el modo promo: si están cargados los espacios
    1, 2 y 5, devuelve esos tres y se reproducen seguidos.

    Cada entrada: {n, url, kind, name}.
    """
    meta = WORKS.get(slug)
    if meta is None:
        return []
    items: list[dict] = []
    for i in range(1, meta["segments"] + 1):
        p = segment_file(slug, i)
        if p is None:
            continue
        items.append(
            {
                "n": i,
                "url": f"/videos/{slug}/{p.name}",
                "kind": "video" if segment_is_video(p) else "image",
                "name": p.name,
            }
        )
    return items


def available_works() -> list[dict]:
    """Reporte para el panel / API.

    Cada entrada: {slug, title, author, synopsis, segments,
                   present_segments, complete}.
    """
    out: list[dict] = []
    for slug, meta in WORKS.items():
        total = meta["segments"]
        seg_files = []
        for i in range(1, total + 1):
            p = segment_file(slug, i)
            seg_files.append(
                {
                    "n": i,
                    "present": p is not None,
                    "url": (f"/videos/{slug}/{p.name}" if p else None),
                    "kind": ("video" if (p and segment_is_video(p)) else
                             ("image" if p else None)),
                    # Si al subirlo se recorta ("últimos 10 s"), para avisarlo
                    # en /library antes de que lo suban.
                    "trim": trim_label(slug, i),
                }
            )
        present = sum(1 for s in seg_files if s["present"])
        out.append(
            {
                "slug": slug,
                **meta,
                "music": bool(meta.get("music")),
                "music_present": background_audio_exists(slug),
                "promo": bool(meta.get("promo")),
                "present_segments": present,
                # En un slot promo "listo" = tiene al menos un video; en una
                # obra normal = están todos.
                "complete": work_is_complete(slug),
                "segment_files": seg_files,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Sección dinámica del system prompt
# ---------------------------------------------------------------------------


def system_prompt_section() -> str:
    """Texto que se inyecta al system prompt de Claude.

    Incluye:
      1. TODOS los temas/obras que MECH puede exponer (con sinopsis), para que
         narre con contexto incluso los que no tienen video.
      2. Cuáles tienen video pre-renderizado (para usar video_slug/segment).
      3. Cuáles tienen música de fondo (para usar el campo background_music).
    """
    # Los slots promo (marketing) NO se le ofrecen a Claude: se disparan con
    # una orden directa y se reproducen con su propio audio, sin narración.
    # Si aparecieran aquí, el modelo intentaría contarlos como una obra.
    works = [w for w in available_works() if not w.get("promo")]
    complete = [w for w in works if w["complete"]]
    music_works = [w for w in works if w.get("music") and w.get("music_present")]

    lines = [
        "## Temas culturales que MECH puede exponer",
        "",
        "Estos son los temas/obras del stand. Usá su sinopsis para narrar con "
        "precisión (sobre todo los artistas costarricenses). Modo `immersive`.",
        "",
        "REGLA DE EXACTITUD (importante): NO inventes datos biográficos, "
        "fechas, profesiones ni hechos. Narrá usando la sinopsis, los 'Datos "
        "verificados' que se dan abajo, y solo conocimiento MUY establecido. "
        "Si no estás seguro de una fecha o un dato, NO lo digas: preferí una "
        "narración evocativa y emotiva antes que afirmar algo que podría ser "
        "falso. Nunca contradigas los 'Datos verificados'.",
        "",
        "REGLA DE VISUAL (importante): cuando el usuario pida cualquiera de "
        "estos temas del stand — aunque lo diga como 'háblame de…', 'qué "
        "es…' o 'explícame…' — usá el modo `immersive` y poné SIEMPRE un "
        "visual en cada segmento: `video_slug`+`video_segment` si la obra "
        "tiene video, o `image_prompt` si no. NUNCA narres un tema del stand "
        "sin visual — la proyección es parte del show (hay pantallas y "
        "visores esperando contenido).",
        "",
    ]
    for w in works:
        tag = " — [VIDEO disponible]" if w["complete"] else ""
        music_tag = " — [MÚSICA de fondo]" if (w.get("music") and w.get("music_present")) else ""
        lines.append(
            f"- **{w['title']}** (`{w['slug']}`){tag}{music_tag}: {w['synopsis']}"
        )
        for fact in w.get("facts", []):
            lines.append(f"    - Dato verificado: {fact}")
    lines.append("")

    if complete:
        lines += [
            "### Obras con material visual pre-cargado",
            "",
            "Para estas hay material listo (videos y/o imágenes reales). Usá "
            "EXACTAMENTE el número de segmentos indicado; en cada `Segment` "
            "poné `video_slug` (exacto) y `video_segment` (1, 2, 3...), y NO "
            "pongas `image_prompt`:",
            "",
        ]
        for w in complete:
            lines.append(f"- `{w['slug']}` — {w['segments']} segmentos.")
        lines += [
            "",
            "Para los temas SIN video, dejá `video_slug`/`video_segment` en "
            "null y usá `image_prompt` (en inglés) como siempre.",
        ]
    else:
        lines.append(
            "Ninguna obra tiene video completo aún: para los visuales usá "
            "`image_prompt` (en inglés) y dejá `video_slug` en null."
        )

    if music_works:
        lines += [
            "",
            "### Música de fondo",
            "",
            "Estas exposiciones tienen música ambiental ya subida. Al narrarlas, "
            "poné en el `Plan` el campo `background_music` con el slug, para que "
            "suene de fondo, suave, mientras hablás:",
            "",
        ]
        for w in music_works:
            lines.append(f"- {w['title']} → `background_music: {w['slug']}`")
        lines += [
            "",
            "IMPORTANTE para las exposiciones CON música: hacé una narración "
            "LARGA y pausada, que dure alrededor de DOS MINUTOS en total. "
            "Aprovechá los segmentos para contar bastante (contexto, historia, "
            "anécdotas, emoción) con párrafos de varias frases cada uno. La "
            "música suena en bucle por debajo todo el tiempo y se detiene sola "
            "cuando terminás de hablar.",
        ]

    return "\n".join(lines)
