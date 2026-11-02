#!/usr/bin/env python3
"""Recoge los aprendizajes que dejaron los proyectos de esta instancia, para incorporarlos a la base de su rubro o
proponerlos al núcleo (nucleo/aprendizaje.md).

Uso, desde la raíz de la instancia:
    python .fabrica/scripts/recoger_aprendizajes.py [--local]
        lista los aprendizajes que todavía no tienen decisión, con su rubro y los avisos de limpieza
    python .fabrica/scripts/recoger_aprendizajes.py --registrar <repositorio>:<A-NNN> --decision rubro|metodo|descartado
        [--nota "<texto>"]
        anota la decisión en instancia/aprendizajes-recogidos.csv, para no volver a recogerlo

- Los proyectos salen de las fichas de clientes/ (tabla "Proyectos"); los cerrados también cuentan.
- De cada proyecto lee solo docs/aprendizajes.md (nucleo/aislamiento.md): de su rama principal en GitHub, con la
  cuenta de config.json, o de su carpeta en proyectos/ con --local o si no hay cuenta configurada.
- Los avisos de limpieza señalan lo que parece un dato del cliente: su nombre o identificador, correos, teléfonos,
  montos y enlaces. No reemplazan la revisión de la Dirección.
"""
import argparse
import csv
import json
import re
import subprocess
import sys
import unicodedata
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import _nucleo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
REGISTRO = Path("instancia") / "aprendizajes-recogidos.csv"
DECISIONES = ("rubro", "metodo", "descartado")
ENTRADA = re.compile(r"^##\s+(A-\d+)\s*[·:-]\s*(.+)$", re.M)
CAMPO = re.compile(r"^-\s+\*\*([^*:]+):\*\*\s*(.*)$", re.M)
SOSPECHOSOS = [
    ("un correo", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")),
    ("un monto", re.compile(r"[$€£]\s?\d|\d[\d.,]*\s?(?:CLP|USD|EUR|UF|MXN|ARS|COP|PEN|BRL)\b", re.I)),
    ("un enlace", re.compile(r"https?://\S+")),
]
TELEFONO = re.compile(r"\+?\d[\d\s-]{7,}\d")
FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def sin_tildes(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn").lower()


def proyectos():
    """[(repositorio, cliente, rubro, nombres del cliente)] de todas las fichas de la instancia."""
    salida = []
    for ficha in sorted((RAIZ / "clientes").glob("*/cliente.md")):
        cliente = ficha.parent.name
        texto = ficha.read_text(encoding="utf-8")
        titulo = re.search(r"^#\s+(.+)$", texto, re.M)
        tipo = re.search(r"^tipo:\s*(\S+)", texto, re.M)
        nombres = [] if tipo and tipo.group(1) == "propio" else [cliente] + ([titulo.group(1).strip()] if titulo else [])
        rubros = _kit.negocios(ficha)
        for fila in _kit.tabla(ficha, "Proyectos"):
            if len(fila) >= 3:
                salida.append((fila[2], cliente, rubros.get(fila[1], ""), nombres))
    return salida


def leer_aprendizajes(repo, propietario, local):
    """Texto de docs/aprendizajes.md del proyecto, o None si no lo tiene."""
    if local or not propietario:
        archivo = RAIZ / "proyectos" / repo / "docs" / "aprendizajes.md"
        return archivo.read_text(encoding="utf-8") if archivo.exists() else None
    r = subprocess.run(["gh", "api", f"repos/{propietario}/{repo}/contents/docs/aprendizajes.md",
                        "-H", "Accept: application/vnd.github.raw"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        if "404" in (r.stderr or "") or "Not Found" in (r.stdout or "") + (r.stderr or ""):
            return None
        raise SystemExit(f"No se pudo leer {repo} en GitHub: {(r.stderr or r.stdout).strip()[:300]}")
    return r.stdout


def entradas(texto):
    """[{id, titulo, tipo, campos, cuerpo}] de un docs/aprendizajes.md."""
    marcas = list(ENTRADA.finditer(texto))
    salida = []
    for i, m in enumerate(marcas):
        if m.group(2).strip().startswith("<"):
            continue  # la entrada de ejemplo de la plantilla
        cuerpo = texto[m.end():marcas[i + 1].start() if i + 1 < len(marcas) else len(texto)]
        campos = {sin_tildes(k.strip()): v.strip() for k, v in CAMPO.findall(cuerpo)}
        tipo = sin_tildes(campos.get("tipo", "")).split()[0] if campos.get("tipo") else ""
        salida.append({"id": m.group(1), "titulo": m.group(2).strip(), "tipo": tipo, "campos": campos,
                       "cuerpo": m.group(2) + "\n" + cuerpo})
    return salida


def avisos(texto, nombres):
    encontrados = []
    for nombre in nombres:
        if len(nombre) >= 4 and re.search(rf"\b{re.escape(sin_tildes(nombre))}\b", sin_tildes(texto)):
            encontrados.append(f"nombra al cliente («{nombre}»)")
    for que, patron in SOSPECHOSOS:
        m = patron.search(texto)
        if m:
            encontrados.append(f"parece {que} («{m.group(0).strip()[:40]}»)")
    for m in TELEFONO.finditer(texto):
        valor = m.group(0).strip()
        if sum(c.isdigit() for c in valor) >= 9 and not FECHA.match(valor):
            encontrados.append(f"parece un teléfono («{valor[:40]}»)")
            break
    return encontrados


def leer_registro():
    ruta = RAIZ / REGISTRO
    if not ruta.exists():
        return set()
    with open(ruta, encoding="utf-8", newline="") as f:
        return {(r["repositorio"], r["id"]) for r in csv.DictReader(f)}


def registrar(clave, decision, nota):
    if ":" not in clave:
        sys.exit("--registrar espera <repositorio>:<A-NNN>, por ejemplo cliente-proyecto:A-001.")
    repo, ident = clave.split(":", 1)
    if (repo, ident) in leer_registro():
        sys.exit(f"{repo}:{ident} ya tiene una decisión registrada en {REGISTRO.as_posix()}.")
    ruta = RAIZ / REGISTRO
    nuevo = not ruta.exists()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        if nuevo:
            w.writerow(["fecha", "repositorio", "id", "decision", "nota"])
        w.writerow([date.today().isoformat(), repo, ident, decision, nota])
    print(f"Registrado: {repo}:{ident} → {decision}.")
    return 0


def main():
    _nucleo.preparar_consola()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--local", action="store_true", help="leer de proyectos/ en vez de GitHub")
    ap.add_argument("--registrar", metavar="REPOSITORIO:A-NNN", help="anotar la decisión sobre un aprendizaje")
    ap.add_argument("--decision", choices=DECISIONES)
    ap.add_argument("--nota", default="", help="destino o motivo, en pocas palabras")
    a = ap.parse_args()

    if _nucleo.es_mantenedor(RAIZ):
        sys.exit("Esta carpeta es el núcleo que mantienes: los aprendizajes se recogen en una instancia.")
    if a.registrar:
        if not a.decision:
            sys.exit("Indica la --decision: rubro, metodo o descartado.")
        return registrar(a.registrar, a.decision, a.nota)

    propietario = ""
    config = RAIZ / ".fabrica" / "config.json"
    if config.exists():
        propietario = (json.loads(config.read_text(encoding="utf-8")).get("github") or {}).get("propietario", "")
    hechos = leer_registro()
    total, con_aviso, bloques = 0, 0, []
    for repo, cliente, rubro, nombres in proyectos():
        texto = leer_aprendizajes(repo, propietario, a.local)
        pendientes = [e for e in entradas(texto or "") if (repo, e["id"]) not in hechos]
        if not pendientes:
            continue
        lineas = [f"## {repo} · rubro {rubro or 'sin definir'}"]
        for e in pendientes:
            total += 1
            lineas.append(f"- {e['id']} · {e['titulo']} [{e['tipo'] or 'sin tipo'}]")
            for campo in ("que aprendimos", "propuesta"):
                if e["campos"].get(campo):
                    lineas.append(f"  {campo.capitalize()}: {e['campos'][campo]}")
            encontrados = avisos(e["cuerpo"], nombres)
            if encontrados:
                con_aviso += 1
                lineas.append("  AVISO DE LIMPIEZA: " + "; ".join(encontrados))
        bloques.append("\n".join(lineas))

    if not total:
        print("No hay aprendizajes nuevos en los proyectos de esta instancia.")
        return 0
    print(f"Aprendizajes nuevos: {total}" + (f" ({con_aviso} con aviso de limpieza)" if con_aviso else "") + "\n")
    print("\n\n".join(bloques))
    print("\nPara anotar una decisión: python .fabrica/scripts/recoger_aprendizajes.py --registrar "
          "<repositorio>:<A-NNN> --decision rubro|metodo|descartado [--nota \"...\"]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
