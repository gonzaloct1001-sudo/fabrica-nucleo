---
description: Deja todo el trabajo de la sesión en GitHub, en una rama con su PR, con la siguiente acción al día.
---
Ejecuta, en orden:

1. `git status`. Si no hay cambios y la siguiente acción (`rutas.siguiente_accion` de `.fabrica/proyecto.json`, por
   defecto `docs/siguiente-accion.md`) refleja el estado real (compruébalo igual), dilo y termina.
2. Revisa lo avanzado (`git status`, `git diff` y lo conversado) para saber qué se tocó y qué se decidió de verdad.
   El mensaje del commit resume ese trabajo, nunca "cambios varios".
3. Antes del commit, deja la siguiente acción al día (rol `documentador`):
   - "Qué toca ahora": la ÚNICA acción concreta que sigue, dado lo que avanzó la sesión;
   - "Espera a la Dirección": cada pendiente con su enlace directo y qué botón tocar;
   - lo hecho no se acumula ahí: va a la bitácora de corridas o al Registro del plan;
   - las dudas de negocio que surgieron quedan escritas en su historia o como issue `Pregunta: …`, no solo en el chat.
4. Comprueba las reglas que no se negocian (`.fabrica/nucleo/constitucion.md` y `docs/constitucion.md`):
   - ningún archivo nuevo parece un secreto (`.env`, credenciales, tokens, llaves). Si aparece uno sin estar en
     `.gitignore`, avisa y detente;
   - un dato personal nuevo (identificación, dirección, teléfono, ubicación, audio o imagen) está declarado en el
     registro de tratamiento del proyecto. Si no, avisa antes del commit.
5. Si estás en la rama principal, crea una rama `fabrica/sesion-<AAAA-MM-DD>` antes del commit: nada se sube
   directo a la principal (`.fabrica/motor/corrida.md`, "Cómo trabajas").
6. `git add -A` y `git commit` con un mensaje Conventional Commits en español (`feat:`, `fix:`, `docs:`, `chore:`),
   con la línea de coautoría que indique el entorno.
7. `git push -u origin <rama>` y abre o actualiza su PR con la plantilla del proyecto. En la nube, por la API REST.
8. Confirma en una o dos líneas qué se subió, el enlace al PR y cuál quedó como siguiente acción.

No hagas `git push --force` ni reescribas la historia. Si el push se rechaza por cambios remotos nuevos, avisa: no
hagas un pull ni un rebase automático sin decirlo primero.
