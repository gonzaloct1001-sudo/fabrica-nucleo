# Modelos por rol

Cada rol usa el modelo menos costoso que hace bien su trabajo. Los niveles son genéricos; cada instancia define en
`.fabrica/config.json` qué modelo concreto corresponde a cada uno, y los actualiza cuando salen modelos nuevos.

| Nivel | Para qué |
|---|---|
| **Alto** | Diseño, arquitectura, seguridad, especificación y revisión final de una rama |
| **Medio** | Implementación con criterio, integración entre archivos, revisión por tarea, QA y diseño de experiencia |
| **Bajo** | Tareas mecánicas: una tarea de uno o dos archivos cuyo plan ya trae el código, formatos y actualización de estado |

## Asignación por rol

| Rol | Nivel | Esfuerzo | Notas |
|---|---|---|---|
| Coordinador (sesión principal) | Medio | Medio | Coordina; delega lo difícil |
| `analista` | Alto | Medio | Una mala especificación cuesta más que cualquier modelo |
| `arquitecto` | Alto | Alto | |
| `seguridad` | Alto | Alto | |
| `desarrollador` | Medio | Medio | Bajo si el plan trae el código y toca uno o dos archivos; un nivel más en las rondas 4 y 5 de corrección |
| `revisor` (por tarea) | Medio | Medio | El nivel medio es el mínimo para revisar |
| `revisor` (final de rama) | Alto | Alto | |
| `qa` | Medio | Medio | |
| `disenador` | Medio | Medio | |
| `operaciones` | Medio | Medio | |
| `cuentas` | Medio | Medio | |
| `documentador` | Bajo | Bajo | |

## Cómo se aplica en el asistente

Cada agente del kit (`kit/.claude/agents/`) declara en su encabezado el modelo de su nivel por defecto, como alias de
familia: `opus` para el nivel alto, `sonnet` para el medio y `haiku` para el bajo. Cada alias apunta siempre al modelo
más nuevo de su familia, así que el kit no necesita cambios cuando sale un modelo nuevo. Al delegar, el coordinador
declara el modelo según esta tabla, y lo sube un nivel cuando corresponde (rondas 4 y 5 de corrección, revisión final
de la rama).

## Reglas

- **Siempre se declara el modelo al delegar.** Un subagente sin modelo declarado hereda el de la sesión, que suele ser
  el más caro, y eso anula toda esta tabla.
- **Los turnos pesan más que el precio.** Un modelo barato tarda dos o tres veces más turnos en un trabajo de varios
  pasos y termina costando más. Por eso el nivel bajo se reserva para tareas realmente mecánicas.
- **Un nivel más cuando algo se atasca.** Si una tarea no converge después de tres rondas, la toma un modelo de nivel
  superior con contexto limpio.
- **El esfuerzo también cuesta.** El esfuerzo máximo se usa solo en arquitectura, seguridad o un error difícil, nunca
  como valor por defecto.
- **El consumo se mide antes de cambiar de plan.** Primero se mide el uso real durante dos semanas.
