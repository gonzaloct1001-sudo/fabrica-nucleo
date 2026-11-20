# El motor: que los proyectos avancen solos

El motor es una tarea programada del asistente: una sesión en la nube que se ejecuta sola, a la hora indicada, sobre
el repositorio de un proyecto. Cada corrida sigue `kit/.fabrica/motor/corrida.md`, que en el proyecto vive en
`.fabrica/motor/corrida.md`:
- avanza un paso del ciclo;
- trabaja en ramas y PRs;
- deja las preguntas para la Dirección como issues;
- anota lo que hizo en la bitácora de corridas.

No depende de que el computador de la Dirección esté encendido.

## Una tarea por proyecto

Cada proyecto tiene su propia tarea programada, que solo ve su propio repositorio. Así se cumple el aislamiento entre
clientes (`aislamiento.md`): una corrida no tiene cómo leer otro proyecto.

## Crear la tarea

En claude.ai/code/routines, o con `/schedule` desde una sesión abierta en el proyecto:

| Campo | Valor |
|---|---|
| Nombre | `fabrica · <cliente>-<proyecto>` |
| Repositorio | solo el del proyecto |
| Disparador | horario: una vez al día, o más según el plan (ver abajo) |
| Instrucción | `Ejecuta una corrida de la fábrica: lee y sigue .fabrica/motor/corrida.md.` |
| Conectores | ninguno (quita los que se agregan por defecto): cada conector suma sus herramientas al contexto de cada corrida y es superficie de riesgo |
| Ambiente | el predeterminado; basta con su acceso de red "Trusted" |
| Avisos | push al teléfono, encendido: así la Dirección sabe que la corrida terminó |

Requisito: la aplicación de Claude para GitHub instalada en el repositorio del proyecto, con acceso solo a los
repositorios que la fábrica usa.

## Cuánto puede hacer según el plan

Cada corrida gasta el uso del plan, igual que una sesión normal. No hay un cobro aparte por la nube, salvo que se
activen créditos de uso extra.

| Plan | Corridas sugeridas | `motor.pasos_por_corrida` |
|---|---|---|
| Pro | 1 al día por proyecto activo | 1 |
| Max 5x | 2 o 3 al día | 1 o 2 |
| Max 20x | Hasta una por hora en horario hábil | 2 o 3 |

El valor por defecto (1 paso) está en `.fabrica/proyecto.json` de cada proyecto. Un "paso" de construcción ejecuta
como máximo tres tareas del plan.

## El ritmo: por horario, por relevos, en sesión o en la mañana

La Dirección elige el ritmo según el tiempo que tenga. Todos usan la misma corrida y las mismas reglas: solo cambia
quién la dispara y cuándo.

| Ritmo | Cuándo conviene | Cómo avanza |
|---|---|---|
| **Por horario** | Siempre: es la base, y la Dirección no necesita estar | La tarea programada corre a sus horas, un paso por corrida. Lo que espera a la Dirección se acumula en su bandeja |
| **Por relevos** | La Dirección tiene un rato y quiere decidir rápido | Desde la bandeja (`bandeja-direccion`), cada decisión despierta en el momento la corrida del proyecto. Cuando termina, la bandeja trae lo nuevo, la Dirección decide y sale el relevo siguiente |
| **En sesión** | La Dirección tiene un bloque largo | Se abre el asistente en la carpeta del proyecto y el coordinador trabaja en vivo, con las mismas skills y reglas. Las decisiones se toman al momento |
| **En la mañana** | La Dirección revisa desde el teléfono, con su computador apagado | La tarea de la mañana de cada cliente publica su resumen diario en la misma página de siempre. La Dirección lo lee y responde en la sesión de esa tarea; la bandeja publica e integra desde la nube y, si puede, despierta la corrida del proyecto |

- **Despertar una corrida** es ejecutar ahora la tarea `fabrica · <repositorio>`: desde el asistente, con su
  herramienta de tareas programadas, o con el botón de ejecutar en claude.ai/code/routines. La tarea programada
  sigue igual: un relevo no cambia su horario.
