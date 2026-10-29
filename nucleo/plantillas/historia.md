---
id: H-000
titulo: <verbo + resultado, en palabras del usuario>
estado: borrador          # borrador | listo | en-curso | en-revision | construido | hecho | bloqueado
prioridad: P1             # P1 la más importante
riesgo: bajo              # bajo | medio | alto (ver ciclo.md)
ruta: una-sesion          # directa | una-sesion | completa
epica: <id o "ninguna">
fuentes: []               # de dónde salen los requisitos: entrevista, nota o documento del cliente
---

# <Título de la historia>

## Para qué

Como **<rol de quien la usa>**, quiero **<qué>**, para **<resultado que le importa>**.

**Por qué esta prioridad:** <qué valor entrega y por qué va antes o después de otras>.

**Prueba independiente:** <cómo se demuestra esta historia sola, sin las demás; si se entregara solo esta, ¿sirve?>

## Criterios de aceptación

1. **Dado** <estado inicial>, **cuando** <acción>, **entonces** <resultado observable>.
2. **Dado** …, **cuando** …, **entonces** ….

## Casos borde

- ¿Qué pasa cuando <límite: cero, vacío, máximo, duplicado>?
- ¿Cómo responde ante <error: sin conexión, dato inválido, permiso faltante>?

## Requisitos

- **R1:** El sistema DEBE <capacidad concreta>. *(fuente: …)*
- **R2:** El sistema DEBE <…>. *(fuente: …)*
- **R3:** El sistema DEBE <…> [ACLARAR: <qué falta decidir y quién lo decide>].

## Reglas de negocio

- <regla explícita, con sus números si los tiene>

## Entidades

- **<Entidad>:** qué representa y sus atributos clave, sin detalles de implementación.

## Datos personales

- <qué dato personal toca y para qué> — declarado en el registro de tratamiento: sí / no
- O bien: "No toca datos personales."

## Fuera de alcance

- <lo que alguien podría suponer incluido y no lo está>

## Criterios de éxito

- **E1:** <métrica medible y sin tecnología, por ejemplo: "un pedido se registra en menos de 30 segundos">

## Supuestos

- <supuesto razonable que se tomó porque el pedido no lo decía>

## Dependencias

- <otra historia, ADR o servicio externo del que depende>
