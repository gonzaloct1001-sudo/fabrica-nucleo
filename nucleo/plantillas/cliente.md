---
id: <slug-del-cliente>         # minúsculas, sin tildes ni espacios
tipo: empresa                  # empresa | holding | persona | propio
reserva: estandar              # estandar | estricta (con estricta, recibe su propia instancia de la fábrica)
desde: <AAAA-MM-DD>
---

# <Nombre del cliente>

## Negocios

| Negocio (slug) | Rubro | Descripción breve |
|---|---|---|
| <negocio> | <rubro> | |

## Proyectos

| Proyecto | Negocio | Repositorio | Estado |
|---|---|---|---|
| <proyecto> | <negocio> | `<cliente>-<proyecto>` | activo / pausado / cerrado |

## Contraparte

- **Quién aprueba del lado del cliente:** <rol; los datos de contacto se guardan fuera del repositorio>
- **Canal acordado:** <correo, reunión semanal, etc.>

## Acuerdos

- <alcance, modelo comercial o propiedad del código: lo que se acordó y dónde está el respaldo>

## Notas

- <lo que cualquier agente que trabaje con este cliente debe saber y que no está en otro lugar>
