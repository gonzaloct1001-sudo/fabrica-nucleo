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
    python .fabrica/scripts/bandeja.py --esperar <repositorio> [--desde <AAAA-MM-DDTHH:MM:SSZ>] [--minutos 25]
        espera a que la corrida de ese proyecto termine (deja su entrada en la bitácora después de --desde, por
        defecto ahora) y la muestra: es lo que permite avanzar por relevos (nucleo/motor.md, "El ritmo")
    python .fabrica/scripts/bandeja.py --pagina <repositorio>#<n> [--carpeta <ruta local>] [--salida <archivo>]
        arma la página de una decisión: qué se pide, lo que el motor decidió por la Dirección, los documentos con su
        enlace y los controles; las secciones en lenguaje simple quedan marcadas para completarlas antes de mostrarla
    python .fabrica/scripts/bandeja.py --jornada <repositorio> [--fecha <AAAA-MM-DD>] [--salida <archivo>]
        arma la página de cierre de una jornada: corridas, PRs integrados, preguntas cerradas y lo que sigue
    python .fabrica/scripts/bandeja.py --diario <cliente> [--desde <AAAA-MM-DDTHH:MM:SSZ>] [--salida <archivo>]
        arma el resumen diario de un cliente: lo que avanzó desde --desde (por defecto, las últimas 24 horas), y cada
        decisión pendiente con lo necesario para decidirla; la tarea de la mañana lo publica siempre en la misma página

- Los proyectos salen de las fichas de clientes/ (tabla "Proyectos"; los cerrados no cuentan) y se leen de GitHub
  con la cuenta de config.json.
- Aislamiento (nucleo/aislamiento.md): el resumen muestra solo cifras, igual que el panel. El detalle se abre de a un
  cliente, y en una misma conversación no se abre el de otro.
- Lo que se publica queda firmado con la cuenta de la Dirección, que es como el motor reconoce sus respuestas. Por eso
  se publica solo lo que la Dirección decidió, con sus palabras.
- Las páginas usan nucleo/plantillas/pagina-direccion.html, o instancia/plantillas/pagina-direccion.html si la
  instancia tiene la suya. Todo texto que viene de GitHub se escapa: un issue no puede meter código en la página.
- GitHub se usa solo por la API REST (gh api), así que la bandeja funciona igual en el computador de la Dirección y
  en una sesión en la nube.
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from datetime import time as hora_del_dia
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
HORA_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
VERDE = {"SUCCESS", "NEUTRAL", "SKIPPED"}
ROJO = {"FAILURE", "CANCELLED", "TIMED_OUT", "ERROR", "ACTION_REQUIRED", "STARTUP_FAILURE", "STALE"}
DECISION = re.compile(r"Decisi[oó]n:\s*")
COMPLETAR = "data-completar"
# archivos que una persona no puede leer ni revisar: si un PR los trae, la página lo destaca
NO_SE_LEEN = re.compile(r"(^|/)__pycache__/|\.(pyc|pyo|exe|dll|so|dylib|class|jar|whl|egg|zip|bin)$", re.I)


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


def ultimos_controles(checks):
    """Cada control con su última corrida: si corrió de nuevo (por ejemplo, al ponerle una etiqueta al PR), la
    anterior ya no cuenta, igual que en GitHub."""
    ultimos, sin_nombre = {}, []
    for c in checks or []:
        nombre = c.get("name") or c.get("context")
        if not nombre:
            sin_nombre.append(c)
            continue
        clave = (c.get("workflowName") or "", nombre)
        if clave not in ultimos or (c.get("startedAt") or "") >= (ultimos[clave].get("startedAt") or ""):
            ultimos[clave] = c
    return list(ultimos.values()) + sin_nombre


def estado_ci(checks):
    """verde, rojo, pendiente o sin CI, a partir del statusCheckRollup de gh."""
    checks = ultimos_controles(checks)
    if not checks:
        return "sin CI"
    finales = [(c.get("conclusion") or c.get("state") or "").upper() for c in checks]
    if any(f in ROJO for f in finales):
        return "rojo"
    if all(f in VERDE for f in finales):
        return "verde"
    return "pendiente"


# --- GitHub solo por REST (gh api) ---------------------------------------------------------------------------------
# Así la bandeja funciona igual en el computador de la Dirección y en una sesión en la nube, donde `gh pr` y
# `gh issue` no corren porque usan GraphQL (nucleo/motor.md). Estas funciones devuelven los campos con los nombres
# que usa el resto de la bandeja.

