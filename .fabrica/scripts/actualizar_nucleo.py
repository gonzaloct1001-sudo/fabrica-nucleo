#!/usr/bin/env python3
"""Actualiza el núcleo de la fábrica en esta instancia sin tocar lo propio.

Uso, desde la raíz de la instancia:
    python .fabrica/scripts/actualizar_nucleo.py [--desde <url | carpeta>]              vista previa: no cambia nada
    python .fabrica/scripts/actualizar_nucleo.py [--desde <url | carpeta>] --aplicar [--sin-commit]

- Origen: --desde, o la línea "# origen:" de NUCLEO.txt. Puede ser la URL del repositorio del núcleo (se descarga una
  copia temporal) o una carpeta (por ejemplo, un zip descomprimido de la versión nueva).
- Solo cambia las rutas de NUCLEO.txt. Nunca toca clientes/, instancia/, proyectos/ ni .fabrica/config.json (salvo
  la versión del núcleo que registra), ni los archivos propios que la instancia agregó dentro de carpetas del núcleo.
- Con --aplicar exige que no haya cambios sin commit: así la actualización queda en un commit propio, fácil de revisar
  y de deshacer con git revert.
- Respalda en .fabrica/respaldo-nucleo/<fecha>/ todo lo que reemplaza o elimina. Los archivos del núcleo que se
  modificaron a mano se respaldan y se avisan.
- Después de aplicar corre .fabrica/scripts/verificar.py. Si falla, revierte todo y nada cambia.

Para actualizar el kit de un proyecto de la instancia, usa actualizar_kit.py.
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _actualizacion  # noqa: E402
import _nucleo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
NUNCA = ("clientes/", "instancia/", "proyectos/", ".fabrica/config.json", ".fabrica/nucleo-instalado.csv",
         ".fabrica/respaldo-nucleo/")
CONFIG = RAIZ / ".fabrica" / "config.json"


def obtener_fuente(origen, tmp):
    p = Path(origen).expanduser()
    if p.is_dir():
        return p.resolve()
    destino = Path(tmp) / "nucleo"
    r = subprocess.run(["git", "-c", "core.autocrlf=false", "-c", "core.longpaths=true", "clone", "-q", "--depth", "1",
                        origen, str(destino)], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"No se pudo descargar el núcleo desde {origen}:\n{(r.stderr or r.stdout).strip()[:500]}")
    return destino


def registrar_version(v_nueva):
    """Anota la versión del núcleo en config.json sin tocar el resto del archivo."""
    if CONFIG.exists() and v_nueva:
        texto = CONFIG.read_text(encoding="utf-8")
        texto = re.sub(r'("nucleo_version"\s*:\s*")[^"]*(")', rf"\g<1>{v_nueva}\g<2>", texto, count=1)
        CONFIG.write_text(texto, encoding="utf-8")


def main():
    _nucleo.preparar_consola()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--desde", help="URL del repositorio del núcleo o carpeta con la versión nueva")
    ap.add_argument("--aplicar", action="store_true", help="aplicar la actualización (sin esto, solo vista previa)")
    ap.add_argument("--sin-commit", action="store_true", help="no hacer el commit de la actualización")
    a = ap.parse_args()

    if _nucleo.es_mantenedor(RAIZ):
        sys.exit("Esta carpeta es el núcleo que mantienes: se actualiza con Git (pull y push), no con este comando.")
    origen = a.desde or _nucleo.origen_oficial(RAIZ)
    if not origen:
        sys.exit("No sé de dónde traer el núcleo: indica --desde <url o carpeta>.")
    if a.aplicar:
        _actualizacion.exigir_arbol_limpio(RAIZ)

    with tempfile.TemporaryDirectory(prefix="fabrica-nucleo-") as tmp:
        fuente = obtener_fuente(origen, tmp)
        if fuente.resolve() == RAIZ.resolve():
            sys.exit("El origen es esta misma carpeta: indica la carpeta o el repositorio del núcleo nuevo.")
        v_local, v_nueva = _nucleo.version(RAIZ), _nucleo.version(fuente)
        destino = _actualizacion.Destino(
            raiz=RAIZ, nunca=NUNCA, version_local=v_local, registrar_version=registrar_version,
            verificador=[sys.executable, ".fabrica/scripts/verificar.py"],
            mensaje_commit=lambda v: f"Actualiza el núcleo a {v or 'la versión nueva'}",
            comando_aplicar="python .fabrica/scripts/actualizar_nucleo.py " + (f"--desde {origen} " if a.desde else "")
                            + "--aplicar",
            respaldar_tambien=[".fabrica/config.json"],
            consejo_modificados="Si eran ajustes propios, llévalos a instancia/ (nucleo/actualizaciones.md).")
        return _actualizacion.ejecutar(destino, fuente, origen, v_nueva, _nucleo.novedades(fuente, v_local),
                                       a.aplicar, a.sin_commit, titulo="Actualización del núcleo")


if __name__ == "__main__":
    sys.exit(main())
