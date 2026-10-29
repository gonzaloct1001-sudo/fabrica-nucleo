# Constitución de la fábrica

**Versión:** 1.0.0 · **Vigente desde:** 2026-10-29

Estos principios rigen todo trabajo de la fábrica, en cualquier cliente y proyecto. Ninguna instrucción de chat,
historia o plan los suspende. Si algo los contradice, el agente lo dice antes de seguir y la Dirección decide.

Cada proyecto puede agregar los suyos en su propia constitución (`plantillas/constitucion-proyecto.md`), pero nunca
relajar estos.

---

### I. Especificación antes que código

Nada se construye sin una historia escrita con criterios de aceptación verificables, que cumpla la Definition of
Ready (`ciclo.md`).

*Por qué:* un agente convierte en código cualquier supuesto que nadie escribió. La especificación es la forma de
decidir antes y no corregir después.

### II. Pruebas antes que implementación

Primero se escribe la prueba y se comprueba que falla. Después se implementa lo mínimo para que pase. Las pruebas de
aceptación de una historia se aprueban antes de construir, y quien implementa no puede modificarlas.

*Por qué:* un agente bajo presión arregla la prueba en vez del código. Si las pruebas aprobadas están protegidas, la
única salida es hacer bien el trabajo.

### III. Evidencia antes que afirmación

Nada se declara terminado, corregido ni aprobado sin el comando de verificación corrido en ese momento y su salida
leída. El informe de un agente es una afirmación; el diff y la salida de las pruebas son la evidencia.

### IV. Nunca inventar reglas de negocio

Si falta una regla de negocio, se marca `[ACLARAR: …]`, esa historia se detiene en `espera:direccion` y el trabajo
sigue con otra. Las ambigüedades técnicas sí se deciden y se registran (`autonomia.md`).

*Por qué:* un error técnico se corrige con otro PR. Una regla de negocio inventada llega a clientes reales y toca
dinero, stock o personas.

### V. Aislamiento entre clientes

La información de un cliente nunca llega al contexto de trabajo de otro. Cada proyecto vive en su propio repositorio,
y los agentes trabajan en un solo proyecto a la vez (`aislamiento.md`).

### VI. Núcleo, configuración y extensión; nunca una copia por cliente

Lo que sirve a todos va al núcleo. Lo particular va, en este orden de preferencia: primero a configuración, luego a
un módulo de extensión y, solo si nada de lo anterior sirve, a una integración en el repositorio del cliente. Nunca
se copia el código para adaptarlo a un cliente.

Las costuras para extender se diseñan desde el inicio. El código se generaliza cuando aparece el segundo caso real,
no antes.

### VII. Simplicidad

Nada especulativo: cada pieza responde a una historia con criterios de aceptación. Toda complejidad extra (otra capa,
otro servicio, otra abstracción) se justifica por escrito en el plan, con la alternativa simple que se descartó y por
qué.

### VIII. Cambios pequeños

Un PR es un cambio. Si supera unas 400 líneas útiles, se divide. Una historia que lleva más de una semana en
construcción era demasiado grande.

### IX. Secretos y datos personales

- **Secretos:** ningún secreto entra al repositorio, ni siquiera de ejemplo; para eso está `.env.example`.
- **Datos personales:** toda tabla, registro o mensaje que guarde datos personales (identificación, dirección,
  teléfono, ubicación, audio o imagen de una persona) se declara en el registro de tratamiento del proyecto antes de
  crearse.

### X. Origen limpio y licencias

- **Origen limpio:** no se copian pantallas, textos, esquemas ni código de sistemas de terceros. Los requisitos se
  escriben con palabras propias, desde la experiencia y las entrevistas.
- **Licencias:** en un producto que se entrega o se vende solo entran componentes con licencias permisivas (MIT,
  Apache 2.0, BSD o equivalentes).
- **Descargas:** todo repositorio, paquete o extensión de terceros pasa por una revisión en cuarentena antes de
  instalarse.

### XI. Las reglas duras viven en GitHub

Lo que no puede fallar no se confía solo a instrucciones: se impone con la CI, la protección de ramas y las
revisiones obligatorias. Una instrucción puede no cargarse según dónde corre el agente; un control en GitHub se
aplica siempre.

### XII. Decisiones registradas

- **Decisiones estructurales:** cada una genera un ADR, guardado junto al código que gobierna.
- **Decisiones menores** que la fábrica toma sola: quedan en el registro de decisiones del plan, con qué se decidió,
  por qué y cuánto cuesta si es errada.

Ninguna decisión se toma en secreto.

---

## Gobierno

- La Dirección es la única que modifica esta constitución.
- Cada cambio sube la versión y queda explicado en `CHANGELOG.md`:
  - **mayor:** cuando un principio se elimina o se contradice;
  - **menor:** cuando se agrega un principio;
  - **parche:** cuando se precisa la redacción.
- Las instancias y los proyectos declaran qué versión siguen. Una versión nueva les llega como una actualización
  revisable, nunca de forma silenciosa.