def etiquetas(item):
    return [x.get("name") for x in item.get("labels") or []]


def controles(base, sha):
    """Los controles de un commit: cada corrida con el nombre de su flujo, y los estados de servicios externos."""
    if not sha:
        return []
    flujos = {r.get("check_suite_id"): r.get("name") for r in
              gh_json("api", f"{base}/actions/runs?head_sha={sha}&per_page=100").get("workflow_runs", [])}
    corridas = gh_json("api", f"{base}/commits/{sha}/check-runs?filter=all&per_page=100").get("check_runs", [])
    estados = gh_json("api", f"{base}/commits/{sha}/status").get("statuses", [])
    return ([{"name": c.get("name"), "workflowName": flujos.get((c.get("check_suite") or {}).get("id"), ""),
              "startedAt": c.get("started_at") or "", "status": (c.get("status") or "").upper(),
              "conclusion": (c.get("conclusion") or "").upper()} for c in corridas]
            + [{"context": s.get("context"), "state": (s.get("state") or "").upper()} for s in estados])


def prs_abiertos(base):
    return [{"number": p.get("number"), "title": p.get("title"), "url": p.get("html_url"),
             "isDraft": bool(p.get("draft")), "labels": etiquetas(p),
             "statusCheckRollup": controles(base, (p.get("head") or {}).get("sha"))}
            for p in gh_json("api", f"{base}/pulls?state=open&per_page=100")]


def un_pr(base, numero, con_archivos=False):
    """Un PR, con su estado como lo nombra GitHub: OPEN, MERGED o CLOSED."""
    p = gh_json("api", f"{base}/pulls/{numero}")
    cabeza, destino = p.get("head") or {}, p.get("base") or {}
    pr = {"number": p.get("number"), "title": p.get("title"), "url": p.get("html_url"),
          "state": "MERGED" if p.get("merged_at") else (p.get("state") or "").upper(),
          "isDraft": bool(p.get("draft")), "labels": etiquetas(p),
          "mergeable": {True: "MERGEABLE", False: "CONFLICTING"}.get(p.get("mergeable"), "UNKNOWN"),
          "mergeStateStatus": (p.get("mergeable_state") or "").upper(),
          "baseRefName": destino.get("ref"), "headRefName": cabeza.get("ref"), "headRefOid": cabeza.get("sha"),
          "mismoRepositorio": bool(cabeza.get("repo"))
                              and (cabeza.get("repo") or {}).get("full_name")
                              == (destino.get("repo") or {}).get("full_name"),
          "statusCheckRollup": controles(base, cabeza.get("sha"))}
    if con_archivos:
        pr["files"] = [{"path": f.get("filename"), "additions": f.get("additions", 0),
                        "deletions": f.get("deletions", 0)}
                       for f in gh_json("api", f"{base}/pulls/{numero}/files?per_page=100")]
    return pr


def leer(propietario, repo):
    """Preguntas que esperan a la Dirección, PRs abiertos y última entrada de la bitácora de un proyecto."""
    base = f"repos/{propietario}/{repo}"
    preguntas = [i for i in gh_json("api", f"{base}/issues?labels={quote(ESPERA)}&state=open&per_page=100")
                 if "pull_request" not in i]
    return {"preguntas": preguntas, "prs": prs_abiertos(base), "ultima": ultima_corrida(base)}


def ultima_corrida(base):
    """Último comentario de la bitácora de corridas del proyecto, o None si todavía no hay."""
    bitacora = [i for i in gh_json("api", f"{base}/issues?state=open&per_page=100") if i.get("title") == BITACORA]
    if not bitacora or not bitacora[0].get("comments"):
        return None
    pagina = gh_json("api", f"{base}/issues/{bitacora[0]['number']}/comments?per_page=1"
                            f"&page={bitacora[0]['comments']}")
    return pagina[0] if pagina else None


