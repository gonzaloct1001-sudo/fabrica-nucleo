# Fábrica

Un harness para operar una fábrica de software con agentes de IA. Recibe un proyecto (una aplicación web o móvil, una
plataforma de gestión, un comercio electrónico o lo que sea) y lo lleva de la idea a producción con la disciplina de
un equipo profesional: especificación antes que código, pruebas antes que implementación, revisión independiente y
evidencia antes de dar algo por terminado.

Está pensada para que una sola persona dirija varios clientes y proyectos dedicándole poco tiempo al día. La fábrica
avanza sola, se detiene solo cuando de verdad necesita una decisión humana y entrega cada día un resumen con lo que
hizo, lo que decidió y lo que espera.

> Estado: **v0.10, en construcción.**
> - **v0.1:** los cimientos (constitución, autonomía, áreas, ciclo, calidad, aislamiento, modelos, aprendizaje y
>   plantillas).
> - **v0.2:** los agentes de cada área, las skills del ciclo y el kit que recibe cada proyecto.
> - **v0.3:** el motor que hace avanzar cada proyecto solo en la nube, y la actualización del kit de cada proyecto.
> - **v0.4:** la base de conocimiento de cada rubro, que llega a todos sus proyectos, y el camino de vuelta de lo que
>   aprende cada proyecto.
> - **v0.5:** adoptar un proyecto que ya existe sin perder nada, y sumar negocios a un cliente.
> - **v0.6:** la bandeja de la Dirección, para decidir desde la conversación sin entrar a GitHub.
> - **v0.7:** el ritmo del motor: por horario, por relevos cuando la Dirección tiene tiempo, o en sesión.
> - **v0.8:** una página visual por decisión y otra al cerrar la jornada: la Dirección ve lo que aprueba.
> - **v0.9:** seguridad en capas: las cuatro puertas, el equipo rojo, la revisión independiente según el riesgo y una
>   CI que no deja entrar acciones sin huella, archivos ilegibles ni código sin control.
> - **v0.10:** el resumen diario de la mañana: la Dirección revisa y aprueba desde el teléfono, sin su computador.
> - **Próximo:** el panel de seguimiento y el resumen diario, que la propia fábrica construye como su primer piloto.

## Cómo está organizada

```
fabrica/
├── AGENTS.md          instrucciones para cualquier asistente de IA (CLAUDE.md lo importa)
├── NUCLEO.txt         qué rutas son del núcleo; todo lo demás pertenece a la instancia
├── nucleo/            el método: igual para todos los clientes y proyectos
│   ├── constitucion.md    principios no negociables, con versión
│   ├── autonomia.md       qué decide la fábrica sola, qué avisa y qué nunca hace sin la Dirección
│   ├── areas.md           las áreas de la fábrica, como en una consultora de software
│   ├── ciclo.md           de la entrada de un pedido hasta su cierre, con estados y compuertas
│   ├── calidad.md         revisión, pruebas, evidencia y Definition of Done
│   ├── seguridad.md       las cuatro puertas, lo que se exige antes de datos reales y qué hacer si pasa algo
│   ├── aislamiento.md     clientes, negocios y proyectos, sin que la información se cruce
│   ├── modelos.md         qué nivel de modelo usa cada rol
│   ├── aprendizaje.md     cómo mejora la fábrica con cada proyecto
│   ├── actualizaciones.md núcleo e instancias: crear, actualizar sin perder nada, publicar versiones
│   ├── motor.md           la tarea programada que hace avanzar cada proyecto en la nube
│   ├── referencias.md     marcos públicos que se estudiaron
│   └── plantillas/        historia, plan, ADR, constitución de proyecto, cliente, rubro, aprendizajes, estado,
│                          retrospectiva, modelo de amenazas y la página de la Dirección
├── kit/               lo que recibe cada repositorio de proyecto: agentes, skills del ciclo, CI y plantillas
├── .claude/skills/    skills de la instancia: registrar clientes, crear o adoptar proyectos y recoger aprendizajes
├── .fabrica/
│   ├── config.ejemplo.json   configuración de una instancia (nombres, niveles, topes)
│   └── scripts/              verificar, actualizar el núcleo y los proyectos, registrar clientes, crear o adoptar
│                             proyectos y recoger aprendizajes
├── pruebas/           pruebas del núcleo con resultados conocidos
├── .github/           CI y plantillas de issues y PR
├── clientes/          registro de clientes de la instancia (vacío en el núcleo)
└── rubros/            base de conocimiento de cada rubro (solo en la instancia)
```

## Núcleo e instancia

Este repositorio es el **núcleo**: una plantilla neutral, sin nombres de personas, clientes ni proyectos.

Quien la usa crea su propia **instancia** a partir de ella, como un repositorio privado. Ahí registra a sus clientes,
fija la configuración y abre los repositorios de cada proyecto. Las mejoras del núcleo llegan a cada instancia como
una actualización que se revisa y se acepta; nunca al revés. Lo que una instancia aprende se limpia de datos antes de
proponerlo al núcleo (ver `nucleo/aprendizaje.md`).

## La persona a cargo

En todo el texto, la persona que dirige la fábrica se llama **la Dirección**. Es un rol, no un nombre. Decide lo que
solo una persona puede decidir: reglas de negocio, prioridades, alcance, proveedores con costo, lo que se le promete
a un cliente y el paso a producción. Todo lo demás lo resuelve la fábrica y lo deja registrado.

## Empezar

1. Descarga el núcleo y súbelo como repositorio nuevo y **privado**: esa es tu instancia. No uses "fork", porque un fork
   de un repositorio público no puede ser privado.
2. Copia `.fabrica/config.ejemplo.json` como `.fabrica/config.json` y completa los valores.
3. Registra el núcleo instalado: `python .fabrica/scripts/actualizar_nucleo.py --aplicar`.
4. Abre la instancia con tu asistente de IA y pide: "Lee AGENTS.md y dime cómo empezamos".

## Actualizar

```
python .fabrica/scripts/actualizar_nucleo.py              # vista previa
python .fabrica/scripts/actualizar_nucleo.py --aplicar    # aplica
```

La actualización reemplaza solo los archivos del núcleo y nunca toca tus clientes, tus reglas propias ni tu
configuración. Respalda lo que reemplaza, verifica la fábrica completa y, si algo falla, revierte todo. Queda en un
solo commit que se deshace con `git revert HEAD`. Detalle en `nucleo/actualizaciones.md`.

## Licencia

MIT. Ver `LICENSE`.
