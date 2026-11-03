# Cambios del núcleo

El núcleo sigue versionado semántico:
- **mayor:** cambia o se elimina un principio, o se rompe la compatibilidad con proyectos existentes;
- **menor:** se agrega un área, un rol, una skill o una regla;
- **parche:** se corrige o se precisa algo ya existente.

## 0.8.0 · 2026-11-03

La Dirección ve lo que aprueba: una página visual por decisión y otra al cerrar la jornada.
- **Regla nueva (`nucleo/autonomia.md`, skill `bandeja-direccion`):** nunca se pide una decisión sin mostrar antes
  dónde verla. Tampoco se encadenan aprobaciones rápidas sin que la Dirección vea el resultado de cada una.
- **`bandeja.py --pagina <repositorio>#<n> [--carpeta <ruta local>] [--salida <archivo>]`:** arma la página de una
  decisión con lo que hay en GitHub:
  - qué se pide y el estado del PR o la pregunta;
  - lo que el motor decidió por la Dirección ("Decisión: …"), sin repetir;
  - cada documento con su enlace a la versión del PR y su ruta local, y destacado si nadie puede leerlo ni revisarlo
    (compilados, binarios, comprimidos);
  - los controles.

  Las secciones en lenguaje simple (en simple, cómo se ve, qué pasa si dice sí o no) quedan marcadas «Por completar»
  para quien la presenta.
- **`bandeja.py --jornada <repositorio> [--fecha <AAAA-MM-DD>] [--salida <archivo>]`:** la página de cierre del día.
  Trae corridas, PRs integrados, preguntas cerradas, las decisiones que tomó la fábrica y lo que sigue, en la zona
  horaria de la instancia.
- **`nucleo/plantillas/pagina-direccion.html`:** la plantilla de ambas páginas. Funciona en claro y en oscuro, y en
  el teléfono. Una instancia puede usar la suya en `instancia/plantillas/pagina-direccion.html`.
- **Seguridad:** todo texto que viene de GitHub se escapa, así que un issue no puede meter código en la página.
- **Corrección:** un control que volvió a correr (por ejemplo, al ponerle una etiqueta al PR) cuenta por su última
  corrida, igual que en GitHub. Antes, una falla vieja dejaba el PR "en rojo" en la bandeja y `--integrar` se negaba.
- **`probar_bandeja.py`:** 40 casos, 15 nuevos. Se comprobó además que detectan 10 fallas provocadas: sin escape,
  sin filtro del día, sin deduplicar, la hora en UTC, la plantilla propia ignorada, la ruta local omitida, el texto
  "Más en el PR" sin quitar, sin la última corrida de cada control, sin destacar lo ilegible y un PR integrado
  presentado como abierto.

## 0.7.0 · 2026-11-03

El ritmo del motor: avanzar más rápido cuando la Dirección tiene tiempo, sin perder el horario:
- **`nucleo/motor.md`, "El ritmo":** tres ritmos con la misma corrida y las mismas reglas.
  - **Por horario:** la tarea programada, como hasta ahora; es la base.
  - **Por relevos:** cada decisión tomada en la bandeja despierta en el momento la corrida del proyecto, y al
    terminar sale el relevo siguiente. Un relevo a la vez por proyecto; sin decisiones pendientes siguen solos hasta
    cinco seguidos o hasta la meta que fije la Dirección.
  - **En sesión:** el coordinador trabaja en vivo en la carpeta del proyecto, sin que la tarea programada corra en
    medio.
- **`bandeja.py --esperar <repositorio> [--desde <hora UTC>] [--minutos N]`:** espera a que la corrida deje su
  entrada en la bitácora y la muestra. Un corte de red no termina la espera; si se acaba el tiempo, lo dice.
- **La skill `bandeja-direccion`** despierta la corrida, espera y sigue con los relevos.
- **`probar_bandeja.py`:** 25 casos, 4 nuevos para la espera.

## 0.6.0 · 2026-11-03