def esperar(propietario, repo, desde, minutos):
    """Espera la primera entrada de la bitácora posterior a `desde`: la corrida terminó."""
    base = f"repos/{propietario}/{repo}"
    pausa = float(os.environ.get("FABRICA_ESPERA_SEG", "20"))
    limite = time.monotonic() + minutos * 60
    while True:
        try:
            ultima = ultima_corrida(base)
        except SystemExit:
            ultima = None  # un corte de red no termina la espera
        if ultima and (ultima.get("created_at") or "") > desde:
            print(f"Corrida terminada en {repo} ({cuando(ultima.get('created_at'))}):")
            print("\n".join(f"> {linea}" for linea in (ultima.get("body") or "").strip().splitlines()[:15]))
            return 0
        if time.monotonic() >= limite:
            sys.exit(f"En {minutos:g} min no apareció una entrada nueva en la bitácora de {repo}: la corrida sigue, o "
                     "falló antes de trabajar (nucleo/motor.md, \"Diagnosticar una corrida\").")
        time.sleep(pausa)


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
    base = f"repos/{propietario}/{repo}"
    pr = un_pr(base, numero)
    for _ in range(3):  # GitHub calcula si se puede integrar al pedirlo: si todavía no sabe, se vuelve a mirar
        if pr.get("mergeable") != "UNKNOWN" or pr.get("state") != "OPEN":
            break
        time.sleep(min(float(os.environ.get("FABRICA_ESPERA_SEG", "3")), 3))
        pr = un_pr(base, numero)
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
    rc, salida = gh("api", "-X", "PUT", f"{base}/pulls/{numero}/merge", "-f", "merge_method=merge")
    if rc != 0:
        sys.exit(f"GitHub no integró {repo}#{numero}: {salida[:300]}")
    print(f"Integrado: {repo}#{numero} · {pr.get('title', '')}")
    if pr.get("mismoRepositorio") and pr.get("headRefName"):
        rc, salida = gh("api", "-X", "DELETE", f"{base}/git/refs/heads/{quote(pr['headRefName'], safe='/')}")
        if rc != 0:
            print(f"Aviso: no se pudo borrar la rama {pr['headRefName']}: {salida[:200]}")
    return 0


# --- Páginas para la Dirección -------------------------------------------------------------------------------------

def zona(config):
    """Zona horaria de la instancia (zona_horaria de config.json); UTC si falta o el sistema no la conoce."""
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(config.get("zona_horaria") or "UTC")
    except Exception:
        return timezone.utc


