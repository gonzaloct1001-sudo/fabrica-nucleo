#!/usr/bin/env python3
"""Verifica que la fábrica esté sana. Corre en el núcleo y en cada instancia, en local o en la CI.

Uso: python .fabrica/scripts/verificar.py [--nucleo]

Comprueba que:
1. Existan todas las rutas de NUCLEO.txt y que tenga su línea "# origen:".
2. Los JSON del núcleo, y config.json si existe, sean válidos.
3. La versión de CHANGELOG.md coincida con la de .fabrica/config.ejemplo.json.
4. Las referencias a archivos del núcleo dentro de los .md apunten a archivos que existen.
5. El kit de proyecto esté completo (kit/NUCLEO.txt).
6. Cada agente tenga nombre igual a su archivo, descripción, un modelo válido y un esfuerzo válido; cada skill, nombre
   igual a su carpeta y descripción; y cada rol de nucleo/modelos.md tenga su agente en el kit.
7. Solo en el núcleo: no haya datos de una instancia (clientes, instancia/, config.json).
   Se activa con --nucleo, con la variable FABRICA_ES_NUCLEO=true o con git config fabrica.mantenedor true.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _nucleo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
REFERENCIA = re.compile(r"`((?:nucleo/|plantillas/|\.fabrica/scripts/|\.fabrica/nucleo/)[A-Za-z0-9_./-]+)`")
MODELOS = {"opus", "sonnet", "haiku", "fable", "inherit"}
ESFUERZOS = {"low", "medium", "high", "xhigh", "max"}
COPIA_DEL_METODO = ".fabrica/nucleo/"  # en un proyecto, la copia de nucleo/ que arma nuevo_proyecto.py


def frontmatter(ruta):
    """Campos simples (clave: valor) del encabezado YAML de un .md, o None si no tiene."""
    texto = ruta.read_text(encoding="utf-8")
    m = re.match(r"^---\r?\n(.*?)\r?\n---", texto, re.S)
    if not m:
        return None
    campos = {}
    for linea in m.group(1).splitlines():
        if ":" in linea and not linea.startswith((" ", "\t")):
            clave, valor = linea.split(":", 1)
            campos[clave.strip()] = valor.split(" #")[0].strip()
    return campos


def revisar_rutas(errores):
    lista = RAIZ / "NUCLEO.txt"
    if not lista.exists():
        errores.append("Falta NUCLEO.txt en la raíz.")
        return
    if not _nucleo.origen_oficial(RAIZ):
        errores.append('NUCLEO.txt no tiene la línea "# origen: <url del repositorio del núcleo>".')
    for e in _nucleo.rutas(RAIZ):
        p = RAIZ / e
        if (e.endswith("/") and not p.is_dir()) or (not e.endswith("/") and not p.is_file()):
            errores.append(f"NUCLEO.txt lista {e}, pero no existe.")


def revisar_json(errores):
    candidatos = [RAIZ / ".fabrica" / "config.ejemplo.json", RAIZ / ".fabrica" / "config.json"]
    candidatos += sorted((RAIZ / "nucleo").rglob("*.json"))
    for p in candidatos:
        if p.exists():
            try:
                json.loads(p.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as ex:
                errores.append(f"{p.relative_to(RAIZ).as_posix()} no es un JSON válido: {ex}")


def revisar_version(errores):
    v = _nucleo.version(RAIZ)
    if not v:
        errores.append("CHANGELOG.md no tiene un encabezado de versión (## x.y.z).")
        return
    ejemplo = RAIZ / ".fabrica" / "config.ejemplo.json"
    if ejemplo.exists():
        try:
            v_ejemplo = json.loads(ejemplo.read_text(encoding="utf-8")).get("nucleo_version", "")
        except json.JSONDecodeError:
            return
        if v_ejemplo != v:
            errores.append(f"config.ejemplo.json dice nucleo_version {v_ejemplo!r}, pero CHANGELOG.md va en {v}.")


def revisar_referencias(errores):
    documentos = [RAIZ / "README.md", RAIZ / "AGENTS.md"]
    for carpeta in ("nucleo", "kit", ".claude"):
        if (RAIZ / carpeta).is_dir():
            documentos += sorted((RAIZ / carpeta).rglob("*.md"))
    for doc in documentos:
        if not doc.exists():
            continue
        for n, linea in enumerate(doc.read_text(encoding="utf-8").splitlines(), 1):
            for ref in REFERENCIA.findall(linea):
                if "<" in ref:
                    continue
                destino = ref.rstrip("/")
                candidatos = [RAIZ / destino, RAIZ / "nucleo" / destino, RAIZ / "kit" / destino]
                if destino.startswith(COPIA_DEL_METODO):
                    candidatos.append(RAIZ / "nucleo" / destino[len(COPIA_DEL_METODO):])
                if not any(c.exists() for c in candidatos):
                    errores.append(f"{doc.relative_to(RAIZ).as_posix()}:{n} menciona `{ref}`, que no existe.")


def revisar_kit(errores):
    lista = RAIZ / "kit" / "NUCLEO.txt"
    if not lista.exists():
        errores.append("Falta kit/NUCLEO.txt: el kit de proyecto está incompleto.")
        return
    for linea in lista.read_text(encoding="utf-8").splitlines():
        e = linea.strip()
        if not e or e.startswith("#") or e.startswith(COPIA_DEL_METODO):
            continue
        p = RAIZ / "kit" / e
        if (e.endswith("/") and not p.is_dir()) or (not e.endswith("/") and not p.is_file()):
            errores.append(f"kit/NUCLEO.txt lista {e}, pero kit/{e} no existe.")


def revisar_agentes_y_skills(errores):
    for carpeta in (RAIZ / ".claude" / "agents", RAIZ / "kit" / ".claude" / "agents"):
        for agente in sorted(carpeta.glob("*.md")) if carpeta.is_dir() else []:
            rel = agente.relative_to(RAIZ).as_posix()
            campos = frontmatter(agente)
            if campos is None:
                errores.append(f"{rel} no tiene encabezado (---).")
                continue
            if campos.get("name") != agente.stem:
                errores.append(f"{rel}: 'name' debe ser '{agente.stem}'.")
            if not campos.get("description"):
                errores.append(f"{rel}: falta 'description'.")
            if campos.get("model") not in MODELOS:
                errores.append(f"{rel}: 'model' debe ser uno de {', '.join(sorted(MODELOS))} (declararlo es obligatorio).")
            if "effort" in campos and campos["effort"] not in ESFUERZOS:
                errores.append(f"{rel}: 'effort' debe ser uno de {', '.join(sorted(ESFUERZOS))}.")
    for carpeta in (RAIZ / ".claude" / "skills", RAIZ / "kit" / ".claude" / "skills"):
        for skill in sorted(p for p in carpeta.iterdir() if p.is_dir()) if carpeta.is_dir() else []:
            archivo = skill / "SKILL.md"
            rel = archivo.relative_to(RAIZ).as_posix()
            if not archivo.exists():
                errores.append(f"Falta {rel}.")
                continue
            campos = frontmatter(archivo) or {}
            if campos.get("name") != skill.name:
                errores.append(f"{rel}: 'name' debe ser '{skill.name}'.")
            if not campos.get("description"):
                errores.append(f"{rel}: falta 'description'.")
    modelos = RAIZ / "nucleo" / "modelos.md"
    agentes = RAIZ / "kit" / ".claude" / "agents"
    if modelos.exists() and agentes.is_dir():
        for rol in re.findall(r"^\|\s*`([a-z0-9-]+)`", modelos.read_text(encoding="utf-8"), re.M):
            if not (agentes / f"{rol}.md").exists():
                errores.append(f"nucleo/modelos.md asigna modelo al rol '{rol}', pero falta kit/.claude/agents/{rol}.md.")


def es_nucleo(forzar):
    return forzar or os.environ.get("FABRICA_ES_NUCLEO", "").lower() == "true" or _nucleo.es_mantenedor(RAIZ)


def revisar_nucleo_limpio(errores):
    clientes = RAIZ / "clientes"
    if clientes.is_dir():
        extra = [x for x in clientes.rglob("*") if x.is_file() and x.name != ".gitkeep"]
        if extra:
            errores.append(f"El núcleo no debe tener clientes: hay {len(extra)} archivo(s) en clientes/.")
    instancia = RAIZ / "instancia"
    if instancia.is_dir() and any(x.is_file() for x in instancia.rglob("*")):
        errores.append("El núcleo no debe tener la carpeta instancia/ con archivos.")
    if (RAIZ / ".fabrica" / "config.json").exists():
        errores.append("El núcleo no debe tener .fabrica/config.json: eso pertenece a cada instancia.")


def main():
    _nucleo.preparar_consola()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nucleo", action="store_true", help="comprobar además que el núcleo no tenga datos de instancia")
    a = ap.parse_args()

    errores = []
    revisar_rutas(errores)
    revisar_json(errores)
    revisar_version(errores)
    revisar_referencias(errores)
    revisar_kit(errores)
    revisar_agentes_y_skills(errores)
    nucleo = es_nucleo(a.nucleo)
    if nucleo:
        revisar_nucleo_limpio(errores)

    if errores:
        print("Verificación con problemas:")
        print("\n".join(f"- {e}" for e in errores))
        print(f"Verificación: {len(errores)} problema(s).")
        return 1
    print(f"Verificación: todo en orden (núcleo {_nucleo.version(RAIZ)}{', modo núcleo' if nucleo else ''}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
