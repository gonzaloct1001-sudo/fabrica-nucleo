---
name: bandeja-direccion
description: Trae a la conversación lo que espera a la Dirección en los proyectos de la instancia (preguntas, PRs listos, lo último de cada corrida), lo presenta en lenguaje simple con una recomendación, y publica en GitHub sus respuestas, sus pedidos y las integraciones que autorice. Úsala cuando la Dirección pregunte qué hay pendiente, abra una sesión para operar la fábrica o prefiera decidir desde el chat en vez de GitHub.
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

## Pasos

1. **Resumen:** `python .fabrica/scripts/bandeja.py`. Cuéntale a la Dirección, en dos o tres líneas, qué proyectos
   esperan su decisión y cuándo corrió el motor por última vez. Si nada espera, dilo y termina.
2. **Detalle de un cliente:** `python .fabrica/scripts/bandeja.py --cliente <slug>`. Si hay varios con pendientes,
   pregunta por cuál empezar.
3. **Presenta cada decisión en lenguaje simple:**
   - **Pregunta:** qué se decide, las opciones con lo que cuesta cada una y tu recomendación. Las que ya tienen
     respuesta ("respondida") no se vuelven a preguntar: la próxima corrida las aplica.
   - **PR:** qué cambia, para quién, el estado de sus controles y si está listo. Para explicarlo puedes leer su
     descripción y sus archivos con `gh pr view` y `gh pr diff`, solo de este cliente.
   - Usa AskUserQuestion cuando las opciones sean claras (hasta cuatro decisiones por vez), con la recomendada
     primero.
4. **Publica cada respuesta:**
   `python .fabrica/scripts/bandeja.py --responder <repositorio>#<n> --texto "<respuesta de la Dirección>"`.
   El texto empieza por la opción elegida (por ejemplo "H3") y sigue con lo que la Dirección agregó.
5. **Integra los PRs que la Dirección autorizó:** `python .fabrica/scripts/bandeja.py --integrar <repositorio>#<n>`.
   Si el script se niega, explica por qué. Si el sistema bloquea la integración, dilo y no insistas: la Dirección
   puede integrarlo en GitHub.
6. **Pedidos nuevos:** cuando la Dirección pida trabajo,
   `python .fabrica/scripts/bandeja.py --pedido <repositorio> --titulo "<título>" --texto "<cuerpo>"`, con tres
   secciones: "## Qué necesitas", "## Por qué ahora" y "## Cómo sé que está listo". Va sin etiquetas: la próxima
   corrida lo clasifica.

## Lo que devuelves

- una tabla con lo que se publicó (respuestas, integraciones, pedidos) y sus enlaces;
- lo que sigue esperando y por qué;
- cuándo lo aplica el motor: la próxima corrida de cada proyecto, y un paso por corrida.