def instante(marca):
    return datetime.strptime(marca, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def e(texto):
    """Texto de GitHub escapado para la página, con `código` en monoespaciado."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(str(texto or "")))


def enlace(url, texto):
    return f'<a href="{html.escape(url or "", quote=True)}">{e(texto)}</a>' if url else e(texto)


def completar(que):
    return f'<p class="completar" {COMPLETAR}>Por completar: {html.escape(que)}</p>'


def seccion(titulo, cuerpo):
    return f"<section>\n<h2>{html.escape(titulo)}</h2>\n{cuerpo}\n</section>"


def decisiones(*textos):
    """Las decisiones que el motor tomó por la Dirección ("Decisión: qué — por qué — si es errada, …"), sin repetir."""
    vistas = []
    for texto in textos:
        for linea in (texto or "").splitlines():
            for parte in DECISION.split(linea)[1:]:
                parte = re.sub(r"\s*Más [^.]*\.?\s*$", "", parte).strip(" .-")
                if parte and parte not in vistas:
                    vistas.append(parte)
    return vistas


def tarjetas_decisiones(lista):
    if not lista:
        return "<p>El motor no registró decisiones tomadas por ti.</p>"
    tarjetas = []
    for d in lista:
        trozos = [t.strip() for t in d.split(" — ")]
        si = next((t for t in trozos[1:] if t.lower().startswith("si es errad")), "")
        porque = " — ".join(t for t in trozos[1:] if t != si)
        tarjetas.append('<div class="card"><span class="tag">la fábrica decidió por ti</span>'
                        f'<div class="v">{e(trozos[0])}</div>' + (f"<p>{e(porque)}</p>" if porque else "")
                        + (f'<div class="si">{e(si[0].upper() + si[1:])}</div>' if si else "") + "</div>")
    return '<div class="cards">' + "".join(tarjetas) + "</div>"


def pie(tz):
    ahora = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
    return f"<footer>Armada con la bandeja de la fábrica el {ahora} ({tz}).</footer>"


def armar(titulo, descripcion, partes, salida):
    propia = RAIZ / "instancia" / "plantillas" / "pagina-direccion.html"
    plantilla = propia if propia.exists() else RAIZ / "nucleo" / "plantillas" / "pagina-direccion.html"
    texto = (plantilla.read_text(encoding="utf-8").replace("{{titulo}}", html.escape(titulo))
             .replace("{{descripcion}}", html.escape(descripcion, quote=True))
             .replace("{{contenido}}", "\n\n".join(partes)))
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(texto, encoding="utf-8")
    print(f"Página lista: {salida}")
    pendientes = texto.count(COMPLETAR)
    if pendientes:
        print(f"Antes de mostrarla, completa {pendientes} sección(es) marcadas con {COMPLETAR}, en lenguaje simple.")
    return 0


def decision(propietario, repo, numero, carpeta):
    """Lo que hay en GitHub sobre una decisión (una pregunta o un PR), ya en HTML: sirve a su página y al resumen."""
    base = f"repos/{propietario}/{repo}"
    item = gh_json("api", f"{base}/issues/{numero}")
    comentarios = gh_json("api", f"{base}/issues/{numero}/comments?per_page=100") if item.get("comments") else []
    es_pr = "pull_request" in item
    d = {"titulo": item.get("title") or f"{repo}#{numero}", "es_pr": es_pr, "documentos": "", "controles": "",
         "decisiones": tarjetas_decisiones(decisiones(item.get("body"), *(c.get("body") for c in comentarios)))}
    estado = "abierto" if item.get("state") == "open" else "cerrado"
    hechos = [f"<span><b>{e(repo)}</b> · {'PR' if es_pr else 'pregunta'} #{numero}</span>",
              f"<span>{enlace(item.get('html_url'), 'Abrir en GitHub')}</span>"]
    if es_pr:
        pr = un_pr(base, numero, con_archivos=True)
        estado = {"OPEN": "abierto", "MERGED": "integrado", "CLOSED": "cerrado"}.get(pr.get("state"), estado)
        if pr.get("isDraft"):
            estado += ", borrador"
        ci = estado_ci(pr.get("statusCheckRollup"))
        hechos.append(f'<span>Controles <span class="estado {({"verde": "ok", "rojo": "mal"}).get(ci, "")}">{ci}'
                      "</span></span>")
        hechos += [f'<span class="tag">{e(x)}</span>' for x in pr.get("labels") or [] if x.startswith("riesgo:")]
        if pr.get("state") == "OPEN":
            d["pide"] = (f"<p>Si das el sí, se integra este PR a la rama principal de <b>{e(repo)}</b> y el motor "
                         "sigue con el paso siguiente. Si no, dices qué cambiar: va como comentario al PR y la corrida "
                         "lo corrige.</p>")
        else:
            d["pide"] = f"<p>Este PR ya está {estado}: la página sirve para revisar lo que se hizo.</p>"
        filas = []
        for f in pr.get("files") or []:
            ruta = f.get("path", "")
            url = f"https://github.com/{propietario}/{repo}/blob/{pr.get('headRefOid', '')}/{quote(ruta)}"
            local = f'<span class="local">{e(Path(carpeta) / ruta)}</span>' if carpeta else ""
            if NO_SE_LEEN.search(ruta):
                local += '<span class="estado mal">nadie puede leerlo ni revisarlo: ¿por qué está aquí?</span>'
            filas.append(f"<tr><td>{enlace(url, ruta)}{local}</td>"
                         f'<td class="num">+{f.get("additions", 0)} −{f.get("deletions", 0)}</td></tr>')
        d["documentos"] = ('<div class="tabla"><table><thead><tr><th>Archivo</th><th>Líneas</th></tr></thead>'
                           f'<tbody>{"".join(filas)}</tbody></table></div>' if filas
                           else "<p>El PR no cambia archivos.</p>")
        lista = "".join(f"<li>{e(c.get('name') or c.get('context') or 'control')}: "
                        f"{e((c.get('conclusion') or c.get('state') or c.get('status') or '—').lower())}</li>"
                        for c in ultimos_controles(pr.get("statusCheckRollup")))
        d["controles"] = f"<ul>{lista}</ul>" if lista else "<p>Este proyecto no tiene CI.</p>"
    else:
        d["pide"] = f'<div class="texto">{e(recorte(item.get("body"), 4000))}</div>'
    hechos.insert(1, f"<span>Estado <b>{estado}</b></span>")
    d["hechos"] = "".join(hechos)
    return d


def pagina(propietario, repo, numero, carpeta, salida, tz):
    d = decision(propietario, repo, numero, carpeta)
    partes = [f'<header class="top"><span class="eyebrow">Para decidir</span><h1>{e(d["titulo"])}</h1>'
              f'<div class="facts">{d["hechos"]}</div></header>',
              seccion("Qué decides", d["pide"]),
              seccion("En simple", completar("qué cambia y para quién, en dos o tres frases, sin jerga.")),
              seccion("Cómo se ve", completar("bocetos de las pantallas o un diagrama, si cambia algo que se ve o se "
                                              "usa. Si no aplica, borra esta sección.")),
              seccion("Lo que la fábrica decidió por ti", d["decisiones"])]
    if d["es_pr"]:
        partes += [seccion("Documentos", d["documentos"]), seccion("Controles", d["controles"])]
    partes += [seccion("Si dices sí, si dices no", completar("qué pasa en cada caso y tu recomendación.")), pie(tz)]
    salida = salida or Path(tempfile.gettempdir()) / "fabrica-paginas" / f"{repo}-{numero}.html"
    return armar(f"Decisión {repo} #{numero}", f"Lo que se pide decidir en {repo}#{numero}: {d['titulo']}", partes,
                 salida)


def linea_de(texto, rotulo):
    """El texto que sigue a "- <rótulo>:" en una entrada de la bitácora."""
    m = re.search(rf"^\s*-\s*{rotulo}:\s*(.+)$", texto or "", re.M | re.I)
    return m.group(1).strip() if m else ""


def actividad(propietario, repo, inicio, fin):
    """Lo que pasó en un proyecto entre dos instantes UTC: corridas, PRs integrados, preguntas cerradas, las
    decisiones del motor y los eventos en orden."""
    base = f"repos/{propietario}/{repo}"
    desde = inicio.strftime("%Y-%m-%dT%H:%M:%SZ")

    def dentro(marca):
        return bool(marca) and inicio <= instante(marca) < fin

    bitacora = [i for i in gh_json("api", f"{base}/issues?state=open&per_page=100") if i.get("title") == BITACORA]
    corridas = [c for c in gh_json("api", f"{base}/issues/{bitacora[0]['number']}/comments?since={desde}"
                                          "&per_page=100") if dentro(c.get("created_at"))] if bitacora else []
    integrados = [{"number": p.get("number"), "title": p.get("title"), "url": p.get("html_url"),
                   "mergedAt": p.get("merged_at")}
                  for p in gh_json("api", f"{base}/pulls?state=closed&sort=updated&direction=desc&per_page=100")
                  if dentro(p.get("merged_at"))]
    cerrados = [i for i in gh_json("api", f"{base}/issues?state=closed&since={desde}&per_page=100")
                if "pull_request" not in i and dentro(i.get("closed_at"))]
    eventos = []
    for c in corridas:
        primera = ((c.get("body") or "").strip().splitlines() or [""])[0]
        paso = primera.split("paso:", 1)[1].strip() if "paso:" in primera else primera
        eventos.append((c["created_at"], f"Corrida: {paso}", linea_de(c.get("body"), "Resultado"), c.get("html_url")))
    eventos += [(p["mergedAt"], f"Integrado el PR #{p['number']}: {p.get('title', '')}", "", p.get("url"))
                for p in integrados]
    eventos += [(i["closed_at"], f"Cerrado #{i['number']}: {i.get('title', '')}", "", i.get("html_url"))
                for i in cerrados]
    eventos.sort(key=lambda x: x[0])
    return {"corridas": corridas, "integrados": integrados, "cerrados": cerrados, "eventos": eventos,
            "tomadas": decisiones(*(c.get("body") for c in corridas))}


def cifras(lista):
    return '<div class="cifras">' + "".join(f'<div class="cifra"><b>{n}</b><span>{t}</span></div>'
                                            for n, t in lista) + "</div>"


def en_orden(eventos, tz, formato="%H:%M"):
    items = "".join(f'<li><span class="hora">{instante(t).astimezone(tz).strftime(formato)}</span>'
                    f'<span class="que">{enlace(url, que)}</span>'
                    + (f'<span class="donde">{e(det)}</span>' if det else "") + "</li>"
                    for t, que, det, url in eventos)
    return f'<ol class="dia">{items}</ol>'


def lo_que_sigue(corrida):
    """Esperan tu decisión, Bloqueos y Próximo paso, tal como los dejó una entrada de la bitácora."""
    return "".join(f"<li><b>{r}:</b> {e(t)}</li>" for r, t in
                   ((r, linea_de(corrida, r)) for r in ("Esperan tu decisión", "Bloqueos", "Próximo paso")) if t)


def jornada(propietario, repo, dia, salida, tz):
    inicio = datetime.combine(dia, hora_del_dia.min, tzinfo=tz).astimezone(timezone.utc)
    fin = datetime.combine(dia + timedelta(days=1), hora_del_dia.min, tzinfo=tz).astimezone(timezone.utc)
    a = actividad(propietario, repo, inicio, fin)
    hechos = f"<span><b>{e(repo)}</b></span><span>{dia.isoformat()}</span><span>horas en {e(tz)}</span>"
    partes = [f'<header class="top"><span class="eyebrow">Cierre de jornada</span><h1>Lo que pasó en {e(repo)}</h1>'
              f'<div class="facts">{hechos}</div></header>',
              cifras([(len(a["corridas"]), "corridas del motor"), (len(a["integrados"]), "PRs integrados"),
                      (len(a["cerrados"]), "preguntas o pedidos cerrados"),
                      (len(a["tomadas"]), "decisiones que tomó la fábrica")]),
              seccion("Lo más importante", completar("en tres o cuatro líneas, qué quedó decidido y qué cambia para "
                                                     "el negocio.")),
              seccion("El día en orden", en_orden(a["eventos"], tz) if a["eventos"]
                      else "<p>Ese día no hubo corridas, integraciones ni cierres.</p>"),
              seccion("Lo que la fábrica decidió por ti", tarjetas_decisiones(a["tomadas"]))]
    sigue = lo_que_sigue(a["corridas"][-1].get("body") if a["corridas"] else "")
    partes += [seccion("Lo que sigue", f"<ul>{sigue}</ul>" if sigue else
                       completar("qué viene después; la última corrida no lo dejó escrito.")), pie(tz)]
    salida = salida or Path(tempfile.gettempdir()) / "fabrica-paginas" / f"{repo}-jornada-{dia.isoformat()}.html"
    return armar(f"Jornada {repo} {dia.strftime('%d-%m')}", f"Cierre de la jornada del {dia.isoformat()} en {repo}.",
                 partes, salida)


def diario(propietario, cliente, repos, desde, salida, tz):
    """El resumen diario de un cliente (nucleo/autonomia.md): lo que avanzó desde `desde`, lo que espera a la
    Dirección con todo lo necesario para decidir, y cómo responder. Una sola página, siempre con el mismo título,
    para publicarla cada mañana en la misma dirección."""
    inicio, fin = instante(desde), datetime.now(timezone.utc)
    por_decidir, avance, en_curso, sigue_html = [], [], [], []
    tomadas, por_aplicar = [], {}
    n_corridas = n_integrados = n_cerrados = 0
    for repo in repos:
        d = leer(propietario, repo)
        a = actividad(propietario, repo, inicio, fin)
        n_corridas, n_integrados, n_cerrados = (n_corridas + len(a["corridas"]), n_integrados + len(a["integrados"]),
                                                n_cerrados + len(a["cerrados"]))
        tomadas += [t for t in a["tomadas"] if t not in tomadas]
        avance += [(t, f"{repo} · {que}", det, url) for t, que, det, url in a["eventos"]]
        por_decidir += [(repo, p["number"]) for p in d["preguntas"] if not p.get("comments")]
        # respuestas de la Dirección que la corrida todavía no aplicó: un PR del proyecto puede depender de ellas
        por_aplicar[repo] = [p["number"] for p in d["preguntas"] if p.get("comments")]
        for p in d["prs"]:
            ci = estado_ci(p.get("statusCheckRollup"))
            if ci == "verde" and not p.get("isDraft"):
                por_decidir.append((repo, p["number"]))
            else:
                nombre = "{} #{}: {}".format(repo, p["number"], p.get("title", ""))
                estado = "borrador" if p.get("isDraft") else f"controles en {ci}"
                en_curso.append(f"<li>{enlace(p.get('url'), nombre)} · {estado}</li>")
        # lo que sigue lo dice la corrida más reciente que lo dejó escrito (una que no tuvo nada que hacer, no lo dice)
        candidatas = sorted(a["corridas"] + ([d["ultima"]] if d["ultima"] else []),
                            key=lambda c: c.get("created_at") or "", reverse=True)
        fuente = next((c for c in candidatas if lo_que_sigue(c.get("body"))), None)
        if fuente:
            cuando_fue = instante(fuente["created_at"]).astimezone(tz).strftime("%d-%m %H:%M")
            sigue_html.append(f"<li><b>{e(repo)}</b>, según la corrida del {cuando_fue}"
                              f"<ul>{lo_que_sigue(fuente.get('body'))}</ul></li>")
    avance.sort(key=lambda x: x[0])

    hoy = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
    hechos = (f"<span><b>{e(cliente)}</b> · {len(repos)} proyecto(s)</span><span>{hoy}</span>"
              f"<span>desde {inicio.astimezone(tz).strftime('%Y-%m-%d %H:%M')}</span><span>horas en {e(tz)}</span>")
    # Se lee de arriba abajo en el teléfono: primero qué decidir y qué responder; el detalle, plegado, para quien quiera
    partes = [f'<header class="top"><span class="eyebrow">Resumen diario</span><h1>Lo que espera tu decisión</h1>'
              f'<div class="facts">{hechos}</div></header>',
              seccion("Lo más importante", completar("en dos o tres líneas, lo que cambió y qué conviene decidir "
                                                     "primero."))]
    if por_decidir:
        ref = e(f"{por_decidir[0][0]}#{por_decidir[0][1]}")
        bloques = []
        for i, (repo, numero) in enumerate(por_decidir, 1):
            d = decision(propietario, repo, numero, "")
            detalle_html = (f'<div class="facts">{d["hechos"]}</div>{d["pide"]}'
                            f"<h3>Lo que la fábrica decidió por ti</h3>{d['decisiones']}"
                            + (f"<h3>Documentos</h3>{d['documentos']}<h3>Controles</h3>{d['controles']}"
                               if d["es_pr"] else ""))
            pendientes = ", ".join(f"#{n}" for n in por_aplicar.get(repo, []))
            aviso = (f'<p><span class="estado mal">ojo</span> Tienes respuestas por aplicar en este proyecto '
                     f"({pendientes}). Si este PR depende de alguna, no lo apruebes todavía: la próxima corrida las "
                     "aplica y el PR vuelve con ellas.</p>" if d["es_pr"] and pendientes else "")
            bloques.append(f'<div class="decidir"><h3>{i}. {e(repo)} #{numero} · {e(d["titulo"])}</h3>{aviso}'
                           + completar("en dos líneas, qué decides y tu recomendación, con la respuesta exacta (por "
                                       f"ejemplo «sí a {repo}#{numero}» o «{repo}#{numero}: A»).")
                           + f"<details><summary>Ver el detalle</summary>{detalle_html}</details></div>")
        partes.append(seccion(f"Para decidir ({len(por_decidir)})",
                              f"<p>Responde en la sesión de esta mañana, en la app de Claude (Code), con una línea por "
                              f"decisión: por ejemplo «sí a {ref}». Se publica en GitHub con tu cuenta.</p>"
                              + "".join(bloques)))
    else:
        partes.append(seccion("Nada espera tu decisión",
                              "<p>Los motores siguen solos con lo que no depende de ti.</p>"))
    plegados = [("Lo que avanzó", en_orden(avance, tz, "%d-%m %H:%M") if avance
                 else "<p>No hubo corridas, integraciones ni cierres en este lapso.</p>"),
                ("Lo que la fábrica decidió por ti", tarjetas_decisiones(tomadas))]
    if en_curso:
        plegados.append(("En curso, sin decisión pendiente", f"<ul>{''.join(en_curso)}</ul>"))
    plegados += [("Lo que sigue", f"<ul>{''.join(sigue_html)}</ul>" if sigue_html else
                  "<p>Las corridas todavía no dejaron escrito lo que sigue.</p>"),
                 ("Uso del plan", '<p>El consumo se ve en '
                                  '<a href="https://claude.ai/settings/usage">claude.ai/settings/usage</a>.</p>')]
    partes += [cifras([(len(por_decidir), "esperan tu decisión"), (n_integrados, "PRs integrados"),
                       (n_corridas, "corridas del motor"), (len(tomadas), "decisiones que tomó la fábrica")]),
               seccion("Para leer con calma", "".join(f"<details><summary>{html.escape(t)}</summary>{c}</details>"
                                                      for t, c in plegados)),
               pie(tz)]
    salida = salida or Path(tempfile.gettempdir()) / "fabrica-paginas" / f"diario-{cliente}.html"
    return armar(f"Resumen diario · {cliente}", f"Lo que avanzó y lo que espera la decisión de la Dirección en los "
                                                f"proyectos de {cliente}.", partes, salida)


def main():
    _nucleo.preparar_consola()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    accion = ap.add_mutually_exclusive_group()
    accion.add_argument("--cliente", help="detalle de un cliente")
    accion.add_argument("--responder", metavar="REPOSITORIO#N", help="publicar la respuesta de la Dirección")
    accion.add_argument("--pedido", metavar="REPOSITORIO", help="crear un pedido para el motor")
    accion.add_argument("--integrar", metavar="REPOSITORIO#N", help="integrar un PR en verde")
    accion.add_argument("--esperar", metavar="REPOSITORIO", help="esperar a que termine la corrida de un proyecto")
    accion.add_argument("--pagina", metavar="REPOSITORIO#N", help="armar la página de una decisión")
    accion.add_argument("--jornada", metavar="REPOSITORIO", help="armar la página de cierre de una jornada")
    accion.add_argument("--diario", metavar="CLIENTE", help="armar el resumen diario de un cliente")
    ap.add_argument("--desde", default="", help="hora UTC desde la que cuenta una entrada nueva (por defecto, ahora)")
    ap.add_argument("--minutos", type=float, default=25, help="cuánto esperar como máximo")
    ap.add_argument("--titulo", default="", help="título del pedido")
    ap.add_argument("--texto", default="", help="respuesta o cuerpo del pedido, con las palabras de la Dirección")
    ap.add_argument("--fecha", default="", help="día de la jornada, AAAA-MM-DD (por defecto, hoy)")
    ap.add_argument("--carpeta", default="", help="carpeta local del proyecto, para mostrar la ruta de cada documento")
    ap.add_argument("--salida", default="", help="dónde escribir la página (por defecto, en la carpeta temporal)")
    a = ap.parse_args()

    if _nucleo.es_mantenedor(RAIZ):
        sys.exit("Esta carpeta es el núcleo que mantienes: la bandeja se usa en una instancia.")
    ruta_config = RAIZ / ".fabrica" / "config.json"
    config = json.loads(ruta_config.read_text(encoding="utf-8")) if ruta_config.exists() else {}
    propietario = (config.get("github") or {}).get("propietario", "")
    if not propietario:
        sys.exit("Falta github.propietario en .fabrica/config.json: la bandeja lee los proyectos desde GitHub.")
    todos = proyectos()
    validos = {r for repos in todos.values() for r in repos}

    if a.responder:
        return responder(propietario, *referencia(a.responder, validos), a.texto)
    if a.integrar:
        return integrar(propietario, *referencia(a.integrar, validos))
    if a.esperar:
        if a.esperar not in validos:
            sys.exit(f"{a.esperar} no es un proyecto activo de esta instancia.")
        desde = a.desde or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if not HORA_UTC.match(desde):
            sys.exit(f"--desde «{desde}» debe ser una hora UTC como 2026-11-03T13:57:05Z.")
        return esperar(propietario, a.esperar, desde, a.minutos)
    salida = Path(a.salida).resolve() if a.salida else None
    if a.pagina:
        return pagina(propietario, *referencia(a.pagina, validos), a.carpeta, salida, zona(config))
    if a.jornada:
        if a.jornada not in validos:
            sys.exit(f"{a.jornada} no es un proyecto activo de esta instancia.")
        try:
            dia = date.fromisoformat(a.fecha) if a.fecha else datetime.now(zona(config)).date()
        except ValueError:
            sys.exit(f"--fecha «{a.fecha}» debe ser un día como 2026-11-03.")
        return jornada(propietario, a.jornada, dia, salida, zona(config))
    if a.diario:
        if a.diario not in todos:
            sys.exit(f"El cliente '{a.diario}' no tiene proyectos activos. Clientes con proyectos: "
                     f"{', '.join(todos) or 'ninguno'}.")
        desde = a.desde or (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        if not HORA_UTC.match(desde):
            sys.exit(f"--desde «{desde}» debe ser una hora UTC como 2026-11-03T13:57:05Z.")
        return diario(propietario, a.diario, todos[a.diario], desde, salida, zona(config))
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
