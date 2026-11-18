# Principios opcionales de la fábrica

Principios ya escritos que un proyecto puede adoptar. Se copian a "Principios propios" de su constitución,
con su número, y la Dirección lo decide. Si no se copian, no rigen.

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