- **Un relevo a la vez por proyecto.** Antes de despertar una corrida, la anterior tiene que haber terminado: su
  entrada en la bitácora lo confirma (`bandeja.py --esperar <repositorio>`). Dos corridas sobre el mismo repositorio
  pisarían sus ramas.
- **Si no hay nada que decidir, los relevos siguen solos,** hasta cinco seguidos o el tope que fije la Dirección.
  También paran cuando una corrida deja una decisión, cuando no tiene nada que hacer o cuando la Dirección se va.
- **Una meta acota los relevos:** por ejemplo, "hasta que el ADR quede aceptado" o "hasta que la historia H-001 esté
  lista". Al llegar, paran.
- **En sesión,** conviene que la tarea programada de ese proyecto no corra en medio. Se puede apagar mientras dure,
  en claude.ai/code/routines, o elegir un bloque fuera de su horario.
- **Cada relevo gasta lo mismo que una corrida programada** (tabla de arriba). Los relevos aprovechan el tiempo
  disponible de la Dirección; el horario mantiene el avance cuando no está.

### Dónde quedamos: GitHub es la única memoria

Los ritmos se mezclan sin retrabajo porque todos leen y escriben en el mismo lugar:
- **Nada queda solo en un computador ni en una conversación.** Una sesión termina con todo en GitHub: las ramas
  subidas con su PR, y las respuestas, pedidos e integraciones publicados. Lo que no está ahí no existe para el
  motor ni para la sesión de la mañana.
- **Cada corrida decide su paso leyendo GitHub** (`.fabrica/motor/corrida.md`, "Lee el estado real"): etiquetas,
  PRs, la bitácora y el registro de cada plan. Lo que la Dirección ya decidió se aplica, no se vuelve a preguntar, y
  un paso registrado no se repite.
- **El resumen diario dice dónde quedamos.** Al empezar una sesión, la bandeja muestra lo mismo que vio la mañana.
- **Una sesión y una corrida no trabajan a la vez en el mismo proyecto.** Antes de tocar un proyecto en sesión, la
  última corrida tiene que haber terminado (su entrada en la bitácora), y conviene un bloque fuera de su horario.

### La tarea de la mañana

Una tarea programada por cliente, separada de las del motor:

| Campo | Valor |
|---|---|
| Nombre | `fabrica · resumen · <cliente>` |
| Repositorios | la instancia y los proyectos de ese cliente, ninguno más: así no puede leer otro cliente |
| Disparador | horario: cada día a `resumen_diario.hora`, en la zona de la instancia, después de las corridas de la noche |
| Instrucción | `Arma y publica el resumen diario de la fábrica para el cliente <cliente>: sigue la skill bandeja-direccion, paso «Resumen diario».` |
| Conectores | ninguno |
| Avisos | push al teléfono, encendido |

La primera vez, la página se publica a mano y su dirección queda en `resumen_diario.paginas.<cliente>` de
`.fabrica/config.json`. Desde ahí, la tarea la actualiza cada mañana en la misma dirección, que la Dirección fija en
su aplicación.

### Que una respuesta despierte la corrida (opcional)

La tarea del motor puede sumar, en su página de claude.ai/code/routines, un **disparador de GitHub** además del
horario: el evento *Pull request · closed* del repositorio del proyecto. Así, cuando la Dirección integra un PR, la
corrida siguiente parte en el momento y no a la hora fijada.
- **Solo ese evento,** y si el formulario lo permite, filtrado a los PRs integrados. Los eventos de issues no sirven: la
  propia corrida etiqueta issues y se despertaría a sí misma. Por la misma razón, la corrida no cierra PRs sin
  integrar.
- **Con tope:** cada proyecto fija `motor.corridas_por_dia` en `.fabrica/proyecto.json` (por defecto, 6). Una corrida
  que encuentra ese número de entradas de hoy en la bitácora anota "tope diario" y termina sin trabajar.
- Los eventos de GitHub tienen además un tope por hora de la plataforma: lo que pasa de ese tope se pierde, y el
  horario lo recoge después.

