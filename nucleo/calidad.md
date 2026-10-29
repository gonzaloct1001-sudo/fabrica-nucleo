# Calidad

La calidad no se agrega al final: se construye con controles en cada paso, cada uno independiente del que hizo el
trabajo.

## Evidencia antes que afirmación

Antes de declarar cualquier estado:

1. **Identificar** qué comando lo demuestra.
2. **Correrlo** completo, en ese momento.
3. **Leer** la salida entera: el código de salida y el número de fallas.
4. **Afirmar** solo lo que la salida muestra, citándola.

| Afirmación | Evidencia que la respalda | No sirve |
|---|---|---|
| Las pruebas pasan | La salida del comando de pruebas con 0 fallas | Una corrida anterior, "deberían pasar" |
| La compilación funciona | El comando de compilación con código de salida 0 | Que el linter pase |
| El error está corregido | La prueba del síntoma original, ahora en verde | Que el código cambió |
| La prueba de regresión sirve | Ciclo rojo y verde: pasa, se revierte el arreglo y falla, se restaura y vuelve a pasar | Que pase una vez |
| Un agente terminó | El diff muestra los cambios | El agente informa que terminó |
| Se cumplen los requisitos | Una lista revisada requisito por requisito | Que las pruebas pasen |

Las palabras "debería", "probablemente" y "parece" en un informe de estado son una señal de alerta.

## Pruebas protegidas

Las pruebas de aceptación de una historia se escriben y se aprueban antes de construir, en una carpeta propia
(`pruebas/aceptacion/`). La CI de cada proyecto rechaza cualquier PR que las modifique, salvo que lleve la etiqueta
`pruebas-aprobadas`, que solo pone la Dirección. Para cambiarlas hay que volver a la especificación.

## Revisión por tarea: dos veredictos

Después de cada tarea, un revisor con contexto limpio, que no participó en la construcción, entrega dos veredictos:

1. **Cumplimiento.** Compara el diff con lo pedido:
   - qué falta: requisitos omitidos, o declarados como hechos sin estarlo;
   - qué sobra: funciones no pedidas y complejidad innecesaria;
   - qué se malentendió: lo correcto hecho de forma equivocada, o el problema equivocado resuelto.
2. **Calidad.** Separación de responsabilidades, manejo de errores, casos borde, pruebas que verifican comportamiento
   real, y archivos con una sola responsabilidad.

Reglas del revisor:

- **No confía en el informe del implementador.** Son afirmaciones por verificar contra el diff, incluidas las
  justificaciones de diseño.
- **Cita archivo y línea** en cada hallazgo.
- **Calibra la severidad:**
  - **Crítico:** rompe algo o expone datos.
  - **Importante:** no se puede confiar en la tarea hasta corregirlo.
  - **Menor:** una mejora deseable.
- **Lo que no puede verificar desde el diff** lo marca como "no verificable" en vez de salir a recorrer todo el código.
- **No lanza otros revisores.** La fábrica ya define cuántas revisiones recibe cada cambio.

## Profundidad según el riesgo

| Riesgo | Revisión por tarea | Revisión final de la rama |
|---|---|---|
| Bajo | Rápida: un revisor | Un revisor de nivel alto |
| Medio | Rápida, más QA | Un revisor de nivel alto, más QA |
| Alto | Exhaustiva: cuatro revisiones independientes (el diff, los casos borde, los huecos de prueba y si cumple lo pedido) | Exhaustiva, más el veredicto de seguridad |

## Ciclo de corrección con tope

Se abre cuando la revisión encuentra un incumplimiento o un hallazgo crítico o importante. Los hallazgos menores van
al registro como "diferidos" y la revisión final decide cuáles se corrigen antes del merge.

- **Rondas 1 a 3:** corrige el mismo implementador, que conserva el contexto de su tarea.
- **Rondas 4 y 5:** toma la tarea un implementador nuevo, con un modelo de nivel superior, que lee el informe de lo
  intentado.
- **Cada ronda** termina con una revisión acotada a lo corregido.
- **Al llegar a la ronda 5 con hallazgos abiertos,** el coordinador decide cada uno: lo estaciona con su justificación
  o resuelve el cambio mínimo que destraba el trabajo. En ambos casos lo registra como decisión.

Ningún hallazgo se descarta en silencio.

## Revisión final de la rama

Cuando todas las tareas están cerradas, un revisor de nivel alto mira la rama completa junto con los hallazgos
diferidos y estacionados.

Si encuentra problemas, se lanza una sola tanda de corrección con todos ellos juntos, no un arreglo por hallazgo, y
después una revisión acotada de esa tanda. No hay segunda tanda: lo que quede abierto llega a la Dirección en el PR.

## Consistencia entre documentos

- **Antes de construir:** el revisor compara la historia, el plan y las tareas, buscando contradicciones, requisitos
  sin tarea y tareas sin requisito. No modifica nada.
- **Antes de cerrar:** compara el código con la historia y agrega como tareas lo que falta.
