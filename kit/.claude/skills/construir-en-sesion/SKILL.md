---
name: construir-en-sesion
description: Construye una historia con plan analizado dentro de una sesión en vivo. La sesión principal programa con la prueba primero y la revisión independiente se hace por tramo. Úsala solo cuando la Dirección la pide para una historia; el motor programado sigue usando `construir`.
---

# Construir en sesión

Variante de `construir` para cuando la Dirección tiene un bloque de tiempo y no quiere avanzar a una tarea por
corrida. Cambia **quién programa** y **cuándo se revisa**; no cambia ninguna compuerta.

## Antes de empezar

- **Lee las notas para sesiones** (`rutas.notas` de `.fabrica/proyecto.json`, por defecto
  `docs/notas-para-sesiones.md`).
- **La historia tiene plan analizado** y, si su riesgo lo exige, pruebas de aceptación aprobadas.
- **Ninguna corrida programada está trabajando:** su última entrada en la bitácora de corridas está cerrada.
- **Marca la construcción en este repositorio:** crea `.fabrica/trabajo/construyendo`. El hook del kit impide editar
  `pruebas/aceptacion/` mientras exista. Bórrala al terminar.
- **Marca la historia como tuya:** agrega al Registro del plan, en un PR chico que se integra antes de empezar, la
  línea `En construcción en una sesión en vivo. Mientras esta línea exista, la corrida programada no retoma esta
  historia: elige otro paso.` La corrida la respeta (`.fabrica/motor/corrida.md`).

## Qué cambia respecto de `construir`

| | `construir` | `construir-en-sesion` |
|---|---|---|
| Quién programa | Un `desarrollador` nuevo por tarea | La sesión principal |
| Revisión independiente | Después de cada tarea | Por tramo del plan y al final |
| Ficha, informe y diff por tarea | Sí | No: mandan el plan, las pruebas y `git log` |

Lo que se pierde: un defecto se detecta al cerrar el tramo y no justo después de la tarea. Lo compensan las pruebas de
aceptación congeladas, la prueba primero en cada tarea y la CI.

## Por cada tarea

1. Escribe la prueba y **córrela para verla fallar**. Si pasa sin implementar, la prueba no sirve o la tarea ya estaba
   hecha: averígualo antes de seguir.
2. Implementa lo mínimo para que pase.
3. Corre las pruebas del módulo tocado y el linter del proyecto, con `python .fabrica/scripts/filtrar_salida.py --
   <comando>` para leer solo las fallas y el resumen. Al cerrar un tramo, la batería completa y los mismos
   controles de la CI.
4. Un commit por tarea, o por par de tareas si comparten el archivo de pruebas.
5. Cada tres o cuatro tareas, y siempre antes de terminar: el Registro del plan al día
   (`Tarea N: completa (commit …)` y las líneas `Decisión:`) y la rama subida. Si la sesión se corta, la siguiente
   retoma desde ahí.

## Una sesión por tramo (núcleo 0.13)

Cada tramo del plan se construye en una sesión nueva: cada pedido reenvía la conversación entera, así que una sesión
larga cuesta cada vez más. Al cerrar un tramo, deja el registro y la rama al día, corre `/fin-sesion` y abre una
sesión nueva para el siguiente. El coordinador de una sesión en vivo usa un modelo de nivel medio
(`.fabrica/nucleo/modelos.md`); los revisores de nivel alto se lanzan como agentes, con su modelo declarado.

## Al cerrar cada tramo y al final

Lanza los revisores con contexto limpio, **declarando el modelo** (`.fabrica/nucleo/modelos.md`), y pídeles el informe
en `.fabrica/trabajo/H-NNN/`:
- `revisor`, nivel alto: el diff del tramo y, al final, la rama completa con la matriz de cumplimiento contra la
  historia;
- `seguridad`, nivel alto, si el riesgo es medio o alto: sin su `APRUEBA` no hay PR;
- `equipo-rojo`, nivel alto, si el riesgo es alto: cada hallazgo trae una prueba que lo reproduce.

Todos los hallazgos confirmados van a **una sola tanda de corrección**, cada uno con su prueba que falla primero. Lo
que no se corrige llega al PR como estacionado, con su motivo. Ningún hallazgo se descarta en silencio.

## Al terminar

- Reemplaza la marca de sesión en vivo por el estado real (`Tramo N terminado y en su PR #…`).
- Abre el PR con la plantilla del proyecto. Lo integra quien corresponda: la Dirección, o la fábrica si el proyecto
  lo delegó (`.fabrica/nucleo/autonomia.md`, "Delegación por proyecto").
- Corre `/fin-sesion`.

## Lo que no cambia

- `pruebas/aceptacion/` no se toca sin la etiqueta `pruebas-aprobadas`, y nunca en el PR que construye: quien
  implementa no pone esa etiqueta, ni con delegación. Un cambio necesario va en su propio PR de especificación.
- Una regla de negocio que falta no se inventa: se pregunta a la Dirección o, si el proyecto adoptó la opción, se
  vuelve un parámetro `propuesto` del catálogo (constitución de la fábrica, art. IV).
- Una dependencia nueva espera el sí de la Dirección y la revisión en cuarentena.
- Nada se sube a la rama principal: todo llega por un PR.
- Evidencia antes que afirmación: lo que se informa es lo que mostró el comando corrido en ese momento.
