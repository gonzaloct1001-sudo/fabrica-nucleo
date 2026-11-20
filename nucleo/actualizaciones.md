# Núcleo, instancias y actualizaciones

## Dos zonas que no se mezclan

Cada archivo pertenece a una de dos zonas. Esa separación es la que permite actualizar sin perder nada.

| Zona | Qué contiene | Quién la cambia | Al actualizar |
|---|---|---|---|
| **Núcleo** | Las rutas de `NUCLEO.txt`: `nucleo/`, `AGENTS.md`, `.fabrica/scripts/`, `.github/`, `pruebas/` y los archivos de la raíz | Solo el repositorio del núcleo | Se reemplaza por la versión nueva |
| **Instancia** | `clientes/`, `rubros/`, `instancia/`, `proyectos/`, `.fabrica/config.json` y los archivos propios dentro de carpetas del núcleo | Solo la instancia | Nunca se toca |

**La regla de oro:** en una instancia no se editan archivos del núcleo. Lo propio va en estos lugares:

- **Reglas propias:** en `instancia/reglas.md`. Complementan la constitución; nunca la relajan.
- **Skills, agentes o flujos de trabajo propios:** como archivos nuevos dentro de las carpetas del núcleo, con prefijo
  `local-` (por ejemplo `.github/workflows/local-panel.yml`). Una actualización los reconoce como propios y los
  conserva.
- **Nombres, niveles y topes:** en `.fabrica/config.json`.

Si de todos modos se editó un archivo del núcleo, la actualización se detiene sin cambiar nada (ver «El contrato de
instalación»).

## El contrato de instalación

Desde la 0.13.2, toda actualización (del núcleo en una instancia, o del kit en un proyecto) cumple esto:

1. **Nunca cambia lo propio.** Solo toca la zona de `NUCLEO.txt`. Un archivo propio que tiene el mismo nombre que uno
   de la versión nueva (por ejemplo, un comando que el proyecto tenía antes de que el kit lo trajera) se conserva, la
   versión del kit no se instala, y se avisa. Para pasar a la del kit, se renombra el propio a `local-*` y se actualiza
   de nuevo.
2. **Nunca pisa una «pata» en silencio.** Una pata es un archivo de la zona editado o borrado a mano. Si la hay, la
   actualización se detiene sin cambiar nada y la nombra. Alguien decide: llevar el ajuste a un archivo `local-*` o a la
   constitución, proponerlo al núcleo (`aprendizaje.md`) o descartarlo. Después se actualiza con
   `--reemplazar-editados`, y lo anterior queda en el respaldo. Un flujo del kit que se quiera apagado no se borra:
   se desactiva en GitHub (**Actions** → el flujo → **Disable workflow**), y así ninguna actualización lo reactiva.
3. **La zona se puede comprobar.** `.fabrica/nucleo-instalado.csv` guarda la huella de cada archivo instalado. En un
   proyecto, `verificar_proyecto.py` avisa siempre de lo editado, lo que falta y lo propio sin `local-` dentro de la
   zona, y en un PR rechaza la pata nueva salvo con la etiqueta `nucleo-aprobado`. El PR que actualiza el kit cambia
   ese registro, así que también la pide: la pone la Dirección después de ver el ensayo. Vale también la forma
   `nucleo-aprobado:<huella>` que algunos proyectos ya exigen en su propia CI, para poner una sola etiqueta.
4. **Los agentes no hacen patas.** El hook de guardia niega que un agente edite un archivo del kit o cree uno nuevo sin
   `local-` en su zona, y dice adónde llevar el ajuste. Una persona puede hacerlo a mano; la CI lo ve igual.
5. **Se ensaya antes.** Antes de abrir el PR de actualización en un proyecto real, se ensaya en una copia: del master
   del día, con los PR abiertos encima, y si se puede en una copia privada del repositorio con su CI completa
   (`ensayar_actualizacion.py`, en «Actualizar el kit de cada proyecto»).
6. **Se puede deshacer.** Cada actualización es un solo commit y un solo PR: **Revert** deja todo como estaba.

**Lo que el contrato no cubre**, dicho para no confiar de más: la etiqueta `nucleo-aprobado` no prueba quién la puso
(un agente con permisos puede ponerla), la guardia solo vigila las ediciones de archivos de los agentes (no un comando
de terminal), y la CI que revisa un PR es la que trae ese mismo PR. La defensa de fondo es que la Dirección integra los
PR que tocan la zona del kit, y que un repositorio con plan de pago puede exigir su revisión (CODEOWNERS).

`inventario.py` muestra, para un proyecto, qué es del kit y si está intacto, qué es propio, qué choca y qué parece
duplicar algo del kit: lo que el proyecto creó y podría subir al núcleo.

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

