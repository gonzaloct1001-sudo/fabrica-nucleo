#!/usr/bin/env python3
"""Actualiza el kit de la fábrica en un proyecto de esta instancia, sin tocar lo propio del proyecto.

Uso, desde la raíz de la instancia:
    python .fabrica/scripts/actualizar_kit.py <carpeta del proyecto>              vista previa: no cambia nada
    python .fabrica/scripts/actualizar_kit.py <carpeta del proyecto> --aplicar [--sin-commit]

- La versión nueva es la del núcleo instalado en esta instancia. Primero se actualiza la instancia con
  actualizar_nucleo.py, y después cada proyecto con este comando.
- Solo cambia las rutas del NUCLEO.txt del proyecto: AGENTS.md, agentes, skills, la copia del método, la base del
  rubro (rubros/<rubro>/ de la instancia, según la ficha del cliente), el motor, la CI de la fábrica y las plantillas.
  Nunca toca el código, docs/, pruebas/, .fabrica/estado.json ni .fabrica/proyecto.json
  (salvo la versión que registra), ni los archivos propios del proyecto (por ejemplo, su propia CI o una skill local-*).
- Exige que el proyecto no tenga cambios sin commit, respalda lo que reemplaza, corre verificar_proyecto.py y, si
  falla, revierte todo. Termina con un commit local; subirlo e integrarlo sigue la regla de quién integra cada PR.
"""
import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _actualizacion  # noqa: E402
import _kit  # noqa: E402
import _nucleo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
NUNCA = (".fabrica/proyecto.json", ".fabrica/estado.json", ".fabrica/nucleo-instalado.csv", ".fabrica/respaldo-nucleo/",
         ".fabrica/trabajo/", "docs/", "pruebas/")


def main():
    _nucleo.preparar_consola()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("proyecto", help="carpeta del proyecto, por ejemplo proyectos/<cliente>-<proyecto>")
    ap.add_argument("--aplicar", action="store_true", help="aplicar la actualización (sin esto, solo vista previa)")
    ap.add_argument("--sin-commit", action="store_true", help="no hacer el commit de la actualización")
    a = ap.parse_args()

    if _nucleo.es_mantenedor(RAIZ):
        sys.exit("Esta carpeta es el núcleo que mantienes: los proyectos se actualizan desde una instancia.")
    proyecto = Path(a.proyecto)
    proyecto = (proyecto if proyecto.is_absolute() else Path.cwd() / proyecto).resolve()
    ficha = proyecto / ".fabrica" / "proyecto.json"
    if not ficha.exists() or not (proyecto / "NUCLEO.txt").exists():
        sys.exit(f"{proyecto} no es un proyecto de la fábrica: le falta .fabrica/proyecto.json o NUCLEO.txt.")
    if a.aplicar:
        _actualizacion.exigir_arbol_limpio(proyecto)

    datos = json.loads(ficha.read_text(encoding="utf-8"))
    v_local = datos.get("nucleo", "")
    v_nueva = _nucleo.version(RAIZ)
    rubro = _kit.rubro_de(RAIZ, datos.get("cliente", ""), datos.get("negocio", ""))

    def registrar_version(v):
        if v:
            texto = ficha.read_text(encoding="utf-8")
            ficha.write_text(re.sub(r'("nucleo"\s*:\s*")[^"]*(")', rf"\g<1>{v}\g<2>", texto, count=1), encoding="utf-8")
        # Desde el núcleo 0.13, los flujos propios ignoran las ramas wip/ del guardado automático (con respaldo).
        for rel in _kit.ignorar_wip_en_flujos(proyecto):
            print(f"Flujo ajustado para ignorar las ramas wip/: {rel}")
        # Desde el núcleo 0.13 el kit trae hooks: se fusionan en .claude/settings.json sin tocar lo propio.
        aviso = _kit.fusionar_hooks(proyecto)
        if aviso:
            print(f"Aviso: {aviso}")
        # Desde el núcleo 0.11 el kit lee dónde están las historias y los planes. Un proyecto anterior que las guarda
        # en otra carpeta las recibe detectadas, una sola vez; después son suyas y la actualización no las toca.
        datos_ahora = json.loads(ficha.read_text(encoding="utf-8"))
        if "rutas" not in datos_ahora:
            detectadas = _kit.detectar_rutas(proyecto)
            if detectadas:
                datos_ahora["rutas"] = detectadas
                ficha.write_text(json.dumps(datos_ahora, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print("Rutas propias registradas en .fabrica/proyecto.json: "
                      + ", ".join(f"{k} = {v}" for k, v in detectadas.items()))

    with tempfile.TemporaryDirectory(prefix="fabrica-kit-") as tmp:
        fuente = Path(tmp) / "kit"
        _kit.armar(RAIZ, fuente, rubro)
        destino = _actualizacion.Destino(
            raiz=proyecto, nunca=NUNCA, version_local=v_local, registrar_version=registrar_version,
            verificador=[sys.executable, ".fabrica/scripts/verificar_proyecto.py"],
            mensaje_commit=lambda v: f"Actualiza el kit de la fábrica a {v or 'la versión nueva'}",
            comando_aplicar=f"python .fabrica/scripts/actualizar_kit.py {a.proyecto} --aplicar",
            respaldar_tambien=[".fabrica/proyecto.json", ".claude/settings.json", *_kit.flujos_a_filtrar(proyecto)],
            consejo_modificados="Si eran ajustes propios del proyecto, llévalos a docs/constitucion.md o a archivos local-*.")
        return _actualizacion.ejecutar(destino, fuente, f"núcleo de esta instancia ({RAIZ.name})", v_nueva,
                                       _nucleo.novedades(RAIZ, v_local), a.aplicar, a.sin_commit,
                                       titulo=f"Actualización del kit · {proyecto.name}")


if __name__ == "__main__":
    sys.exit(main())
