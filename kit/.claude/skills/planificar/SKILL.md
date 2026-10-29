---
name: planificar
description: Escribe el plan de implementación de una historia lista, con tareas cortas que empiezan por la prueba que debe fallar, y lo somete a un análisis de consistencia antes de construir. Úsala cuando una historia está en estado listo y no tiene plan.
---

# Planificar

## Quién lo escribe

- **El `arquitecto`** (nivel alto), si el riesgo es alto o la ruta es completa.
- **El `desarrollador`** (nivel medio), en los demás casos.

## Pasos

1. **El plan.** Se escribe `docs/planes/H-NNN-plan.md` desde `.fabrica/nucleo/plantillas/plan.md`:
   - los archivos, con la responsabilidad de cada uno;
   - las restricciones globales, copiadas tal cual de la historia y de la constitución;
   - los riesgos a vigilar, cada uno con su prueba;
   - la tabla de complejidad justificada;
   - las tareas de 2 a 5 minutos. Cada tarea indica sus archivos exactos, las interfaces que usa y entrega, la
     prueba que debe fallar primero, el comando de verificación y el resultado esperado.
2. **La revisión propia,** antes de entregarlo:
   - **Cobertura:** cada requisito de la historia tiene al menos una tarea.
   - **Pasos:** cada paso permite hacer una sola cosa razonable. Sin líneas que no decidan nada, y sin código que la
     firma y la prueba ya determinan.
   - **Consistencia:** los nombres y los tipos coinciden entre tareas.
   - **Proporción:** si el plan es más largo que el código que describe, sobra detalle.
3. **El análisis de consistencia.** El `revisor`, en modo consistencia, compara historia, plan y tareas sin cambiar
   nada. Lo que encuentre se corrige en el plan, y el resultado se anota en el registro del plan.

## Lo que devuelves

La ruta del plan, el número de tareas y el resultado del análisis de consistencia.
