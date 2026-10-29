# Áreas de la fábrica

La fábrica se organiza como una consultora de software: cada área tiene una misión, entrega algo concreto y tiene un
rol responsable. Los roles son agentes de IA. La Dirección encabeza la fábrica y conserva las decisiones de
`autonomia.md`.

**Madurez** indica cuánto conocimiento experto tiene hoy cada área en el núcleo:

- **Sólida:** método completo, probado y con plantillas.
- **Base:** método definido y plantillas parciales.
- **Por desarrollar:** existe el rol, pero falta el método.

| Área | Misión | Entrega | Rol | Madurez |
|---|---|---|---|---|
| **Dirección** | Fijar prioridades, aprobar lo que solo una persona puede aprobar y mejorar la fábrica | Panel de seguimiento, resumen diario, retrospectivas | La Dirección, con el apoyo de `documentador` | Base |
| **Comercial y cuentas** | Convertir una necesidad en una propuesta clara, con alcance y precio | Propuesta, alcance, presupuesto y registro del cliente | `cuentas` | Por desarrollar |
| **Producto y análisis** | Entender el dominio y especificar qué construir y en qué orden | Notas de descubrimiento, historias y prioridades | `analista` | Sólida |
| **Diseño de experiencia** | Definir cómo se ve y cómo se usa el producto | Flujos, pantallas y prototipos | `disenador` | Base |
| **Arquitectura** | Tomar solo las decisiones que mantienen consistentes las partes construidas por separado | ADR, constitución del proyecto y contratos | `arquitecto` | Sólida |
| **Desarrollo** | Convertir planes en código probado | Código, pruebas y commits | `desarrollador` | Sólida |
| **Calidad y pruebas** | Comprobar que lo construido cumple lo pedido y está bien hecho | Veredictos de revisión, pruebas de punta a punta y evidencia | `revisor`, `qa` | Sólida |
| **Seguridad** | Que nada exponga datos, credenciales ni permisos | Veredicto de seguridad y revisión de dependencias | `seguridad` | Base |
| **Servidores y despliegue** | Ambientes, CI/CD, respaldos y monitoreo | Ambientes, pipelines y runbooks | `operaciones` | Por desarrollar |
| **Soporte y operación** | Recibir, clasificar y resolver errores e incidentes | Triage de errores, postmortems | `operaciones` | Por desarrollar |

## Cómo se relacionan

```
             Dirección
                 │
   Comercial ─── Producto ─── Diseño
                 │
             Arquitectura
                 │
             Desarrollo ─── Calidad ─── Seguridad
                 │
        Servidores y despliegue ─── Soporte
```

El trabajo baja por el diagrama y lo aprendido sube. Un error que llega a Soporte vuelve a Producto como historia, y
un hallazgo repetido en Calidad vuelve a Arquitectura como regla o ADR.

## Áreas por desarrollar

Las áreas marcadas así tienen rol, pero su método se escribe cuando la fábrica llegue a ellas, con fuentes expertas
revisadas en cuarentena:

- **Comercial y cuentas:** propuestas y presupuestos de software, estimación y contratos.
- **Servidores y despliegue:** ambientes, CI/CD, respaldos, monitoreo y costos de infraestructura.
- **Soporte y operación:** mesa de ayuda, triage automático de errores e incidentes.

Hasta entonces, el rol actúa con lo que dicen la constitución y `calidad.md`, y marca como pendiente lo que no sabe
resolver.
