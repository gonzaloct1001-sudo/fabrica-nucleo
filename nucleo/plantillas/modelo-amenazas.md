---
proyecto: <nombre del proyecto>
actualizado: <AAAA-MM-DD>
revisado-por: seguridad
---

# Modelo de amenazas de <proyecto>

Qué se protege, de quién, por dónde podría entrar y qué lo cierra. Se escribe antes de la primera historia de riesgo
alto, y se actualiza cuando una historia abre una puerta nueva (`seguridad.md` del método). Lo escribe el
`arquitecto` y lo revisa `seguridad`.

## Qué se protege

| Activo | Por qué importa | Dónde vive |
|---|---|---|
| <por ejemplo: datos personales de los clientes finales> | <qué pasa si se filtran o se alteran> | <tabla, servicio, archivo> |

## De quién

- <quién podría intentarlo y para qué: un bot automático, un usuario curioso, un ex empleado, alguien que se hace
  pasar por otro>

## Las puertas

| Puerta | Qué podría pasar | Qué lo cierra | Estado | Lo demuestra |
|---|---|---|---|---|
| Inicio de sesión y cuentas | | | abierta · parcial · cerrada | <prueba o control> |
| Permisos entre usuarios, roles y empresas | | | | |
| Datos personales | | | | |
| Entradas: formularios, archivos, integraciones | | | | |
| Piezas de terceros | | | | |
| Servidores, configuración y claves | | | | |
| Agentes de la fábrica | | | | |

## Casos de abuso

Cada caso es una prueba de aceptación de la historia que lo cierra.

- **AB-1:** **Dado** <un atacante con …>, **cuando** <intenta …>, **entonces** <el sistema lo impide y lo
  registra>. Prueba: `<ruta de la prueba>`.

## Lista de verificación

Capítulos de OWASP ASVS nivel 2 que aplican a este proyecto, y dónde se verifica cada uno.

| Capítulo | Aplica | Dónde se verifica |
|---|---|---|
| <por ejemplo: autenticación> | sí / no, y por qué | <historia, prueba o control> |

## Antes de datos reales

| Requisito | Estado | Fecha y evidencia |
|---|---|---|
| Modelo de amenazas sin puertas abiertas de severidad alta | | |
| Casos de abuso en verde en la CI | | |
| Prueba de intrusión profesional, con hallazgos críticos y altos corregidos | | |
| Respaldo con restauración probada | | |
| Alertas que le llegan a una persona | | |
| Preguntas legales respondidas por una asesoría | | |

## Si pasa algo

- **A quién se avisa, y cómo:** <persona, canal>
- **Cómo se corta un acceso:** <qué se rota, dónde se cierran sesiones>
- **Dónde están los respaldos y cómo se restauran:** <ubicación, pasos, última prueba>
- **Qué exige la ley y en qué plazo:** <según la consulta legal del proyecto>
