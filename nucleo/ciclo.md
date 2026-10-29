# Ciclo de vida de un pedido

Todo lo que entra a la fábrica recorre este ciclo. No todo pedido pasa por todas las etapas: el triage decide cuánto
proceso necesita. Lo que nunca se salta es una compuerta: si algo llega a una etapa sin cumplir la anterior, se
devuelve.

```
Entrada → Triage → (Descubrir) → Especificar → (Decidir) → Planificar → Analizar
        → Construir → Revisar → Verificar → Entregar → Aprender
```

Las etapas entre paréntesis se usan solo cuando hacen falta.

## Triage: cuánto proceso necesita

Al entrar, cada pedido recibe una **ruta** y un **riesgo**.

| Ruta | Cuándo | Qué recorre |
|---|---|---|
| **Directa** | Cambio obvio y de bajo riesgo (un texto, un estilo, una configuración). | Construir → Verificar → Entregar |
| **Una sesión** | Cambio claro que se puede entender, construir y revisar de una vez. | Especificar (breve) → Planificar → Construir → Revisar → Verificar → Entregar |
| **Completa** | Iniciativa grande, ambigua o que toca varias partes. | Todo el ciclo, en tres niveles: iniciativa → épicas → historias |

| Riesgo | Señales | Efecto |
|---|---|---|
| **Bajo** | No toca dinero, datos personales, permisos ni contratos entre módulos. | Revisión rápida |
| **Medio** | Toca lógica de negocio o varios archivos con dependencias entre sí. | Revisión rápida, más QA |
| **Alto** | Toca dinero, stock, datos personales, seguridad o un contrato público. | Revisión exhaustiva, más QA y seguridad |

> El tamaño decide cuántas sesiones necesita el trabajo; el riesgo decide cuánto se planifica y se revisa.

Si hay riesgo, requisitos poco claros, alcance sobre la arquitectura o varias personas involucradas, el pedido sube
de ruta aunque sea pequeño.

## Etapas

| Etapa | Quién | Entra | Sale | Compuerta para seguir | Decide la Dirección |
|---|---|---|---|---|---|
| **Descubrir** | analista | Conocimiento en la cabeza de alguien | Notas de descubrimiento del dominio | Los temas del guion están cubiertos o tienen dueño | Qué es verdad y qué falta preguntar |
| **Especificar** | analista | Descubrimiento o pedido | Historia (`plantillas/historia.md`) | Definition of Ready | Si la historia describe la operación real |
| **Decidir** | arquitecto | Historia que implica estructura nueva o integración externa | ADR (`plantillas/adr.md`) | Tres opciones evaluadas, con costo de operar y de salir | La opción, si implica gasto mensual |
| **Planificar** | arquitecto o desarrollador | Historia lista y ADR si aplica | Plan (`plantillas/plan.md`) | Cada paso permite hacer una sola cosa razonable | Nada |
| **Analizar** | revisor | Historia, plan y tareas | Informe de consistencia, sin cambios | Sin contradicciones ni requisitos sin tarea | Nada |
| **Construir** | desarrollador | Plan analizado | Código, pruebas y commits | Primero una prueba que falla; todas en verde al final | Nada (si pregunta algo de negocio, la especificación quedó mal) |
| **Revisar** | revisor | Diff de cada tarea | Dos veredictos: cumplimiento y calidad | Sin hallazgos críticos ni importantes abiertos | Nada |
| **Verificar** | qa y seguridad | Rama completa | Matriz de casos y veredicto de seguridad | Definition of Done | Si el comportamiento es el que espera la operación |
| **Entregar** | coordinador | Rama verificada | PR con vista previa | Controles de GitHub en verde | El merge, según el nivel de autonomía |
| **Aprender** | documentador | Historia o épica cerrada | Estado, bitácora y retrospectiva | Aprendizajes separados entre proyecto y núcleo | Qué mejora pasa al núcleo |

## Estados

Cada historia lleva un estado, visible como etiqueta en GitHub Issues.

```
borrador → listo → en-curso → en-revision → construido → hecho
                       ↘ bloqueado (con motivo)
```

- **borrador:** especificación en curso o con `[ACLARAR]` abiertos.
- **listo:** cumple la Definition of Ready. Puede entrar a construcción.
- **en-curso:** una corrida la está construyendo. Solo una por proyecto a la vez.
- **en-revision:** construida; pasa por revisión y verificación.
- **construido:** PR abierto con todos los controles en verde. Espera a la Dirección.
- **hecho:** integrada. **Solo una persona marca "hecho".**
- **bloqueado:** detenida. El motivo sale de esta lista:
  - `falta-regla-de-negocio` (además lleva `espera:direccion`);
  - `intencion-poco-clara`;
  - `verificacion-fallida`;
  - `tope-de-correcciones`;
  - `arbol-de-trabajo-sucio`;
  - `dependencia-pendiente`.

Si la corrida se detiene por intención poco clara, guarda su intento como parche junto al plan y deja el código como
estaba. La Dirección decide si lo aplica.

## Definition of Ready (para entrar a construcción)

- [ ] Historia con criterios de aceptación en formato Dado / Cuando / Entonces.
- [ ] Reglas de negocio explícitas y sin `[ACLARAR]` abiertos.
- [ ] Fuera de alcance declarado.
- [ ] Datos personales identificados y declarados.
- [ ] Riesgo asignado (bajo, medio o alto).
- [ ] Dependencias resueltas o declaradas.
- [ ] Pruebas de aceptación aprobadas por la Dirección cuando el riesgo es alto.

## Definition of Done (para cerrar)

- [ ] Todas las pruebas en verde en la CI, con la salida a la vista.
- [ ] Cobertura del dominio tocado de al menos 80 %.
- [ ] Revisión sin hallazgos críticos ni importantes abiertos.
- [ ] Veredicto de seguridad aprobado cuando el riesgo es medio o alto.
- [ ] Contratos (API) y documentación al día.
- [ ] Registro de decisiones entregado en el resumen.
- [ ] `estado.json` del proyecto actualizado.
- [ ] Demo posible en la vista previa o en staging.

## Regla del ciclo corto

Una historia termina su recorrido antes de que otra entre a construcción en el mismo proyecto. Tres historias a medio
hacer valen cero; una terminada vale una. Mientras una se construye, la siguiente sí puede especificarse.

## Cuando algo se atasca

- Si el agente pide la misma decisión tres veces, falta un ADR o falta descubrimiento. Hay que volver a esa etapa, no
  seguir parchando.
- Si una tercera revisión sigue encontrando problemas reales, la falla está en la especificación o en las reglas del
  proyecto, no en el código.
