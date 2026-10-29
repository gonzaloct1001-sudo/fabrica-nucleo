# Plan: <título de la historia>

**Historia:** `<ruta a la historia>` — el plan argumenta desde ella; si se contradicen, manda la historia.
**Objetivo:** <una oración con lo que construye>.
**Enfoque:** <dos o tres oraciones sobre cómo>.
**Tecnología:** <piezas clave>.

> Un plan es el conjunto de decisiones que quien implementa no puede tomar solo. Si el plan es más largo que el código
> que describe, se escribió el código en vez de planificar. Si una línea no decide nada ("manejar errores", "agregar
> validaciones", "pendiente"), falta una decisión.

## Restricciones globales

Requisitos de la historia o de la constitución del proyecto que rigen todas las tareas, uno por línea y con sus
valores exactos.

- <ejemplo: "Toda consulta filtra por empresaId">

## Riesgos a vigilar

Las entradas o fallas que la historia implica y que ninguna tarea prueba todavía. Van las más probables primero, y
cada una con la prueba que la cubre en su tarea.

- <entrada o condición> → <comportamiento esperado> (prueba en la tarea N)

## Complejidad justificada

| Qué se agrega | Por qué hace falta | Alternativa simple descartada y por qué |
|---|---|---|
| | | |

(Vacía si no hay nada que justificar.)

## Archivos

| Archivo | Crear o modificar | Responsabilidad |
|---|---|---|
| | | |

---

### Tarea 1: <componente>

**Archivos:** crear `ruta/exacta`, modificar `ruta/exacta:líneas`, prueba en `pruebas/ruta/exacta`.

**Interfaces:**
- **Usa:** <lo que necesita de tareas anteriores, con firma exacta>
- **Entrega:** <lo que tareas siguientes usarán: nombres, parámetros y tipos>

- [ ] **Paso 1. Escribir la prueba que falla.** <nombre de la prueba y sus aserciones, con los valores exactos de la
  historia>
- [ ] **Paso 2. Comprobar que falla.** Comando: `<comando>`. Resultado esperado: FALLA con "<mensaje>".
- [ ] **Paso 3. Implementar.** `<firma exacta>` en `<archivo>`. <Una línea sobre el enfoque, solo si la firma y la
  prueba dejan una elección abierta.>
- [ ] **Paso 4. Comprobar que pasa.** Comando: `<comando>`. Resultado esperado: PASA.
- [ ] **Paso 5. Commit.** `<tipo>: <descripción>`

### Tarea 2: …

---

## Registro

La fábrica completa esta sección mientras trabaja. Sobrevive a la compactación del contexto: ante una duda sobre
dónde quedó la corrida, manda este registro junto con el historial de git, no la memoria del agente.

```
Tarea 1: completa (commits a1b2c3d..e4f5a6b, revisión limpia)
Tarea 2: ronda de corrección 1/5 (1 resuelto, 0 abiertos)
Tarea 2: menor diferido: <descripción breve>
Decisión: <qué se decidió> — <por qué> — <qué cuesta si es errada>
```
