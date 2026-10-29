#!/usr/bin/env python3
"""Prueba de punta a punta de la actualización del núcleo, con resultados conocidos de antemano.

Arma en una carpeta temporal un núcleo v1, una instancia con datos propios y un núcleo v2, y comprueba que:
- la actualización reemplaza, agrega y elimina lo que corresponde al núcleo;
- nunca toca clientes/, instancia/, config.json (salvo su versión) ni los archivos propios dentro de carpetas del núcleo;
- respalda los archivos del núcleo modificados a mano;
- deja un commit propio que se puede revertir;
- revierte todo si la versión nueva no pasa la verificación;
- se niega a actualizar con cambios sin commit o en la copia del mantenedor.

Uso: python pruebas/probar_actualizacion.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / ".fabrica" / "scripts"))
import _nucleo  # noqa: E402

ENTORNO = {k: v for k, v in os.environ.items() if k != "FABRICA_ES_NUCLEO"}
resultados = []


def comprobar(nombre, condicion, detalle=""):
    resultados.append((nombre, bool(condicion)))
    print(f"{'OK   ' if condicion else 'FALLA'} {nombre}" + (f" — {detalle}" if detalle and not condicion else ""))


def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENTORNO)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def git(cwd, *args):
    return run(["git", "-c", "user.name=prueba", "-c", "user.email=prueba@example.com", *args], cwd)


def copiar_nucleo(destino):
    for rel in _nucleo.archivos(RAIZ):
        (destino / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(RAIZ / rel, destino / rel)
    (destino / "clientes").mkdir(exist_ok=True)
    (destino / "clientes" / ".gitkeep").write_text("", encoding="utf-8")


def subir_version(carpeta, version):
    log = carpeta / "CHANGELOG.md"
    texto = log.read_text(encoding="utf-8")
    m = re.search(r"^##\s+\d", texto, re.M)
    texto = texto[:m.start()] + f"## {version} · prueba\n\n- Cambio de prueba.\n\n" + texto[m.start():]
    log.write_text(texto, encoding="utf-8")
    ejemplo = carpeta / ".fabrica" / "config.ejemplo.json"
    ejemplo.write_text(re.sub(r'("nucleo_version"\s*:\s*")[^"]*(")', rf"\g<1>{version}\g<2>",
                              ejemplo.read_text(encoding="utf-8"), count=1), encoding="utf-8")


def actualizar(instancia, desde, *extra):
    return run([sys.executable, ".fabrica/scripts/actualizar_nucleo.py", "--desde", str(desde), *extra], instancia)


def leer(p):
    return Path(p).read_text(encoding="utf-8")


def main():
    _nucleo.preparar_consola()
    with tempfile.TemporaryDirectory(prefix="prueba-fabrica-") as tmp:
        tmp = Path(tmp)
        v1, v2, v3, inst = tmp / "v1", tmp / "v2", tmp / "v3", tmp / "instancia"

        # Núcleo v1: el actual, más un archivo que v2 eliminará
        copiar_nucleo(v1)
        (v1 / "nucleo" / "obsoleto.md").write_text("Este archivo desaparece en v2.\n", encoding="utf-8")
        subir_version(v1, "9.9.8")

        # Núcleo v2: cambia un archivo, agrega otro y elimina obsoleto.md
        shutil.copytree(v1, v2)
        (v2 / "nucleo" / "calidad.md").write_text(leer(v2 / "nucleo" / "calidad.md") + "\nRegla nueva de v2.\n",
                                                   encoding="utf-8")
        (v2 / "nucleo" / "nuevo-en-v2.md").write_text("Agregado en v2.\n", encoding="utf-8")
        (v2 / "nucleo" / "obsoleto.md").unlink()
        subir_version(v2, "9.9.9")

        # Núcleo v3: roto a propósito (NUCLEO.txt lista un archivo que no existe)
        shutil.copytree(v2, v3)
        (v3 / "NUCLEO.txt").write_text(leer(v3 / "NUCLEO.txt") + "nucleo/no-existe.md\n", encoding="utf-8")
        subir_version(v3, "9.9.10")

        # Instancia creada desde v1, con datos propios
        shutil.copytree(v1, inst)
        config = leer(inst / ".fabrica" / "config.ejemplo.json").replace('"Mi Fábrica"', '"Fábrica de prueba"')
        (inst / ".fabrica" / "config.json").write_text(config, encoding="utf-8")
        (inst / "clientes" / "demo").mkdir(parents=True)
        (inst / "clientes" / "demo" / "cliente.md").write_text("Cliente de la instancia.\n", encoding="utf-8")
        (inst / "instancia").mkdir()
        (inst / "instancia" / "reglas.md").write_text("Regla propia de la instancia.\n", encoding="utf-8")
        (inst / ".github" / "workflows" / "local-propio.yml").write_text("# flujo propio de la instancia\n",
                                                                          encoding="utf-8")
        git(inst, "init", "-q", "-b", "main")
        git(inst, "config", "user.name", "prueba")
        git(inst, "config", "user.email", "prueba@example.com")
        git(inst, "add", "-A")
        git(inst, "commit", "-q", "-m", "Instancia creada")

        rc, out = actualizar(inst, v1, "--aplicar")
        comprobar("Registra el núcleo instalado en una instancia nueva", rc == 0 and (inst / _nucleo.MANIFIESTO).exists(), out)

        # Ajuste hecho a mano sobre un archivo del núcleo (lo que no se debe hacer, pero puede pasar)
        modelos = inst / "nucleo" / "modelos.md"
        modelos.write_text(leer(modelos) + "\nAjuste local hecho a mano.\n", encoding="utf-8")
        git(inst, "commit", "-qam", "Ajuste a mano")

        # Vista previa: no cambia nada
        antes = leer(inst / "nucleo" / "calidad.md")
        rc, out = actualizar(inst, v2)
        comprobar("La vista previa no cambia archivos", rc == 0 and leer(inst / "nucleo" / "calidad.md") == antes, out)
        comprobar("La vista previa anuncia el cambio de versión", "9.9.8 → 9.9.9" in out, out)

        # Con cambios sin commit, se niega
        (inst / "clientes" / "demo" / "borrador.md").write_text("sin commit\n", encoding="utf-8")
        rc, out = actualizar(inst, v2, "--aplicar")
        comprobar("Se niega a actualizar con cambios sin commit", rc != 0 and "sin commit" in out, out)
        (inst / "clientes" / "demo" / "borrador.md").unlink()

        # Actualización real a v2
        rc, out = actualizar(inst, v2, "--aplicar")
        comprobar("La actualización a v2 termina bien", rc == 0, out)
        comprobar("Reemplaza el archivo cambiado del núcleo", "Regla nueva de v2." in leer(inst / "nucleo" / "calidad.md"))
        comprobar("Agrega el archivo nuevo del núcleo", (inst / "nucleo" / "nuevo-en-v2.md").exists())
        comprobar("Elimina el archivo que el núcleo ya no trae", not (inst / "nucleo" / "obsoleto.md").exists())
        comprobar("No toca clientes/", leer(inst / "clientes" / "demo" / "cliente.md") == "Cliente de la instancia.\n")
        comprobar("No toca instancia/", leer(inst / "instancia" / "reglas.md") == "Regla propia de la instancia.\n")
        comprobar("Conserva un archivo propio dentro de una carpeta del núcleo",
                  (inst / ".github" / "workflows" / "local-propio.yml").exists())
        cfg = leer(inst / ".fabrica" / "config.json")
        comprobar("Actualiza solo la versión en config.json", '"nucleo_version": "9.9.9"' in cfg and "Fábrica de prueba" in cfg, cfg[:300])
        respaldos = list((inst / ".fabrica" / "respaldo-nucleo").rglob("modelos.md"))
        comprobar("Respaldó el archivo del núcleo modificado a mano",
                  respaldos and "Ajuste local hecho a mano." in leer(respaldos[0]))
        comprobar("Avisa del archivo modificado a mano", "nucleo/modelos.md" in out, out)
        rc_l, log = git(inst, "log", "-1", "--format=%s")
        comprobar("Deja un commit propio de la actualización", "9.9.9" in log, log)
        rc_s, estado = git(inst, "status", "--porcelain")
        comprobar("La instancia queda sin cambios pendientes", rc_s == 0 and estado.strip() == "", estado)

        # Actualización a v3, que no pasa la verificación: debe revertir todo
        cabeza = git(inst, "rev-parse", "HEAD")[1].strip()
        rc, out = actualizar(inst, v3, "--aplicar")
        comprobar("Una versión que no pasa la verificación se rechaza", rc != 0 and "se revirtió" in out, out)
        comprobar("Tras revertir, los archivos siguen en v2", '"nucleo_version": "9.9.9"' in leer(inst / ".fabrica" / "config.json")
                  and "nucleo/no-existe.md" not in leer(inst / "NUCLEO.txt"))
        comprobar("Tras revertir, no hay commit nuevo", git(inst, "rev-parse", "HEAD")[1].strip() == cabeza)

        # Deshacer con git revert devuelve la instancia a v1
        git(inst, "revert", "--no-edit", "-q", "HEAD")
        comprobar("git revert deshace la actualización completa",
                  "Regla nueva de v2." not in leer(inst / "nucleo" / "calidad.md") and (inst / "nucleo" / "obsoleto.md").exists())

        # En la copia del mantenedor, se niega
        git(inst, "config", "fabrica.mantenedor", "true")
        rc, out = actualizar(inst, v2)
        comprobar("Se niega a correr en la copia del mantenedor", rc != 0 and "mantienes" in out, out)

    fallas = [n for n, ok in resultados if not ok]
    print(f"\nPruebas de actualización: {len(resultados) - len(fallas)}/{len(resultados)} correctas.")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
