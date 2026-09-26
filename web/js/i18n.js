/* ═══════════════════════════════════════════════════════════════════════
   MECH — interruptor de idioma ES / EN
   El sitio se escribe en español; aquí vive la traducción al inglés.
   La CLAVE es el texto en español (sin etiquetas, espacios normalizados) y
   el VALOR es el HTML en inglés — así el negrita/cursiva se conserva.
   Si una cadena no está en el diccionario, se queda en español (no rompe).
   ═══════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';

  const DICT = {
    /* ── Navegación, pie y comunes ─────────────────────────────────── */
    'Inicio': 'Home',
    'Empresa': 'Company',
    'Problema': 'Problem',
    'Robot': 'Robot',
    'Evolución': 'Evolution',
    'Aplicaciones': 'Applications',
    'Contacto': 'Contact',
    'La empresa': 'The company',
    'El problema': 'The problem',
    'El robot': 'The robot',
    'La evolución': 'The evolution',
    'Patrocinadores': 'Sponsors',
    'PROYECTO': 'PROJECT',
    'CONTACTO': 'CONTACT',
    'Saltar al contenido': 'Skip to content',
    '← ANTERIOR': '← PREVIOUS',
    'SIGUIENTE →': 'NEXT →',
    'VOLVER AL →': 'BACK TO →',
    'Multisensory Engineering Cyberphysical Humanized. Espacios inmersivos que despiertan el interés en las áreas que sostienen a la sociedad.':
      'Multisensory Engineering Cyberphysical Humanized. Immersive spaces that spark interest in the areas that hold society together.',
    'COLEGIO CIENTÍFICO DE ALAJUELA · COSTA RICA 🇨🇷 · WRO 2026 — ROBOTS AND CULTURE ·':
      'COLEGIO CIENTÍFICO DE ALAJUELA · COSTA RICA 🇨🇷 · WRO 2026 — ROBOTS AND CULTURE ·',
    'COLEGIO CIENTÍFICO DE ALAJUELA · COSTA RICA 🇨🇷 · WRO 2026 ·':
      'COLEGIO CIENTÍFICO DE ALAJUELA · COSTA RICA 🇨🇷 · WRO 2026 ·',

    /* ── Inicio ────────────────────────────────────────────────────── */
    'WRO 2026 · ROBOTS AND CULTURE · COSTA RICA': 'WRO 2026 · ROBOTS AND CULTURE · COSTA RICA',
    'Despertamos el interés en lo que de verdad importa.':
      'We spark interest in <em class="grad">what truly matters.</em>',
    'Construimos espacios inmersivos que combinan inteligencia artificial, proyección y movimiento físico. Nuestros robots convierten cualquier tema —cultura, educación, salud, historia— en una experiencia que se vive, no que se lee.':
      'We build immersive spaces that combine artificial intelligence, projection and physical movement. Our robots turn any subject —culture, education, health, history— into an experience that is <b>lived, not just read</b>.',
    // norm() pega las comillas « » al texto, así que la clave va sin espacios
    '«si es inmersivo, es MECH»': '« if it’s immersive, it’s MECH »',
    'Conocer el robot': 'Meet the robot',
    'Por qué existe': 'Why it exists',
    'CON EL APOYO DE': 'SUPPORTED BY',
    'CAMPEONES NACIONALES · WRO FUTURE INNOVATORS': 'NATIONAL CHAMPIONS · WRO FUTURE INNOVATORS',
    'SALÓN DE TROFEOS': 'TROPHY ROOM',
    'Tres torneos. Tres títulos.': 'Three tournaments.<br>Three titles.',
    'Cada prototipo se ha puesto a prueba frente a jurados y otros equipos. Estos son los títulos que ha ganado el equipo — el más reciente, la final nacional de Costa Rica.':
      'Every prototype has been put to the test in front of judges and other teams. These are the titles the team has won — the latest, the <b>Costa Rica national final</b>.',
    'Ver cada modelo en competencia': 'See each model in competition',
    'FIGURA 45 · PREMIOS GANADOS POR EL EQUIPO MECH': 'FIGURE 45 · AWARDS WON BY THE MECH TEAM',
    'PRIMER LUGAR · NACIONAL': 'FIRST PLACE · NATIONAL',
    'PRIMER LUGAR · REGIONAL': 'FIRST PLACE · REGIONAL',
    'PRIMER LUGAR': 'FIRST PLACE',
    'Campeones nacionales': 'National champions',
    'Campeones regionales': 'Regional champions',
    'Campeones': 'Champions',
    'Final Nacional de la WRO 2026 en Costa Rica, categoría Future Innovators.':
      'Costa Rica’s WRO 2026 National Final, Future Innovators category.',
    'Regional de Guanacaste de la WRO 2026, categoría Future Innovators.':
      'WRO 2026 Guanacaste Regional, Future Innovators category.',
    'Torneo STEAM Luvá — Electrotec.': 'STEAM Luvá Tournament — Electrotec.',
    'CON MECH‑3': 'WITH MECH‑3',
    'CON MECH‑2': 'WITH MECH‑2',
    'CON TITOBOT': 'WITH TITOBOT',
    'EL PROBLEMA, EN CIFRAS': 'THE PROBLEM, IN NUMBERS',
    'Cuando falta contexto, el interés se apaga.': 'When context is missing,<br>interest fades.',
    'No es una intuición: es lo que dicen los datos sobre educación, cultura y atención. Y también lo que dicen sobre la solución.':
      'This is not a hunch: it is what the data says about education, culture and attention. And also what it says about the solution.',
    'de retención de interés ante un robot humanoide': 'more audience interest retention with a humanoid robot',
    'de alumnos de colegios públicos de CR en matemáticas insuficientes': 'of Costa Rican public school students at insufficient maths levels',
    'de las escuelas públicas de Costa Rica son unidocentes': 'of Costa Rica’s public schools have a single teacher',
    'menos participación cultural de los jóvenes frente a los adultos mayores': 'lower cultural participation among youth than older adults',
    'RECORRIDO': 'THE TOUR',
    'Conoce el proyecto.': 'Explore the project.',
    'Cada sección responde una pregunta distinta.': 'Each section answers a different question.',
    'Quiénes somos, qué significa M.E.C.H y el equipo detrás del proyecto.':
      'Who we are, what M.E.C.H stands for and the team behind the project.',
    'La indiferencia, la crisis educativa costarricense y la ciencia de la atención.':
      'Indifference, Costa Rica’s education crisis and the science of attention.',
    'Cómo funciona, de qué está hecho y cómo se construyó desde cero.':
      'How it works, what it is made of and how it was built from scratch.',
    'De MECH‑1 a MECH‑5: qué aprendimos y qué mejora cada generación.':
      'From MECH‑1 to MECH‑5: what we learned and what each generation improves.',
    'Museos, aulas, farmacéuticas y empresas — con su modelo de negocio.':
      'Museums, classrooms, pharma and business — with the business model.',
    'Hablemos. Y conoce a quienes hacen posible el proyecto.':
      'Let’s talk. And meet those who make the project possible.',
    '«La única manera de frenar este problema es combatirlo con la misma tecnología.» — Trabajo escrito de MECH, WRO 2026':
      '«The only way to stop this problem is to fight it with the very same technology.» <cite>— MECH written report, WRO 2026</cite>',
    'Ver aplicaciones': 'See applications',
    'Contactar al equipo': 'Contact the team',

    /* ── Empresa ───────────────────────────────────────────────────── */
    'LA EMPRESA': 'THE COMPANY',
    'Multisensory Engineering Cyberphysical Humanized.': 'Multisensory Engineering<br>Cyberphysical Humanized.',
    'Una empresa tecnológica costarricense que construye espacios inmersivos para generar interés en las áreas con mayor beneficio para el desarrollo humano.':
      'A <b>Costa Rican</b> technology company that builds immersive spaces to spark interest in the areas with the greatest benefit for human development.',
    'QUÉ SIGNIFICA M.E.C.H': 'WHAT M.E.C.H STANDS FOR',
    'Cuatro letras, una misión.': 'Four letters, one mission.',
    'Cada letra es un compromiso de diseño que todo lo que construimos debe cumplir.':
      'Each letter is a design commitment that everything we build must meet.',
    'Experiencias con visión, tacto, movimiento y sonido. Un tema se vive con todos los sentidos, no solo se lee.':
      'Experiences with sight, touch, movement and sound. A subject is lived with every sense, not just read.',
    'Ingeniería integrada: sistemas físicos y mecatrónicos diseñados y ensamblados por el propio equipo.':
      'Integrated engineering: physical and mechatronic systems designed and assembled by the team itself.',
    'Firmware propio que une lo digital con lo físico: la IA decide y los motores, luces y proyectores obedecen.':
      'In-house firmware that bridges digital and physical: the AI decides and the motors, lights and projectors obey.',
    'Diseñado para la experiencia humana: reacciona a las personas, escucha y responde en español.':
      'Designed for the human experience: it reacts to people, listens and answers in Spanish.',
    'PROPUESTA DE VALOR': 'VALUE PROPOSITION',
    'Qué nos proponemos.': 'What we set out to do.',
    'Construir espacios inmersivos que capten y sostengan la atención.':
      'Build <b>immersive spaces</b> that capture and hold attention.',
    'Involucrar distintas ingenierías en la construcción de esos espacios.':
      'Involve <b>different engineering fields</b> in building those spaces.',
    'Preservar áreas con beneficios para el desarrollo humano.':
      'Preserve <b>areas that benefit human development</b>.',
    'Agrandar el arraigo cultural de las nuevas generaciones.':
      'Deepen the <b>cultural roots</b> of new generations.',
    'ACTIVIDADES CLAVE': 'KEY ACTIVITIES',
    'Cómo lo hacemos.': 'How we do it.',
    'Ingeniería aplicada — mecánica, electrónica y mecatrónica.':
      '<b>Applied engineering</b> — mechanical, electronic and mechatronic.',
    'Programación — firmware, orquestador de IA y panel de control.':
      '<b>Programming</b> — firmware, AI orchestrator and control panel.',
    'Investigación y análisis de mercado.': '<b>Research and market analysis</b>.',
    'Manufactura del producto.': 'Product <b>manufacturing</b>.',
    '«Si es inmersivo, es MECH.» — Eslogan de la empresa':
      '«If it’s immersive, it’s MECH.» <cite>— Company slogan</cite>',
    'EL EQUIPO': 'THE TEAM',
    'Tres estudiantes, un robot.': 'Three students, one robot.',
    'Colegio Científico de Alajuela · Alajuela, Costa Rica': 'Colegio Científico de Alajuela · Alajuela, Costa Rica',
    'MECATRÓNICA': 'MECHATRONICS',
    'MECÁNICA': 'MECHANICS',
    'CIRCUITOS': 'CIRCUITS',
    'DISEÑO · FIRMWARE · ORQUESTACIÓN': 'DESIGN<span>·</span>FIRMWARE<span>·</span>ORCHESTRATION',
    'ESTRUCTURA · PROTOTIPADO · DISEÑO': 'STRUCTURE<span>·</span>PROTOTYPING<span>·</span>DESIGN',
    'ENERGÍA · VISIÓN · SONIDO': 'POWER<span>·</span>VISION<span>·</span>SOUND',
    'Responsable del diseño de los sistemas mecatrónicos y de todo el desarrollo neuronal robótico: cada orden y tarea que el prototipo ejecuta nació de sus instrucciones. También produjo los esquemas y diagramas que perfeccionan el proceso de orquestación.':
      'Responsible for the design of the mechatronic systems and the whole <b>robotic neural development</b>: every command and task the prototype performs came from his instructions. He also produced the schematics and diagrams that refine the orchestration process.',
    'Especialista de la parte mecánica. Supervisó cada etapa de la producción y materialización del robot, asegurando que cada componente fuera amigable con el diseño, y fue clave para iterar prototipos hacia un ecosistema inmersivo funcional y estético.':
      'Specialist in the mechanical side. He supervised every stage of the robot’s <b>production and materialisation</b>, making sure each component was friendly to the design, and was key to iterating prototypes into a functional, aesthetic immersive ecosystem.',
    'El puente entre la estructura y el cerebro del robot. Desarrolló los sistemas de movimiento, energía, comunicación, sonido y visión, elementos clave para el correcto funcionamiento y la sincronización del prototipo.':
      'The <b>bridge between the structure and the brain</b> of the robot. He developed the movement, power, communication, sound and vision systems — key elements for the prototype to work and stay in sync.',
    'MECH · ALAJUELA, COSTA RICA': 'MECH · ALAJUELA, COSTA RICA',
    'FIGURA 44 · MIEMBROS DE MECH': 'FIGURE 44 · MEMBERS OF MECH',

    /* ── Problema ──────────────────────────────────────────────────── */
    'EL PROBLEMA': 'THE PROBLEM',
    'La indiferencia hacia lo que no se comprende.': 'Indifference towards<br>what we do not understand.',
    'Cuando falta contexto, el interés desaparece — y con él se debilitan la educación, la cultura, la salud y la historia. Esta es la evidencia.':
      'When context is missing, interest disappears — and with it education, culture, health and history grow weaker. Here is the evidence.',
    'EL MOTIVO': 'THE REASON',
    'Existen datos que la gente necesita para entender un tema.': 'There is information people need<br>in order to understand a subject.',
    'En muchas ocasiones áreas como la salud, la cultura, la educación, la política o la religión se ven perjudicadas por la falta de contexto en el que se desarrollan algunas situaciones. Sin ese contexto el interés de la población disminuye, y esas áreas se debilitan.':
      'Areas such as <b>health, culture, education, politics or religion</b> are often harmed by the lack of context in which some situations unfold. Without that context public interest declines, and those areas grow weaker.',
    'Por eso MECH considera prioridad frenar las brechas de conocimiento que causan la indiferencia que hoy acecha a la sociedad. Y como las redes sociales han acelerado esa indiferencia en los jóvenes, la única manera de frenarla es combatirla con la misma tecnología.':
      'That is why MECH treats <b>closing the knowledge gaps</b> that cause today’s indifference as a priority. And since social media has accelerated that indifference among young people, the only way to stop it is to <b>fight it with the very same technology</b>.',
    'CULTURA': 'CULTURE',
    'La herencia cultural se volvió un concepto abstracto.': 'Cultural heritage has become<br>an abstract concept.',
    'Las nuevas generaciones sí atribuyen valor a los lugares y a la historia, pero lo hacen mediante espacios comunitarios alternativos que las instituciones tradicionales no consideran provechosos para la conservación de la riqueza cultural.':
      'New generations do value places and history, but they do so through <b>alternative community spaces</b> that traditional institutions do not consider useful for preserving cultural wealth.',
    'El contraste es medible: según el Departamento de Cultura del Reino Unido, solo el 60% de los jóvenes de 16 a 19 años interactúa de forma física con el patrimonio cultural tradicional, frente al 73% de los adultos mayores. Y el dato viene de Europa, donde la inversión en patrimonio es mayor que en el resto de continentes.':
      'The contrast is measurable: according to the UK Department for Culture, only <b>60% of young people aged 16 to 19</b> engage physically with traditional cultural heritage, compared with <b>73% of older adults</b>. And that figure comes from Europe, where heritage investment is higher than on any other continent.',
    'de brecha de participación cultural entre jóvenes y adultos mayores': 'cultural participation gap between young people and older adults',
    'participación física en patrimonio cultural: jóvenes frente a adultos mayores': 'physical engagement with cultural heritage: youth vs. older adults',
    'EDUCACIÓN · COSTA RICA': 'EDUCATION · COSTA RICA',
    'Una crisis que ya no es un riesgo: es una realidad cotidiana.': 'A crisis that is no longer a risk:<br>it is an everyday reality.',
    'El Décimo Informe Estado de la Educación 2025, del Programa Estado de la Nación (CONARE), advierte de la profunda crisis educativa costarricense de las últimas cuatro décadas.':
      'The Tenth State of Education Report 2025, by the State of the Nation Programme (CONARE), warns of the deep Costa Rican education crisis of the past four decades.',
    'del PIB destinado a educación entre 1980 y 2025': 'of GDP spent on education between 1980 and 2025',
    'de alumnos de colegios públicos en niveles insuficientes de matemáticas': 'of public school students at insufficient maths levels',
    'peor desempeño histórico de Costa Rica en las pruebas PISA': 'Costa Rica’s worst ever performance in the PISA tests',
    'comprensión lectora: del nivel esperado en 1.º grado a apenas una cuarta parte en secundaria':
      'reading comprehension: from the expected level in 1st grade to barely a quarter in secondary school',
    'La tecnología ganó la batalla por la atención': 'Technology won the battle for attention',
    'Un estudio de la UNESCO (2023) revela que la tecnología ha superado la atracción que generan los centros educativos, hasta volverse un medio de distracción para el aprendizaje. Una interrupción puede hacer que el alumnado tarde unos 20 minutos en recuperar completamente el enfoque en la clase.':
      'A <b>UNESCO (2023)</b> study reveals that technology has surpassed the pull of schools, to the point of becoming a distraction from learning. A single interruption can make students take <b>around 20 minutes</b> to fully regain focus in class.',
    'El problema no es la disciplina, sino el conflicto entre dos estímulos: el pasivo del aprendizaje tradicional y el instantáneo de los medios digitales.':
      'The problem is not discipline, but the clash between two stimuli: the <b>passive</b> one of traditional learning and the <b>instant</b> one of digital media.',
    '«La revolución digital debe dirigirse a mejorar las experiencias de aprendizaje y el bienestar de estudiantes y profesores.» — Audrey Azoulay, directora general de la UNESCO (2023)':
      '«The digital revolution must be aimed at improving learning experiences and the wellbeing of students and teachers.» <cite>— Audrey Azoulay, Director-General of UNESCO (2023)</cite>',
    'ESCUELAS UNIDOCENTES': 'SINGLE-TEACHER SCHOOLS',
    'Un solo docente para toda una escuela.': 'One teacher<br>for an entire school.',
    'La enseñanza unidocente exige que una sola persona asuma simultáneamente responsabilidades académicas y administrativas que normalmente estarían repartidas entre varios profesionales. En Costa Rica no es un caso aislado.':
      'Single-teacher schooling requires one person to take on academic and administrative duties at once that would normally be shared among several professionals. In Costa Rica this is not an isolated case.',
    'de los centros educativos públicos de Costa Rica son unidocentes': 'of Costa Rica’s public schools have a single teacher',
    'de esas escuelas tiene menos de 10 estudiantes': 'of those schools have fewer than 10 students',
    'cobertura de inglés: escuelas del país frente a escuelas unidocentes': 'English coverage: schools nationwide vs. single-teacher schools',
    'egresados de estas escuelas abandona secundaria por haber perdido el interés': 'graduates of these schools drop out of secondary school after losing interest',
    'UN CASO REAL · FLOR DE ISLITA, PUNTARENAS': 'A REAL CASE · FLOR DE ISLITA, PUNTARENAS',
    'Una escuela dentro de un manglar de difícil acceso atiende a un grupo reducido de estudiantes de primero a sexto grado bajo la responsabilidad de un único docente, Óscar Castro, que imparte lecciones a niños de edades y niveles completamente distintos en la misma aula. Vive sin electricidad ni agua potable y ha debido incluso proteger a sus alumnos durante un asalto armado en la zona.':
      'A school inside a hard-to-reach mangrove serves a small group of students from first to sixth grade under the responsibility of <b>a single teacher, Óscar Castro</b>, who teaches children of completely different ages and levels in the same classroom. He lives without electricity or drinking water and has even had to protect his students during an armed robbery in the area.',
    'Entre ellos está Jessica, de 12 años, que cada mañana camina hasta la escuela después de realizar tareas domésticas en condiciones de precariedad económica.':
      'Among them is <b>Jessica</b>, aged 12, who walks to school every morning after doing household chores in conditions of economic hardship.',
    'REPORTAJE DE INVESTIGACIÓN · QUESADA, LA NACIÓN (2017)': 'INVESTIGATIVE REPORT · QUESADA, LA NACIÓN (2017)',
    'El desinterés académico no solo nace de la competencia entre tecnología y educación: se agrava donde el estudiante ni siquiera cuenta con los recursos mínimos para sostener su motivación. Un docente que es a la vez maestro, director, gestor administrativo y figura de protección tiene muy poco margen para diversificar sus estrategias didácticas.':
      'Academic disinterest does not only come from the competition between technology and education: <b>it worsens where the student does not even have the minimum resources</b> to sustain their motivation. A teacher who is at once instructor, principal, administrator and protector has very little room to diversify their teaching strategies.',
    'LA CIENCIA DE LA ATENCIÓN': 'THE SCIENCE OF ATTENTION',
    'Por qué un robot sí consigue que lo miren.': 'Why a robot does<br>get people to look.',
    'La solución no es una intuición estética: hay evidencia de que la presencia física y la novedad capturan la atención de forma involuntaria.':
      'The solution is not an aesthetic hunch: there is evidence that physical presence and novelty capture attention involuntarily.',
    'Los robots humanoides provocan «atracción por novedad y presencia física», aumentando la retención de interés de una audiencia y dando acceso a información que las personas no buscarían proactivamente.':
      'Humanoid robots trigger «attraction through novelty and physical presence», increasing an audience’s interest retention and giving access to information people would not seek out proactively.',
    'El cerebro tiene un circuito de detección de novedad regulado por neuronas dopaminérgicas: ante estímulos nuevos, dinámicos o físicamente presentes interrumpe lo que está haciendo para enfocarse en ellos.':
      'The brain has a novelty-detection circuit regulated by dopaminergic neurons: faced with new, dynamic or physically present stimuli, it interrupts whatever it is doing to focus on them.',
    'Combinar tecnología con las industrias creativas locales incrementa drásticamente el interés y la retención del conocimiento tradicional en las nuevas generaciones.':
      'Combining technology with local creative industries dramatically increases interest in and retention of traditional knowledge among new generations.',
    'Las nuevas generaciones perciben la herencia cultural como un concepto abstracto y la valoran por vías alternativas que las instituciones tradicionales no aprovechan.':
      'New generations perceive cultural heritage as an abstract concept and value it through alternative channels that traditional institutions fail to use.',
    'Gran parte de los jóvenes relaciona la ingeniería con industrias frías y trabajo manual, una percepción falsa que condiciona sus decisiones de carrera.':
      'Many young people associate engineering with cold industries and manual labour — a false perception that shapes their career decisions.',
    'Un expositor humanoide que proyecta, explica e interactúa: unifica en un solo lugar funciones que hoy están dispersas, igual que el primer iPhone unificó las herramientas del entretenimiento.':
      'A humanoid presenter that projects, explains and interacts: it unifies in one place functions that today are scattered, just as the first iPhone unified the tools of entertainment.',
    'LA RESPUESTA DEL PROYECTO': 'THE PROJECT’S ANSWER',
    'VER REFERENCIAS BIBLIOGRÁFICAS +': 'VIEW BIBLIOGRAPHIC REFERENCES +',

    /* ── Robot ─────────────────────────────────────────────────────── */
    'EL ROBOT': 'THE ROBOT',
    'Un expositor humanoide construido desde cero.': 'A humanoid presenter<br>built from scratch.',
    'Proyecta, escucha, piensa, narra y se mueve. Cuerpo cilíndrico de 52 × 66 cm, cabeza proyectora y una franja de píxeles como firma visual.':
      'It projects, listens, thinks, narrates and moves. A <b>52 × 66 cm</b> cylindrical body, a projector head and a pixel stripe as its visual signature.',
    'EN NÚMEROS': 'BY THE NUMBERS',
    'La ficha técnica.': 'The spec sheet.',
    'de autonomía — un día escolar completo': 'of battery life — a full school day',
    'consulta de IA por historia completa': 'AI request per full story',
    'de la voz a texto procesada localmente': 'of speech-to-text processed locally',
    'movimiento con ruedas omnidireccionales': 'movement with omnidirectional wheels',
    'CÓMO FUNCIONA': 'HOW IT WORKS',
    'De tu voz a un mundo proyectado en segundos.': 'From your voice to a projected<br>world in seconds.',
    'Todo el flujo lo orquesta una Raspberry Pi 5 dentro del robot. La IA recibe una sola consulta y devuelve el guion completo de la exposición: rápido, económico y predecible.':
      'The whole flow is orchestrated by a Raspberry Pi 5 inside the robot. The AI receives <b>a single request</b> and returns the full script of the presentation: fast, cheap and predictable.',
    'Escucha': 'Listens',
    'El micrófono capta tu voz y se transcribe 100% local, sin depender de internet. Un sistema detecta cuándo baja la longitud de onda para cerrar la recepción — así funciona incluso con ruido.':
      'The microphone picks up your voice and transcribes it <b>100% locally</b>, with no internet needed. A system detects when the wavelength drops to close the recording — so it works <b>even with background noise</b>.',
    'Piensa': 'Thinks',
    'El orquestador de IA recibe la petición y devuelve un plan estructurado: narración por escenas, visuales y gestos.':
      'The AI orchestrator receives the request and returns a <b>structured plan</b>: narration by scenes, visuals and gestures.',
    'Narra y proyecta': 'Narrates and projects',
    'La voz se sintetiza en español y el proyector despliega el espacio inmersivo: videos por escena o imágenes generadas al vuelo.':
      'The voice is synthesised in Spanish and the projector unfolds the <b>immersive space</b>: videos per scene or images generated on the fly.',
    'Se mueve': 'Moves',
    'Un Arduino ejecuta gestos con los brazos y desplazamientos con las ruedas, dando el aspecto humano que capta la atención.':
      'An <b>Arduino</b> performs arm gestures and wheel movements, giving it the human quality that captures attention.',
    'HARDWARE': 'HARDWARE',
    'Tres capas, un solo organismo.': 'Three layers,<br>one single organism.',
    'FIGURA 1 · DIAGRAMA DE ARQUITECTURA': 'FIGURE 1 · ARCHITECTURE DIAGRAM',
    'CAPA SUPERIOR': 'UPPER LAYER',
    'CAPA CENTRAL': 'CENTRAL LAYER',
    'CAPA MECÁNICA': 'MECHANICAL LAYER',
    'Proyector — el corazón del espacio inmersivo': '<b>Projector</b> — the heart of the immersive space',
    'Webcam Logitech — comprensión del entorno y detección de usuarios': '<b>Logitech webcam</b> — environment understanding and user detection',
    'Raspberry Pi 5 (8 GB) — el cerebro del robot': '<b>Raspberry Pi 5 (8 GB)</b> — the robot’s brain',
    'Micrófono — interpretación de lenguaje a texto': '<b>Microphone</b> — speech-to-text interpretation',
    'Parlante JBL Charge — la voz del robot': '<b>JBL Charge speaker</b> — the robot’s voice',
    'Servomotores — los brazos y sus gestos': '<b>Servo motors</b> — the arms and their gestures',
    'Arduino — orquestación del movimiento, en comunicación con la Pi': '<b>Arduino</b> — movement orchestration, talking to the Pi',
    '2× driver L298N + motores DC — movilidad terrestre': '<b>2× L298N drivers + DC motors</b> — ground mobility',
    'Ruedas multidireccionales — desplazamiento en cualquier dirección': '<b>Multidirectional wheels</b> — movement in any direction',
    'Batería 12 V — regulada a 9 V para los motores': '<b>12 V battery</b> — regulated to 9 V for the motors',
    'DIAGRAMAS DEL SISTEMA': 'SYSTEM DIAGRAMS',
    'Cómo se planificó.': 'How it was planned.',
    'El proyecto arrancó con diagramas que definieron las funciones e ideas principales del robot antes de construir nada.':
      'The project started with diagrams that defined the robot’s main functions and ideas before anything was built.',
    'DIAGRAMA · FLUJO DE HARDWARE': 'DIAGRAM · HARDWARE FLOW',
    'DIAGRAMA · FLUJO DE SOFTWARE': 'DIAGRAM · SOFTWARE FLOW',
    'FIGURA 2 · DIAGRAMA DE CASO DE USO': 'FIGURE 2 · USE CASE DIAGRAM',
    'CONSTRUCCIÓN': 'CONSTRUCTION',
    'De qué está hecho.': 'What it is made of.',
    'Estructura metálica de aluminio, ensamblada con soportes y tornillos.': 'An <b>aluminium</b> metal frame, assembled with brackets and screws.',
    '4 ruedas reaprovechadas de una silla, para movilidad y estabilidad.': '<b>4 wheels</b> repurposed from a chair, for mobility and stability.',
    'Cuerpo de tubo PVC de 52 cm de diámetro y 66 cm de altura.': 'A body of <b>PVC pipe, 52 cm in diameter and 66 cm tall</b>.',
    'Forrado en coroplast: flexible, muy resistente, 100% reciclable y no tóxico — y mucho más ligero que usar solo PVC.':
      'Wrapped in <b>coroplast</b>: flexible, highly resistant, 100% recyclable and non-toxic — and far lighter than PVC alone.',
    'Cabeza de cartón y coroplast con rejilla de ventilación, para que el calor no degrade el material.':
      'A cardboard and coroplast head with a <b>ventilation grille</b>, so heat does not degrade the material.',
    'Estructura interna de madera para sostener los componentes.': 'An internal wooden structure to hold the components.',
    'MECANISMO': 'MECHANISM',
    'Cómo se mueve.': 'How it moves.',
    'Los motores de brazos y ruedas se conectan a la Raspberry Pi mediante una tarjeta Arduino.':
      'The arm and wheel motors connect to the <b>Raspberry Pi through an Arduino board</b>.',
    'Los motores de dirección continua se encargan de la movilidad terrestre.': 'The <b>continuous rotation motors</b> handle ground mobility.',
    '2 drivers L298N coordinan los motores con el Arduino desde una protoboard.': '<b>2 L298N drivers</b> coordinate the motors with the Arduino from a breadboard.',
    'Cada motor recibe corriente directamente de la batería, bajando de 12 V a 9 V con un regulador.':
      'Each motor draws current straight from the battery, <b>stepping down from 12 V to 9 V</b> with a regulator.',
    'Los servomotores de los brazos no necesitan driver: no son de dirección continua, así que van en un circuito sencillo alimentado por la batería.':
      'The <b>arm servo motors need no driver</b>: they are not continuous rotation, so they sit on a simple circuit powered by the battery.',
    'EL CÓDIGO': 'THE CODE',
    'Cuatro piezas de software.': 'Four pieces of software.',
    'Todo el proyecto es de código abierto y está publicado en GitHub.': 'The whole project is open source and published on GitHub.',
    'Un archivo en lenguaje C con los modos de movimiento: automático (solo brazos), escucha (quieto) y habla (gestos). Orquesta cómo recibe información de la Raspberry Pi.':
      'A file in <b>C</b> with the movement modes: automatic (arms only), listening (still) and speaking (gestures). It orchestrates how data arrives from the Raspberry Pi.',
    'El orquestador en Python: recepción de voz, conversión a texto y de vuelta a voz, proyección, videos y comunicación con el Arduino. Se eligió Python por su facilidad para orquestar IA.':
      'The <b>Python orchestrator</b>: voice capture, speech to text and back to speech, projection, videos and communication with the Arduino. Python was chosen for how easily it orchestrates AI.',
    'El portal de control técnico en HTML, CSS y JavaScript: paro de emergencia, estado del firmware, sensores, proyector y cámaras. Funciona como respaldo ante problemas técnicos.':
      'The <b>technical control portal</b> in HTML, CSS and JavaScript: emergency stop, firmware status, sensors, projector and cameras. It acts as a backup when technical problems arise.',
    'Guías': 'Guides',
    'Documentación de ensamblaje y uso: cómo armar el robot, los pines exactos del Arduino, cómo iniciar el servidor en la Pi y los requerimientos de hardware y energía.':
      '<b>Assembly and usage</b> documentation: how to build the robot, the exact Arduino pins, how to start the server on the Pi and the hardware and power requirements.',
    'RETOS AFRONTADOS': 'CHALLENGES FACED',
    'Lo que costó llegar aquí.': 'What it took to get here.',
    'Materiales limitados': 'Limited materials',
    'Al inicio no se tenían los componentes necesarios, así que hubo que optar por piezas disponibles y conseguir los elementos estrictamente necesarios.':
      'At the start we did not have the components we needed, so we had to settle for available parts and source only what was strictly necessary.',
    'El tiempo': 'Time',
    'La exigencia académica del colegio científico obligó a priorizar evaluaciones. El plazo para la magnitud del trabajo fue limitado y hubo que aprovecharlo al máximo.':
      'The academic demands of the science high school forced us to prioritise exams. The deadline was tight for the scale of the work and had to be used to the fullest.',
    'Unir dos sistemas': 'Bridging two systems',
    'El equipo no había trabajado antes con Arduino y Raspberry Pi: hubo que aprender y formular métodos para unificar su funcionamiento.':
      'The team had never worked with Arduino and Raspberry Pi before: we had to learn and devise ways to unify how they work together.',
    'La energía del proyector': 'The projector’s power draw',
    'El primer proyector consumía 25 V y habría drenado la batería de 12 V en poco tiempo. Hubo que buscar uno cuyo bulbo no superara ese umbral.':
      'The first projector drew 25 V and would have drained the 12 V battery in no time. We had to find one whose bulb stayed under that threshold.',
    'BITÁCORA DE CONSTRUCCIÓN': 'BUILD LOG',
    'Del esqueleto de aluminio al robot con identidad.': 'From an aluminium skeleton<br>to a robot with identity.',
    'Desliza para ver la evolución →': 'Scroll to see how it evolved →',
    'FIGURA 3 Modelado 3D en Fusion': '<span class="mono">FIGURE 3</span> 3D model in Fusion',
    'FIGURA 4 Primera estructura': '<span class="mono">FIGURE 4</span> First structure',
    'FIGURA 5 Primer sistema de movilidad': '<span class="mono">FIGURE 5</span> First mobility system',
    'FIGURA 6 Ensamblaje de PVC': '<span class="mono">FIGURE 6</span> PVC assembly',
    'FIGURA 7 Estructura con movimiento': '<span class="mono">FIGURE 7</span> Structure with movement',
    'FIGURA 8 Recubrimiento en coroplast': '<span class="mono">FIGURE 8</span> Coroplast covering',
    'FIGURA 9 Estructura interna reforzada': '<span class="mono">FIGURE 9</span> Reinforced inner structure',
    'FIGURA 10 Montaje de la cabeza': '<span class="mono">FIGURE 10</span> Head assembly',
    'FIGURA 11 Sistema de ventilación': '<span class="mono">FIGURE 11</span> Ventilation system',
    'FIGURA 12 Acoplamiento de sistemas': '<span class="mono">FIGURE 12</span> Systems coupling',
    'FIGURA 13 Boceto de decoración': '<span class="mono">FIGURE 13</span> Decoration sketch',
    'FIGURA 14 MECH‑1 completo': '<span class="mono">FIGURE 14</span> MECH‑1 complete',

    /* ── Evolución ─────────────────────────────────────────────────── */
    'LA EVOLUCIÓN': 'THE EVOLUTION',
    'Cinco generaciones. Una misma misión.': 'Five generations.<br>One same mission.',
    'Tres modelos lanzados, MECH‑4 a punto de salir y MECH‑5 en preparación. Cada uno aprende del anterior — y el más reciente es campeón nacional.':
      'Three models launched, <b>MECH‑4</b> about to come out and <b>MECH‑5</b> in the works. Each one learns from the last — and the latest is a national champion.',
    'FIGURA 38 · COMPARACIÓN VISUAL DE LA EVOLUCIÓN': 'FIGURE 38 · VISUAL COMPARISON OF THE EVOLUTION',
    'LANZADO': 'LAUNCHED',
    'LANZADO · ACTUAL': 'LAUNCHED · CURRENT',
    'POR LANZAR': 'COMING SOON',
    'EN PREPARACIÓN': 'IN THE WORKS',
    'BASE DEL PROYECTO': 'PROJECT FOUNDATION',
    '+ AUTONOMÍA': '+ BATTERY LIFE',
    '+ SUBTÍTULOS': '+ SUBTITLES',
    '+ PORTABILIDAD': '+ PORTABILITY',
    '+ IDIOMAS': '+ LANGUAGES',
    '+ TRADUCTOR': '+ TRANSLATOR',
    '🏆 CAMPEÓN REGIONAL': '🏆 REGIONAL CHAMPION',
    '🏆 CAMPEÓN NACIONAL': '🏆 NATIONAL CHAMPION',
    'El modelo de lanzamiento: voz, proyección, movimiento y narración con IA. Estableció toda la base — estructura de aluminio y coroplast, orquestador en Python y firmware en Arduino.':
      'The launch model: voice, projection, movement and AI narration. It set the whole foundation — aluminium and coroplast structure, Python orchestrator and Arduino firmware.',
    'Lentes de realidad virtual, batería propia de 8 horas y un diseño nuevo: mucho más versátil y llamativo.':
      'A virtual reality headset, its own 8-hour battery and a new design: far more versatile and eye-catching.',
    'Más accesible, portátil y resistente: subtítulos, batería de litio recargable y un cuerpo que se desarma para viajar.':
      'More accessible, portable and durable: subtitles, a rechargeable lithium battery and a body that comes apart for travel.',
    'Habla cuatro idiomas, juega trivia con el público y traduce conversaciones en tiempo real.':
      'It speaks four languages, plays trivia with the audience and translates conversations in real time.',
    'Un modelo aún más universal, con más idiomas e indicadores más precisos.':
      'An even more universal model, with more languages and more precise indicators.',
    'EN COMPETENCIA': 'IN COMPETITION',
    'Cada modelo, puesto a prueba.': 'Every model,<br>put to the test.',
    'MECH ha competido en tres eventos oficiales de la WRO, y cada modelo llegó más lejos que el anterior: MECH‑2 ganó la regional de Guanacaste y MECH‑3, la final nacional de Costa Rica en la categoría Future Innovators.':
      'MECH has competed in three official WRO events, and each model went further than the last: MECH‑2 won the Guanacaste regional and MECH‑3 won the <b>Costa Rica national final</b> in the Future Innovators category.',
    'FIGURA 39 MECH‑1 debuta en la regional WRO de Alajuela': '<span class="mono">FIGURE 39</span> MECH‑1 debuts at the Alajuela WRO regional',
    'FIGURA 40 MECH‑2, campeón de la regional WRO de Guanacaste': '<span class="mono">FIGURE 40</span> MECH‑2, champion of the Guanacaste WRO regional',
    'FIGURA 41 MECH‑3, campeón de la final nacional WRO': '<span class="mono">FIGURE 41</span> MECH‑3, champion of the WRO national final',
    'Ver el salón de trofeos': 'See the trophy room',
    'MECH‑2 · QUÉ CAMBIÓ': 'MECH‑2 · WHAT CHANGED',
    'Del prototipo funcional al robot autónomo.': 'From working prototype<br>to autonomous robot.',
    'Lentes de realidad virtual': 'Virtual reality headset',
    'Una experiencia inmersiva a nivel individual, que se adapta mejor a las preferencias de cada usuario.':
      'An immersive experience at an individual level, better adapted to each user’s preferences.',
    'Nuevo diseño': 'New design',
    'Una apariencia más atractiva para el público general, adaptada a los sistemas y sensores mejorados.':
      'A more appealing look for the general public, adapted to the upgraded systems and sensors.',
    'Batería propia': 'Its own battery',
    'Energía suficiente para sostener todos los sistemas con una autonomía de 8 horas: un día completo.':
      'Enough energy to power every system with <b>8 hours</b> of battery life: a full day.',
    'Mejor orquestador': 'Better orchestrator',
    'Mayor compatibilidad con las funciones de audio, para evitar errores en la respuesta o en el guion.':
      'Greater compatibility with the audio functions, to avoid errors in the response or the script.',
    'FIGURA 15 Optimización de movilidad': '<span class="mono">FIGURE 15</span> Mobility optimisation',
    'FIGURA 16 Cableado trenzado': '<span class="mono">FIGURE 16</span> Braided wiring',
    'FIGURA 17 Componentes electrónicos': '<span class="mono">FIGURE 17</span> Electronic components',
    'FIGURA 18 Lentes de realidad virtual': '<span class="mono">FIGURE 18</span> Virtual reality headset',
    'FIGURA 19 Movilidad finalizada': '<span class="mono">FIGURE 19</span> Mobility completed',
    'FIGURA 20 MECH‑2 completo': '<span class="mono">FIGURE 20</span> MECH‑2 complete',
    'MECH‑3 · EL MODELO ACTUAL': 'MECH‑3 · THE CURRENT MODEL',
    'Más accesible. Más resistente. Más portátil.': 'More accessible.<br>More durable. More portable.',
    'Los seis aspectos que lo convierten en una versión más eficiente que sus predecesores — y el modelo con el que el equipo ganó la final nacional.':
      'The six aspects that make it a more efficient version than its predecessors — and the model the team won the national final with.',
    'Modo subtítulos — para personas con dificultad auditiva, o que simplemente lo prefieran.':
      '<b>Subtitle mode</b> — for people with hearing difficulties, or who simply prefer it.',
    'Mayor portabilidad — para que el usuario pueda transportarlo con más libertad.':
      '<b>Greater portability</b> — so the user can move it around more freely.',
    'Diseño más compacto — acomoda mejor los componentes y su apariencia atrae más al público joven.':
      '<b>A more compact design</b> — it arranges the components better and its look appeals more to a younger audience.',
    'Materiales más resistentes — más durabilidad ante golpes o accidentes, sin disparar los costos.':
      '<b>Tougher materials</b> — more durability against knocks or accidents, without driving up costs.',
    'Componentes optimizados — cambios estratégicos en la electrónica para mejorar la autonomía.':
      '<b>Optimised components</b> — strategic changes to the electronics to improve battery life.',
    'Batería de litio — una nueva fuente de energía, ahora recargable.':
      '<b>Lithium battery</b> — a new power source, now rechargeable.',
    'FIGURA 35 Render 3D de MECH‑3': '<span class="mono">FIGURE 35</span> 3D render of MECH‑3',
    'FIGURA 37 MECH‑3 completo': '<span class="mono">FIGURE 37</span> MECH‑3 complete',
    'FIGURA 36': 'FIGURE 36',
    'FIGURA 42': 'FIGURE 42',
    'FIGURA 43': 'FIGURE 43',
    'Se desarma para viajar': 'Comes apart for travel',
    'El tercer modelo se separa en piezas para transportarlo con facilidad de un evento a otro.':
      'The third model breaks down into pieces so it can easily travel from one event to the next.',
    'Cargador propio': 'Its own charger',
    'Un cargador de batería incluido, para que el usuario pueda usarlo con total versatilidad.':
      'A battery charger is included, so the user can use it with full versatility.',
    'Todo en su lugar': 'Everything in its place',
    'Vista superior de los sistemas y circuitos internos, reorganizados de forma más compacta.':
      'Top view of the internal systems and circuits, rearranged more compactly.',
    'BITÁCORA DE MECH‑3': 'MECH‑3 BUILD LOG',
    'Del desarme de MECH‑2 al lanzamiento.': 'From taking MECH‑2 apart<br>to launch day.',
    'FIGURA 26 MECH‑2 desarmado para el rediseño': '<span class="mono">FIGURE 26</span> MECH‑2 taken apart for the redesign',
    'FIGURA 27 Modelado 3D de la nueva versión': '<span class="mono">FIGURE 27</span> 3D model of the new version',
    'FIGURA 28 Nuevo sistema de movimiento': '<span class="mono">FIGURE 28</span> New movement system',
    'FIGURA 29 Circuito reubicado y mejorado': '<span class="mono">FIGURE 29</span> Relocated, improved circuit',
    'FIGURA 30 Rediseño de la cara': '<span class="mono">FIGURE 30</span> Face redesign',
    'FIGURA 31 Nuevo frente': '<span class="mono">FIGURE 31</span> New front',
    'FIGURA 32 Cuerpo ensamblado': '<span class="mono">FIGURE 32</span> Body assembled',
    'FIGURA 33 Construcción de la cabeza': '<span class="mono">FIGURE 33</span> Building the head',
    'FIGURA 34 Cabeza montada en el cuerpo': '<span class="mono">FIGURE 34</span> Head mounted on the body',
    'DISEÑO 3D DE MECH‑3': 'MECH‑3 3D DESIGN',
    'Modelado pieza por pieza en Autodesk Fusion.': 'Modelled piece by piece in Autodesk Fusion.',
    'FIGURA 21 · BASE INFERIOR': 'FIGURE 21 · LOWER BASE',
    'FIGURA 22 · CORAZA': 'FIGURE 22 · SHELL',
    'FIGURA 23 · PARTE SUPERIOR': 'FIGURE 23 · UPPER SECTION',
    'FIGURA 24 · ESTRUCTURA INTERNA': 'FIGURE 24 · INTERNAL STRUCTURE',
    'FIGURA 25 · SOPORTE DE CABEZA': 'FIGURE 25 · HEAD MOUNT',
    'MECH‑4 · A PUNTO DE LANZARSE': 'MECH‑4 · ABOUT TO LAUNCH',
    'Habla cuatro idiomas. Y juega contigo.': 'It speaks four languages.<br>And plays with you.',
    'Las siete mejoras que ya se implementaron en el próximo modelo.': 'The seven improvements already built into the next model.',
    'Cuatro idiomas': 'Four languages',
    'Español, inglés, francés y portugués: el robot ya puede usarse en otras regiones del mundo.':
      'Spanish, English, French and Portuguese: the robot can now be used in other regions of the world.',
    'Modo trivia': 'Trivia mode',
    'Hace preguntas sobre lo que acaba de contar, para un aprendizaje dinámico, interactivo y eficiente.':
      'It asks questions about what it has just presented, for dynamic, interactive and efficient learning.',
    'Traductor en tiempo real': 'Real-time translator',
    'Permite conversar a dos personas que hablan idiomas distintos.':
      'It lets two people who speak different languages hold a conversation.',
    'Comando «Hey MECH»': 'The “Hey MECH” command',
    'Pausa la presentación en cualquier momento para cambiar el tema de conversación.':
      'It pauses the presentation at any moment to change the topic of conversation.',
    'Parlante alámbrico': 'Wired speaker',
    'Para que el robot dependa al 100% de una sola fuente de energía.':
      'So the robot runs 100% on a single power source.',
    'Carga en la mitad del tiempo': 'Charges in half the time',
    'Un cargador nuevo que completa la carga el doble de rápido y mejora la vida de la batería.':
      'A new charger that delivers a full charge twice as fast and improves battery life.',
    'Diseño más moderno': 'A more modern design',
    'Ligeros cambios de diseño que realzan su aspecto moderno.':
      'Slight design changes that enhance its modern look.',
    'LO QUE VIENE': 'WHAT COMES NEXT',
    'El equipo ya prepara un modelo aún más universal: más idiomas a los que puede acceder e indicadores más precisos que lo hagan todavía más versátil. Y seguirá buscando nuevas funciones según lo que reporten los usuarios o lo que el equipo considere importante.':
      'The team is already preparing an even more <b>universal</b> model: more languages it can speak and <b>more precise indicators</b> that make it more versatile still. And it will keep looking for new features based on what users report or what the team considers important.',
    'Proponer una idea': 'Suggest an idea',

    /* ── Aplicaciones ──────────────────────────────────────────────── */
    'APLICACIONES': 'APPLICATIONS',
    'La misma tecnología, infinidad de usos.': 'The same technology,<br><span class="grad">endless uses.</span>',
    'MECH no se limita a un tema. Es una plataforma versátil: allí donde el interés de las personas se apaga, un espacio inmersivo puede volver a encenderlo.':
      'MECH is not limited to one subject. It is a versatile platform: wherever people’s interest fades, an immersive space can light it up again.',
    'DÓNDE ENCAJA': 'WHERE IT FITS',
    'Un robot, muchos mundos.': 'One robot, many worlds.',
    'Educación': 'Education',
    'Apoyo para docentes y escuelas unidocentes: ayuda a distribuir la información y a que el alumnado la comprenda. Su batería de 8 horas cubre un día escolar completo. También sirve en casa para reforzar lo aprendido en clase.':
      'Support for teachers and <b>single-teacher schools</b>: it helps deliver information and helps students understand it. Its <b>8-hour battery</b> covers a full school day. It also works at home to reinforce what was learned in class.',
    'Cultura y museos': 'Culture and museums',
    'Genera mayor atracción hacia el visitante y produce enriquecimiento sociocultural, sobre todo en la población joven — la que está 13% por debajo en participación cultural.':
      'It draws visitors in and produces sociocultural enrichment, especially among young people — the group that is <b>13% behind</b> in cultural participation.',
    'Industria farmacéutica': 'Pharmaceutical industry',
    'Un nicho importante: empresas de mercadeo médico —como nuestro partner 360 Health & Value, que publicita medicamentos hacia hospitales y clínicas— verán sus ventas potenciadas por MECH.':
      'An important niche: <b>medical marketing</b> companies —such as our partner <b>360 Health &amp; Value</b>, which advertises medicines to hospitals and clinics— will see their sales boosted by MECH.',
    'Empresas tecnológicas': 'Technology companies',
    'Presentación de productos al público con el apoyo de un robot que capta la atención de forma involuntaria, en ferias y lanzamientos.':
      'Product presentations to the public backed by a robot that captures attention involuntarily, at fairs and launches.',
    'Dispositivos médicos': 'Medical devices',
    'Las empresas del sector pueden potenciar sus ventas ante inversores mediante espacios inmersivos y el aumento atencional que generan.':
      'Companies in the sector can boost sales to investors through immersive spaces and the rise in attention they generate.',
    'Artistas y espacios': 'Artists and venues',
    'Artistas independientes pueden exponer su obra con el contexto necesario sin estar siempre presentes. También encaja en cafeterías, medios culturales y entretenimiento inmersivo.':
      'Independent artists can exhibit their work with the context it needs <b>without always being present</b>. It also fits coffee shops, cultural media and immersive entertainment.',
    'SEGMENTOS DE CLIENTE': 'CUSTOMER SEGMENTS',
    'A quién nos dirigimos.': 'Who we serve.',
    'Museos': 'Museums',
    'Artistas independientes': 'Independent artists',
    'Medios de comunicación cultural': 'Cultural media outlets',
    'Cafeterías': 'Coffee shops',
    'Empresas tecnológicas (presentaciones de productos)': 'Technology companies (product presentations)',
    'Empresas de dispositivos médicos (presentaciones de productos)': 'Medical device companies (product presentations)',
    'CANALES Y RELACIÓN': 'CHANNELS AND RELATIONSHIPS',
    'Cómo llegamos.': 'How we reach them.',
    'Sitio web y redes sociales': 'Website and social media',
    'Correo electrónico y reuniones presenciales o virtuales': 'Email and in-person or virtual meetings',
    'Demostraciones visuales en ambientes reales, para mostrar la efectividad del robot':
      '<b>Visual demonstrations in real environments</b>, to show how effective the robot is',
    'Manual del usuario y atención al usuario': 'User manual and customer support',
    'MODELO DE NEGOCIO': 'BUSINESS MODEL',
    'Los números del proyecto.': 'The project’s numbers.',
    'Costos reales de los componentes de un robot y las fuentes de ingreso previstas.':
      'Real component costs for one robot and the expected revenue streams.',
    'Estructura de costos': 'Cost structure',
    'COMPONENTES POR UNIDAD (USD)': 'COMPONENTS PER UNIT (USD)',
    'Componente': 'Component',
    'Costo': 'Cost',
    'Raspberry Pi 5 (8 GB) con case y microSD': 'Raspberry Pi 5 (8 GB) with case and microSD',
    'Cargador de batería': 'Battery charger',
    'Batería 12,8 V 12 Ah Litime': 'Litime 12.8 V 12 Ah battery',
    'Arduino UNO (cableado y drivers)': 'Arduino UNO (wiring and drivers)',
    '6 servomotores': '6 servo motors',
    'Proyector HY300': 'HY300 projector',
    'Ruedas': 'Wheels',
    'Subtotal (sin márgenes de ganancia)': 'Subtotal (before profit margins)',
    '$236,00': '$236.00', '$117,24': '$117.24', '$115,00': '$115.00',
    '$80,00': '$80.00', '$70,00': '$70.00', '$52,00': '$52.00',
    '$42,00': '$42.00', '$28,67': '$28.67', '$16,00': '$16.00',
    '$756,91': '$756.91',
    'Fuentes de ingreso': 'Revenue streams',
    'VENTA PRINCIPAL': 'MAIN SALE',
    '/ robot': '/ robot',
    'Un 24,31% de ganancia sobre el costo de los componentes.': 'A <b>24.31%</b> margin over the cost of components.',
    'SERVICIO': 'SERVICE',
    'Diagnóstico previo al mantenimiento. Los costos adicionales de mantenimiento son variables.':
      'Pre-maintenance diagnostics. Additional maintenance costs vary.',
    'RECURSOS CLAVE': 'KEY RESOURCES',
    'Raspberry Pi 5 · Arduino · servomotores · ruedas multidireccionales · JBL Charge · webcam Logitech.':
      'Raspberry Pi 5 · Arduino · servo motors · multidirectional wheels · JBL Charge · Logitech webcam.',
    'VER EL BUSINESS MODEL CANVAS COMPLETO +': 'VIEW THE FULL BUSINESS MODEL CANVAS +',
    'IMPACTO SOCIOECONÓMICO': 'SOCIOECONOMIC IMPACT',
    'Tecnología que suma, no que sustituye.': 'Technology that adds,<br>not replaces.',
    'No reemplaza empleos': 'It replaces no jobs',
    'La función de expositor es necesaria en muchas instituciones y aún no ha sido cubierta. MECH no destituye a nadie de su cargo: complementa la labor humana.':
      'The <b>presenter</b> role is needed in many institutions and has not been filled yet. MECH removes no one from their post: it complements human work.',
    'Empodera a los artistas': 'It empowers artists',
    'Exponer una obra deja de requerir la presencia permanente del autor ni pagar un expositor: es más accesible y más económico.':
      'Exhibiting a work no longer requires the author’s constant presence or paying a presenter: it is more accessible and cheaper.',
    'Refuerza lo público': 'It strengthens public services',
    'En escuelas unidocentes y centros con pocos recursos, el robot da apoyo justo donde la sobrecarga del personal limita la calidad de la enseñanza.':
      'In single-teacher schools and under-resourced centres, the robot gives support exactly where staff overload limits teaching quality.',

    /* ── Contacto ──────────────────────────────────────────────────── */
    'Hablemos.': 'Let’s talk.',
    '¿Te interesa una demostración, una alianza o llevar un espacio inmersivo a tu institución? Escríbenos — respondemos en español.':
      'Interested in a demo, a partnership or bringing an immersive space to your institution? Write to us — we answer in Spanish and English.',
    'Correo electrónico': 'Email',
    '@wr0mech — avances, demostraciones y bitácora del proyecto.': '@wr0mech — updates, demos and the project log.',
    'Todo el código del robot es abierto: firmware, backend y panel de control.':
      'All the robot’s code is open: firmware, backend and control panel.',
    'Dónde estamos': 'Where we are',
    'Colegio Científico de Alajuela — Alajuela, Costa Rica. Equipo: Leonardo Ramírez · Jimmy Jara · Alejandro Ramírez.':
      '<b>Colegio Científico de Alajuela</b> — Alajuela, Costa Rica.<br>Team: Leonardo Ramírez · Jimmy Jara · Alejandro Ramírez.',
    'PATROCINADORES Y ALIADOS': 'SPONSORS AND PARTNERS',
    'Quienes hacen posible el proyecto.': 'The people who make<br>the project possible.',
    'Instituciones y empresas que han apoyado a MECH con recursos, conocimiento o acompañamiento.':
      'Institutions and companies that have supported MECH with resources, knowledge or guidance.',
    '¿Quieres sumarte como patrocinador? Escríbenos a wromech@gmail.com.':
      'Want to join as a sponsor? Write to us at <a href="mailto:wromech@gmail.com" style="color:var(--text)">wromech@gmail.com</a>.',
    'Volver al inicio': 'Back to home',

    /* ── Fuentes de las cifras (los nombres propios se conservan) ──── */
    'ESTADO DE LA EDUCACIÓN, 2025': 'STATE OF EDUCATION REPORT, 2025',
    'DCMS REINO UNIDO, 2023': 'DCMS UNITED KINGDOM, 2023',
    'FUENTES-MORALEDA ET AL., 2021 · UNIV. REY JUAN CARLOS': 'FUENTES-MORALEDA ET AL., 2021 · REY JUAN CARLOS UNIV.',
    'TODOROV, 2026 · INSTITUTO KAROLINSKA DE ESTOCOLMO': 'TODOROV, 2026 · KAROLINSKA INSTITUTE, STOCKHOLM',
    'ZHANG, 2025 · UNIV. TECNOLÓGICA DE EINDHOVEN': 'ZHANG, 2025 · EINDHOVEN UNIVERSITY OF TECHNOLOGY',

    /* ── 404 ───────────────────────────────────────────────────────── */
    'ERROR 404': 'ERROR 404',
    'Esta página no está en el guion.': 'This page<br><span class="grad">is not in the script.</span>',
    'MECH buscó en su biblioteca y no encontró nada aquí. Puede que el enlace haya cambiado de lugar.':
      'MECH searched its library and found nothing here. The link may have moved.',
  };

  /* Títulos del navegador por página */
  const TITLES = {
    'index': 'MECH — If it’s immersive, it’s MECH',
    'empresa': 'The company — MECH',
    'problema': 'The problem — MECH',
    'robot': 'The robot — MECH',
    'evolucion': 'The evolution — MECH',
    'aplicaciones': 'Applications and business model — MECH',
    'contacto': 'Contact and sponsors — MECH',
    '404': 'Page not found — MECH',
  };

  const SEL = 'h1,h2,h3,h4,p,li,cite,figcaption,summary,th,td,blockquote,' +
    '.nav-links a,.footer-col h4,.pager .dir,.pager .ttl,.kicker,.tag,' +
    '.tl-status,.tl-tags span,.work-tags span,.sponsors-label,.stat span,' +
    '.stat b,.btn,.profile-kicker,.profile-role,.card-icon,.chip,.pipe-tag,' +
    '.sponsor-tile span,.versus-tag,.team-role,.skip,caption,.stat-src,' +
    '.award-txt,.trophy-rank,.card-fig';
  // no se traducen (marcas, nombres propios, siglas)
  const SKIP = new Set(['MECH', 'Arduino', 'Backend', 'Frontend', 'Multisensory',
    'Engineering', 'Cyberphysical', 'Humanized', 'M', 'E', 'C', 'H', 'VR',
    'Py', 'JS', 'Doc', 'IG', 'wromech@gmail.com', 'Logitech C920', 'JBL Charge 5',
    'MECH‑1', 'MECH‑2', 'MECH‑3', 'MECH‑4', 'MECH‑5']);

  const norm = (s) => s
    .replace(/ /g, ' ')
    .replace(/\s+/g, ' ')
    // al cambiar las etiquetas por espacio, "<b>se lee</b>." deja " .":
    // se vuelve a pegar la puntuacion para que la clave coincida.
    .replace(/\s+([.,;:!?%)»])/g, '$1')
    .replace(/([(«])\s+/g, '$1')
    .trim();

  // Quita etiquetas (poniendo un ESPACIO, para que un <br> no pegue las
  // palabras) y DECODIFICA las entidades: "&amp;" tiene que volver a ser "&"
  // o la clave nunca coincidiria con el diccionario.
  const _tmp = document.createElement('div');
  function stripTags(html) {
    _tmp.innerHTML = html.replace(/<[^>]*>/g, ' ');
    return _tmp.textContent;
  }

  function apply(lang) {
    const els = document.querySelectorAll(SEL);
    const done = [];
    els.forEach((el) => {
      // no tocar si un ancestro ya se tradujo, ni si contiene otro bloque
      if (done.some((d) => d.contains(el))) return;
      if (el.querySelector('h1,h2,h3,h4,p,li,ul,ol,div,figure,blockquote,table')) return;
      if (el.dataset.i18nEs === undefined) el.dataset.i18nEs = el.innerHTML;
      const key = norm(stripTags(el.dataset.i18nEs));
      if (!key || SKIP.has(key)) return;
      if (lang === 'en') {
        const en = DICT[key];
        if (en !== undefined) { el.innerHTML = en; done.push(el); }
      } else if (el.innerHTML !== el.dataset.i18nEs) {
        el.innerHTML = el.dataset.i18nEs;
        done.push(el);
      }
    });

    document.documentElement.lang = lang;
    const page = (location.pathname.split('/').pop() || 'index').replace('.html', '') || 'index';
    if (lang === 'en' && TITLES[page]) {
      if (!document.body.dataset.titleEs) document.body.dataset.titleEs = document.title;
      document.title = TITLES[page];
    } else if (document.body.dataset.titleEs) {
      document.title = document.body.dataset.titleEs;
    }
    document.querySelectorAll('.lang-btn').forEach((b) => {
      const on = b.dataset.lang === lang;
      b.setAttribute('aria-pressed', String(on));
      b.classList.toggle('on', on);
    });
    try { localStorage.setItem('mech-lang', lang); } catch (e) {}
  }

  /* Interruptor en la barra de navegación */
  function mountToggle() {
    const links = document.getElementById('navLinks');
    if (!links || links.querySelector('.lang-switch')) return;
    const wrap = document.createElement('div');
    wrap.className = 'lang-switch';
    wrap.setAttribute('role', 'group');
    wrap.setAttribute('aria-label', 'Idioma / Language');
    wrap.innerHTML =
      '<button type="button" class="lang-btn" data-lang="es" aria-pressed="true">ES</button>' +
      '<button type="button" class="lang-btn" data-lang="en" aria-pressed="false">EN</button>';
    const cta = links.querySelector('.nav-cta');
    links.insertBefore(wrap, cta || null);
    wrap.addEventListener('click', (e) => {
      const b = e.target.closest('.lang-btn');
      if (b) apply(b.dataset.lang);
    });
  }

  let saved = 'es';
  try { saved = localStorage.getItem('mech-lang') || 'es'; } catch (e) {}
  mountToggle();
  apply(saved);
})();
