---
name: bandeja-direccion
description: Trae a la conversación lo que espera a la Dirección en los proyectos de la instancia (preguntas, PRs listos, lo último de cada corrida), se lo muestra en una página visual con los documentos a la mano y una recomendación, y publica en GitHub sus respuestas, sus pedidos y las integraciones que autorice. Si la Dirección quiere avanzar sin esperar el horario, despierta la corrida del proyecto en el momento y trabaja por relevos. Al cerrar, deja una página con lo que pasó en la jornada. Úsala cuando la Dirección pregunte qué hay pendiente, abra una sesión para operar la fábrica, prefiera decidir desde el chat en vez de GitHub, diga que tiene tiempo para avanzar o pida ver lo que se hizo. También la usa la tarea de la mañana, que publica el resumen diario de un cliente y recibe sus respuestas desde el teléfono.
---

# Bandeja de la Dirección

La Dirección decide en la conversación; la fábrica lo publica en GitHub con su cuenta, que es como el motor reconoce
sus respuestas (`nucleo/motor.md`, `nucleo/autonomia.md`). El script es `.fabrica/scripts/bandeja.py`.

## Reglas

- **Publicas solo lo que la Dirección decidió, con sus palabras.** Nunca agregas decisiones, nunca respondes por ella
  y nunca das por respondida una pregunta que no contestó. Si su respuesta es ambigua, preguntas de nuevo.
- **Aislamiento (`nucleo/aislamiento.md`):** el resumen muestra solo cifras. El detalle se abre de a un cliente, y en
  una misma conversación no abres el de otro: para pasar a otro cliente, la Dirección abre una sesión nueva. Desde la
  bandeja no se trabaja en un proyecto: si una pregunta exige revisar el proyecto, se hace en una sesión de ese
  proyecto.
