# Notas para las sesiones de trabajo

Lo que la fábrica aprendió trabajando en este repositorio y que no está en otro documento. Toda sesión en vivo, también
una sesión en la nube, lo lee antes de construir. Cada nota dice qué hacer. Lo que sirva a todos los proyectos se
propone al núcleo (`.fabrica/nucleo/aprendizaje.md`).

## Antes de subir un commit

- **Correr en local lo mismo que la CI,** con los comandos exactos de `.github/workflows/`. Sin protección de rama nada
  impide integrar con la CI en rojo: se integra solo con todos los controles en verde, comprobados en ese momento.
- **Un escáner de secretos revisa todos los commits del PR, también los intermedios.** Una clave de prueba que quedó en
  un commit intermedio se marca aunque se corrija después: se arma una rama nueva con un solo commit del árbol final,
  se abre un PR nuevo y se cierra el viejo con un comentario.
- **Un PR con conflictos contra la rama principal no dispara la CI:** se trae la rama principal antes de esperar
  resultados.
- **Si GitHub Actions responde "repository not found" en todos los trabajos,** es una caída de GitHub: se espera y se
  relanza solo lo fallido.

## PRs e integración

- **PRs apilados:** si se integran seguidos, el de arriba queda en su rama base y no llega a la principal. Se integran
  de a uno, el de abajo primero, y después se comprueba con `git merge-base --is-ancestor`.
- **En la nube, `gh pr` y `gh issue` no funcionan** (usan GraphQL): se usa `gh api repos/{dueño}/{repo}/...`.

## Sesión en vivo y rutina programada

- **Para construir en vivo sin que la rutina retome la misma historia,** se agrega al Registro de su plan, en la rama
  principal, la línea "En construcción en una sesión en vivo." La corrida programada elige otro paso mientras exista.
  Al terminar, se reemplaza por el estado real.

## Con la Dirección

- **Todo lo que espera a la Dirección en GitHub** va con su enlace directo y una línea que diga qué botón tocar.
- **La fábrica opera con la cuenta de la Dirección,** y GitHub no le avisa lo que esa cuenta escribe. Lo urgente va en
  el resumen de la sesión, con su enlace.
- **Antes de lanzar agentes opcionales** (investigación, revisiones extra), se dice cuántos son y el orden de su costo.

## Propias de este proyecto

- <nota: qué pasó y qué hacer>
