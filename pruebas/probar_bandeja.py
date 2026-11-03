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
- sin cuenta configurada, y en la copia del mantenedor, la bandeja no corre.

Uso: python pruebas/probar_bandeja.py
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
import _kit  # noqa: E402
import _nucleo  # noqa: E402
import bandeja  # noqa: E402

resultados = []

GH_FALSO = r'''
import json, os, sys
datos = json.load(open(os.environ["GH_FALSO_DATOS"], encoding="utf-8"))
a = sys.argv[1:]
def anotar(x):
    with open(os.environ["GH_FALSO_LOG"], "a", encoding="utf-8") as f:
        f.write(json.dumps(x, ensure_ascii=False) + "\n")
def campo(nombre):
    return next((v.split("=", 1)[1] for k, v in zip(a, a[1:]) if k == "-f" and v.startswith(nombre + "=")), None)
def repo():
    return a[a.index("-R") + 1].split("/", 1)[1]
if a[0] == "api" and "-f" in a:
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
elif a[0] == "api":
    if a[1] not in datos["api"]:
        sys.stderr.write("HTTP 404: Not Found"); sys.exit(1)
    print(json.dumps(datos["api"][a[1]]))
elif a[:2] == ["pr", "list"]:
    print(json.dumps(datos["prs"].get(repo(), [])))
elif a[:2] == ["pr", "view"]:
    print(json.dumps(datos["pr_view"][repo() + "#" + a[2]]))
elif a[:2] == ["pr", "merge"]:
    anotar({"accion": "integrar", "ref": repo() + "#" + a[2], "args": a})
    print("merged")
else:
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
            "repos/duena/propio-panel/issues/5": {"state": "open", "labels": [{"name": "espera:direccion"}]},
            "repos/duena/propio-panel/issues/7": {"state": "closed", "labels": [{"name": "espera:direccion"}]},
            # existe en GitHub, pero no es un proyecto de la instancia: la bandeja no debe tocarlo
            "repos/duena/otro-repo/issues/1": {"state": "open", "labels": [{"name": "espera:direccion"}]},
            f"repos/duena/propio-plataforma/{q}": [],
            f"repos/duena/propio-plataforma/{t}": [],
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
        "pr_view": {
            "propio-panel#4": {"state": "OPEN", "isDraft": False, "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN",
                               "statusCheckRollup": VERDE, "title": "Iniciativa del panel", "baseRefName": "main"},
            "propio-panel#9": {"state": "OPEN", "isDraft": False, "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN",
                               "statusCheckRollup": ROJO, "title": "Kit nuevo", "baseRefName": "main"},
            "propio-panel#10": {"state": "OPEN", "isDraft": False, "mergeable": "MERGEABLE",
                                "mergeStateStatus": "BEHIND", "statusCheckRollup": VERDE, "title": "Atrasado",
                                "baseRefName": "master"},
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
        comprobar("Integra un PR en verde y al día",
                  rc == 0 and hechos[-1]["accion"] == "integrar" and hechos[-1]["ref"] == "propio-panel#4"
                  and "--merge" in hechos[-1]["args"], out)

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

        subprocess.run(["git", "init", "-q"], cwd=inst, check=True)
        subprocess.run(["git", "config", "--local", "fabrica.mantenedor", "true"], cwd=inst, check=True)
        rc, out = correr()
        comprobar("En la copia del mantenedor la bandeja no corre", rc != 0 and "núcleo que mantienes" in out, out)

    fallas = [n for n, ok in resultados if not ok]
    print(f"\n{len(resultados) - len(fallas)}/{len(resultados)} pruebas pasaron.")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
