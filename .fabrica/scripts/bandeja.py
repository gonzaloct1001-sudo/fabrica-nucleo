#!/usr/bin/env python3
"""La bandeja de la Dirección: lo que espera su decisión en los proyectos de esta instancia, para resolverlo desde una
conversación sin entrar a GitHub (skill bandeja-direccion).

Uso, desde la raíz de la instancia:
    python .fabrica/scripts/bandeja.py
        resumen de todos los proyectos: solo cifras (preguntas, PRs y última corrida), sin textos
    python .fabrica/scripts/bandeja.py --cliente <slug>
        detalle de un cliente: sus preguntas, sus PRs y la última entrada de su bitácora de corridas
    python .fabrica/scripts/bandeja.py --responder <repositorio>#<n> --texto "<respuesta>"
        publica la respuesta de la Dirección en esa pregunta o PR, con una marca que dice de dónde vino
    python .fabrica/scripts/bandeja.py --pedido <repositorio> --titulo "<título>" --texto "<cuerpo>"
        crea un pedido para el motor, sin etiquetas: la próxima corrida lo clasifica
    python .fabrica/scripts/bandeja.py --integrar <repositorio>#<n>
        integra un PR, solo si sus controles están en verde y su rama está al día

- Los proyectos salen de las fichas de clientes/ (tabla "Proyectos"; los cerrados no cuentan) y se leen de GitHub
  con la cuenta de config.json.
- Aislamiento (nucleo/aislamiento.md): el resumen muestra solo cifras, igual que el panel. El detalle se abre de a un
  cliente, y en una misma conversación no se abre el de otro.
- Lo que se publica queda firmado con la cuenta de la Dirección, que es como el motor reconoce sus respuestas. Por eso
  se publica solo lo que la Dirección decidió, con sus palabras.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _kit  # noqa: E402
import _nucleo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
ESPERA = "espera:direccion"
BITACORA = "Bitácora de corridas de la fábrica"
MARCA = "_Respuesta de la Dirección, tomada en una conversación y publicada con la bandeja de la fábrica._"
MARCA_PEDIDO = "_Pedido de la Dirección, creado con la bandeja de la fábrica._"
REF = re.compile(r"^([a-z0-9]+(?:-[a-z0-9]+)*)#(\d+)$")
VERDE = {"SUCCESS", "NEUTRAL", "SKIPPED"}
ROJO = {"FAILURE", "CANCELLED", "TIMED_OUT", "ERROR", "ACTION_REQUIRED", "STARTUP_FAILURE", "STALE"}


def gh(*args):
    """Corre gh y devuelve (código, salida o error). FABRICA_GH lo reemplaza en las pruebas."""
    falso = os.environ.get("FABRICA_GH", "")
    cmd = ([sys.executable, falso] if falso.endswith(".py") else [falso or "gh"]) + list(args)
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return r.returncode, (r.stderr or r.stdout or "").strip()
    return 0, r.stdout or ""


def gh_json(*args):
    rc, salida = gh(*args)
    if rc != 0:
        raise SystemExit(f"GitHub no respondió a «{' '.join(args[:2])}»: {salida[:300]}")
    return json.loads(salida or "null")


def proyectos():
    """{cliente: [repositorio, ...]} según las fichas de la instancia, sin los proyectos cerrados."""
    salida = {}
    for ficha in sorted((RAIZ / "clientes").glob("*/cliente.md")):
        repos = [f[2] for f in _kit.tabla(ficha, "Proyectos")
                 if len(f) >= 3 and not (len(f) >= 4 and f[3].lower() == "cerrado")]
        if repos:
            salida[ficha.parent.name] = repos
    return salida


def estado_ci(checks):
    """verde, rojo, pendiente o sin CI, a partir del statusCheckRollup de gh."""
    if not checks:
        return "sin CI"
    finales = [(c.get("conclusion") or c.get("state") or "").upper() for c in checks]
    if any(f in ROJO for f in finales):
        return "rojo"
    if all(f in VERDE for f in finales):
        return "verde"
    return "pendiente"


def leer(propietario, repo):
    """Preguntas que esperan a la Dirección, PRs abiertos y última entrada de la bitácora de un proyecto."""
    base = f"repos/{propietario}/{repo}"
    preguntas = [i for i in gh_json("api", f"{base}/issues?labels={quote(ESPERA)}&state=open&per_page=100")
                 if "pull_request" not in i]
    prs = gh_json("pr", "list", "-R", f"{propietario}/{repo}", "--state", "open", "--json",
                  "number,title,isDraft,statusCheckRollup,url")
    bitacora = [i for i in gh_json("api", f"{base}/issues?state=open&per_page=100") if i.get("title") == BITACORA]
    ultima = None
    if bitacora and bitacora[0].get("comments"):
        pagina = gh_json("api", f"{base}/issues/{bitacora[0]['number']}/comments?per_page=1"
                                f"&page={bitacora[0]['comments']}")
        ultima = pagina[0] if pagina else None
    return {"preguntas": preguntas, "prs": prs, "ultima": ultima}


def cuando(marca):
    """2026-11-03T09:12:44Z → 2026-11-03 09:12 UTC."""
    return f"{marca[:10]} {marca[11:16]} UTC" if marca else "—"


def resumen(propietario, todos):
    out = [f"# Bandeja de la Dirección · {date.today().isoformat()}", "",
           "| Cliente | Proyecto | Preguntas sin respuesta | Respondidas, por aplicar | PRs abiertos | PRs en verde "
           "| Última corrida |", "|---|---|---|---|---|---|---|"]
    pendientes = []
    for cliente, repos in todos.items():
        for repo in repos:
            try:
                d = leer(propietario, repo)
            except SystemExit as e:
                out.append(f"| {cliente} | {repo} | no se pudo leer: {str(e)[:120]} | | | | |")
                continue
            sin = sum(1 for p in d["preguntas"] if not p.get("comments"))
            con = len(d["preguntas"]) - sin
            verdes = sum(1 for p in d["prs"] if not p.get("isDraft") and estado_ci(p.get("statusCheckRollup")) == "verde")
            out.append(f"| {cliente} | {repo} | {sin} | {con} | {len(d['prs'])} | {verdes} | "
                       f"{cuando((d['ultima'] or {}).get('created_at'))} |")
            if sin or d["prs"]:
                pendientes.append(cliente)
    out.append("")
    if pendientes:
        clientes = ", ".join(dict.fromkeys(pendientes))
        out.append(f"Esperan tu decisión: {clientes}. Detalle de un cliente: python .fabrica/scripts/bandeja.py "
                   "--cliente <slug>")
        out.append("El detalle se abre de a un cliente por conversación (nucleo/aislamiento.md).")
    else:
        out.append("Nada espera tu decisión.")
    print("\n".join(out))
    return 0


def recorte(texto, maximo=1200):
    texto = (texto or "").strip()
    return texto if len(texto) <= maximo else texto[:maximo].rstrip() + " […]"


def detalle(propietario, cliente, repos):
    out = [f"# Bandeja de la Dirección · cliente {cliente}"]
    for repo in repos:
        d = leer(propietario, repo)
        out += ["", f"## {repo}", "", f"### Preguntas que esperan tu decisión ({len(d['preguntas'])})"]
        for p in d["preguntas"]:
            estado = "respondida: la aplica la próxima corrida" if p.get("comments") else "sin respuesta"
            out += [f"- #{p['number']} · {p['title']} · {estado}", f"  {p.get('html_url', '')}"]
            out += [f"  > {linea}" for linea in recorte(p.get("body")).splitlines()]
        out += ["", f"### PRs abiertos ({len(d['prs'])})"]
        for p in d["prs"]:
            borrador = " · borrador" if p.get("isDraft") else ""
            out += [f"- #{p['number']} · {p['title']} · controles en {estado_ci(p.get('statusCheckRollup'))}"
                    f"{borrador}", f"  {p.get('url', '')}"]
        if d["ultima"]:
            out += ["", f"### Última corrida ({cuando(d['ultima'].get('created_at'))})"]
            out += [f"> {linea}" for linea in (d["ultima"].get("body") or "").strip().splitlines()[:15]]
    print("\n".join(out))
    return 0


def referencia(texto, validos):
    m = REF.match(texto or "")
    if not m:
        sys.exit(f"«{texto}» no es una referencia válida: usa <repositorio>#<número>, por ejemplo propio-panel#12.")
    if m.group(1) not in validos:
        sys.exit(f"{m.group(1)} no es un proyecto activo de esta instancia (tabla Proyectos de las fichas de clientes/).")
    return m.group(1), int(m.group(2))


def responder(propietario, repo, numero, texto):
    if not texto.strip():
        sys.exit("Falta la respuesta: --texto \"...\".")
    item = gh_json("api", f"repos/{propietario}/{repo}/issues/{numero}")
    if item.get("state") != "open":
        sys.exit(f"{repo}#{numero} está cerrado: la respuesta ya no le llega al motor.")
    etiquetas = {e.get("name") for e in item.get("labels", [])}
    if "pull_request" not in item and ESPERA not in etiquetas:
        print(f"Aviso: {repo}#{numero} no tiene la etiqueta {ESPERA}; el motor podría no leerlo como respuesta.")
    hecho = gh_json("api", f"repos/{propietario}/{repo}/issues/{numero}/comments", "-f",
                    f"body={texto.strip()}\n\n{MARCA}")
    print(f"Publicada en {repo}#{numero}: {hecho.get('html_url', '')}")
    return 0


def pedido(propietario, repo, titulo, texto):
    if not titulo.strip() or not texto.strip():
        sys.exit("Un pedido necesita --titulo y --texto (qué necesitas, por qué ahora y cómo sabes que está listo).")
    hecho = gh_json("api", f"repos/{propietario}/{repo}/issues", "-f", f"title={titulo.strip()}", "-f",
                    f"body={texto.strip()}\n\n{MARCA_PEDIDO}")
    print(f"Pedido creado: {repo}#{hecho.get('number')} {hecho.get('html_url', '')}")
    print("La próxima corrida del motor lo clasifica.")
    return 0


def integrar(propietario, repo, numero):
    pr = gh_json("pr", "view", str(numero), "-R", f"{propietario}/{repo}", "--json",
                 "state,isDraft,mergeable,mergeStateStatus,statusCheckRollup,title,url,baseRefName")
    problemas = []
    if pr.get("state") != "OPEN":
        problemas.append("no está abierto")
    if pr.get("isDraft"):
        problemas.append("es un borrador")
    ci = estado_ci(pr.get("statusCheckRollup"))
    if ci != "verde":
        problemas.append(f"sus controles están en {ci}")
    if pr.get("mergeable") != "MERGEABLE":
        problemas.append("GitHub no lo da por integrable (conflictos, o todavía lo está calculando)")
    if pr.get("mergeStateStatus") in ("BEHIND", "DIRTY"):
        problemas.append(f"su rama no está al día con {pr.get('baseRefName') or 'la rama principal'}")
    if problemas:
        sys.exit(f"No se integra {repo}#{numero}: " + "; ".join(problemas) + ".")
    rc, salida = gh("pr", "merge", str(numero), "-R", f"{propietario}/{repo}", "--merge", "--delete-branch")
    if rc != 0:
        sys.exit(f"GitHub no integró {repo}#{numero}: {salida[:300]}")
    print(f"Integrado: {repo}#{numero} · {pr.get('title', '')}")
    return 0


def main():
    _nucleo.preparar_consola()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    accion = ap.add_mutually_exclusive_group()
    accion.add_argument("--cliente", help="detalle de un cliente")
    accion.add_argument("--responder", metavar="REPOSITORIO#N", help="publicar la respuesta de la Dirección")
    accion.add_argument("--pedido", metavar="REPOSITORIO", help="crear un pedido para el motor")
    accion.add_argument("--integrar", metavar="REPOSITORIO#N", help="integrar un PR en verde")
    ap.add_argument("--titulo", default="", help="título del pedido")
    ap.add_argument("--texto", default="", help="respuesta o cuerpo del pedido, con las palabras de la Dirección")
    a = ap.parse_args()

    if _nucleo.es_mantenedor(RAIZ):
        sys.exit("Esta carpeta es el núcleo que mantienes: la bandeja se usa en una instancia.")
    config = RAIZ / ".fabrica" / "config.json"
    propietario = ""
    if config.exists():
        propietario = (json.loads(config.read_text(encoding="utf-8")).get("github") or {}).get("propietario", "")
    if not propietario:
        sys.exit("Falta github.propietario en .fabrica/config.json: la bandeja lee los proyectos desde GitHub.")
    todos = proyectos()
    validos = {r for repos in todos.values() for r in repos}

    if a.responder:
        return responder(propietario, *referencia(a.responder, validos), a.texto)
    if a.integrar:
        return integrar(propietario, *referencia(a.integrar, validos))
    if a.pedido:
        if a.pedido not in validos:
            sys.exit(f"{a.pedido} no es un proyecto activo de esta instancia.")
        return pedido(propietario, a.pedido, a.titulo, a.texto)
    if a.cliente:
        if a.cliente not in todos:
            sys.exit(f"El cliente '{a.cliente}' no tiene proyectos activos. Clientes con proyectos: "
                     f"{', '.join(todos) or 'ninguno'}.")
        return detalle(propietario, a.cliente, todos[a.cliente])
    if not todos:
        print("Esta instancia todavía no tiene proyectos activos.")
        return 0
    return resumen(propietario, todos)


if __name__ == "__main__":
    sys.exit(main())
