---
name: nuevo-cliente
description: Registra un cliente nuevo en la instancia de la fábrica (empresa, holding con varios negocios, persona o propio). Úsala cuando la Dirección menciona un cliente que todavía no está en clientes/, antes de crear su primer proyecto.
---

# Nuevo cliente

1. **Reúne los datos.** Pregúntale a la Dirección solo lo que falte, en una sola tanda:
   - **nombre** del cliente;
   - **identificador corto** (propónlo tú: minúsculas y guiones);
   - **tipo:** empresa, holding, persona o propio;
   - **negocios:** por cada uno, un identificador, el rubro y una descripción breve. Un holding tiene varios;
   - **si exige reserva estricta.**
2. **Si exige reserva estricta, no lo registres aquí.** Recomienda una instancia separada de la fábrica para ese
   cliente (`nucleo/aislamiento.md`) y detente.
3. **Ejecuta:**

   ```
   python .fabrica/scripts/nuevo_cliente.py --id <slug> --nombre "<Nombre>" --tipo <tipo> \
       --negocio "<slug>:<rubro>:<descripción>" [--negocio ...]
   ```

4. **Completa la ficha** `clientes/<id>/cliente.md` con la contraparte y los acuerdos que la Dirección te dé. Los datos
   de contacto no van al repositorio.
5. **Haz commit** de la ficha en la instancia, con el mensaje `Registra el cliente <id>`.

## Lo que devuelves

Una línea con la ficha creada, y la pregunta de si se crea ya su primer proyecto (skill `nuevo-proyecto`).
