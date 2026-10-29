## Qué cambia

<!-- Una o dos oraciones. -->

## Por qué

<!-- El problema que resuelve o la mejora que trae. Si viene del aprendizaje de una instancia, va sin nombres ni datos
     del cliente. -->

## Tipo de cambio

- [ ] Parche: corrige o precisa algo existente
- [ ] Menor: agrega un área, un rol, una skill o una regla
- [ ] Mayor: cambia o elimina un principio, o rompe la compatibilidad con instancias existentes

## Lista de control

- [ ] `CHANGELOG.md` tiene la entrada de la versión nueva
- [ ] `nucleo_version` de `.fabrica/config.ejemplo.json` coincide con esa versión
- [ ] `python .fabrica/scripts/verificar.py --nucleo` pasa
- [ ] `python pruebas/probar_actualizacion.py` pasa
- [ ] Sin nombres de personas, clientes ni proyectos reales
- [ ] Si se agregó una ruta nueva al núcleo, está en `NUCLEO.txt`
