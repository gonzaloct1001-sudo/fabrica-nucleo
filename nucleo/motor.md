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
| Conectores | ninguno (quita los que se agregan por defecto) |
| Ambiente | el predeterminado; basta con su acceso de red "Trusted" |

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

## Lo que la nube permite y lo que no

- **GitHub:**
  - se usa por la API REST (`gh api ...`) o con las herramientas integradas;
  - `gh issue` y `gh pr` fallan, porque usan GraphQL;
  - una corrida solo alcanza los repositorios asignados a su tarea.
- **Permisos:** la corrida empieza en modo automático, y un clasificador puede bloquear acciones riesgosas. Si
  bloquea una acción, la corrida lo anota y sigue con otra cosa. Si una acción queda esperando permiso, la Dirección
  la responde desde la sesión de la corrida, en claude.ai/code o en la app.
- **Ramas:** la nube puede subir cambios a cualquier rama, `main` incluida. La regla de no subir a `main` está en la
  corrida. En un repositorio público o en planes de pago, conviene además una protección de rama en GitHub.
- **Identidad:** todo lo que hace la corrida aparece en GitHub con la cuenta de la Dirección. Por eso GitHub no le
  notifica sus propias preguntas ni la bitácora. Para recibir avisos hace falta un mensaje creado por otra identidad
  (por ejemplo, un bot de GitHub Actions). Ese es el trabajo del panel y del resumen diario de la instancia.

## Detener el motor

- **Un proyecto:** `"pausa": true` en `.fabrica/proyecto.json`, mediante un PR. La siguiente corrida lo respeta.
- **Todos los proyectos:** apagar las tareas en claude.ai/code/routines.
