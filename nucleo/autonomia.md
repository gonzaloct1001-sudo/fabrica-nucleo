# Contrato de autonomía

Este contrato define cuánto puede hacer la fábrica sin la Dirección. La idea central es una sola: **la fábrica no se
queda esperando**. Decide lo que le toca, lo registra y sigue, y solo se detiene ante lo que de verdad necesita a una
persona.

## Las tres listas

| La fábrica decide sola | Decide y avisa en el resumen diario | Nunca sin la Dirección |
|---|---|---|
| Nombres, estructura de archivos y división en tareas | Cambios de alcance técnico dentro de una historia | Reglas de negocio: dinero, stock, precios, plazos, permisos |
| Elección entre alternativas técnicas equivalentes | Hallazgos que quedaron estacionados al llegar al tope de correcciones | Qué se le promete o se le cobra a un cliente |
| Cómo corregir un hallazgo de revisión | Deuda técnica detectada y no corregida | Proveedores externos con costo mensual |
| Qué pruebas agregar más allá de las aprobadas | Uso del plan sobre lo habitual | Pasar a producción |
| Cuándo pedir una revisión adicional | | Agregar una dependencia nueva al producto |
| | | Tratar datos personales nuevos |
| | | Cambiar la constitución, un ADR vigente o las pruebas de aceptación aprobadas |
| | | Cualquier acción irreversible o destructiva |

## Cuándo se detiene una corrida

Una corrida solo se detiene por uno de estos cinco motivos:

1. **Irreversible o destructivo:** borrar datos, reescribir el historial, eliminar recursos.
2. **Sensible para la seguridad:** credenciales, permisos, datos personales, exposición a internet.
3. **Efecto fuera de su espacio:** hacer un merge, subir a una rama compartida, publicar o desplegar.
4. **Plan roto:** el plan está tan mal que cualquier camino sería adivinar.
5. **Falta una regla de negocio:** según el artículo IV de la constitución.

Ante los motivos 1 a 4, la corrida se detiene y lo explica. Ante el motivo 5, solo se detiene esa historia: queda en
`espera:direccion` con la pregunta escrita, y la fábrica sigue con otra.

Todo lo demás (ambigüedades técnicas, contradicciones menores del plan, un tope que convendría superar) se decide.

## Registro de decisiones

Cada decisión que la fábrica toma por su cuenta queda en el registro del plan, en una línea con este formato:

```
Decisión: <qué se decidió> — <por qué> — <qué cuesta si es errada>
```

Al cerrar una historia, la lista completa pasa al resumen diario, bajo **"Decisiones que tomé por ti"**. Es el único
lugar donde la Dirección ve lo que se decidió en su nombre, así que no se resume ni se omite ninguna.

## Niveles de autonomía

La autonomía se gana con evidencia, no se regala. Cada instancia fija su nivel en `.fabrica/config.json` y lo sube
solo cuando el examen de la fábrica (`aprendizaje.md`) lo respalda.

| Nivel | Qué hace la fábrica sola | Para subir al siguiente |
|---|---|---|
| **1 · Propone** | Construye, abre el PR y pregunta quién lo integra. Por defecto lo integra la Dirección. | 4 semanas sin defectos críticos escapados y al menos 70 % de historias sin intervención |
| **2 · Integra lo de bajo riesgo** | Integra sin preguntar los PRs de riesgo bajo con todos los controles en verde; los demás, como en el nivel 1. | 8 semanas en nivel 2 sin revertir un merge automático |
| **3 · Especifica** | Además, convierte notas y entrevistas en historias. La Dirección solo confirma que describen la operación real. | No hay nivel superior |

En todos los niveles, **producción es siempre una decisión de la Dirección**.

Los umbrales son el punto de partida; cada instancia los ajusta en su configuración.

## Quién integra cada PR

Integrar un PR es un efecto fuera del espacio de la fábrica (motivo 3), así que nunca ocurre en silencio.

- **Cada vez que un PR queda listo, la fábrica pregunta:** "¿Lo integro yo o lo integras tú?". Si la Dirección está
  en la conversación, la pregunta va ahí. Si no, va en el resumen diario y como comentario en el PR.
- **Por defecto, integra la Dirección.** Si no hay respuesta, el PR queda esperando: la fábrica nunca integra por
  omisión.
- **Una respuesta "intégralo" autoriza ese PR, y solo ese.** Si llega como comentario en el PR, la fábrica comprueba
  que lo escribió la cuenta de la Dirección: la dueña del repositorio, o la que indique el campo `direccion` de
  `.fabrica/proyecto.json`.
- **Antes de integrar,** la fábrica vuelve a comprobar que todos los controles estén en verde y que la rama esté al
  día con `main`.
- **En el nivel 2,** los PRs de riesgo bajo con todos los controles en verde se integran sin preguntar. Los demás
  siguen esta regla.

## Topes

| Tope | Valor por defecto | Al alcanzarlo |
|---|---|---|
| Rondas de corrección por tarea | 5 | El coordinador decide y registra (`calidad.md`) |
| Tamaño de un PR | ~400 líneas útiles | Se divide en PRs más pequeños |
| Historias en construcción a la vez por proyecto | 1 | Las demás esperan; sí se puede especificar en paralelo |
| Uso del plan | El que fije la instancia | La fábrica se pausa sola y lo informa |

## Interruptor

Con `"pausa": true` en `.fabrica/config.json`, la pausa rige para toda la instancia. Con `"pausa": true` en
`.fabrica/proyecto.json`, rige solo para ese proyecto. En ambos casos, ninguna corrida inicia trabajo nuevo. Las que estaban en curso terminan su paso actual, registran dónde quedaron y se
detienen.

## Resumen diario

Cada día la Dirección recibe un resumen corto, pensado para leerse en el celular en unos 15 minutos. Tiene cinco
partes:

1. **Para revisar:** PRs listos, cada uno con su enlace a la vista previa y su nivel de riesgo.
2. **Esperan tu decisión:** preguntas de negocio agrupadas por proyecto, cada una con su enlace.
3. **Decisiones que tomé por ti:** la lista completa del día.
4. **Bloqueos:** qué se detuvo y por qué.
5. **Uso:** consumo del plan respecto del tope.
