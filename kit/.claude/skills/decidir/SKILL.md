---
name: decidir
description: Toma y registra una decisión estructural como ADR (stack, hosting, integración externa, contrato entre módulos, separación entre núcleo y extensión). Úsala cuando una historia implica estructura nueva, cuando se va a elegir un proveedor, o cuando la misma duda técnica apareció tres veces.
---

# Decidir

## Cuándo

- Hay que elegir algo que después cuesta cambiar: el stack, la base de datos, el hosting, un proveedor o la forma de
  integrar un sistema externo.
- Varias partes construidas por separado tienen que coincidir: un contrato, un formato o una convención.
- El agente pidió la misma decisión tres veces. Eso significa que falta un ADR.

## Pasos

1. El `arquitecto` (nivel alto) escribe `docs/adr/ADR-NNNN-<slug>.md` desde `.fabrica/nucleo/plantillas/adr.md`, con
   tres opciones. Una de ellas es la más simple posible. Cada opción lleva su costo de operar y su costo de salir.
2. **Quién decide:**
   - **La Dirección,** si la decisión implica costo mensual, un proveedor nuevo, datos personales o el reemplazo de
     un ADR vigente. El ADR queda en `propuesta`, el issue con `espera:direccion` y la recomendación en una línea.
   - **El arquitecto,** en cualquier otro caso. El ADR pasa a `aceptada` y la decisión se anota en el registro.
3. Si la decisión fija un principio del proyecto (por ejemplo, "toda consulta filtra por la empresa"), el arquitecto
   propone agregarlo a `docs/constitucion.md`. Ese cambio lo aprueba la Dirección.

## Lo que devuelves

Una línea: el ADR, la opción elegida o recomendada, y quién decide.
