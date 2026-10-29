---
name: triage
description: Clasifica un pedido nuevo (por chat, issue o nota) según su ruta (directa, una sesión o completa) y su riesgo (bajo, medio o alto), lo registra y decide el paso siguiente. Úsala cada vez que entra trabajo nuevo al proyecto, antes de especificar o construir.
---

# Triage

Decide cuánto proceso necesita un pedido. Lo hace el coordinador, sin delegar.

## Pasos

1. **Revisa la pausa.** Si `.fabrica/proyecto.json` dice `"pausa": true`, registra el pedido y no sigas.
2. **Entiende el pedido.** Qué quiere lograr quien lo pide, no solo qué pidió.
3. **Elige la ruta** (`.fabrica/nucleo/ciclo.md`):
   - **directa:** cambio obvio y de bajo riesgo (un texto, un estilo, una configuración);
   - **una sesión:** cambio claro que se entiende, se construye y se revisa de una vez;
   - **completa:** grande, ambiguo o que toca varias partes. Se trabaja como iniciativa, épicas e historias.
4. **Elige el riesgo:**
   - **alto:** toca dinero, stock, datos personales, permisos, seguridad o un contrato público;
   - **medio:** toca lógica de negocio o varios archivos que dependen entre sí;
   - **bajo:** todo lo demás.
5. **Ante la duda, elige la ruta y el riesgo más altos.** Nunca clasifiques como bajo algo que toque dinero, datos
   personales o permisos.
6. **Regístralo** como issue en GitHub, con las etiquetas `tipo:*`, `ruta:*`, `riesgo:*` y `estado:borrador`. Sin
   GitHub, regístralo como historia en borrador en `docs/historias/`. En el issue va una línea de justificación:
   "Ruta X y riesgo Y, porque …".
7. **Sigue con el paso siguiente:**
   - **directa:** `construir`, con un plan de una o dos tareas escrito en el mismo issue;
   - **una sesión:** `especificar`, en versión breve;
   - **completa:** `especificar`, primero a nivel de iniciativa.

## Lo que devuelves

Una línea: enlace al issue, ruta, riesgo y siguiente paso. Si la clasificación fue dudosa, anótala como decisión:
`Decisión: ruta X y riesgo Y — por qué — qué cuesta si es errada`.
