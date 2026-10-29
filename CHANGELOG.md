# Cambios del núcleo

El núcleo sigue versionado semántico:
- **mayor:** cambia o se elimina un principio, o se rompe la compatibilidad con proyectos existentes;
- **menor:** se agrega un área, un rol, una skill o una regla;
- **parche:** se corrige o se precisa algo ya existente.

## 0.1.0 · 2026-10-29

Cimientos de la fábrica:
- Constitución v1.0.0 con doce principios.
- Contrato de autonomía: tres listas, cinco motivos de detención, registro de decisiones, niveles de autonomía,
  topes, interruptor y resumen diario.
- Diez áreas, con su rol y su madurez.
- Ciclo de vida: triage por ruta y riesgo, etapas, estados, motivos de bloqueo, Definition of Ready y Definition of
  Done.
- Calidad: evidencia antes de afirmar, pruebas protegidas, revisión doble, profundidad según el riesgo, ciclo de
  corrección con tope y revisión final.
- Aislamiento entre clientes en tres capas.
- Modelos por rol y por nivel.
- Aprendizaje: retrospectiva, promoción al núcleo y examen de la fábrica.
- Plantillas: historia, plan, ADR, constitución de proyecto, cliente, estado y retrospectiva.
- Núcleo e instancias:
  - `NUCLEO.txt` separa la zona del núcleo de la zona de la instancia;
  - `actualizar_nucleo.py` actualiza con vista previa, respaldo, verificación, reversión automática y un commit propio;
  - `verificar.py` revisa rutas, JSON, versión, referencias entre documentos y, en el núcleo, que no haya datos de una
    instancia.
- Prueba de punta a punta de la actualización, con resultados conocidos.
- CI en GitHub, plantillas de issues y de PR, y licencia MIT.
