---
name: adoptar-proyecto
description: Trae a la fábrica un proyecto que ya existe (un repositorio con historia, documentos o código) sin perder nada. Lleva sus reglas propias a su constitución, decide qué hacer con sus agentes y skills, le instala el kit y lo registra en la ficha del cliente. Úsala cuando un cliente llega con su propio repositorio o cuando un proyecto anterior entra a la fábrica.
---

# Adoptar un proyecto

El detalle está en `nucleo/actualizaciones.md`, en "Adoptar un proyecto que ya existe". Todo se hace en una rama
propia del proyecto (`fabrica/adopcion`), y llega a su rama principal por un PR.

## Pasos

1. **Cliente y negocio.** Si faltan, regístralos con la skill `nuevo-cliente`. Para sumar un negocio a un cliente que
   ya existe: `python .fabrica/scripts/nuevo_cliente.py --id <cliente> --agregar --negocio <slug>:<rubro>:<descripción>`.
2. **Vista previa:**
   `python .fabrica/scripts/adoptar_proyecto.py <carpeta> --cliente <c> --negocio <n> --proyecto <p> --fase <fase>`.
   Muestra qué archivos del proyecto reemplaza el kit y cuáles son propios dentro de carpetas del kit.
3. **Prepara el proyecto antes de adoptarlo,** en la rama `fabrica/adopcion`:
   - **Reglas propias.** Lo que digan los archivos que el kit reemplaza (por ejemplo, un `CLAUDE.md` o un `AGENTS.md`
     con reglas) pasa a `docs/constitucion.md`, desde `nucleo/plantillas/constitucion-proyecto.md`. Una regla que
     contradice la constitución de la fábrica se le pregunta a la Dirección; no se descarta en silencio.
   - **Agentes y skills propios.** Para cada uno, propone una de tres salidas: sigue con prefijo `local-`, lo
     reemplaza el del kit, o su conocimiento pasa a la base del rubro (`rubros/<rubro>/`).
   - **Documentos.** No se mueven. Si no usan las carpetas de la fábrica, `docs/constitucion.md` dice dónde está cada
     cosa: descubrimiento, ADR, historias y bitácora.
   - Haz un commit con esa preparación.
4. **Adopta:** el mismo comando con `--aplicar`. Respalda lo que reemplaza, verifica y deja un commit.
5. **Publica y conecta,** cada paso con el sí de la Dirección:
   - el PR de la adopción, preguntando quién lo integra;
   - si el repositorio no se llama `<cliente>-<proyecto>`, el cambio de nombre (GitHub redirige el anterior);
   - las etiquetas, con `.fabrica/scripts/crear_etiquetas.py`. Ese script quita las etiquetas predeterminadas de GitHub:
     si el proyecto las usa, córrelo con `--conservar-predeterminadas`;
   - la CI propia: si falla porque el proyecto todavía no tiene código, se condiciona o se apaga hasta que lo tenga;
   - el motor, si la Dirección lo quiere (`nucleo/motor.md`).
6. **Commit en la instancia** con la ficha del cliente.

## Lo que devuelves

- qué se reemplazó y dónde quedó el respaldo;
- la decisión sobre cada regla, agente y skill propios;
- los pasos que quedan en manos de la Dirección.
