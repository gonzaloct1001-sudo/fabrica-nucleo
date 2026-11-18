#!/usr/bin/env python3
"""Prueba de las herramientas del kit del núcleo 0.13, en repositorios temporales y sin red.

Comprueba que:
- el guardado automático hace commit solo en la copia de trabajo de un proyecto, nunca en la rama principal; toma lo
  registrado y lo nuevo que .gitignore permite, y deja fuera secretos, imágenes y archivos pesados; respalda en
  wip/<rama> solo con gitleaks limpio y sin flujos que corran con push a cualquier rama; y deja el resultado a la vista;
- el hook de guardia niega editar pruebas de aceptación durante una construcción, y deja pasar todo lo demás;
- el filtro de salida muestra las fallas y el resumen, recorta lo demás y conserva el código de salida;
- el archivador mueve el plan (de un archivo o partido) y el modelo de amenazas de una historia hecha, y se niega con
  una historia sin terminar;
- los hooks del kit se fusionan en .claude/settings.json sin tocar lo propio, sin duplicarse y sin romper un JSON roto;
- el estado lee planes partidos, suma el consumo de la bitácora, publica el estado en su issue, avisa cuando la
  siguiente acción es anterior a lo último integrado y muestra el último respaldo.

Uso: python pruebas/probar_herramientas.py
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import time
from contextlib import redirect_stdout
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "kit" / ".fabrica" / "scripts"
sys.dont_write_bytecode = True
resultados = []


def cargar(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = modulo
    spec.loader.exec_module(modulo)
    return modulo


estado = cargar("estado", SCRIPTS / "estado.py")
guardado = cargar("hook_guardado", SCRIPTS / "hook_guardado.py")
guardia = cargar("hook_guardia", SCRIPTS / "hook_guardia.py")
filtro = cargar("filtrar_salida", SCRIPTS / "filtrar_salida.py")
archivar = cargar("archivar", SCRIPTS / "archivar.py")
limpiar = cargar("limpiar_wip", SCRIPTS / "limpiar_wip.py")
sys.path.insert(0, str(RAIZ / ".fabrica" / "scripts"))
import _kit  # noqa: E402

ENTORNO = dict(os.environ, GIT_AUTHOR_NAME="p", GIT_AUTHOR_EMAIL="p@e.com", GIT_COMMITTER_NAME="p",
               GIT_COMMITTER_EMAIL="p@e.com")


def comprobar(nombre, condicion, detalle=""):
    resultados.append((nombre, bool(condicion)))
    print(f"{'OK   ' if condicion else 'FALLA'} {nombre}" + (f" — {str(detalle)[:600]}" if detalle and not condicion else ""))


def git(raiz, *args):
    r = subprocess.run(["git", *args], cwd=raiz, capture_output=True, text=True, env=ENTORNO)
    return r.returncode, r.stdout + r.stderr


def repo(tmp, nombre="proyecto"):
    raiz = Path(tmp) / nombre
    (raiz / ".fabrica").mkdir(parents=True)
    (raiz / ".fabrica/proyecto.json").write_text(json.dumps({"nombre": "P", "rutas": {}}), encoding="utf-8")
    (raiz / ".gitignore").write_text(".fabrica/trabajo/\n*.log\n", encoding="utf-8")
    (raiz / "app.py").write_text("print(1)\n", encoding="utf-8")
    git(raiz, "init", "-q", "-b", "main")
    git(raiz, "add", "-A")
    git(raiz, "commit", "-qm", "inicio")
    remoto = Path(tmp) / f"{nombre}-remoto.git"
    git(Path(tmp), "init", "-q", "--bare", str(remoto))
    git(raiz, "remote", "add", "origin", str(remoto))
    git(raiz, "push", "-q", "origin", "main")
    return raiz, remoto


def probar_guardado(tmp):
    raiz, remoto = repo(tmp)
    os.environ.update({k: ENTORNO[k] for k in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME",
                                                 "GIT_COMMITTER_EMAIL")})
    (raiz / "app.py").write_text("print(2)\n", encoding="utf-8")
    mensaje = guardado.guardar(raiz, respaldar=False)
    _, log = git(raiz, "log", "--oneline")
    comprobar("en la rama principal no hace commits y lo avisa",
              "hay cambios sin commit en main" in (mensaje or "") and len(log.splitlines()) == 1, mensaje)

    git(raiz, "switch", "-q", "-c", "h-001-vender")
    (raiz / "nuevo.py").write_text("x = 1\n", encoding="utf-8")
    (raiz / ".env").write_text("CLAVE=1\n", encoding="utf-8")
    (raiz / "captura.png").write_bytes(b"\x89PNG")
    (raiz / "grande.csv").write_text("x" * 1_100_000, encoding="utf-8")
    (raiz / "ruido.log").write_text("ignorado\n", encoding="utf-8")
    mensaje = guardado.guardar(raiz, respaldar=False)
    _, en_commit = git(raiz, "show", "--name-only", "--format=", "HEAD")
    _, sin_registrar = git(raiz, "status", "--porcelain", "--ignored")
    comprobar("commit en la rama de trabajo con lo registrado y lo nuevo permitido",
              set(en_commit.split()) == {"app.py", "nuevo.py"} and "wip: guardado automático" in git(raiz, "log", "-1")[1],
              en_commit)
    comprobar("deja fuera el secreto, la imagen y el archivo pesado, y lo dice; lo ignorado ni se nombra",
              all(x in sin_registrar for x in (".env", "captura.png", "grande.csv"))
              and ".env (parece un secreto)" in mensaje and "ruido.log" not in mensaje, mensaje)
    antes = git(raiz, "rev-parse", "HEAD")[1]
    nada = guardado.guardar(raiz, respaldar=False)
    comprobar("sin cambios nuevos no hace commit; solo recuerda lo que quedó fuera",
              git(raiz, "rev-parse", "HEAD")[1] == antes and (nada is None or nada.startswith("Quedaron fuera")), nada)
    comprobar("los secretos se reconocen por el nombre del archivo, no por la carpeta",
              guardado.SECRETO.search(".npmrc") and guardado.SECRETO.search("service-account-prod.json")
              and guardado.SECRETO.search("terraform.tfstate") and not guardado.SECRETO.search("acta.md")
              and not guardado.SECRETO.search(Path("docs/secretaria/acta.md").name))
    (raiz / "manual.pdf").write_bytes(b"%PDF-1.4")
    (raiz / "dato.bin2").write_bytes(b"\x00\x01\x02")
    mensaje = guardado.guardar(raiz, respaldar=False) or ""
    comprobar("deja fuera documentos y binarios aunque su extensión no esté en la lista",
              mensaje.startswith("Quedaron fuera")
              and not git(raiz, "ls-files", "manual.pdf", "dato.bin2")[1].strip()
              and "manual.pdf" in git(raiz, "status", "--porcelain")[1], mensaje)
    (raiz / "manual.pdf").unlink()
    (raiz / "dato.bin2").unlink()

    (raiz / "app.py").write_text("print(3)\n", encoding="utf-8")
    mensaje = guardado.guardar(raiz, revisar=lambda r: "gitleaks no está instalado")
    registro = json.loads((raiz / ".fabrica/trabajo/respaldo.json").read_text(encoding="utf-8"))
    _, ramas = git(raiz, "ls-remote", str(remoto))
    comprobar("sin gitleaks limpio no respalda, lo dice y lo deja anotado",
              "SIN RESPALDO" in mensaje and "wip/" not in ramas and registro["resultado"].startswith("sin subir"), mensaje)
    texto = "\n".join(estado.respaldo(raiz))
    comprobar("estado.py muestra que no hay respaldo", "AVISO" in texto and "nunca" in texto, texto)

    (raiz / ".fabrica/trabajo/respaldo.json").unlink()
    (raiz / ".github/workflows").mkdir(parents=True)
    (raiz / ".github/workflows/ci.yml").write_text("on:\n  push:\n  pull_request:\njobs: {}\n", encoding="utf-8")
    git(raiz, "add", ".github")
    git(raiz, "commit", "-qm", "flujo")
    (raiz / "app.py").write_text("print(4)\n", encoding="utf-8")
    mensaje = guardado.guardar(raiz, revisar=lambda r: None)
    comprobar("con un flujo que corre con push a cualquier rama no respalda y dice cuál",
              "SIN RESPALDO" in mensaje and "ci.yml" in mensaje, mensaje)

    (raiz / ".fabrica/trabajo/respaldo.json").unlink()
    (raiz / ".github/workflows/ci.yml").write_text(
        "on:\n  push:\n    branches-ignore: ['wip/**']\n  pull_request:\njobs: {}\n", encoding="utf-8")
    (raiz / "app.py").write_text("print(5)\n", encoding="utf-8")
    mensaje = guardado.guardar(raiz, revisar=lambda r: None)
    _, ramas = git(raiz, "ls-remote", str(remoto))
    comprobar("con gitleaks limpio y los flujos filtrados, respalda en wip/<rama>",
              "respaldado en GitHub, en wip/h-001-vender" in mensaje and "refs/heads/wip/h-001-vender" in ramas
              and "refs/heads/h-001-vender" not in ramas.replace("wip/h-001-vender", ""), mensaje + ramas)
    (raiz / "app.py").write_text("print(6)\n", encoding="utf-8")
    mensaje = guardado.guardar(raiz, revisar=lambda r: None)
    comprobar("respalda como mucho cada 30 minutos", "respaldado" not in mensaje, mensaje)
    comprobar("estado.py muestra la fecha del último respaldo",
              estado.respaldo(raiz)[0].startswith("Respaldo en GitHub: 20"), estado.respaldo(raiz))

    for flujo, malo in (("on: [push, pull_request]\n", True), ("on: push\n", True),
                        ("on:\n  push: { branches: [main, master] }\n", False),
                        ("on:\n  push:\n    tags: ['v*']\n", False), ("on:\n  pull_request:\n", False),
                        ("on:\n  push:\n    branches: ['**']\n", True),
                        ("on:\n  push:\n    branches-ignore: ['borrador/**']\n", True),
                        ("on:\n  create:\n  pull_request:\n", True)):
        (raiz / ".github/workflows/ci.yml").write_text(flujo + "jobs: {}\n", encoding="utf-8")
        if bool(guardado.flujos_sin_filtro(raiz)) != malo:
            comprobar(f"reconoce el flujo {flujo.strip()!r}", False)
            break
    else:
        comprobar("reconoce qué flujos correrían con una rama wip/", True)

    otra = Path(tmp) / "no-proyecto"
    otra.mkdir()
    git(otra, "init", "-q", "-b", "trabajo")
    (otra / "a.txt").write_text("x\n", encoding="utf-8")
    comprobar("no toca una carpeta que no es un proyecto de la fábrica", guardado.guardar(otra) is None)
    (raiz / ".fabrica/proyecto.json").write_text(json.dumps({"guardado_automatico": False}), encoding="utf-8")
    comprobar("se apaga con guardado_automatico: false", guardado.guardar(raiz) is None)


def probar_copias(tmp):
    raiz, remoto = repo(tmp, "copias")
    hermana = Path(tmp) / "copias-h002"
    git(raiz, "worktree", "add", "-q", "-b", "h-002-cobrar", str(hermana))
    (hermana / "cobro.py").write_text("total = 1\n", encoding="utf-8")
    (raiz / "app.py").write_text("print('suelto en main')\n", encoding="utf-8")
    avisos = guardado.guardar_todas(raiz, sesion="s1", respaldar=False)
    _, log_h = git(hermana, "log", "--oneline", "-1")
    _, log_m = git(raiz, "log", "--oneline")
    comprobar("guarda la copia hermana donde está el trabajo, aunque la sesión esté en la principal",
              "guardado automático" in log_h and "cobro.py" in git(hermana, "show", "--name-only", "HEAD")[1], log_h)
    comprobar("en la copia de la rama principal no hace commit y avisa de los cambios sueltos",
              len(log_m.splitlines()) == 1 and any("cambios sin commit en main" in a for a in avisos), avisos)
    (hermana / "cobro.py").write_text("total = 2\n", encoding="utf-8")
    otra_vez = guardado.guardar_todas(raiz, sesion="s1", respaldar=False)
    comprobar("el mismo aviso no se repite en la misma sesión, y el guardado sigue",
              otra_vez == [] and "total = 2" in git(hermana, "show", "HEAD:cobro.py")[1], otra_vez)
    comprobar("en una sesión nueva vuelve a avisar una vez",
              any("main" in a for a in guardado.guardar_todas(raiz, sesion="s2", respaldar=False)))
    git(raiz, "checkout", "-q", "--", "app.py")
    (hermana / "cobro.py").write_text("total = 3\n", encoding="utf-8")
    comprobar("un guardado que sale bien no dice nada",
              guardado.guardar_todas(raiz, sesion="s4", respaldar=False) == []
              and "total = 3" in git(hermana, "show", "HEAD:cobro.py")[1])

    (hermana / "acción de cobro.md").write_text("nota\n", encoding="utf-8")
    (hermana / "cobro.py").write_text("total = 4\n", encoding="utf-8")
    guardado.guardar_todas(raiz, sesion="s5", respaldar=False)
    _, nombres = git(hermana, "-c", "core.quotePath=false", "show", "--name-only", "--format=", "HEAD")
    comprobar("guarda archivos con acentos y espacios en el nombre", "acción de cobro.md" in nombres, nombres)

    (hermana / "cobro.py").write_text("total = 5\n", encoding="utf-8")
    (hermana / "otro.py").write_text("y = 1\n", encoding="utf-8")
    git(hermana, "add", "otro.py")
    antes = git(hermana, "rev-parse", "HEAD")[1]
    guardado.guardar_todas(raiz, sesion="s6", respaldar=False)
    comprobar("no barre lo que otra sesión dejó preparado a mano (git add)",
              git(hermana, "rev-parse", "HEAD")[1] == antes)
    git(hermana, "reset", "-q")
    _, gitdir = git(hermana, "rev-parse", "--git-dir")
    candado = Path(gitdir.strip()) if Path(gitdir.strip()).is_absolute() else hermana / gitdir.strip()
    (candado / "index.lock").write_text("", encoding="utf-8")
    guardado.guardar_todas(raiz, sesion="s7", respaldar=False)
    comprobar("no toca una copia con otra operación de git en curso (index.lock)",
              git(hermana, "rev-parse", "HEAD")[1] == antes)
    (candado / "index.lock").unlink()


def probar_flujos(tmp):
    raiz = Path(tmp) / "flujos"
    (raiz / ".github/workflows").mkdir(parents=True)
    w = raiz / ".github/workflows"
    (w / "ci.yml").write_text("name: CI\r\non:\r\n  push:\r\n  pull_request:\r\njobs: {}\r\n", encoding="utf-8",
                              newline="")
    (w / "otro.yml").write_text("on:\n  push: {}\njobs: {}\n", encoding="utf-8")
    (w / "bien.yml").write_text("on:\n  push:\n    branches: [main, master]\njobs: {}\n", encoding="utf-8")
    (w / "lista.yml").write_text("on: [push, pull_request]\njobs: {}\n", encoding="utf-8")
    cambiados = _kit.ignorar_wip_en_flujos(raiz)
    ci = (w / "ci.yml").read_bytes().decode("utf-8")
    comprobar("el kit agrega branches-ignore wip a los flujos sin filtro, respetando los finales de línea",
              cambiados == [".github/workflows/ci.yml", ".github/workflows/otro.yml"]
              and "  push:\r\n    branches-ignore: ['wip/**']" in ci and "branches-ignore" in (w / "otro.yml").read_text()
              and "branches-ignore" not in (w / "bien.yml").read_text(), (cambiados, ci))
    comprobar("una segunda vez no cambia nada", _kit.ignorar_wip_en_flujos(raiz) == [])
    comprobar("la forma en lista no se toca y la red del hook la sigue viendo",
              (w / "lista.yml").read_text().startswith("on: [push") and guardado.flujos_sin_filtro(raiz) == ["lista.yml"],
              guardado.flujos_sin_filtro(raiz))


def probar_limpieza():
    from datetime import datetime, timezone
    ahora = datetime(2026, 12, 1, tzinfo=timezone.utc)
    refs = [{"ref": "refs/heads/wip/h-001-viejo", "object": {"sha": "a"}},
            {"ref": "refs/heads/wip/h-002-vivo", "object": {"sha": "b"}},
            {"ref": "refs/heads/wip/h-003-reciente", "object": {"sha": "c"}}]
    fechas = {"a": "2026-11-01T00:00:00Z", "b": "2026-11-01T00:00:00Z", "c": "2026-11-28T00:00:00Z"}
    borrados = []

    def falso(orden):
        comando = " ".join(orden)
        if "matching-refs" in comando:
            return json.dumps(refs)
        if "/git/commits/" in comando:
            return json.dumps({"committer": {"date": fechas[comando.rsplit("/", 1)[1]]}})
        if "DELETE" in comando:
            borrados.append(comando.rsplit("/", 2)[-1])
            return "{}"
        if "git/ref/heads/h-002-vivo" in comando:
            return "{}"
        return None
    candidatas = limpiar.abandonadas(falso, ahora)
    comprobar("borra solo los respaldos viejos cuya rama de origen ya no existe",
              candidatas == [("wip/h-001-viejo", 30)], candidatas)
    with redirect_stdout(io.StringIO()):
        limpiar.main(["--aplicar"], ejecutar=falso)
    comprobar("con --aplicar los borra por la API", borrados == ["h-001-viejo"], borrados)

    def caido(orden):
        comando = " ".join(orden)
        if "git/ref/heads/" in comando:
            raise limpiar.SinRespuesta("HTTP 502")
        return falso(orden)
    borrados.clear()
    with redirect_stdout(io.StringIO()) as salida:
        codigo = limpiar.main(["--aplicar"], ejecutar=caido)
    comprobar("si GitHub falla al preguntar por la rama de origen, no borra nada",
              codigo == 0 and borrados == [] and "no se borra nada" in salida.getvalue(), salida.getvalue())


def probar_guardia(tmp):
    raiz = Path(tmp) / "g"
    (raiz / "pruebas/aceptacion/H-001").mkdir(parents=True)
    protegida = str(raiz / "pruebas/aceptacion/H-001/test_x.py")
    entrada = {"tool_name": "Edit", "tool_input": {"file_path": protegida}}
    comprobar("sin construcción en curso, deja editar las pruebas", guardia.decidir(entrada, raiz) is None)
    (raiz / ".fabrica/trabajo").mkdir(parents=True)
    (raiz / ".fabrica/trabajo/construyendo").write_text("H-001\n", encoding="utf-8")
    respuesta = guardia.decidir(entrada, raiz)
    comprobar("durante una construcción niega editar una prueba aprobada, con su motivo",
              respuesta and respuesta["hookSpecificOutput"]["permissionDecision"] == "deny"
              and "pruebas/aceptacion/H-001/test_x.py" in respuesta["hookSpecificOutput"]["permissionDecisionReason"])
    comprobar("nunca aprueba ni reescribe: solo niega", "updatedInput" not in json.dumps(respuesta))
    comprobar("deja editar el código y lo de fuera del proyecto",
              guardia.decidir({"tool_input": {"file_path": str(raiz / "src/a.py")}}, raiz) is None
              and guardia.decidir({"tool_input": {"file_path": "/etc/pruebas/aceptacion/x"}}, raiz) is None)
    proyecto_g, _ = repo(tmp, "guardia-repo")
    hermana_g = Path(tmp) / "guardia-h001"
    git(proyecto_g, "worktree", "add", "-q", "-b", "h-001", str(hermana_g))
    (hermana_g / ".fabrica/trabajo").mkdir(parents=True)
    (hermana_g / ".fabrica/trabajo/construyendo").write_text("H-001\n", encoding="utf-8")
    entrada_h = {"tool_input": {"file_path": str(hermana_g / "pruebas/aceptacion/H-001/test_y.py")}}
    respuesta_h = guardia.decidir(entrada_h, proyecto_g)
    comprobar("protege las pruebas también cuando se construye en una copia hermana de la sesión",
              respuesta_h and respuesta_h["hookSpecificOutput"]["permissionDecision"] == "deny")
    hecho = subprocess.run([sys.executable, str(SCRIPTS / "hook_guardia.py")], input="no es json", text=True,
                           capture_output=True, env=dict(ENTORNO, CLAUDE_PROJECT_DIR=str(raiz)))
    comprobar("con una entrada rota deja pasar sin fallar", hecho.returncode == 0 and hecho.stdout == "")


def probar_filtro():
    corta = ["a", "b", "1 passed in 0.1s"]
    comprobar("una salida corta pasa entera", filtro.filtrar(corta) == corta)
    larga = [f"pruebas/test_{i}.py::test_x PASSED" for i in range(300)]
    larga[150:150] = ["______ test_cobro ______", "    def test_cobro():", ">       assert 1 == 2",
                      "E       assert 1 == 2"]
    larga += ["=== short test summary info ===", "FAILED pruebas/test_cobro.py::test_cobro", "== 1 failed, 300 passed =="]
    salida = filtro.filtrar(larga)
    texto = "\n".join(salida)
    comprobar("una salida larga deja la falla con su detalle y el resumen, y recorta lo demás",
              "E       assert 1 == 2" in texto and "1 failed, 300 passed" in texto and len(salida) < 80
              and "omitidas" in texto, len(salida))
    with redirect_stdout(io.StringIO()) as capturado:
        codigo = filtro.main(["--", sys.executable, "-c", "import sys; print('hola'); sys.exit(3)"])
    comprobar("conserva el código de salida del comando", codigo == 3 and "[código de salida: 3]" in capturado.getvalue())


def probar_archivo(tmp):
    raiz, _ = repo(tmp, "archivo")
    historias = raiz / "docs/historias"
    historias.mkdir(parents=True)
    (historias / "H-001-a.md").write_text("---\nid: H-001\nestado: hecho\n---\n", encoding="utf-8")
    (historias / "H-002-b.md").write_text("---\nid: H-002\nestado: en-curso\n---\n", encoding="utf-8")
    (historias / "H-003-c.md").write_text("---\nid: H-003\nestado: hecho\n---\n", encoding="utf-8")
    (raiz / "docs/planes/H-003").mkdir(parents=True)
    (raiz / "docs/planes/H-001-plan.md").write_text("# Plan\n", encoding="utf-8")
    (raiz / "docs/planes/H-003/plan.md").write_text("# Plan\n", encoding="utf-8")
    (raiz / "docs/planes/H-003/tarea-01.md").write_text("## Tarea 1: a\n", encoding="utf-8")
    (raiz / "docs/seguridad/historias").mkdir(parents=True)
    (raiz / "docs/seguridad/historias/H-001.md").write_text("# Amenazas\n", encoding="utf-8")
    git(raiz, "add", "-A")
    git(raiz, "commit", "-qm", "historias")
    with redirect_stdout(io.StringIO()) as salida:
        codigo = archivar.main(["H-002"], raiz=raiz)
    comprobar("no archiva una historia sin terminar", codigo == 1 and "solo se archiva una historia hecha" in salida.getvalue())
    with redirect_stdout(io.StringIO()):
        vista = archivar.main(["H-001"], raiz=raiz)
    comprobar("la vista previa no mueve nada", vista == 0 and (raiz / "docs/planes/H-001-plan.md").exists())
    with redirect_stdout(io.StringIO()):
        a1 = archivar.main(["H-001", "--aplicar"], raiz=raiz)
        a3 = archivar.main(["h-003", "--aplicar"], raiz=raiz)
    comprobar("archiva el plan de un archivo, el plan partido y el modelo de amenazas, y deja la historia",
              a1 == a3 == 0 and (raiz / "docs/archivo/planes/H-001-plan.md").exists()
              and (raiz / "docs/archivo/planes/H-003/tarea-01.md").exists()
              and (raiz / "docs/archivo/seguridad/historias/H-001.md").exists()
              and not (raiz / "docs/planes/H-003").exists() and (historias / "H-001-a.md").exists())
    cifras = estado.cifras_de_historias(raiz, estado.RUTAS_POR_DEFECTO)
    comprobar("las historias archivadas siguen contando en el estado", cifras["total"] == 3 and cifras["hechas"] == 2)


def probar_hooks_en_settings(tmp):
    raiz = Path(tmp) / "hooks"
    (raiz / ".claude").mkdir(parents=True)
    propio = {"permissions": {"deny": ["Read(./.env)"]},
              "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "mi-hook.sh"}]}]}}
    (raiz / ".claude/settings.json").write_text(json.dumps(propio), encoding="utf-8")
    _kit.fusionar_hooks(raiz)
    _kit.fusionar_hooks(raiz)
    datos = json.loads((raiz / ".claude/settings.json").read_text(encoding="utf-8"))
    comandos = [h["command"] for g in datos["hooks"]["PreToolUse"] for h in g["hooks"]]
    comprobar("los hooks del kit se suman sin tocar los permisos ni los hooks propios, y no se duplican",
              datos["permissions"] == propio["permissions"] and "mi-hook.sh" in comandos
              and sum("hook_guardia" in c for c in comandos) == 1
              and sum("hook_guardado" in h["command"] for g in datos["hooks"]["Stop"] for h in g["hooks"]) == 1, datos)
    (raiz / ".claude/settings.json").write_text("{roto", encoding="utf-8")
    aviso = _kit.fusionar_hooks(raiz)
    comprobar("un settings.json roto no se toca y se avisa",
              aviso and (raiz / ".claude/settings.json").read_text(encoding="utf-8") == "{roto")


def probar_estado(tmp):
    raiz, _ = repo(tmp, "estado")
    (raiz / "docs/historias").mkdir(parents=True)
    (raiz / "docs/historias/H-005-x.md").write_text("---\nid: H-005\nestado: en-curso\ntitulo: X\n---\n", encoding="utf-8")
    plan = raiz / "docs/planes/H-005"
    plan.mkdir(parents=True)
    (plan / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (plan / "tarea-01.md").write_text("## Tarea 1: el modelo\n", encoding="utf-8")
    (plan / "tarea-02.md").write_text("## Tarea 2: la vista\n", encoding="utf-8")
    (plan / "registro.md").write_text("# Registro\n\nTarea 1: completa (commit abc)\n", encoding="utf-8")
    lineas = "\n".join(estado.reunir(raiz, estado.correr, con_red=False))
    comprobar("lee el avance de un plan partido", "plan: 1 de 2 tareas; sigue la 2: la vista" in lineas, lineas)

    entrada = ("Corrida 2026-11-18 · paso: construir\n- Consumo: H-005 · 34 min · agentes: sonnet ×2, opus ×1 · leídos: "
               "6 documentos, ~41.000 tokens\n")
    lecturas = estado.leer_consumo(entrada)
    comprobar("lee la línea de consumo de la bitácora",
              lecturas and lecturas[0][0] == "H-005" and lecturas[0][1] == 34 and lecturas[0][3] == 41000
              and lecturas[0][2] == {"sonnet": 2, "opus": 1}, lecturas)

    def falso(orden, _raiz):
        comando = " ".join(orden)
        if "issues/5/comments" in comando:
            return json.dumps([{"body": entrada}, {"body": entrada.replace("34 min", "10 min")}]) if comando.endswith("page=1") else "[]"
        if "issues?state=all" in comando:
            return json.dumps([{"number": 5, "title": "Bitácora de corridas de la fábrica"}])
        return None
    texto = "\n".join(estado.consumo(raiz, falso))
    comprobar("suma el consumo por historia", "H-005  2 registro(s) · 44 min · agentes: opus ×2, sonnet ×4 · ~82.000"
              in texto, texto)

    publicaciones = []

    def falso_gh(orden, _raiz):
        comando = " ".join(orden)
        if "-X" in orden:
            publicaciones.append(orden)
            return "{}"
        if "pulls?state=open" in comando:
            return "[]"
        if "issues?state=open" in comando:
            return json.dumps([{"number": 9, "title": "Estado del proyecto", "labels": []}])
        return estado.correr(orden, _raiz)
    resultado = estado.publicar(raiz, falso_gh, ahora="2026-11-18 08:00 UTC")
    cuerpo = next((a for a in publicaciones[0] if a.startswith("body=")), "") if publicaciones else ""
    comprobar("publica el estado en su issue, sin la rama de la máquina que calcula",
              resultado == ["Estado publicado en #9."] and "PATCH" in publicaciones[0] and "H-005" in cuerpo
              and "Rama:" not in cuerpo and "2026-11-18 08:00 UTC" in cuerpo, (resultado, cuerpo[:300]))

    (raiz / "docs/siguiente-accion.md").write_text("# Siguiente acción\n", encoding="utf-8")
    hace = int(time.time()) - 3 * 86400
    entorno_viejo = dict(ENTORNO, GIT_AUTHOR_DATE=f"@{hace}", GIT_COMMITTER_DATE=f"@{hace}")
    subprocess.run(["git", "add", "-A"], cwd=raiz, env=ENTORNO)
    subprocess.run(["git", "commit", "-qm", "siguiente acción"], cwd=raiz, env=entorno_viejo)
    (raiz / "app.py").write_text("print('integrado')\n", encoding="utf-8")
    git(raiz, "commit", "-qam", "integrado después")
    aviso = estado.siguiente_accion_vieja(raiz, estado.RUTAS_POR_DEFECTO, estado.correr)
    comprobar("avisa cuando la siguiente acción es anterior a lo último integrado",
              aviso and "docs/siguiente-accion.md es del" in aviso[0], aviso)
    (raiz / "docs/siguiente-accion.md").write_text("# Siguiente acción\n\nAl día.\n", encoding="utf-8")
    git(raiz, "commit", "-qam", "siguiente acción al día")
    comprobar("no avisa cuando está al día", estado.siguiente_accion_vieja(raiz, estado.RUTAS_POR_DEFECTO,
                                                                           estado.correr) == [])


def main():
    with tempfile.TemporaryDirectory() as tmp:
        probar_guardado(tmp)
        probar_copias(tmp)
        probar_flujos(tmp)
        probar_limpieza()
        probar_guardia(tmp)
        probar_filtro()
        probar_archivo(tmp)
        probar_hooks_en_settings(tmp)
        probar_estado(tmp)
    ok = sum(1 for _, bueno in resultados if bueno)
    print(f"Pruebas de las herramientas: {ok}/{len(resultados)} correctas.")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