Cada proyecto lleva una copia del kit, del método y de la base de su rubro (`.fabrica/rubro/`, desde
`rubros/<rubro>/` de la instancia; ver `aprendizaje.md`). El rubro sale de la ficha del cliente, según el negocio del
proyecto. Su `NUCLEO.txt` dice qué rutas son del kit; todo lo demás (el código, `docs/`, `pruebas/`, el estado y su
propia CI) pertenece al proyecto.

Después de actualizar la instancia, se actualiza cada proyecto desde ella:

```
python .fabrica/scripts/actualizar_kit.py proyectos/<cliente>-<proyecto>              # vista previa
python .fabrica/scripts/actualizar_kit.py proyectos/<cliente>-<proyecto> --aplicar    # aplica
```

Funciona igual que la actualización del núcleo: respalda, verifica con `verificar_proyecto.py`, revierte si falla y
deja un commit local. Subirlo e integrarlo sigue la regla de "Quién integra cada PR" (`autonomia.md`).

**En un proyecto real, primero el ensayo** (punto 5 del contrato). Desde la instancia:

```
python .fabrica/scripts/ensayar_actualizacion.py <carpeta o URL del proyecto>
```

Clona el proyecto en una carpeta temporal (nunca toca el original), aplica la actualización, corre la verificación,
prueba encima cada PR abierto como si se integrara después, y deja un informe: qué cambia, qué se conserva, qué choca y
qué PR quedaría en rojo. Con una copia privada del repositorio en GitHub, el mismo PR se abre primero ahí, para ver su
CI completa antes de tocar el original.

La base del rubro viaja igual: si cambió `rubros/<rubro>/` en la instancia, la siguiente actualización del kit la lleva
a cada proyecto de ese rubro, aunque el núcleo no haya cambiado de versión.

### Cuando una pieza propia del proyecto pasa al núcleo

A veces un proyecto inventa algo que después sube al núcleo (por ejemplo, en la 0.11, el script de estado, los
comandos de sesión y la construcción en sesión). La actualización que trae la versión oficial no pelea con la propia:
- **Se actualiza en una rama, nunca en la principal,** y llega como un PR con la CI completa en verde.
- **La pieza propia se retira en ese mismo PR,** con una prueba o una comparación que muestre que la del kit hace lo
  mismo. Lo que la propia hacía de más se queda como `local-` o se propone al núcleo.
- **Lo que el proyecto declaraba en su constitución,** y ahora el kit lee de `.fabrica/proyecto.json` (las rutas, la
  autonomía delegada), se copia a `proyecto.json` en ese PR. La constitución sigue siendo la fuente: lo escrito ahí
  manda. Si el PR copia la autonomía, necesita la etiqueta `constitucion-aprobada` (la crea
  `.fabrica/scripts/crear_etiquetas.py`), que pone la Dirección, y lo integra ella.
- **Una versión a la vez,** con la tarea programada del proyecto pausada mientras se integra.
- **Lo nuevo nace apagado.** Al actualizar un proyecto anterior a la 0.12, la comprobación de coherencia del estado
  solo avisa. Se enciende cuando el proyecto corre `python .fabrica/scripts/estado.py --escribir` por primera vez, en
  su propio PR. Si el proyecto guarda sus historias o sus planes en otra carpeta, la actualización los detecta y los
  registra en `rutas` de `.fabrica/proyecto.json`, una sola vez.

## Adoptar un proyecto que ya existe

Un proyecto que llega con su propio repositorio (con historia, documentos o código) entra a la fábrica sin perder
nada. El procedimiento completo está en la skill `adoptar-proyecto`.

```
python .fabrica/scripts/adoptar_proyecto.py <carpeta> --cliente <c> --negocio <n> --proyecto <p>              # vista previa
python .fabrica/scripts/adoptar_proyecto.py <carpeta> --cliente <c> --negocio <n> --proyecto <p> --aplicar    # adopta
```

- **Instala el kit completo,** igual que en un proyecto nuevo.
- **Crea solo los archivos propios que falten:** la ficha, el estado, la constitución, la bitácora y las carpetas de
  la fábrica. Nunca pisa el código, el README, `docs/` ni la CI propia, y al `.gitignore` solo le agrega líneas.
- **Si un archivo del proyecto ocupa una ruta del kit,** lo respalda antes de reemplazarlo. Por ejemplo, su propio
  `CLAUDE.md` o un agente con el mismo nombre. Lo que decía ese archivo se lleva antes a `docs/constitucion.md`.
- **Los agentes y skills propios que el kit no trae se conservan.** Una actualización del kit los reconoce como
  propios.
- **Verifica el proyecto adoptado** y, si falla, deja todo como estaba. Termina con un commit que se deshace con
  `git revert HEAD`.

Desde ese momento, el proyecto se actualiza como cualquier otro, con `actualizar_kit.py`.

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
