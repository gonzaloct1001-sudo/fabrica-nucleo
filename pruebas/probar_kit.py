#!/usr/bin/env python3
"""Prueba de punta a punta del registro de clientes, la creación de proyectos y la protección de las pruebas.

En una instancia temporal comprueba que:
- se registra un holding con dos negocios, y se rechazan identificadores inválidos, duplicados y la reserva estricta;
- un proyecto nace con el kit completo, la copia del método, su estado, su manifiesto y su primer commit;
- la ficha del cliente lista el proyecto, y no se crean proyectos de negocios inexistentes ni repetidos;
- la verificación del proyecto pasa en limpio;
- un cambio en pruebas/aceptacion/ sin la etiqueta pruebas-aprobadas se rechaza, y con ella se acepta;
- en la copia del mantenedor no se pueden registrar clientes ni crear proyectos.

Uso: python pruebas/probar_kit.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / ".fabrica" / "scripts"))
import _nucleo  # noqa: E402

ENTORNO = {k: v for k, v in os.environ.items() if k != "FABRICA_ES_NUCLEO"}
ENTORNO.update({"GIT_AUTHOR_NAME": "prueba", "GIT_AUTHOR_EMAIL": "prueba@example.com",
                "GIT_COMMITTER_NAME": "prueba", "GIT_COMMITTER_EMAIL": "prueba@example.com"})
resultados = []


def comprobar(nombre, condicion, detalle=""):
    resultados.append((nombre, bool(condicion)))
    print(f"{'OK   ' if condicion else 'FALLA'} {nombre}" + (f" — {detalle[:600]}" if detalle and not condicion else ""))


def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENTORNO)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def script(inst, nombre, *args):
    return run([sys.executable, f".fabrica/scripts/{nombre}", *args], inst)


def main():
    _nucleo.preparar_consola()
    with tempfile.TemporaryDirectory(prefix="prueba-kit-") as tmp:
        inst = Path(tmp) / "instancia"
        for rel in _nucleo.archivos(RAIZ):
            (inst / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(RAIZ / rel, inst / rel)
        (inst / "clientes").mkdir()

        # Clientes
        rc, out = script(inst, "nuevo_cliente.py", "--id", "grupo-demo", "--nombre", "Grupo Demo", "--tipo", "holding",
                         "--negocio", "distribucion:logistica:Reparto a domicilio", "--negocio", "farmacia:salud")
        ficha = inst / "clientes" / "grupo-demo" / "cliente.md"
        comprobar("Registra un holding con dos negocios", rc == 0 and ficha.exists(), out)
        texto = ficha.read_text(encoding="utf-8") if ficha.exists() else ""
        comprobar("La ficha tiene nombre, tipo y negocios",
                  "# Grupo Demo" in texto and "tipo: holding" in texto and "| distribucion | logistica |" in texto
                  and "| farmacia | salud |" in texto and "<negocio>" not in texto and "<proyecto>" not in texto, texto)
        rc, out = script(inst, "nuevo_cliente.py", "--id", "grupo-demo", "--nombre", "Otro", "--negocio", "x:y")
        comprobar("Rechaza un cliente repetido", rc != 0 and "ya existe" in out, out)
        rc, out = script(inst, "nuevo_cliente.py", "--id", "Mi Cliente", "--nombre", "X", "--negocio", "x:y")
        comprobar("Rechaza un identificador inválido", rc != 0 and "no es válido" in out, out)
        rc, out = script(inst, "nuevo_cliente.py", "--id", "reservado", "--nombre", "X", "--reserva", "estricta",
                         "--negocio", "x:y")
        comprobar("Un cliente con reserva estricta se deriva a otra instancia",
                  rc != 0 and "propia instancia" in out and not (inst / "clientes" / "reservado").exists(), out)

        # Proyecto
        rc, out = script(inst, "nuevo_proyecto.py", "--cliente", "grupo-demo", "--negocio", "distribucion",
                         "--proyecto", "plataforma", "--nombre", "Plataforma de reparto")
        proy = inst / "proyectos" / "grupo-demo-plataforma"
        comprobar("Crea el proyecto", rc == 0 and proy.is_dir(), out)
        esperados = ["AGENTS.md", "CLAUDE.md", "NUCLEO.txt", ".claude/agents/desarrollador.md",
                     ".claude/agents/revisor.md", ".claude/skills/construir/SKILL.md", ".github/workflows/fabrica.yml",
                     ".fabrica/scripts/verificar_proyecto.py", ".fabrica/nucleo/constitucion.md",
                     ".fabrica/nucleo/plantillas/historia.md", ".fabrica/proyecto.json", ".fabrica/estado.json",
                     ".fabrica/nucleo-instalado.csv", "docs/constitucion.md", "docs/bitacora.md",
                     "pruebas/aceptacion/.gitkeep", ".gitignore"]
        faltan = [e for e in esperados if not (proy / e).exists()]
        comprobar("El proyecto trae el kit completo", not faltan, f"faltan: {faltan}")
        comprobar("La copia del método es idéntica al núcleo",
                  (proy / ".fabrica/nucleo/constitucion.md").read_bytes() == (inst / "nucleo/constitucion.md").read_bytes())
        datos = json.loads((proy / ".fabrica/proyecto.json").read_text(encoding="utf-8"))
        estado = json.loads((proy / ".fabrica/estado.json").read_text(encoding="utf-8"))
        comprobar("proyecto.json y estado.json identifican el proyecto",
                  datos["cliente"] == estado["cliente"] == "grupo-demo" and datos["proyecto"] == estado["proyecto"] ==
                  "plataforma" and estado["nucleo"] == _nucleo.version(RAIZ) and not any(k.startswith("_") for k in estado),
                  json.dumps(estado, ensure_ascii=False))
        comprobar("La constitución del proyecto lleva su nombre",
                  "# Constitución de Plataforma de reparto" in (proy / "docs/constitucion.md").read_text(encoding="utf-8"))
        rc_l, log = run(["git", "log", "--oneline"], proy)
        comprobar("El proyecto nace con su repositorio y su primer commit", rc_l == 0 and len(log.strip().splitlines()) == 1, log)
        comprobar("La ficha del cliente lista el proyecto",
                  "| plataforma | distribucion | `grupo-demo-plataforma` | activo |" in ficha.read_text(encoding="utf-8"))
        rc, out = script(inst, "nuevo_proyecto.py", "--cliente", "grupo-demo", "--negocio", "inexistente", "--proyecto", "x")
        comprobar("Rechaza un negocio que no está en la ficha", rc != 0 and "no está en la ficha" in out, out)
        rc, out = script(inst, "nuevo_proyecto.py", "--cliente", "grupo-demo", "--negocio", "distribucion",
                         "--proyecto", "plataforma")
        comprobar("Rechaza un proyecto repetido", rc != 0 and "no está vacía" in out, out)
        rc, out = script(inst, "nuevo_proyecto.py", "--cliente", "nadie", "--negocio", "x", "--proyecto", "x")
        comprobar("Rechaza un cliente no registrado", rc != 0 and "no está registrado" in out, out)

        # Verificación del proyecto y protección de las pruebas de aceptación
        verif = [sys.executable, ".fabrica/scripts/verificar_proyecto.py"]
        rc, out = run(verif, proy)
        comprobar("La verificación del proyecto pasa en limpio", rc == 0, out)
        run(["git", "checkout", "-q", "-b", "cambio-codigo"], proy)
        (proy / "src").mkdir()
        (proy / "src" / "modulo.txt").write_text("código\n", encoding="utf-8")
        run(["git", "add", "-A"], proy)
        run(["git", "commit", "-qm", "Código"], proy)
        rc, out = run(verif + ["--base", "main", "--etiquetas", ""], proy)
        comprobar("Un cambio que no toca las pruebas de aceptación pasa sin etiqueta", rc == 0, out)
        (proy / "pruebas" / "aceptacion" / "H-001").mkdir(parents=True)
        (proy / "pruebas" / "aceptacion" / "H-001" / "caso.md").write_text("Dado… cuando… entonces…\n", encoding="utf-8")
        run(["git", "add", "-A"], proy)
        run(["git", "commit", "-qm", "Toca pruebas de aceptación"], proy)
        rc, out = run(verif + ["--base", "main", "--etiquetas", ""], proy)
        comprobar("Un cambio en pruebas de aceptación sin etiqueta se rechaza", rc != 0 and "pruebas-aprobadas" in out, out)
        rc, out = run(verif + ["--base", "main", "--etiquetas", "riesgo:alto,pruebas-aprobadas"], proy)
        comprobar("Con la etiqueta pruebas-aprobadas se acepta", rc == 0, out)
        evento = Path(tmp) / "evento.json"
        evento.write_text(json.dumps({"pull_request": {"labels": [{"name": "riesgo:alto"}]}}), encoding="utf-8")
        ENTORNO["GITHUB_EVENT_PATH"] = str(evento)
        rc, out = run(verif + ["--base", "main"], proy)
        comprobar("Lee las etiquetas del evento de GitHub (sin la etiqueta, rechaza)", rc != 0, out)
        ENTORNO.pop("GITHUB_EVENT_PATH")

        # La verificación de la instancia completa, con su cliente y su proyecto, sigue pasando
        rc, out = script(inst, "verificar.py")
        comprobar("La instancia con clientes y proyectos pasa la verificación", rc == 0, out)

        # En la copia del mantenedor, se niega
        run(["git", "init", "-q", "-b", "main"], inst)
        run(["git", "config", "fabrica.mantenedor", "true"], inst)
        rc, out = script(inst, "nuevo_cliente.py", "--id", "otro", "--nombre", "Otro", "--negocio", "x:y")
        comprobar("En el núcleo no se registran clientes", rc != 0 and "núcleo que mantienes" in out, out)
        rc, out = script(inst, "nuevo_proyecto.py", "--cliente", "grupo-demo", "--negocio", "farmacia", "--proyecto", "y")
        comprobar("En el núcleo no se crean proyectos", rc != 0 and "núcleo que mantienes" in out, out)

    fallas = [n for n, ok in resultados if not ok]
    print(f"\nPruebas del kit: {len(resultados) - len(fallas)}/{len(resultados)} correctas.")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
