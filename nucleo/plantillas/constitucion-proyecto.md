# Constitución de <proyecto>

**Versión:** 1.0.0 · **Vigente desde:** <AAAA-MM-DD> · **Sigue la constitución de la fábrica:** v1.0.0

Este proyecto cumple la constitución de la fábrica completa. Esta página agrega los principios propios del proyecto;
nunca relaja los de la fábrica.

## Qué construimos

<Una o dos oraciones: el producto, para quién, y el modelo (producto propio, encargo a medida o plataforma para varios
clientes).>

## Principios propios

### P-1. <nombre>

<La regla, en una o dos oraciones verificables.>
*Por qué:* <qué evita o qué asegura.>

### P-2. <nombre>

…

Ejemplos de principios que suelen ir aquí:
- **Multi-empresa desde el día 1:** toda consulta filtra por la empresa.
- **Contrato primero:** la API se define antes de implementarla.
- **Funciona sin conexión:** la aplicación de terreno trabaja sin red.
- **Migraciones reversibles,** siempre.

## Principios opcionales de la fábrica

Se adoptan copiándolos a "Principios propios" con su número. Si no se copian, no rigen.

### Lo desconocido se vuelve configurable

Cuando falta una regla de negocio que puede variar de un cliente a otro, la historia no se detiene. La regla se
modela como un parámetro con un valor por defecto, se anota en el catálogo (`docs/catalogo-parametros.md`, desde
`.fabrica/nucleo/plantillas/catalogo-parametros.md`) y se construye. La Dirección aprueba el catálogo, no cada
pregunta (constitución de la fábrica, art. IV).
- **Siguen siendo pregunta a la Dirección, sin excepción:** lo que es ley o norma, el dinero (qué se cobra y cuánto),
  lo que se le promete al cliente final y todo dato personal nuevo.
- **Un parámetro nace solo cuando una historia toca ese comportamiento.** Tiene de 2 a 4 valores, su valor por
  defecto es el comportamiento más simple o el que ya existe, y cada valor tiene su prueba.
- **Un valor que la Dirección todavía no confirma lleva la marca `propuesto`.** Sirve para construir y probar con
  datos sintéticos; ninguno llega a datos reales sin confirmarse.

*Por qué:* la información completa nunca llega antes de construir. Esperar cada respuesta frena más que corregir un
valor por defecto, que se cambia sin tocar el código.

## Stack

Lo decidido en el ADR-0001. No se cambia sin un ADR nuevo.

## Convenciones

- **Commits:** <formato, por ejemplo Conventional Commits en español>.
- **Ramas:** `<tipo>/H-NNN-descripcion`.
- **Idioma:** el dominio se nombra en <idioma del negocio> y la infraestructura en <idioma técnico>.

## Glosario

Términos con un significado preciso en este proyecto: `<ruta al glosario>`.

## Decisiones reservadas a la Dirección en este proyecto

Además de las de `autonomia.md`:
- <por ejemplo: cualquier cambio en cómo se calcula un precio>

## Autonomía en este proyecto

Por defecto, la Dirección integra, aprueba las pruebas de aceptación y marca las historias como hechas
(`.fabrica/nucleo/autonomia.md`). Si delega alguna de esas decisiones, lo escribe aquí, con su fecha y sus palabras, y
la fábrica la registra en `autonomia` de `.fabrica/proyecto.json` ("Delegación por proyecto"):

- <por ejemplo: «La fábrica integra sola los PRs que cumplen las condiciones de la delegación» · decidido el AAAA-MM-DD>

## Gobierno

Igual que la constitución de la fábrica: solo la Dirección la modifica, cada cambio sube la versión y el cambio queda
explicado.