- **Integrar un PR exige un sí de la Dirección para ese PR**, dado en esta conversación (`nucleo/autonomia.md`, "Quién
  integra cada PR"). El script además se niega si los controles no están en verde o la rama está atrasada.
- **Lo que publiques en un proyecto de un cliente** (respuestas, pedidos) no lleva datos de otro cliente.
- **Nunca pides una decisión sin mostrar antes dónde verla.** Un resumen en el chat no basta: la Dirección decide
  mirando una página con lo que aprueba (cómo se ve, las reglas, lo que la fábrica decidió por ella) y con el enlace a
  cada documento, por si quiere entrar al detalle. Ella elige si lo revisa a fondo o no. Una página por proyecto: nunca
  mezcla clientes.
- **No encadenas aprobaciones rápidas.** Si en una sesión salen varias decisiones seguidas, la Dirección ve el
  resultado de cada una (su página) antes de la siguiente.
- **GitHub es la única memoria** (`nucleo/motor.md`, "Dónde quedamos"). Al empezar, el resumen dice dónde quedamos.
  Al terminar, nada queda solo en este computador ni en esta conversación.

## Pasos

1. **Resumen:** `python .fabrica/scripts/bandeja.py`. Cuéntale a la Dirección, en dos o tres líneas, qué proyectos
   esperan su decisión y cuándo corrió el motor por última vez. Si nada espera, dilo y termina.
2. **Detalle de un cliente:** `python .fabrica/scripts/bandeja.py --cliente <slug>`. Si hay varios con pendientes,
   pregunta por cuál empezar.
3. **Presenta cada decisión en lenguaje simple:**
   - **Pregunta:** qué se decide, las opciones con lo que cuesta cada una y tu recomendación. Las que ya tienen
     respuesta ("respondida") no se vuelven a preguntar: la próxima corrida las aplica.
   - **PR:** qué cambia, para quién, el estado de sus controles y si está listo. Para explicarlo puedes leer su
     descripción y sus archivos por la API REST (`gh api repos/<dueño>/<repositorio>/pulls/<n>` y `.../files`),
     solo de este cliente. `gh pr` no funciona en la nube.
   - **Antes de preguntar, arma la página de la decisión:**
     `python .fabrica/scripts/bandeja.py --pagina <repositorio>#<n> --carpeta <carpeta local del proyecto, si la
     sabes> --salida <archivo .html>`. Trae lo que está en GitHub: qué se pide, lo que el motor decidió por la
     Dirección, cada documento con su enlace y su ruta local, y los controles. Completa a mano las secciones marcadas
     «Por completar» (en simple, cómo se ve con bocetos de las pantallas, qué pasa si dice sí o no) y no la muestres
     mientras quede alguna (`data-completar`). Publícala como página privada si el entorno lo permite (en Claude
     Code, con la herramienta Artifact); si no, ábrela en el navegador. Dale el enlace y espera a que la mire.
   - Una página puede reunir varias decisiones del mismo proyecto que se entienden juntas, por ejemplo un PR y las
     preguntas que lo originaron.
   - Usa AskUserQuestion cuando las opciones sean claras (hasta cuatro decisiones por vez), con la recomendada
     primero y el enlace a la página en la pregunta.
4. **Publica cada respuesta:**
   `python .fabrica/scripts/bandeja.py --responder <repositorio>#<n> --texto "<respuesta de la Dirección>"`.
   El texto empieza por la opción elegida (por ejemplo "H3") y sigue con lo que la Dirección agregó.
5. **Integra los PRs que la Dirección autorizó:** `python .fabrica/scripts/bandeja.py --integrar <repositorio>#<n>`.
   Si el script se niega, explica por qué. Si el sistema bloquea la integración, dilo y no insistas: la Dirección
   puede integrarlo en GitHub.
6. **Relevos, si la Dirección quiere avanzar sin esperar el horario** (`nucleo/motor.md`, "El ritmo"):
   1. Anota la hora UTC y despierta la corrida del proyecto con la herramienta de tareas programadas: busca la tarea
      `fabrica · <repositorio>`, comprueba que su última corrida terminó (tiene hora de término) y ejecútala.
   2. Espera en segundo plano a que termine:
      `python .fabrica/scripts/bandeja.py --esperar <repositorio> --desde <hora UTC del paso anterior>`.
   3. Con su entrada en la bitácora, vuelve al paso 2 de esta skill: presenta lo nuevo y publica lo que se decida.
   4. Si no hay nada que decidir, despierta el relevo siguiente: hasta cinco seguidos, o el tope o la meta que fije
      la Dirección. Para cuando aparezca una decisión, cuando una corrida no tenga nada que hacer o cuando la
      Dirección se vaya.
   5. Si la herramienta de tareas no está disponible, dilo: la Dirección puede ejecutar la tarea en
      claude.ai/code/routines, o la aplica la próxima corrida programada.
7. **Pedidos nuevos:** cuando la Dirección pida trabajo,
   `python .fabrica/scripts/bandeja.py --pedido <repositorio> --titulo "<título>" --texto "<cuerpo>"`, con tres
   secciones: "## Qué necesitas", "## Por qué ahora" y "## Cómo sé que está listo". Va sin etiquetas: la próxima
   corrida lo clasifica.

8. **Cierre de la jornada:** cuando la Dirección termina un rato de trabajo en el que se decidió algo, arma
   `python .fabrica/scripts/bandeja.py --jornada <repositorio> [--fecha <AAAA-MM-DD>] --salida <archivo .html>`,
   completa «Lo más importante» y, si sirven, agrega los bocetos de lo aprobado. Las horas salen en la zona de la
   instancia (`zona_horaria` de `.fabrica/config.json`). Publícala igual que la de una decisión. Antes de cerrar,
   comprueba que nada quede solo en este computador: en la instancia y en cada proyecto que tocaste, `git status`
   limpio y las ramas subidas con su PR.
9. **Resumen diario, en la tarea de la mañana** (`nucleo/motor.md`, "La tarea de la mañana"). La sesión corre en
   la nube, sin la Dirección mirando:
   1. Arma `python .fabrica/scripts/bandeja.py --diario <cliente> --salida <archivo .html>`. Trae lo que avanzó en
      las últimas 24 horas y cada decisión pendiente con lo necesario para decidirla.
   2. Completa las secciones «Por completar» en lenguaje simple: lo más importante y, en cada decisión, qué cambia,
      cómo se ve si cambia algo visible y qué pasa si dice sí o no, con tu recomendación. Para explicarla puedes leer
      sus documentos.
   3. Publícala en la dirección de `resumen_diario.paginas.<cliente>` de `.fabrica/config.json`, para que la
      Dirección la encuentre siempre en el mismo lugar. Si no hay dirección, publica una página nueva y dilo.
   4. Termina con un mensaje corto: cuántas decisiones esperan, la primera que conviene tomar y el enlace.
   5. Si la Dirección responde en esta sesión, sigue los pasos 4 a 6: publica sus respuestas, integra lo que
      apruebe y, si puedes, despierta la corrida del proyecto. Si no puedes despertarla, dile que la aplica la
      próxima corrida programada.

## Lo que devuelves

- el enlace a cada página que armaste;
- una tabla con lo que se publicó (respuestas, integraciones, pedidos) y sus enlaces;
- lo que sigue esperando y por qué;
- cuándo lo aplica el motor: el relevo que despertaste o la próxima corrida programada, y un paso por corrida.
