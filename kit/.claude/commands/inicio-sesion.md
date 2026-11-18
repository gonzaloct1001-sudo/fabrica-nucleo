---
description: Trae lo último de GitHub y resume en tres o cuatro líneas dónde quedamos y qué toca ahora.
---
Ejecuta, en orden:

1. `git fetch origin` y luego `git pull` sobre la rama actual, para traer lo que cambió en otra máquina, en otra
   sesión o en un PR integrado. Si hay conflictos o cambios locales sin commit que lo impiden, avisa y detente: no
   fuerces nada.
2. `python .fabrica/scripts/estado.py`: en unas 20 líneas da la rama, las historias en curso con el avance de su plan,
   los PRs abiertos con sus controles, lo que espera a la Dirección y la última entrada de la bitácora de corridas.
   Reemplaza al `git log` y a las lecturas de rutina. Sin `gh` o sin red, agrega `--sin-red`.
3. Lee la siguiente acción: la ruta está en `rutas.siguiente_accion` de `.fabrica/proyecto.json`
   (por defecto, `docs/siguiente-accion.md`).
4. Si la sesión va a construir, lee también las notas para sesiones (`rutas.notas`, por defecto
   `docs/notas-para-sesiones.md`).

Con eso, responde en tres o cuatro líneas:
- la fase y la etapa del ciclo;
- qué se completó último, según el estado y el último commit;
- qué toca ahora, según la siguiente acción, con la skill o el comando exacto para pedirlo.

No empieces a trabajar todavía: espera la confirmación de la Dirección.
