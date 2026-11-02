# Cómo aprende la fábrica

La fábrica mejora con cada proyecto sin que la información de un cliente llegue a otro. Lo hace con tres
mecanismos: la retrospectiva, la promoción al núcleo y el examen.

## 1. Retrospectiva

Al cerrar cada épica (o cada proyecto en la ruta de una sesión), el `documentador` y el `revisor` hacen una
retrospectiva con `plantillas/retrospectiva.md`:

- **Comparan el resultado con la meta:** qué se pidió, qué se entregó y la diferencia.
- **Buscan duplicación y desvíos** entre historias: código casi repetido, o patrones que divergieron entre sesiones.
  Cada hallazgo se vuelve una historia de refactorización, separada de las funciones nuevas.
- **Revisan qué falló en el proceso:** preguntas que llegaron tarde, decisiones revertidas por la Dirección y
  hallazgos que se repitieron.

## 2. Promoción al núcleo

Cada aprendizaje se clasifica en una de tres categorías:

| Tipo | Ejemplo | Destino |
|---|---|---|
| Propio del proyecto | "El cliente factura por sucursal" | Se queda en el repositorio del proyecto |
| Del dominio o rubro | "Los envases retornables se controlan como activos en préstamo" | La base del rubro, en la instancia: `rubros/<rubro>/conocimiento.md` |
| Del método | "Las historias con más de cinco criterios terminan divididas en revisión" | Propuesta de mejora al núcleo |

Antes de salir del proyecto, todo aprendizaje se **limpia**: sin nombres de personas, clientes, montos, direcciones,
ni ningún detalle que identifique al cliente.

### La base de cada rubro

Es lo que la fábrica sabe de un rubro (gas, farmacia, muebles…), sin datos de ningún cliente: su glosario, sus flujos,
sus reglas frecuentes, las normas que aplican y las preguntas que siempre hay que hacer (`plantillas/rubro.md`).

- **Vive en la instancia,** en `rubros/<rubro>/`, porque nace de sus clientes. El núcleo solo define su forma.
- **Nace con el primer cliente del rubro:** `nuevo_cliente.py` la crea desde la plantilla. Se puede completar desde
  antes con fuentes públicas, como las normas del rubro.
- **Llega a cada proyecto del rubro** en `.fabrica/rubro/`, al crearlo y con cada actualización del kit. Así un
  proyecto nuevo parte sabiendo lo que aprendieron los anteriores, sin ver nada de ellos.
- **Un cliente con reserva estricta** tiene su propia instancia, y lo que se aprende con él se queda en ella.

### El camino de un aprendizaje

1. **En el proyecto.** Al cerrar una épica, la skill `cerrar` escribe los aprendizajes del rubro y del método en
   `docs/aprendizajes.md` (`plantillas/aprendizajes.md`), ya limpios.
2. **En la instancia.** La Dirección los recoge con la skill `recoger-aprendizajes`, que lee solo ese archivo de cada
   proyecto (`aislamiento.md`), revisa por segunda vez que estén limpios y anota cada decisión en
   `instancia/aprendizajes-recogidos.csv`, para no recoger dos veces lo mismo.
   - **Uno del rubro** se incorpora a la base del rubro. Si ya estaba, sube su cuenta de "Confirmada en".
   - **Uno del método** se propone al núcleo como un PR pequeño, con su porqué, o como un issue si quien opera la
     instancia no mantiene el núcleo. La Dirección lo aprueba y el núcleo sube de versión (`CHANGELOG.md`).
3. **De vuelta a los proyectos.** La siguiente actualización del kit (`actualizaciones.md`) lleva a cada proyecto el
   método nuevo y la base de su rubro. Llega como una actualización revisable, nunca de forma silenciosa.

## 3. Examen de la fábrica

Una pieza nueva del núcleo (una skill, un agente o una regla) se da por buena solo después de probarla en casos cuya
respuesta ya se conoce.

- **Banco de casos:** de 5 a 10 historias pequeñas con su resultado correcto y sus pruebas de aceptación ya escritas.
- **Cuándo se rinde:** cada vez que cambia el núcleo, y antes de subir el nivel de autonomía (`autonomia.md`).
- **Qué se mide:**

| Métrica | Qué indica |
|---|---|
| Historias terminadas sin intervención humana (%) | Cuán autónoma es la fábrica de verdad |
| Defectos que encontró la Dirección y no la fábrica | La calidad real de la verificación |
| Decisiones registradas que la Dirección revirtió (%) | El criterio de la fábrica |
| Costo y tiempo por historia | La eficiencia |
| Rondas de corrección por tarea | La calidad de los planes |

## Diagnóstico de sesiones

Cuando una corrida sale mal (repite trabajo, se desvía del plan o gasta de más), se revisa su transcripción con
evidencia línea por línea: dónde se perdió, qué instrucción faltó o sobró, y qué regla lo habría evitado. El resultado
es una propuesta concreta al núcleo, no un reproche.
