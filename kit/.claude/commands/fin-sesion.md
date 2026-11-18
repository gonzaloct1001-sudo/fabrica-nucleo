---
description: Deja todo el trabajo de la sesión en GitHub, en una rama con su PR, con la siguiente acción al día.
---
El guardado automático (núcleo 0.13) hace un commit en local después de cada respuesta y, cada 30 minutos, lo
respalda en una rama `wip/<rama>` sin PR ni CI. Este comando hace lo que el guardado no hace: deja la siguiente acción
al día y abre el PR, con un solo commit.

Ejecuta, en orden:

1. `git status`. Si no hay cambios y la siguiente acción (`rutas.siguiente_accion` de `.fabrica/proyecto.json`, por
   defecto `docs/siguiente-accion.md`) refleja el estado real (compruébalo igual), dilo y termina.
2. Revisa lo avanzado (`git status`, `git diff` y lo conversado) para saber qué se tocó y qué se decidió de verdad.
   El mensaje del commit resume ese trabajo, nunca "cambios varios".
3. Antes del commit, deja la siguiente acción al día (rol `documentador`):
   - "Qué toca ahora": la ÚNICA acción concreta que sigue, dado lo que avanzó la sesión;
   - "Espera a la Dirección": cada pendiente con su enlace directo y qué botón tocar;
   - lo hecho no se acumula ahí: va al Registro del plan y a un comentario en la bitácora de corridas (el issue),
     con el mismo formato que deja una corrida;
   - si cambió el estado de alguna historia, `python .fabrica/scripts/estado.py --escribir`;
   - las dudas de negocio que surgieron quedan escritas en su historia o como issue `Pregunta: …`, no solo en el chat.
4. Comprueba las reglas que no se negocian (`.fabrica/nucleo/constitucion.md` y `docs/constitucion.md`):
   - ningún archivo nuevo parece un secreto (`.env`, credenciales, tokens, llaves). Si aparece uno sin estar en
     `.gitignore`, avisa y detente;
   - un dato personal nuevo (identificación, dirección, teléfono, ubicación, audio o imagen) está declarado en el
     registro de tratamiento del proyecto. Si no, avisa antes del commit.
5. Si estás en la rama principal, crea una rama `fabrica/sesion-<AAAA-MM-DD>-<hhmm>` antes del commit: nada se sube
   directo a la principal (`.fabrica/motor/corrida.md`, "Cómo trabajas").
6. Junta en un solo commit lo de la rama, si la rama todavía no tiene PR: `git fetch origin` y
   `git reset --soft "$(git merge-base origin/<principal> HEAD)"` (el punto exacto donde la rama salió de la
   principal; nunca la punta actual, que revertiría lo integrado después) y `git commit` con un mensaje Conventional Commits en español (`feat:`, `fix:`, `docs:`,
   `chore:`) y la línea de coautoría que indique el entorno. Si la rama ya se subió sin PR, súbela con
   `--force-with-lease`: todavía es solo tuya. Si la rama ya tiene PR, junta solo lo que todavía no subiste
   (`git reset --soft origin/<rama>` y un commit nuevo encima): lo que ya está en el PR no se reescribe, y los commits
   de guardado no llegan al PR uno por uno. Antes de subir, `gitleaks git --log-opts="HEAD --not --remotes" .` si está instalado: un
   secreto subido a GitHub no se puede retirar.
7. `git push -u origin <rama>` y abre o actualiza su PR con la plantilla del proyecto. En la nube, por la API REST.
8. Confirma en una o dos líneas qué se subió, el enlace al PR y cuál quedó como siguiente acción.

No hagas `git push --force` sobre una rama con PR ni sobre la principal, ni reescribas su historia. Si el push se rechaza por cambios remotos nuevos, avisa: no
hagas un pull ni un rebase automático sin decirlo primero.
