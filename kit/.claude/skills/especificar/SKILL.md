---
name: especificar
description: Convierte un pedido clasificado en historias que cumplen la Definition of Ready, con criterios de aceptación, reglas de negocio explícitas y, si el riesgo lo exige, pruebas de aceptación aprobadas. Úsala después del triage y antes de planificar o construir.
---

# Especificar

## Ruta completa: primero la iniciativa

El `analista` escribe `docs/iniciativas/<slug>.md` con:
- el objetivo;
- quiénes la usan;
- lo que queda fuera de alcance;
- las épicas, en orden de valor, cada una con su lista de historias tentativas.

La Dirección confirma la iniciativa antes de especificar las historias.

## Por cada historia

1. **Descubrimiento, si falta conocimiento del dominio.** El `analista` (nivel alto) completa
   `docs/descubrimiento/<tema>.md`. Lo que solo sabe una persona del cliente queda como pregunta con dueño.
2. **La historia.** El `analista` escribe `docs/historias/H-NNN-<slug>.md` desde
   `.fabrica/nucleo/plantillas/historia.md`, usando el siguiente número libre.
3. **Lo que falta definir:**
   - **Duda técnica:** el analista la decide y la anota en "Supuestos".
   - **Duda de negocio:** queda `[ACLARAR: … — decide: Dirección]`. El issue recibe la etiqueta `espera:direccion`,
     con la pregunta escrita en un comentario que se pueda responder en una línea. **Esa historia se detiene, y tú
     sigues con otra.**
4. **El diseño, si la historia tiene interfaz.** El `disenador` define el flujo y los estados de cada pantalla.
5. **Las pruebas de aceptación:**
   - **Riesgo alto:** obligatorias.
   - **Riesgo medio:** recomendables.
   - **Riesgo bajo:** opcionales; bastan los criterios.

   Las escribe `qa` en `pruebas/aceptacion/H-NNN/`.
6. **El PR de especificación.** La historia, el diseño y las pruebas van en un PR "Especificación H-NNN". Si incluye
   pruebas de aceptación, la Dirección lo aprueba poniendo la etiqueta `pruebas-aprobadas`. La CI no deja pasar
   cambios en `pruebas/aceptacion/` sin esa etiqueta.
7. **La Definition of Ready.** Revísala punto por punto (`.fabrica/nucleo/ciclo.md`). Si se cumple, la historia pasa
   a `estado:listo`.

## Lo que devuelves

- las historias que quedaron listas, cada una con su enlace;
- las que esperan a la Dirección, con su pregunta;
- el siguiente paso.
