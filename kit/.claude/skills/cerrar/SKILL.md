---
name: cerrar
description: Cierra una historia integrada o una épica terminada. Verifica la Definition of Done, actualiza el estado del proyecto para el panel, registra la bitácora y, al cerrar una épica, hace la retrospectiva. Úsala después de que la Dirección integra un PR o marca una historia como hecha.
---

# Cerrar

## Al cerrar una historia

1. **Comprueba la Definition of Done** (`.fabrica/nucleo/ciclo.md`), punto por punto y con su evidencia: CI en
   verde, revisión limpia, seguridad (si correspondía), contratos y documentación al día, y decisiones entregadas.
   Si falta algo, no cierres: crea la tarea que falta y avísalo.
2. **El `documentador`** (nivel bajo) actualiza `.fabrica/estado.json` y agrega la entrada en `docs/bitacora.md`.
3. **Solo una persona marca una historia como `hecho`.** Si la Dirección integró el PR pero la etiqueta no cambió,
   pregúntalo en el resumen; no la cambies tú.

## Al cerrar una épica

1. **Retrospectiva.** El `revisor` (nivel medio) busca duplicación y desvíos entre las historias de la épica, sobre
   el diff acumulado. El `documentador` completa `.fabrica/nucleo/plantillas/retrospectiva.md` en
   `docs/retrospectivas/<epica>.md`.
2. **Refactorización:** cada hallazgo de duplicación o desvío se vuelve una historia aparte, que pasa por el ciclo
   normal.
3. **Aprendizajes:** se clasifican en propios del proyecto, del rubro o del método (`.fabrica/nucleo/aprendizaje.md`).
   Los del rubro y los del método se escriben limpios en `docs/aprendizajes.md`, sin nombres, montos ni datos del
   cliente. La Dirección decide cuáles se proponen al núcleo.

## Lo que devuelves

Dos líneas: qué se cerró, el semáforo del proyecto y si hay retrospectiva o aprendizajes nuevos para revisar.