La bandeja de la Dirección, para decidir desde la conversación sin entrar a GitHub:
- **`bandeja.py`** y la skill de instancia `bandeja-direccion`:
  - **Resumen** de todos los proyectos activos: preguntas sin respuesta, respondidas por aplicar, PRs abiertos, PRs en
    verde y la hora de la última corrida. Solo cifras, igual que el panel (`nucleo/aislamiento.md`).
  - **Detalle de un cliente:** sus preguntas con su texto, sus PRs con el estado de los controles y la última entrada
    de su bitácora. Se abre de a un cliente por conversación.
  - **Publicar** la respuesta de la Dirección en una pregunta o un PR, con una marca que dice que vino de la bandeja.
    Se niega en repositorios que no son proyectos de la instancia, en issues cerrados y con el texto vacío.
  - **Crear un pedido** para el motor, sin etiquetas, para que la próxima corrida lo clasifique.
  - **Integrar un PR** que la Dirección autorizó, solo con los controles en verde y la rama al día con su rama base
    (sea `main` o `master`).
- **`pruebas/probar_bandeja.py`** (21 casos, con un `gh` falso que no toca GitHub), también en la CI. Cada control
  se comprobó rompiéndolo a propósito: las 10 mutaciones hacen fallar la prueba.
- `nucleo/autonomia.md` y `nucleo/aislamiento.md` describen la bandeja.

## 0.5.1 · 2026-11-02

Lo aprendido al adoptar el primer proyecto real:
- **Corrección en `adoptar_proyecto.py`:** en Windows y macOS, git no registra un cambio que es solo de mayúsculas.
  Al reemplazar `pull_request_template.md` por `PULL_REQUEST_TEMPLATE.md`, el índice conservaba el nombre anterior, y
  en Linux (la CI) faltaba la ruta del kit. Ahora la adopción saca el nombre anterior del índice antes del commit.
- **La prueba** revisa además el índice de git, no solo el disco. Sin la corrección, falla con el mismo síntoma que
  apareció en el proyecto real.

## 0.5.0 · 2026-11-02

Adoptar un proyecto que ya existe, y sumar negocios a un cliente:
- **`adoptar_proyecto.py`** y la skill de instancia `adoptar-proyecto`: un repositorio que ya tiene historia,
  documentos o código entra a la fábrica sin perder nada (`nucleo/actualizaciones.md`).
  - Instala el kit completo y crea solo los archivos propios que falten. Nunca pisa el código, el README, `docs/` ni
    la CI propia, y al `.gitignore` solo le agrega líneas.
  - Respalda lo que el kit reemplaza, incluso un archivo que solo difiere en mayúsculas (en Windows y macOS son el
    mismo). Conserva los agentes y skills propios.
  - Verifica y, si falla, deja todo como estaba. Termina con un commit y anota el proyecto en la ficha del cliente.
  - La skill lleva antes las reglas propias a `docs/constitucion.md` y decide con la Dirección qué pasa con cada
    agente y skill propios.
- **`nuevo_cliente.py --agregar`:** suma negocios a un cliente registrado, y crea la base de su rubro si es nuevo.
- **Una sola lógica para crear y adoptar:** los archivos iniciales de un proyecto salen de `_kit.preparar_proyecto`,
  que nunca pisa uno que ya exista.
- **Pruebas:** 24 de actualización y 60 del kit. Las nuevas se comprobaron rompiendo el código a propósito (sin
  respaldo, sin reversión, pisando lo existente), y cada falla introducida hace fallar su caso. Un archivo que falta
  hace fallar el caso en vez de cortar la prueba.

## 0.4.0 · 2026-11-02

La base de conocimiento de cada rubro, y el camino completo de un aprendizaje (`nucleo/aprendizaje.md`):
- **Base del rubro:** lo que la fábrica sabe de un rubro, sin datos de ningún cliente. Incluye el glosario, los
  flujos, las reglas frecuentes, las normas y las preguntas que siempre hay que hacer (`plantillas/rubro.md`).
  - Vive en la instancia, en `rubros/<rubro>/`. El núcleo solo define su forma y nunca la trae ni la toca.
  - `nuevo_cliente.py` la crea desde la plantilla con el primer cliente del rubro. El rubro pasa a ser un
    identificador (por ejemplo, `gas-licuado`).
- **Llega sola a cada proyecto,** en `.fabrica/rubro/`, al crearlo y con cada actualización del kit, aunque el núcleo
  no cambie de versión. El rubro sale de la ficha del cliente, según el negocio del proyecto. Sin base, el proyecto
  recibe un aviso en su lugar.