### Dónde ver el estado

El estado vivo de cada proyecto está en su issue **"Estado del proyecto"**. Lo rehace el flujo
`.github/workflows/fabrica-estado.yml` cuando se integra algo que cambia el estado (`docs/` o `.fabrica/`), una vez
al día y a mano (**Actions** → **Fábrica · estado** → **Run workflow**), así que nunca depende de que una sesión se
cierre bien. Corre poco a propósito: cada corrida cuesta al menos un minuto de Actions, y el motor cambia etiquetas
muchas veces al día. El estado al minuto lo da `estado.py` al iniciar una sesión. Conviene fijar el issue como
destacado una vez.
`.fabrica/estado.json` es una copia de las cifras para el panel; la CI exige que coincida con las historias, y la
rehace `estado.py --escribir`.

### Guardado automático

El kit registra en `.claude/settings.json` un hook (`.fabrica/scripts/hook_guardado.py`) que corre al terminar cada
respuesta de Claude:
- **Recorre todas las copias de trabajo del repositorio** (`git worktree list`): la sesión suele abrirse en la copia de
  la rama principal y el trabajo vive en copias hermanas, una por historia. Guarda cada copia que tenga cambios.
- **Commit en local, en la rama de esa copia.** Nunca en `main` ni en `master`: si hay cambios sueltos ahí, avisa y no
  los toca. Toma lo ya registrado en git que cambió y los archivos nuevos que `.gitignore` permite; deja fuera, y lo
  dice, los que parecen secretos, las imágenes, videos y comprimidos, y los de más de 1 MB.
- **Respaldo en GitHub cada 30 minutos,** en la rama `wip/<rama>`, que no tiene PR: no dispara la CI. Antes de subir
  corre gitleaks en local; no sube si gitleaks falta o encuentra algo, o si un flujo del proyecto correría con esa
  rama.
- **Habla poco:** un guardado que sale bien no dice nada; cada problema se avisa una vez por sesión. `estado.py`
  muestra siempre la fecha del último respaldo, o «nunca».
- **El PR se abre aparte, con un solo commit** (`/fin-sesion` y `construir`).
- **Limpieza:** cada día, el flujo `fabrica-estado.yml` borra las `wip/` de PR ya integrados (solo si el respaldo es
  anterior a la integración) y las que llevan más de 14 días sin cambios sin su rama de origen
  (`.fabrica/scripts/limpiar_wip.py`). Ante una respuesta dudosa de GitHub, no borra nada.
- Se apaga con `"guardado_automatico": false` en `.fabrica/proyecto.json`. Lo que solo se conversó no se guarda: las
  decisiones se escriben en la historia, en el registro del plan o en un issue.

**Puesta en marcha, una vez por computador y por proyecto:**
1. **Instalar gitleaks** en el computador donde se trabaja, pasando por la revisión de piezas de terceros de la
   fábrica (`seguridad.md`, "Las piezas de terceros"). Sin gitleaks el guardado sigue haciendo commits en local, pero
   no respalda en GitHub, y lo avisa.
2. **En Windows, Git para Windows** (trae Git Bash): Claude Code corre los hooks con él. El hook busca Python 3 como
   `python3`, `python` o `py`, y salta el acceso directo de la Microsoft Store, que no corre nada. Si no encuentra
   Python 3, Claude Code muestra el error «no encontré Python 3» al terminar cada respuesta: no bloquea nada, pero
   hasta instalarlo no hay guardado automático. Sin Git Bash, Claude Code usa PowerShell, que no entiende el comando:
   aparece un error en cada respuesta, tampoco bloquea, y no hay guardado.
3. **Los flujos del proyecto ya quedan listos:** al crear, adoptar o actualizar el kit, se agrega
   `branches-ignore: ['wip/**']` a cada flujo cuyo `push:` no filtraba ramas, con respaldo. Las formas `on: push` u
   `on: [push, …]` no se cambian solas: `verificar_proyecto.py` las avisa para corregirlas a mano.

