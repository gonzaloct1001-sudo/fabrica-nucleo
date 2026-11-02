---
name: nuevo-cliente
description: Registra un cliente nuevo en la instancia de la fábrica (empresa, holding con varios negocios, persona o propio), o le suma un negocio a uno que ya existe. Úsala cuando la Dirección menciona un cliente que todavía no está en clientes/, o un negocio nuevo de un cliente, antes de crear su proyecto.
---

# Nuevo cliente

1. **Reúne los datos.** Pregúntale a la Dirección solo lo que falte, en una sola tanda:
   - **nombre** del cliente;
   - **identificador corto** (propónlo tú: minúsculas y guiones);
   - **tipo:** empresa, holding, persona o propio;
   - **negocios:** por cada uno, un identificador, el rubro y una descripción breve. Un holding tiene varios. El rubro
     también es un identificador (por ejemplo, `gas-licuado`); usa el mismo de los clientes anteriores del rubro, para
     que compartan su base (`rubros/`);
   - **si exige reserva estricta.**
2. **Si exige reserva estricta, no lo registres aquí.** Recomienda una instancia separada de la fábrica para ese
   cliente (`nucleo/aislamiento.md`) y detente.
3. **Ejecuta:**

   ```
   python .fabrica/scripts/nuevo_cliente.py --id <slug> --nombre "<Nombre>" --tipo <tipo> \
       --negocio "<slug>:<rubro>:<descripción>" [--negocio ...]
   ```

   Si el cliente ya existe y solo suma un negocio:

   ```
   python .fabrica/scripts/nuevo_cliente.py --id <slug> --agregar --negocio "<slug>:<rubro>:<descripción>"
   ```

   Con un rubro nuevo, se crea su base en `rubros/<rubro>/conocimiento.md`: complétala con lo que la Dirección sepa.
4. **Completa la ficha** `clientes/<id>/cliente.md` con la contraparte y los acuerdos que la Dirección te dé. Los datos
   de contacto no van al repositorio.
5. **Haz commit** de la ficha y de la base del rubro, si es nueva, en la instancia, con el mensaje
   `Registra el cliente <id>` o `Suma el negocio <slug> a <id>`.

## Lo que devuelves

Una línea con la ficha creada, y la pregunta de si se crea ya su primer proyecto (skill `nuevo-proyecto`).
