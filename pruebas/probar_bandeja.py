#!/usr/bin/env python3
"""Prueba de la bandeja de la Dirección, con un gh falso: no toca GitHub.

En una instancia temporal con dos clientes comprueba que:
- el resumen cuenta preguntas (sin respuesta y respondidas), PRs y PRs en verde, y no muestra ningún texto de los
  proyectos (aislamiento);
- el detalle de un cliente muestra sus preguntas, sus PRs con el estado de los controles y su última corrida, y nada
  del otro cliente;
- una respuesta se publica con la marca de la bandeja, y no se publica en un repositorio ajeno ni en un issue cerrado;
- un pedido se crea sin etiquetas;
- un PR se integra solo con los controles en verde y la rama al día;
- la página de una decisión escapa lo que viene de GitHub, trae las decisiones del motor sin repetir, enlaza cada
  documento en la versión del PR y marca lo que falta escribir en lenguaje simple;
- la página de una jornada cuenta solo lo de ese día, en la hora de la instancia, y dice lo que sigue;
- sin cuenta configurada, y en la copia del mantenedor, la bandeja no corre.

Uso: python pruebas/probar_bandeja.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / ".fabrica" / "scripts"))
import _kit  # noqa: E402
import _nucleo  # noqa: E402
import bandeja  # noqa: E402

resultados = []

GH_FALSO = r'''
import json, os, re, sys
datos = json.load(open(os.environ["GH_FALSO_DATOS"], encoding="utf-8"))
a = sys.argv[1:]
def anotar(x):
    with open(os.environ["GH_FALSO_LOG"], "a", encoding="utf-8") as f:
        f.write(json.dumps(x, ensure_ascii=False) + "\n")
def campo(nombre):
    return next((v.split("=", 1)[1] for k, v in zip(a, a[1:]) if k == "-f" and v.startswith(nombre + "=")), None)
def sha(repo, n, pr):
    return pr.get("headRefOid") or f"sha-{repo}-{n}"
def controles_por_sha():
    r = {}
    for repo, lista in datos.get("prs", {}).items():
        for p in lista:
            r[sha(repo, p["number"], p)] = p.get("statusCheckRollup") or []
    for ref, p in datos.get("pr_view", {}).items():
        repo, n = ref.split("#")
        r[sha(repo, int(n), p)] = p.get("statusCheckRollup") or []
    return r
def un_pr(repo, n, p):
    estado = p.get("state", "OPEN")
    return {"number": n, "title": p.get("title"), "html_url": p.get("url", f"https://github.com/duena/{repo}/pull/{n}"),
            "state": "open" if estado == "OPEN" else "closed",
            "merged_at": "2026-11-03T12:00:00Z" if estado == "MERGED" else None, "draft": p.get("isDraft", False),
            "labels": [{"name": x} for x in p.get("labels", [])],
            "mergeable": {"MERGEABLE": True, "CONFLICTING": False}.get(p.get("mergeable")),
            "mergeable_state": (p.get("mergeStateStatus") or "unknown").lower(),
            "base": {"ref": p.get("baseRefName", "main"), "repo": {"full_name": f"duena/{repo}"}},
            "head": {"ref": p.get("headRefName", f"rama-{n}"), "sha": sha(repo, n, p),
                     "repo": {"full_name": f"duena/{repo}"}}}
def rest(ruta):
    """Responde como la API REST de GitHub a partir de los PRs de los datos; None si no conoce la ruta."""
    m = re.match(r"^repos/duena/([^/]+)/(.+)$", ruta)
    if not m:
        return None
    repo, resto = m.groups()
    if resto == "pulls?state=open&per_page=100":
        return [{"number": p["number"], "title": p.get("title"), "html_url": p.get("url"), "draft": p.get("isDraft"),
                 "labels": [{"name": x} for x in p.get("labels", [])], "head": {"sha": sha(repo, p["number"], p)}}
                for p in datos.get("prs", {}).get(repo, [])]
    if resto == "pulls?state=closed&sort=updated&direction=desc&per_page=100":
        return [{"number": p["number"], "title": p.get("title"), "html_url": p.get("url"),
                 "merged_at": p.get("mergedAt")}
                for p in datos.get("integrados", {}).get(repo, [])]
    m = re.match(r"^pulls/(\d+)(/files\?per_page=100)?$", resto)
    if m and f"{repo}#{m.group(1)}" in datos.get("pr_view", {}):
        p = datos["pr_view"][f"{repo}#{m.group(1)}"]
        if m.group(2):
            return [{"filename": f["path"], "additions": f["additions"], "deletions": f["deletions"]}
                    for f in p.get("files", [])]
        return un_pr(repo, int(m.group(1)), p)
    m = re.match(r"^(?:commits/([^/]+)/(check-runs\?filter=all&per_page=100|status)"
                 r"|actions/runs\?head_sha=([^&]+)&per_page=100)$", resto)
    if m:
        lista = controles_por_sha().get(m.group(1) or m.group(3), [])
        if m.group(3):
            flujos = list(dict.fromkeys(c["workflowName"] for c in lista if c.get("workflowName")))
            return {"workflow_runs": [{"name": f, "check_suite_id": f} for f in flujos]}
        if m.group(2) == "status":
            return {"statuses": [{"context": c["context"], "state": c["state"].lower()} for c in lista if "state" in c]}
        return {"check_runs": [{"name": c.get("name", f"control-{i}"),
                                "status": (c.get("status") or "completed").lower(),
                                "conclusion": (c.get("conclusion") or "").lower() or None,
                                "started_at": c.get("startedAt"), "check_suite": {"id": c.get("workflowName", "")}}
                               for i, c in enumerate(lista) if "state" not in c]}
    return None
if a[0] == "api" and "-X" in a:
    metodo, ruta = a[a.index("-X") + 1], next(x for x in a[1:] if x.startswith("repos/"))
    if metodo == "PUT" and ruta.endswith("/merge"):
        anotar({"accion": "integrar", "ref": ruta.split("/")[2] + "#" + ruta.split("/")[4], "args": a})
        print(json.dumps({"merged": True}))
    elif metodo == "DELETE":
        anotar({"accion": "borrar-rama", "ruta": ruta})
    else:
        sys.stderr.write("gh falso: no sé responder " + " ".join(a)); sys.exit(1)
elif a[0] == "api" and "-f" in a:
    if a[1].endswith("/comments"):
        anotar({"accion": "comentario", "ruta": a[1], "body": campo("body")})
        print(json.dumps({"html_url": "https://github.com/x/c/1"}))
    else:
        anotar({"accion": "pedido", "ruta": a[1], "title": campo("title"), "body": campo("body"), "args": a})
        print(json.dumps({"number": 99, "html_url": "https://github.com/x/i/99"}))
elif a[0] == "api" and a[1] in datos.get("secuencias", {}):
    # respuestas que cambian de una llamada a la siguiente (una corrida que termina mientras se espera)
    ruta_estado = os.environ["GH_FALSO_ESTADO"]
    estado = json.load(open(ruta_estado, encoding="utf-8")) if os.path.exists(ruta_estado) else {}
    serie = datos["secuencias"][a[1]]
    print(json.dumps(serie[min(estado.get(a[1], 0), len(serie) - 1)]))
    estado[a[1]] = estado.get(a[1], 0) + 1
    json.dump(estado, open(ruta_estado, "w", encoding="utf-8"))
elif a[0] == "api" and a[1] in datos["api"]:
    print(json.dumps(datos["api"][a[1]]))
elif a[0] == "api" and rest(a[1]) is not None:
    print(json.dumps(rest(a[1])))
elif a[0] == "api":
    sys.stderr.write("HTTP 404: Not Found"); sys.exit(1)
else:
    # `gh pr` y `gh issue` usan GraphQL, que no corre en la nube: la bandeja no debe llamarlos
    sys.stderr.write("gh falso: no sé responder " + " ".join(a)); sys.exit(1)
'''

VERDE = [{"conclusion": "SUCCESS"}, {"conclusion": "SKIPPED"}]
ROJO = [{"conclusion": "SUCCESS"}, {"conclusion": "FAILURE"}]
EN_CURSO = [{"conclusion": "", "status": "IN_PROGRESS"}]


def datos():
    q = "issues?labels=espera%3Adireccion&state=open&per_page=100"
    t = "issues?state=open&per_page=100"
    return {
        "api": {
            f"repos/duena/propio-panel/{q}": [
                {"number": 5, "title": "Pregunta: plazo de entrega", "body": "Responde A o B.", "comments": 0,
                 "html_url": "https://github.com/duena/propio-panel/issues/5"},
                {"number": 6, "title": "Pregunta: color del semáforo", "body": "Responde 1 o 2.", "comments": 1,
                 "html_url": "https://github.com/duena/propio-panel/issues/6"},
                {"number": 11, "title": "PR etiquetado", "pull_request": {}, "comments": 0}],
            f"repos/duena/propio-panel/{t}": [{"number": 2, "title": bandeja.BITACORA, "comments": 3}],
            "repos/duena/propio-panel/issues/2/comments?per_page=1&page=3": [
                {"created_at": "2026-11-03T09:12:44Z", "body": "Corrida 2026-11-03 · paso: especificar H-001"}],
            "repos/duena/propio-panel/issues/5": {"state": "open", "labels": [{"name": "espera:direccion"}],
                                                  "title": "Pregunta: plazo de entrega", "body": "Responde A o B.",
                                                  "comments": 0},
            "repos/duena/propio-panel/issues/4": {
                "state": "open", "pull_request": {}, "comments": 2, "title": "Iniciativa <script>alert(1)</script>",
                "html_url": "https://github.com/duena/propio-panel/pull/4",
                "body": "Resumen.\n\n## Decisiones que tomé por ti\n\n- Decisión: usar `semaforo` de tres colores — lo "
                        "pide la ficha — si es errada, se cambia el componente.\n- Decisión: sin sonido — molesta "
                        "en bodega — si es errada, se agrega."},
            "repos/duena/propio-panel/issues/20": {"state": "closed", "pull_request": {}, "comments": 0,
                                                   "title": "Ya integrado", "body": ""},
            "repos/duena/propio-panel/issues/4/comments?per_page=100": [
                {"body": "- Decisión: sin sonido — molesta en bodega — si es errada, se agrega."},
                {"body": "- Decisiones que tomé por ti: Decisión: plazo de 2 días — dato del cliente — si es errada, "
                         "se ajusta. Más en el PR #4."}],
            # jornada del 2026-11-03 en America/Santiago (UTC−3): de 03:00 UTC del 3 a 03:00 UTC del 4
            "repos/duena/propio-panel/issues/2/comments?since=2026-11-03T03:00:00Z&per_page=100": [
                {"created_at": "2026-11-03T02:30:00Z", "body": "Corrida 2026-11-02 · paso: noche anterior"},
                {"created_at": "2026-11-03T13:47:00Z", "html_url": "c1",
                 "body": "Corrida 2026-11-03 · paso: especificar H-001\n- Resultado: PR #16 con la historia.\n"
                         "- Decisiones que tomé por ti: Decisión: partir la capa en tres — es lo mínimo — si es "
                         "errada, se reagrupan. Decisión: la hoja de ruta hace de iniciativa — ya validada — si es "
                         "errada, se escribe. Más supuestos en el PR #16.\n- Próximo paso: diseño."},
                {"created_at": "2026-11-04T02:59:00Z", "html_url": "c2",
                 "body": "Corrida 2026-11-03 · paso: diseño y pruebas\n- Resultado: PR #17.\n- Decisiones que "
                         "tomé por ti: ninguna nueva.\n- Esperan tu decisión: PR #17.\n- Bloqueos: ninguno.\n"
                         "- Próximo paso: plan de construcción."},
                {"created_at": "2026-11-04T03:00:00Z", "body": "Corrida 2026-11-04 · paso: mañana siguiente"}],
            "repos/duena/propio-panel/issues?state=closed&since=2026-11-03T03:00:00Z&per_page=100": [
                {"number": 12, "title": "Precios", "closed_at": "2026-11-03T14:50:00Z", "html_url": "u12"},
                {"number": 18, "title": "PR cerrado", "pull_request": {}, "closed_at": "2026-11-03T15:00:00Z"}],
            "repos/duena/propio-panel/issues/7": {"state": "closed", "labels": [{"name": "espera:direccion"}]},
            # existe en GitHub, pero no es un proyecto de la instancia: la bandeja no debe tocarlo
            "repos/duena/otro-repo/issues/1": {"state": "open", "labels": [{"name": "espera:direccion"}]},
            f"repos/duena/propio-plataforma/{q}": [],
            f"repos/duena/propio-plataforma/{t}": [],
            "repos/duena/propio-plataforma/issues?state=closed&since=2026-11-03T03:00:00Z&per_page=100": [],
            f"repos/duena/cliente-b-app/{q}": [
                {"number": 1, "title": "SECRETO-B: precio pactado", "body": "SECRETO-B en el cuerpo", "comments": 0}],
            f"repos/duena/cliente-b-app/{t}": [],
        },
        "prs": {
            "propio-panel": [
                {"number": 4, "title": "Iniciativa del panel", "isDraft": False, "statusCheckRollup": VERDE,
                 "url": "https://github.com/duena/propio-panel/pull/4"},
                {"number": 9, "title": "Kit nuevo", "isDraft": False, "statusCheckRollup": ROJO, "url": "u9"}],
            "propio-plataforma": [
                {"number": 3, "title": "ADR-0001", "isDraft": False, "statusCheckRollup": EN_CURSO, "url": "u3"}],
        },
        "integrados": {
            "propio-panel": [
                {"number": 16, "title": "H-001", "url": "u16", "mergedAt": "2026-11-03T14:58:00Z"},
                {"number": 15, "title": "Viejo", "url": "u15", "mergedAt": "2026-11-02T20:00:00Z"}],
        },
        "pr_view": {
            "propio-panel#4": {"state": "OPEN", "isDraft": False, "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN",
                               "statusCheckRollup": VERDE, "title": "Iniciativa del panel", "baseRefName": "main",
                               "headRefOid": "abc123",
                               "files": [{"path": "docs/diseño panel.md", "additions": 10, "deletions": 2},
                                         {"path": "app/__pycache__/x.cpython-311.pyc", "additions": 0,
                                          "deletions": 0}]},
            "propio-panel#9": {"state": "OPEN", "isDraft": False, "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN",
                               "statusCheckRollup": ROJO, "title": "Kit nuevo", "baseRefName": "main"},
            "propio-panel#20": {"state": "MERGED", "isDraft": False, "statusCheckRollup": VERDE, "headRefOid": "d4",
                                "files": []},
            "propio-panel#10": {"state": "OPEN", "isDraft": False, "mergeable": "MERGEABLE",
                                "mergeStateStatus": "BEHIND", "statusCheckRollup": VERDE, "title": "Atrasado",
                                "baseRefName": "master"},
            # un control que falló y volvió a correr en verde (por ejemplo, al ponerle una etiqueta al PR)
            "propio-panel#21": {"state": "OPEN", "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN",
                                "title": "Con reintento", "headRefName": "fabrica/reintento",
                                "statusCheckRollup": [
                                    {"name": "fabrica", "workflowName": "Fábrica", "startedAt": "2026-11-03T10:00:00Z",
                                     "conclusion": "FAILURE"},
                                    {"name": "fabrica", "workflowName": "Fábrica", "startedAt": "2026-11-03T10:05:00Z",
                                     "conclusion": "SUCCESS"},
                                    {"context": "servicio-externo", "state": "SUCCESS"}]},
            # el mismo nombre de control en otro flujo, en rojo: un verde posterior del primer flujo no lo tapa
            "propio-panel#22": {"state": "OPEN", "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN",
                                "title": "Otro flujo en rojo", "statusCheckRollup": [
                                    {"name": "fabrica", "workflowName": "Otro", "startedAt": "2026-11-03T09:00:00Z",
                                     "conclusion": "FAILURE"},
                                    {"name": "fabrica", "workflowName": "Fábrica", "startedAt": "2026-11-03T10:05:00Z",
                                     "conclusion": "SUCCESS"}]},
            # un servicio externo (estado de commit) en rojo, con las corridas en verde
            "propio-panel#24": {"state": "OPEN", "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN",
                                "title": "Externo en rojo",
                                "statusCheckRollup": VERDE + [{"context": "servicio-externo", "state": "FAILURE"}]},
            "propio-panel#23": {"state": "OPEN", "headRefOid": "sha23", "statusCheckRollup": VERDE},
        },
    }


def comprobar(nombre, condicion, detalle=""):
    resultados.append((nombre, bool(condicion)))
    print(f"{'OK   ' if condicion else 'FALLA'} {nombre}" + (f" — {detalle[:600]}" if detalle and not condicion else ""))


def main():
    _nucleo.preparar_consola()
    comprobar("Estado de los controles: verde, rojo, pendiente y sin CI",
              (bandeja.estado_ci(VERDE), bandeja.estado_ci(ROJO), bandeja.estado_ci(EN_CURSO),
               bandeja.estado_ci([])) == ("verde", "rojo", "pendiente", "sin CI"))
    viejo_mal = {"name": "fabrica", "workflowName": "CI", "startedAt": "2026-11-03T10:00:00Z", "conclusion": "FAILURE"}
    nuevo_bien = {"name": "fabrica", "workflowName": "CI", "startedAt": "2026-11-03T10:05:00Z", "conclusion": "SUCCESS"}
    comprobar("Un control que volvió a correr cuenta por su última corrida",
              bandeja.estado_ci([viejo_mal, nuevo_bien]) == "verde"
              and bandeja.estado_ci([nuevo_bien, viejo_mal]) == "verde"
              and bandeja.estado_ci([dict(viejo_mal, startedAt="2026-11-03T11:00:00Z"), nuevo_bien]) == "rojo")
    comprobar("Una zona horaria desconocida cae en UTC", bandeja.zona({"zona_horaria": "No/Existe"}) is timezone.utc)

    with tempfile.TemporaryDirectory(prefix="prueba-bandeja-") as tmp:
        tmp = Path(tmp)
        inst = tmp / "instancia"
        for rel in _nucleo.archivos(RAIZ):
            (inst / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(RAIZ / rel, inst / rel)
        (inst / "clientes").mkdir()
        log = tmp / "gh.log"
        (tmp / "gh_falso.py").write_text(GH_FALSO, encoding="utf-8")
        (tmp / "datos.json").write_text(json.dumps(datos(), ensure_ascii=False), encoding="utf-8")
        entorno = {k: v for k, v in os.environ.items() if k != "FABRICA_ES_NUCLEO"}
        entorno.update({"FABRICA_GH": str(tmp / "gh_falso.py"), "GH_FALSO_DATOS": str(tmp / "datos.json"),
                        "GH_FALSO_LOG": str(log), "GH_FALSO_ESTADO": str(tmp / "estado.json"),
                        "FABRICA_ESPERA_SEG": "0.05"})

        def correr(*args):
            r = subprocess.run([sys.executable, ".fabrica/scripts/bandeja.py", *args], cwd=inst, capture_output=True,
                               text=True, encoding="utf-8", errors="replace", env=entorno)
            return r.returncode, (r.stdout or "") + (r.stderr or "")

        def registro():
            if not log.exists():
                return []
            return [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]

        for cliente, negocio in (("propio", "fabrica:software"), ("cliente-b", "tienda:comercio")):
            r = subprocess.run([sys.executable, ".fabrica/scripts/nuevo_cliente.py", "--id", cliente, "--nombre",
                                cliente.title(), "--negocio", negocio], cwd=inst, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", env=entorno)
            comprobar(f"Registra el cliente {cliente}", r.returncode == 0, (r.stdout or "") + (r.stderr or ""))
        for cliente, negocio, proyecto in (("propio", "fabrica", "panel"), ("propio", "fabrica", "plataforma"),
                                           ("cliente-b", "tienda", "app"), ("cliente-b", "tienda", "viejo")):
            _kit.anotar_en_ficha(inst / "clientes" / cliente / "cliente.md", cliente, negocio, proyecto)
        ficha_b = inst / "clientes" / "cliente-b" / "cliente.md"
        ficha_b.write_text(ficha_b.read_text(encoding="utf-8").replace("`cliente-b-viejo` | activo",
                                                                        "`cliente-b-viejo` | cerrado"),
                           encoding="utf-8")

        rc, out = correr()
        comprobar("Sin cuenta configurada, la bandeja no corre", rc != 0 and "propietario" in out, out)
        (inst / ".fabrica" / "config.json").write_text(json.dumps({"github": {"propietario": "duena"}}),
                                                       encoding="utf-8")

        rc, out = correr()
        comprobar("El resumen cuenta preguntas, respondidas, PRs y PRs en verde",
                  rc == 0 and "| propio | propio-panel | 1 | 1 | 2 | 1 | 2026-11-03 09:12 UTC |" in out
                  and "| propio | propio-plataforma | 0 | 0 | 1 | 0 | — |" in out
                  and "| cliente-b | cliente-b-app | 1 | 0 | 0 | 0 | — |" in out, out)
        comprobar("El resumen no muestra textos de los proyectos (aislamiento)",
                  "SECRETO-B" not in out and "plazo de entrega" not in out and "Iniciativa" not in out, out)
        comprobar("Un proyecto cerrado no aparece", "cliente-b-viejo" not in out, out)

        rc, out = correr("--cliente", "propio")
        comprobar("El detalle muestra las preguntas y si ya tienen respuesta",
                  rc == 0 and "#5 · Pregunta: plazo de entrega · sin respuesta" in out
                  and "#6 · Pregunta: color del semáforo · respondida" in out and "> Responde A o B." in out, out)
        comprobar("El detalle muestra los PRs con el estado de sus controles",
                  "#4 · Iniciativa del panel · controles en verde" in out and "#9 · Kit nuevo · controles en rojo" in out
                  and "#3 · ADR-0001 · controles en pendiente" in out, out)
        comprobar("El detalle muestra la última corrida", "Corrida 2026-11-03 · paso: especificar H-001" in out, out)
        comprobar("El detalle de un cliente no trae nada del otro", "SECRETO-B" not in out, out)
        rc, out = correr("--cliente", "nadie")
        comprobar("Un cliente sin proyectos se rechaza", rc != 0 and "propio" in out, out)

        rc, out = correr("--responder", "propio-panel#5", "--texto", "B, con entrega el lunes")
        hechos = registro()
        comprobar("La respuesta se publica con la marca de la bandeja",
                  rc == 0 and len(hechos) == 1 and hechos[0]["ruta"] == "repos/duena/propio-panel/issues/5/comments"
                  and hechos[0]["body"].startswith("B, con entrega el lunes") and bandeja.MARCA in hechos[0]["body"], out)
        rc, out = correr("--responder", "otro-repo#1", "--texto", "x")
        comprobar("No responde en un repositorio ajeno a la instancia",
                  rc != 0 and "no es un proyecto activo" in out and len(registro()) == 1, out)
        rc, out = correr("--responder", "propio-panel#7", "--texto", "x")
        comprobar("No responde en un issue cerrado", rc != 0 and "cerrado" in out and len(registro()) == 1, out)
        rc, out = correr("--responder", "propio-panel#5", "--texto", "  ")
        comprobar("No publica una respuesta vacía", rc != 0 and len(registro()) == 1, out)

        rc, out = correr("--pedido", "propio-plataforma", "--titulo", "Preparar X", "--texto", "Qué necesito")
        hechos = registro()
        comprobar("El pedido se crea sin etiquetas y con la marca",
                  rc == 0 and hechos[-1]["accion"] == "pedido" and hechos[-1]["title"] == "Preparar X"
                  and bandeja.MARCA_PEDIDO in hechos[-1]["body"] and "labels" not in " ".join(hechos[-1]["args"]), out)

        antes = len(registro())
        rc, out = correr("--integrar", "propio-panel#9")
        comprobar("No integra un PR con controles en rojo", rc != 0 and "rojo" in out and len(registro()) == antes, out)
        rc, out = correr("--integrar", "propio-panel#10")
        comprobar("No integra un PR con la rama atrasada", rc != 0 and "master" in out and len(registro()) == antes, out)
        rc, out = correr("--integrar", "propio-panel#4")
        hechos = registro()
        comprobar("Integra un PR en verde y al día, y borra su rama",
                  rc == 0 and hechos[-2]["accion"] == "integrar" and hechos[-2]["ref"] == "propio-panel#4"
                  and "merge_method=merge" in hechos[-2]["args"] and hechos[-1]["accion"] == "borrar-rama"
                  and hechos[-1]["ruta"] == "repos/duena/propio-panel/git/refs/heads/rama-4", out)
        rc, out = correr("--integrar", "propio-panel#21")
        hechos = registro()
        comprobar("Por REST, un control que volvió a correr cuenta por su última corrida",
                  rc == 0 and hechos[-2]["ref"] == "propio-panel#21"
                  and hechos[-1]["ruta"] == "repos/duena/propio-panel/git/refs/heads/fabrica/reintento", out)
        antes = len(registro())
        rc, out = correr("--integrar", "propio-panel#22")
        comprobar("Un control con el mismo nombre en otro flujo no tapa su falla",
                  rc != 0 and "rojo" in out and len(registro()) == antes, out)
        rc, out = correr("--integrar", "propio-panel#24")
        comprobar("Un servicio externo en rojo también detiene la integración",
                  rc != 0 and "rojo" in out and len(registro()) == antes, out)
        calculando = datos()
        p23 = {"number": 23, "title": "Recién abierto", "state": "open", "merged_at": None, "draft": False,
               "labels": [], "base": {"ref": "main", "repo": {"full_name": "duena/propio-panel"}},
               "head": {"ref": "rama-23", "sha": "sha23", "repo": {"full_name": "duena/propio-panel"}}}
        calculando["secuencias"] = {"repos/duena/propio-panel/pulls/23": [
            dict(p23, mergeable=None, mergeable_state="unknown"), dict(p23, mergeable=True, mergeable_state="clean")]}
        (tmp / "datos.json").write_text(json.dumps(calculando, ensure_ascii=False), encoding="utf-8")
        rc, out = correr("--integrar", "propio-panel#23")
        comprobar("Si GitHub todavía calcula si se puede integrar, vuelve a mirar",
                  rc == 0 and registro()[-2]["ref"] == "propio-panel#23", out)
        (tmp / "datos.json").write_text(json.dumps(datos(), ensure_ascii=False), encoding="utf-8")
        (tmp / "estado.json").unlink(missing_ok=True)
        fuente = (RAIZ / ".fabrica" / "scripts" / "bandeja.py").read_text(encoding="utf-8")
        comprobar("La bandeja usa GitHub solo por REST, que también funciona en la nube",
                  not re.search(r'gh(_json)?\(\s*"(pr|issue)"', fuente))

        # Relevos: esperar a que la corrida deje su entrada en la bitácora
        t_b = "repos/duena/cliente-b-app/issues?state=open&per_page=100"
        con_relevo = datos()
        con_relevo["secuencias"] = {
            t_b: [[{"number": 3, "title": bandeja.BITACORA, "comments": 1}],
                  [{"number": 3, "title": bandeja.BITACORA, "comments": 1}],
                  [{"number": 3, "title": bandeja.BITACORA, "comments": 2}]],
            "repos/duena/cliente-b-app/issues/3/comments?per_page=1&page=1": [
                [{"created_at": "2026-11-03T10:00:00Z", "body": "Corrida vieja · paso: ninguno"}]],
            "repos/duena/cliente-b-app/issues/3/comments?per_page=1&page=2": [
                [{"created_at": "2026-11-04T01:00:00Z", "body": "Corrida nueva · paso: ajustar el plan"}]],
        }
        (tmp / "datos.json").write_text(json.dumps(con_relevo, ensure_ascii=False), encoding="utf-8")
        rc, out = correr("--esperar", "cliente-b-app", "--desde", "2026-11-04T00:00:00Z", "--minutos", "1")
        estado = json.loads((tmp / "estado.json").read_text(encoding="utf-8")) if (tmp / "estado.json").exists() else {}
        comprobar("Espera a que termine la corrida y muestra su entrada nueva",
                  rc == 0 and "Corrida nueva · paso: ajustar el plan" in out and "Corrida vieja" not in out
                  and estado.get(t_b, 0) >= 3, out)
        rc, out = correr("--esperar", "propio-panel", "--desde", "2099-01-01T00:00:00Z", "--minutos", "0.005")
        comprobar("Si la corrida no termina a tiempo, lo dice y sale con error",
                  rc != 0 and "no apareció una entrada nueva" in out, out)
        rc, out = correr("--esperar", "propio-panel", "--desde", "ayer")
        comprobar("Rechaza una hora que no está en UTC", rc != 0 and "--desde" in out, out)
        rc, out = correr("--esperar", "otro-repo", "--minutos", "0.005")
        comprobar("No espera en un repositorio ajeno", rc != 0 and "no es un proyecto activo" in out, out)

        # Páginas para la Dirección
        def leer_pagina(nombre):
            ruta = tmp / nombre
            return ruta.read_text(encoding="utf-8") if ruta.exists() else ""

        antes = len(registro())
        rc, out = correr("--pagina", "propio-panel#4", "--carpeta", "C:/proy", "--salida", str(tmp / "p4.html"))
        web = leer_pagina("p4.html")
        comprobar("La página de un PR escapa lo que viene de GitHub",
                  rc == 0 and "Iniciativa &lt;script&gt;" in web and "<script>alert" not in web, out + web[-800:])
        comprobar("La página trae las decisiones del motor, sin repetir",
                  "usar <code>semaforo</code> de tres colores" in web and web.count("sin sonido") == 1
                  and "plazo de 2 días" in web and "Si es errada, se cambia el componente" in web
                  and "Más en el PR" not in web, web[-3000:])
        comprobar("La página enlaza cada documento en la versión del PR y muestra su ruta local",
                  "https://github.com/duena/propio-panel/blob/abc123/docs/dise%C3%B1o%20panel.md" in web
                  and str(Path("C:/proy") / "docs/diseño panel.md") in web and "+10 −2" in web, web[-3000:])
        comprobar("La página destaca los archivos que nadie puede revisar",
                  web.count("nadie puede leerlo") == 1
                  and web.index("x.cpython-311.pyc") < web.index("nadie puede leerlo"), web[-3000:])
        comprobar("La página marca lo que falta escribir en lenguaje simple",
                  web.count(bandeja.COMPLETAR) == 3 and "completa 3 sección(es)" in out, out)
        comprobar("Armar una página no publica nada", len(registro()) == antes, str(registro()[antes:]))
        rc, out = correr("--pagina", "propio-panel#5", "--salida", str(tmp / "p5.html"))
        web = leer_pagina("p5.html")
        comprobar("La página de una pregunta muestra su texto",
                  rc == 0 and "Responde A o B." in web and "Documentos" not in web, out)
        rc, out = correr("--pagina", "propio-panel#20", "--salida", str(tmp / "p20.html"))
        web = leer_pagina("p20.html")
        comprobar("La página de un PR ya integrado no ofrece integrarlo",
                  rc == 0 and "ya está integrado" in web and "Si das el sí" not in web, out)
        rc, out = correr("--pagina", "otro-repo#1", "--salida", str(tmp / "otro.html"))
        comprobar("No arma páginas de un repositorio ajeno",
                  rc != 0 and "no es un proyecto activo" in out and not (tmp / "otro.html").exists(), out)

        (inst / ".fabrica" / "config.json").write_text(json.dumps(
            {"github": {"propietario": "duena"}, "zona_horaria": "America/Santiago"}), encoding="utf-8")
        rc, out = correr("--jornada", "propio-panel", "--fecha", "2026-11-03", "--salida", str(tmp / "j.html"))
        web = leer_pagina("j.html")
        comprobar("La jornada cuenta solo lo de ese día, en la hora de la instancia",
                  rc == 0 and "<b>2</b><span>corridas del motor" in web and "<b>1</b><span>PRs integrados" in web
                  and "<b>1</b><span>preguntas o pedidos cerrados" in web
                  and "<b>2</b><span>decisiones que tomó la fábrica" in web
                  and not any(x in web for x in ("noche anterior", "mañana siguiente", "Viejo", "PR cerrado")),
                  out + web[-3000:])
        horas = [web.find(f'<span class="hora">{h}</span>') for h in ("10:47", "11:50", "11:58", "23:59")]
        comprobar("La jornada ordena el día con horas locales y dice lo que sigue",
                  -1 not in horas and horas == sorted(horas) and "plan de construcción" in web
                  and "<b>Bloqueos:</b> ninguno" in web, str(horas))
        rc, out = correr("--jornada", "propio-panel", "--fecha", "3-nov")
        comprobar("Rechaza una fecha mal escrita", rc != 0 and "--fecha" in out, out)

        antes = len(registro())
        rc, out = correr("--diario", "propio", "--desde", "2026-11-03T03:00:00Z", "--salida", str(tmp / "d.html"))
        web = leer_pagina("d.html")
        comprobar("El resumen diario trae cada decisión pendiente con lo necesario para decidirla",
                  rc == 0 and "propio-panel #5 · Pregunta: plazo de entrega" in web and "Responde A o B." in web
                  and "propio-panel #4 · Iniciativa &lt;script&gt;" in web and "usar <code>semaforo</code>" in web
                  and "blob/abc123/docs/dise%C3%B1o%20panel.md" in web and "color del semáforo" not in web,
                  out + web[-3000:])
        comprobar("El resumen diario separa lo que está en curso y dice cómo responder",
                  "propio-panel #9: Kit nuevo</a> · controles en rojo" in web
                  and "propio-plataforma #3: ADR-0001</a> · controles en pendiente" in web
                  and "sí a propio-panel#5" in web and "<b>2</b><span>esperan tu decisión" in web, web[-3000:])
        comprobar("El resumen diario cuenta lo que avanzó desde --desde, en la hora de la instancia",
                  "propio-panel · Corrida: especificar H-001" in web and "noche anterior" not in web
                  and "<b>1</b><span>PRs integrados" in web and "plan de construcción" in web, web[-3000:])
        comprobar("El resumen diario lleva su título fijo y marca lo que falta escribir",
                  "<title>Resumen diario · propio</title>" in web and web.count(bandeja.COMPLETAR) == 3
                  and "completa 3 sección(es)" in out, out)
        primera = web.find("1. propio-panel #5")
        comprobar("En el resumen, cada decisión dice primero qué responder y deja el detalle plegado",
                  -1 < web.find("Lo más importante") < primera
                  < web.find("Por completar: en dos líneas", primera) < web.find("<details>", primera)
                  < web.find("2. propio-panel #4") and web.find("Para leer con calma") > web.find("2. propio-panel #4")
                  and "<summary>Lo que avanzó</summary>" in web, web[-2500:])
        bloque_4 = web[web.find("2. propio-panel #4"):web.find("Para leer con calma")]
        comprobar("Un PR de un proyecto con respuestas por aplicar avisa que puede depender de ellas",
                  "respuestas por aplicar en este proyecto (#6)" in bloque_4
                  and "respuestas por aplicar" not in web[:web.find("2. propio-panel #4")], bloque_4[:800])
        comprobar("El resumen diario es de un solo cliente y no publica nada",
                  "SECRETO-B" not in web and "cliente-b" not in web and len(registro()) == antes, web[-2000:])
        rc, out = correr("--diario", "nadie")
        comprobar("No arma el resumen de un cliente sin proyectos", rc != 0 and "propio" in out, out)
        rc, out = correr("--diario", "propio", "--desde", "ayer")
        comprobar("El resumen diario rechaza una hora que no está en UTC", rc != 0 and "--desde" in out, out)
        propia = inst / "instancia" / "plantillas" / "pagina-direccion.html"
        propia.parent.mkdir(parents=True, exist_ok=True)
        propia.write_text("<html>PLANTILLA PROPIA {{titulo}} {{contenido}}</html>", encoding="utf-8")
        rc, out = correr("--pagina", "propio-panel#5", "--salida", str(tmp / "propia.html"))
        comprobar("Una instancia puede usar su propia plantilla", "PLANTILLA PROPIA" in leer_pagina("propia.html"), out)
        propia.unlink()

        subprocess.run(["git", "init", "-q"], cwd=inst, check=True)
        subprocess.run(["git", "config", "--local", "fabrica.mantenedor", "true"], cwd=inst, check=True)
        rc, out = correr()
        comprobar("En la copia del mantenedor la bandeja no corre", rc != 0 and "núcleo que mantienes" in out, out)

    fallas = [n for n, ok in resultados if not ok]
    print(f"\n{len(resultados) - len(fallas)}/{len(resultados)} pruebas pasaron.")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
