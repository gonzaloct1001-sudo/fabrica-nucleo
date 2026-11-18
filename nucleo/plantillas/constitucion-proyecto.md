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

Principios opcionales que la fábrica ya tiene escritos (`.fabrica/nucleo/plantillas/principios-opcionales.md`): se
adoptan copiándolos aquí con su número. Si no se copian, no rigen.

Ejemplos de principios que suelen ir aquí:
- **Multi-empresa desde el día 1:** toda consulta filtra por la empresa.
- **Contrato primero:** la API se define antes de implementarla.
- **Funciona sin conexión:** la aplicación de terreno trabaja sin red.
- **Migraciones reversibles,** siempre.

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
