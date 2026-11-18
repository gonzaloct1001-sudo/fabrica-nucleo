# Catálogo de parámetros de <proyecto>

Las reglas de negocio que pueden variar de un cliente a otro, modeladas como parámetros (constitución de la fábrica,
art. IV, y el principio opcional "lo desconocido se vuelve configurable"). La Dirección aprueba este catálogo antes de
usar datos reales.

| Parámetro | Valores posibles | Por defecto | Estado | Nació en | Prueba |
|---|---|---|---|---|---|
| `<modulo.parametro>` | `<a>` · `<b>` | `<a>` | propuesto | H-NNN | `<ruta de la prueba>` |

- **Estado:** `propuesto` (sirve para construir y probar con datos sintéticos) o `confirmado` (la Dirección lo aprobó,
  con su fecha).
- **Valores:** de 2 a 4. Cada uno tiene su prueba.
- **Por defecto:** el comportamiento más simple o el que ya existe.
