# Núcleo, instancias y actualizaciones

## Dos zonas que no se mezclan

Cada archivo pertenece a una de dos zonas. Esa separación es la que permite actualizar sin perder nada.

| Zona | Qué contiene | Quién la cambia | Al actualizar |
|---|---|---|---|
| **Núcleo** | Las rutas de `NUCLEO.txt`: `nucleo/`, `AGENTS.md`, `.fabrica/scripts/`, `.github/`, `pruebas/` y los archivos de la raíz | Solo el repositorio del núcleo | Se reemplaza por la versión nueva |
| **Instancia** | `clientes/`, `instancia/`, `proyectos/`, `.fabrica/config.json` y los archivos propios dentro de carpetas del núcleo | Solo la instancia | Nunca se toca |

**La regla de oro:** en una instancia no se editan archivos del núcleo. Lo propio va en estos lugares:

- **Reglas propias:** en `instancia/reglas.md`. Complementan la constitución; nunca la relajan.
- **Skills, agentes o flujos de trabajo propios:** como archivos nuevos dentro de las carpetas del núcleo, con prefijo
  `local-` (por ejemplo `.github/workflows/local-panel.yml`). Una actualización los reconoce como propios y los
  conserva.
- **Nombres, niveles y topes:** en `.fabrica/config.json`.

Si de todos modos se editó un archivo del núcleo, la actualización lo respalda antes de reemplazarlo y avisa, para
llevar ese ajuste a la zona de la instancia.

## Crear una instancia

1. Descarga el núcleo: el zip de la última versión, o clónalo.
2. Crea un repositorio privado nuevo con ese contenido. No uses "fork": un fork de un repositorio público no puede ser
   privado.
3. Copia `.fabrica/config.ejemplo.json` como `.fabrica/config.json` y complétalo.
4. Registra el núcleo instalado:

   ```
   python .fabrica/scripts/actualizar_nucleo.py --aplicar
   ```

   Si no hay nada que actualizar, solo deja anotada la huella de cada archivo del núcleo. Desde ese momento, la fábrica
   distingue lo que es del núcleo de lo que es tuyo.

## Actualizar una instancia

```
python .fabrica/scripts/actualizar_nucleo.py              # vista previa: muestra qué cambiaría, no toca nada
python .fabrica/scripts/actualizar_nucleo.py --aplicar    # aplica
```

Al aplicar, el actualizador sigue estos pasos:

1. **Exige que no haya cambios sin commit,** para que la actualización quede aislada en su propio commit.
2. **Descarga la versión nueva** desde el origen que indica `NUCLEO.txt`.
3. **Compara archivo por archivo** usando las huellas: qué es nuevo, qué cambió, qué ya no existe, qué modificaste a
   mano y qué es tuyo.
4. **Respalda** en `.fabrica/respaldo-nucleo/<fecha>/` todo lo que va a reemplazar o eliminar.
5. **Aplica** los cambios en la zona del núcleo y anota la versión nueva en `config.json`.
6. **Verifica** la fábrica completa con `verificar.py`. Si algo falla, revierte todo, avisa y nada cambia.
7. **Hace un commit** llamado "Actualiza el núcleo a x.y.z".

**Para deshacer:** `git revert HEAD` devuelve la instancia exactamente a la versión anterior.

Este comportamiento tiene una prueba automática con resultados conocidos (`pruebas/probar_actualizacion.py`), que
corre en la CI en cada cambio del núcleo.

## Actualizar el kit de cada proyecto

Cada proyecto lleva una copia del kit y del método. Su `NUCLEO.txt` dice qué rutas son del kit; todo lo demás (el
código, `docs/`, `pruebas/`, el estado y su propia CI) pertenece al proyecto.

Después de actualizar la instancia, se actualiza cada proyecto desde ella:

```
python .fabrica/scripts/actualizar_kit.py proyectos/<cliente>-<proyecto>              # vista previa
python .fabrica/scripts/actualizar_kit.py proyectos/<cliente>-<proyecto> --aplicar    # aplica
```

Funciona igual que la actualización del núcleo: respalda, verifica con `verificar_proyecto.py`, revierte si falla y
deja un commit local. Subirlo e integrarlo sigue la regla de "Quién integra cada PR" (`autonomia.md`).

## Mantener el núcleo

El repositorio del núcleo lo mantiene una sola persona. En esa copia, `git config fabrica.mantenedor true` impide
correr el actualizador por error y activa la verificación de que el núcleo no tenga datos de instancia.

Cada versión nueva sigue estos pasos:

1. Se trabaja en una rama y se cierra con un PR que completa la lista de control.
2. Se agrega la entrada en `CHANGELOG.md` y se sube `nucleo_version` en `config.ejemplo.json`.
3. La CI corre la verificación y las pruebas.
4. Se integra el PR. Un agente puede integrarlo solo con la confirmación explícita de quien mantiene el núcleo,
   pedida en la conversación para ese PR.
5. Se crea la etiqueta `vX.Y.Z` y su release en GitHub.

## Mejoras que nacen en una instancia

Lo que una instancia aprende y sirve a todos llega al núcleo como una propuesta, siempre limpia de nombres y datos del
cliente (`nucleo/aprendizaje.md`). Se integra en el repositorio del núcleo y vuelve a cada instancia con la
actualización siguiente. Nunca se copia a mano de una instancia a otra.