### Tablero por estados (opcional)

Para ver las historias por columna desde GitHub móvil, la Dirección arma una vez un tablero de GitHub Projects:
1. En el repositorio, pestaña **Projects** → **Link a project** → **New project** → plantilla **Board**.
2. En **Settings** del tablero, agrega el campo **Status** con las columnas del ciclo: borrador, listo, en-curso,
   en-revision, construido, hecho y bloqueado.
3. En **Workflows**, activa **Auto-add to project** con el filtro `is:issue label:estado:*`.
4. Las tarjetas se mueven a mano o con la vista **Table** agrupada por etiqueta. La fábrica no escribe en el tablero:
   Projects usa GraphQL, que en la nube no funciona. Las etiquetas `estado:*` siguen siendo la fuente.

## Lo que la nube permite y lo que no

- **GitHub:**
  - se usa por la API REST (`gh api ...`) o con las herramientas integradas. La bandeja de la Dirección usa solo la
    API REST, así que funciona igual en la nube;
  - `gh issue` y `gh pr` fallan, porque usan GraphQL;
  - una corrida solo alcanza los repositorios asignados a su tarea.
- **Permisos:** la corrida empieza en modo automático, y un clasificador puede bloquear acciones riesgosas. Si
  bloquea una acción, la corrida lo anota y sigue con otra cosa. Si una acción queda esperando permiso, la Dirección
  la responde desde la sesión de la corrida, en claude.ai/code o en la app.
- **Ramas:** la nube puede subir cambios a cualquier rama, la principal incluida. La regla de no subir a la rama
  principal está en la corrida. En un repositorio público o en planes de pago, conviene además una protección de rama en GitHub.
- **Identidad:** todo lo que hace la corrida aparece en GitHub con la cuenta de la Dirección. Por eso GitHub no le
  notifica sus propias preguntas ni la bitácora. Para recibir avisos hace falta un mensaje creado por otra identidad.
  Desde la 0.12, el kit trae el flujo `.github/workflows/fabrica-avisos.yml`: cuando un issue o un PR recibe
  `espera:direccion` o `estado:construido`, comenta como `github-actions` y menciona a la Dirección. El panel y el resumen
  diario de la instancia completan los avisos.

## Diagnosticar una corrida

Si en GitHub no aparece nada después de una corrida (ni comentario en la bitácora, ni ramas, ni issues), la corrida
falló antes de trabajar. Su registro está en claude.ai/code/routines, en la página de la tarea, en la lista de
corridas. Desde una sesión del asistente también se puede pedir: "muestra el registro de la última corrida de
<tarea>".

Una corrida que termina en menos de diez segundos casi siempre es un problema de acceso, no de la fábrica.

| Mensaje | Qué significa | Qué hacer |
|---|---|---|
| "Your organization has disabled Claude subscription access for Claude Code" (`oauth_org_not_allowed`) | La cuenta no permite usar Claude Code con su suscripción en la nube | Revisar el plan y la configuración de la organización en claude.ai. Si persiste, autenticar con una clave de API o contactar al soporte |
| "GitHub access to … is not enabled for this session" | La tarea no tiene acceso a ese repositorio | Instalar la aplicación de Claude para GitHub en el repositorio, o agregarlo a la tarea |
| "Routines are disabled by your organization's policy" | La organización apagó las tareas programadas | Un dueño de la organización las activa en la configuración |
| Se agotó el uso del plan | La corrida no inicia hasta que se reinicia el límite | Esperar el reinicio, reducir la frecuencia o subir de plan |

## Detener el motor

- **Un proyecto, desde el teléfono:** la etiqueta `motor:pausa` en el issue "Bitácora de corridas de la fábrica".
  La siguiente corrida la ve primero, anota "En pausa" y termina. Para reanudar, se quita la etiqueta.
- **Un proyecto, de forma permanente:** `"pausa": true` en `.fabrica/proyecto.json`, mediante un PR.
- **Todos los proyectos:** apagar las tareas en claude.ai/code/routines.