- **El analista** parte de la base del rubro, y cada "pregunta que siempre hay que hacer" queda respondida o anotada
  como pregunta. Una regla del rubro es una hipótesis para cada cliente, salvo que sea una norma pública.
- **El camino de vuelta:**
  - la skill `cerrar` escribe los aprendizajes en `docs/aprendizajes.md`, con su número y su tipo
    (`plantillas/aprendizajes.md`);
  - la skill de instancia `recoger-aprendizajes` y `recoger_aprendizajes.py` los recogen de todos los proyectos;
  - de cada proyecto se lee solo ese archivo, con avisos de lo que parece un dato del cliente: su nombre, correos,
    teléfonos, montos y enlaces;
  - cada decisión (rubro, método o descartado) queda en `instancia/aprendizajes-recogidos.csv`.
- **`verificar.py`** exige que el núcleo no tenga `rubros/`. `nuevo_proyecto.py` lee los negocios solo de su tabla en
  la ficha.
- **Pruebas:** 24 de actualización y 42 del kit, con resultados conocidos.
  - Un caso nuevo prueba la protección de verdad: un núcleo defectuoso que reclama `clientes/` y `rubros/` no los pisa.
    Antes, "no toca clientes/" pasaba aunque se quitara la protección, porque el núcleo nunca listaba esa carpeta.
  - Las pruebas nuevas se comprobaron rompiendo el código a propósito: cada falla introducida hace fallar su caso.

## 0.3.2 · 2026-11-02

Lo aprendido al responder las primeras preguntas del motor:
- **Las respuestas a las preguntas** de una misma historia, iniciativa o ADR se aplican todas juntas y cuentan como
  un solo paso. Antes, cada respuesta gastaba un paso, y cuatro respuestas tardaban cuatro corridas. Al aplicarlas, la
  corrida actualiza el PR del documento y cierra cada pregunta con un enlace al cambio.
- **Pedidos sin clasificar:** la corrida ya no confunde con pedidos nuevos las preguntas, la bitácora de corridas ni
  los PRs, que tampoco llevan etiqueta `estado:*`.
- **Los supuestos son decisiones:** los que se anotan al especificar van también en "Decisiones que tomé por ti" del
  PR de especificación y de la bitácora. Antes, un PR con varios supuestos podía decir "ninguna" (`autonomia.md` y la
  skill `especificar`).

## 0.3.1 · 2026-11-02

Lo aprendido en la primera corrida real del motor:
- **La corrida** ya no intenta fijar la bitácora como issue destacado, porque la API REST no lo permite. Ahora la
  busca por su título y, si no existe, la crea.
- **`nucleo/motor.md`** suma la sección "Diagnosticar una corrida":
  - cómo leer el registro de una corrida;
  - por qué una corrida de menos de diez segundos casi siempre es un problema de acceso;
  - qué hacer ante los errores más comunes: suscripción no habilitada para Claude Code, repositorio sin acceso,
    tareas apagadas por la organización y límite de uso.

## 0.3.0 · 2026-10-29

El motor y la actualización de proyectos:
- **Motor** (`nucleo/motor.md` y `kit/.fabrica/motor/corrida.md`): una tarea programada por proyecto, en la nube.
  - Cada corrida avanza un paso del ciclo, en un orden fijo de prioridades.
  - Trabaja en ramas y PRs, y nunca sube cambios a `main`.
  - Deja las preguntas como issues `espera:direccion`.
  - Solo integra con un "intégralo" de la cuenta de la Dirección.
  - Escribe la bitácora de corridas en un issue fijo.
  - El presupuesto va en `motor.pasos_por_corrida`, 1 por defecto, que cabe en el plan Pro.
- **GitHub en la nube:** el kit usa la API REST (`gh api`) o las herramientas integradas, porque `gh issue` y `gh pr`
  fallan en la nube (usan GraphQL).
- **`actualizar_kit.py`:** actualiza el kit de un proyecto desde su instancia, sin tocar el código, `docs/`,
  `pruebas/` ni su propia CI.
  - Respalda, verifica, revierte si falla y deja un commit.
  - La lógica común con `actualizar_nucleo.py` pasa a `_actualizacion.py`, y el armado del kit a `_kit.py`.
- **Del piloto:**
  - el kit trae `.gitattributes` (saltos de línea LF);
  - `crear_etiquetas.py` usa REST y quita las etiquetas que GitHub crea por defecto.
