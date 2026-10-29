---
name: nuevo-proyecto
description: Crea un proyecto para un cliente registrado, como un repositorio propio con el kit de la fábrica (agentes, skills, CI que protege las pruebas aprobadas y una copia del método). Úsala cuando la Dirección quiere empezar un trabajo nuevo para un cliente o para la propia fábrica.
---

# Nuevo proyecto

1. **Revisa que el cliente exista** en `clientes/`. Si no existe, usa primero la skill `nuevo-cliente`.
2. **Reúne los datos:**
   - el **negocio** del cliente al que pertenece;
   - el **identificador corto** del proyecto (propónlo tú);
   - el **nombre** legible;
   - una línea sobre **qué se quiere lograr.**
3. **Ejecuta:**

   ```
   python .fabrica/scripts/nuevo_proyecto.py --cliente <cliente> --negocio <negocio> --proyecto <slug> --nombre "<Nombre>"
   ```

   Se crea `proyectos/<cliente>-<proyecto>/` con su repositorio Git y su primer commit.
4. **GitHub.** Pregúntale a la Dirección si se crea ya el repositorio privado. Es una acción hacia afuera, así que
   necesita su sí explícito. Con ese sí, repite con `--github`: se crea el repositorio y sus etiquetas.
5. **Haz commit** de la ficha del cliente en la instancia, que ahora lista el proyecto.
6. **Deja anotado el primer pedido.** La línea de "qué se quiere lograr" se escribe como issue (o como nota en
   `docs/historias/`), lista para que el coordinador del proyecto haga el `triage` al abrirlo.

## Lo que devuelves

- la ruta del proyecto y el enlace del repositorio, si se creó;
- el siguiente paso: abrir el proyecto con el asistente.
