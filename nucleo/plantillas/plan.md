# Plan: <título de la historia>

> Va en `docs/planes/H-NNN/plan.md`: es el índice. Cada tarea va en `tarea-NN.md` y el registro en `registro.md`,
> en la misma carpeta (núcleo 0.13). Así cada lectura trae solo lo que necesita.

**Historia:** `<ruta a la historia>` — el plan argumenta desde ella; si se contradicen, manda la historia.
**Objetivo:** <una oración con lo que construye>.
**Enfoque:** <dos o tres oraciones sobre cómo>.
**Tecnología:** <piezas clave>.

> Un plan es el conjunto de decisiones que quien implementa no puede tomar solo. Si el plan es más largo que el código
> que describe, se escribió el código en vez de planificar. Si una línea no decide nada ("manejar errores", "agregar
> validaciones", "pendiente"), falta una decisión.

## Restricciones globales

Requisitos de la historia o de la constitución del proyecto que rigen todas las tareas, uno por línea y con sus
valores exactos.

- <ejemplo: "Toda consulta filtra por empresaId">

## Riesgos a vigilar

Las entradas o fallas que la historia implica y que ninguna tarea prueba todavía. Van las más probables primero, y
cada una con la prueba que la cubre en su tarea.

- <entrada o condición> → <comportamiento esperado> (prueba en la tarea N)

## Complejidad justificada

| Qué se agrega | Por qué hace falta | Alternativa simple descartada y por qué |
|---|---|---|
| | | |

(Vacía si no hay nada que justificar.)

## Archivos

| Archivo | Crear o modificar | Responsabilidad |
|---|---|---|
| | | |

---

## Tareas

Una tarea por archivo, `tarea-NN.md` en esta misma carpeta, desde `.fabrica/nucleo/plantillas/tarea.md`. Cada archivo
es la ficha que recibe el `desarrollador`: completo por sí solo, sin copiar nada más del plan.

| N | Tarea | Archivo | Depende de |
|---|---|---|---|
| 1 | <componente> | `tarea-01.md` | — |

El registro va aparte, en `registro.md` (`.fabrica/nucleo/plantillas/registro-plan.md`).
