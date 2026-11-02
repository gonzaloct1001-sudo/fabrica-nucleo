---
name: recoger-aprendizajes
description: Recoge los aprendizajes que dejaron los proyectos de la instancia (docs/aprendizajes.md de cada uno), revisa que estén limpios y, con la decisión de la Dirección, los incorpora a la base del rubro o los propone al núcleo. Úsala cuando un proyecto cierra una épica, o cada cierto tiempo, para que la fábrica aprenda.
---

# Recoger aprendizajes

El camino completo está en `nucleo/aprendizaje.md`. Aquí se hace el paso de la instancia: de cada proyecto se lee
solo `docs/aprendizajes.md`, nunca otra cosa (`nucleo/aislamiento.md`).

## Pasos

1. **Lista los nuevos:** `python .fabrica/scripts/recoger_aprendizajes.py`. Si no hay, dilo y termina.
2. **Propón una decisión por cada uno,** con tu recomendación:
   - **rubro:** en qué sección de `rubros/<rubro>/conocimiento.md` entra y con qué texto exacto. Si la regla ya estaba,
     sube su cuenta de "Confirmada en".
   - **metodo:** qué cambiaría en el núcleo y por qué.
   - **descartado:** si en realidad es propio del proyecto, si no se puede limpiar o si no aporta.
3. **Resuelve primero cada aviso de limpieza:** reescribe el texto sin el dato o descarta el aprendizaje. Nada con
   datos de un cliente entra a la base del rubro, porque llega a todos los proyectos del rubro, de cualquier cliente.
4. **Con la decisión de la Dirección:**
   - **rubro:** edita la base del rubro.
   - **metodo:** si esta instancia también mantiene el núcleo, prepara el cambio como un PR pequeño en el repositorio
     del núcleo. Si no, redacta el issue para el núcleo y entrégalo a la Dirección, que decide si lo publica.
   - **En todos los casos,** anota la decisión para no recogerlo de nuevo:
     `python .fabrica/scripts/recoger_aprendizajes.py --registrar <repositorio>:<A-NNN> --decision <rubro|metodo|descartado> --nota "<destino o motivo>"`.
5. **Haz un commit en la instancia** con la base del rubro y el registro.

## Lo que devuelves

- una tabla con cada aprendizaje, su proyecto, la decisión y su destino;
- qué proyectos reciben la base del rubro con su siguiente actualización del kit (`actualizar_kit.py`).