- **Corrección:** dos actualizaciones dentro del mismo segundo compartían carpeta de respaldo, y revertir la segunda
  restauraba también los respaldos de la primera. Ahora cada una tiene su carpeta.
- **Corrección en la prueba:** `git revert` no acepta `-q`, así que la prueba del revert nunca se había ejecutado de
  verdad (la tapaba el error anterior). Ahora además se exige que la instancia quede limpia tras revertir.
- **Pruebas:** 22 de actualización y 33 del kit, con resultados conocidos.

## 0.2.1 · 2026-10-29

Quién integra cada PR:
- **En los proyectos,** la fábrica pregunta siempre "¿lo integro yo o lo integras tú?":
  - por defecto, integra la Dirección;
  - un "intégralo" autoriza solo ese PR, y si llega como comentario se comprueba que venga de la cuenta de la Dirección;
  - nunca se integra por omisión.
  Cambian `autonomia.md`, la skill `construir` y el `AGENTS.md` del kit.
- **`.fabrica/proyecto.json`** registra en `direccion` la cuenta cuyo "intégralo" autoriza un merge.
- **En el núcleo,** un agente puede integrar un PR solo con la confirmación explícita de quien lo mantiene
  (`actualizaciones.md`).
- La prueba del kit agrega un caso para el campo `direccion` (24 casos).

## 0.2.0 · 2026-10-29

Agentes, skills y kit de proyecto:
- **Kit de proyecto** (`kit/`): lo que recibe cada repositorio de proyecto:
  - un `AGENTS.md` para el coordinador del proyecto;
  - diez agentes, uno por rol de cada área, con su modelo y su esfuerzo declarados;
  - seis skills del ciclo: `triage`, `especificar`, `decidir`, `planificar`, `construir` y `cerrar`;
  - plantillas de issues y de PR, y las etiquetas de estado, riesgo, ruta y tipo;
  - la CI `fabrica.yml`, que rechaza cualquier cambio en `pruebas/aceptacion/` sin la etiqueta `pruebas-aprobadas`.
- **Instancia:**
  - las skills `nuevo-cliente` y `nuevo-proyecto`;
  - los scripts `nuevo_cliente.py` (empresas, holdings con varios negocios, personas o propio) y
    `nuevo_proyecto.py` (arma el kit, copia el método, crea el estado y el manifiesto, y opcionalmente el repositorio
    privado en GitHub);
  - un cliente con reserva estricta se deriva a una instancia propia.
- **`verificar.py`** revisa además:
  - el kit;
  - el encabezado de cada agente (nombre, descripción, modelo y esfuerzo) y de cada skill;
  - que cada rol de `modelos.md` tenga su agente;
  - las referencias dentro del kit.
- **Prueba de punta a punta del kit:** 23 casos con resultados conocidos, en la CI.
- **La pausa por proyecto** se configura en `.fabrica/proyecto.json`.

## 0.1.0 · 2026-10-29

Cimientos de la fábrica:
- Constitución v1.0.0 con doce principios.
- Contrato de autonomía: tres listas, cinco motivos de detención, registro de decisiones, niveles de autonomía,
  topes, interruptor y resumen diario.
- Diez áreas, con su rol y su madurez.
- Ciclo de vida: triage por ruta y riesgo, etapas, estados, motivos de bloqueo, Definition of Ready y Definition of
  Done.
- Calidad: evidencia antes de afirmar, pruebas protegidas, revisión doble, profundidad según el riesgo, ciclo de
  corrección con tope y revisión final.
- Aislamiento entre clientes en tres capas.
- Modelos por rol y por nivel.
- Aprendizaje: retrospectiva, promoción al núcleo y examen de la fábrica.
- Plantillas: historia, plan, ADR, constitución de proyecto, cliente, estado y retrospectiva.
- Núcleo e instancias:
  - `NUCLEO.txt` separa la zona del núcleo de la zona de la instancia;
  - `actualizar_nucleo.py` actualiza con vista previa, respaldo, verificación, reversión automática y un commit propio;
  - `verificar.py` revisa rutas, JSON, versión, referencias entre documentos y, en el núcleo, que no haya datos de una
    instancia.
- Prueba de punta a punta de la actualización, con resultados conocidos.
- CI en GitHub, plantillas de issues y de PR, y licencia MIT.
