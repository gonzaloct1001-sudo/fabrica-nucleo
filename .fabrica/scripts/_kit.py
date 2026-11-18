"""Cómo se arma el kit de proyecto: lo mismo al crear un proyecto (nuevo_proyecto.py), al adoptar uno que ya existe
(adoptar_proyecto.py) y al actualizarlo (actualizar_kit.py).

El kit es lo que trae kit/ más una copia del método y la base del rubro del proyecto:
- nucleo/ va a .fabrica/nucleo/;
- rubros/<rubro>/ de la instancia va a .fabrica/rubro/. Si la instancia todavía no tiene esa base, va un aviso en su
  lugar, para que la ruta exista siempre (nucleo/aprendizaje.md).

Además, cada proyecto tiene sus archivos propios iniciales (preparar_proyecto): su ficha, su estado, su constitución,
su bitácora y sus carpetas. Se crean solo si faltan, así que adoptar un proyecto no pisa lo que ya tenía.
"""
import json
import re
import shutil
from datetime import date, datetime, timezone
from pathlib import Path

import _nucleo

COPIA_DEL_METODO = Path(".fabrica") / "nucleo"
COPIA_DEL_RUBRO = Path(".fabrica") / "rubro"
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

SIN_BASE = """# Rubro: {rubro}

La fábrica todavía no tiene una base de conocimiento de este rubro. Se crea en la instancia, en `rubros/{rubro}/`,
desde `.fabrica/nucleo/plantillas/rubro.md`, y llega aquí con la siguiente actualización del kit.

Mientras tanto, el descubrimiento parte de cero: todo lo que el pedido no diga es una pregunta.
"""

GITIGNORE = """# Entorno y secretos
.env
.env.*
!.env.example

# Archivos de trabajo de la fábrica (fichas, informes y diffs de cada corrida)
.fabrica/trabajo/
.fabrica/respaldo-nucleo/

# Configuración personal del asistente
.claude/settings.local.json

# Compilados y cachés: nadie puede leerlos ni revisarlos, así que no van al repositorio
__pycache__/
*.py[cod]
*.class

# Sistema
.DS_Store
Thumbs.db
desktop.ini
"""
CARPETAS = ("docs/historias", "docs/planes", "docs/adr", "docs/descubrimiento", "pruebas/aceptacion")


def copiar_arbol(origen, destino):
    origen, destino = Path(origen), Path(destino)
    for x in sorted(origen.rglob("*")):
        rel = x.relative_to(origen)
        if x.is_file() and not (set(rel.parts) & _nucleo.IGNORAR_PARTES) and rel.name not in _nucleo.IGNORAR_NOMBRES \
                and x.suffix != ".pyc":
            (destino / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(x, destino / rel)


def tabla(ficha, seccion):
    """Filas de la tabla bajo `## <seccion>` de una ficha de cliente, como listas de celdas (sin encabezado)."""
    filas, dentro = [], False
    for linea in Path(ficha).read_text(encoding="utf-8").splitlines():
        if linea.startswith("## "):
            dentro = linea.strip() == f"## {seccion}"
            continue
        if dentro and linea.startswith("|"):
            celdas = [c.strip().strip("`") for c in linea.strip().strip("|").split("|")]
            if celdas and SLUG.match(celdas[0]):
                filas.append(celdas)
    return filas


def negocios(ficha):
    """{negocio: rubro} de la tabla "Negocios" de una ficha de cliente."""
    return {f[0]: f[1] for f in tabla(ficha, "Negocios") if len(f) >= 2}


def rubro_de(raiz_instancia, cliente, negocio):
    """Rubro del negocio según la ficha del cliente, o cadena vacía si no se encuentra."""
    ficha = Path(raiz_instancia) / "clientes" / cliente / "cliente.md"
    return negocios(ficha).get(negocio, "") if ficha.exists() else ""


def armar(raiz_instancia, destino, rubro=""):
    """Copia en `destino` el kit de la instancia, con su copia del método y la base del rubro."""
    raiz_instancia, destino = Path(raiz_instancia), Path(destino)
    copiar_arbol(raiz_instancia / "kit", destino)
    copiar_arbol(raiz_instancia / "nucleo", destino / COPIA_DEL_METODO)
    base = raiz_instancia / "rubros" / rubro if rubro and SLUG.match(rubro) else None
    if base and base.is_dir() and any(base.rglob("*.md")):
        copiar_arbol(base, destino / COPIA_DEL_RUBRO)
    else:
        (destino / COPIA_DEL_RUBRO).mkdir(parents=True, exist_ok=True)
        (destino / COPIA_DEL_RUBRO / "conocimiento.md").write_text(SIN_BASE.format(rubro=rubro or "sin definir"),
                                                                  encoding="utf-8")


def _crear(destino, rel, texto, creados):
    p = Path(destino) / rel
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8")
        creados.append(rel)


ID_DE_HISTORIA = re.compile(r"^id:\s*[A-Z]+-\d+\s*(#.*)?$")
NO_BUSCAR = {".git", ".fabrica", ".claude", ".github", "node_modules", ".venv", "__pycache__"}


def _tiene_id_de_historia(archivo):
    """Si la cabecera `---` del archivo, y solo ella, tiene un `id: X-NNN`."""
    try:
        lineas = archivo.read_text(encoding="utf-8", errors="replace").splitlines()[:40]
    except OSError:
        return False
    if not lineas or lineas[0].strip() != "---":
        return False
    for linea in lineas[1:]:
        if linea.strip() == "---":
            return False
        if ID_DE_HISTORIA.match(linea.strip()):
            return True
    return False


def detectar_rutas(raiz):
    """En un proyecto que ya existe, dónde guarda sus historias, sus planes, su siguiente acción y sus notas para
    sesiones, si no usa las rutas de la fábrica.

    Historias: la carpeta con más archivos .md cuya cabecera tiene un `id: X-NNN`. Planes: la que tiene más archivos
    `*-plan.md`. Siguiente acción y notas: el archivo con ese nombre, si no está en docs/. Devuelve solo las rutas
    distintas de las de la fábrica.
    """
    import os
    raiz = Path(raiz)
    historias, planes, archivos_por_nombre = {}, {}, {}
    for actual, carpetas, archivos in os.walk(raiz):
        carpetas[:] = sorted(c for c in carpetas if c not in NO_BUSCAR)  # no recorre node_modules ni .git
        rel = Path(actual).relative_to(raiz)
        if not rel.parts:
            continue
        carpeta = rel.as_posix()
        for nombre in archivos:
            if not nombre.endswith(".md"):
                continue
            if nombre in ("siguiente-accion.md", "notas-para-sesiones.md"):
                archivos_por_nombre.setdefault(nombre, []).append(f"{carpeta}/{nombre}")
            if nombre.endswith("-plan.md"):
                planes[carpeta] = planes.get(carpeta, 0) + 1
            elif _tiene_id_de_historia(Path(actual) / nombre):
                historias[carpeta] = historias.get(carpeta, 0) + 1
    rutas = {}
    for clave, nombre in (("siguiente_accion", "siguiente-accion.md"), ("notas", "notas-para-sesiones.md")):
        if not (raiz / "docs" / nombre).exists() and nombre in archivos_por_nombre:
            rutas[clave] = sorted(archivos_por_nombre[nombre])[0]
    for clave, cuentas, defecto in (("historias", historias, "docs/historias"), ("planes", planes, "docs/planes")):
        if cuentas:
            mejor = max(sorted(cuentas), key=lambda c: cuentas[c])
            if mejor != defecto:
                rutas[clave] = mejor
    return rutas


HOOK_GUARDIA = "python3 \"$CLAUDE_PROJECT_DIR/.fabrica/scripts/hook_guardia.py\""
HOOK_GUARDADO = "python3 \"$CLAUDE_PROJECT_DIR/.fabrica/scripts/hook_guardado.py\""
HOOKS_DEL_KIT = {"PreToolUse": [{"matcher": "Edit|Write|MultiEdit|NotebookEdit",
                                 "hooks": [{"type": "command", "command": HOOK_GUARDIA, "timeout": 10}]}],
                 "Stop": [{"hooks": [{"type": "command", "command": HOOK_GUARDADO, "timeout": 120}]}]}


def _es_del_kit(grupo):
    return any(".fabrica/scripts/hook_" in str(h.get("command", "")) for h in grupo.get("hooks", []))


def fusionar_hooks(destino):
    """Deja en `.claude/settings.json` los hooks del kit (núcleo 0.13) y conserva todo lo demás del proyecto.

    Reemplaza solo los grupos de hooks que llaman a `.fabrica/scripts/hook_*`. Si el archivo no es un JSON válido, no
    lo toca y devuelve el aviso. Devuelve None si no hubo nada que decir.
    """
    ruta = Path(destino) / ".claude" / "settings.json"
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    except ValueError:
        return f"{ruta.relative_to(destino).as_posix()} no es un JSON válido: no se agregaron los hooks del kit."
    if not isinstance(datos, dict):
        return f"{ruta.relative_to(destino).as_posix()} no es un objeto JSON: no se agregaron los hooks del kit."
    hooks = datos.get("hooks") if isinstance(datos.get("hooks"), dict) else {}
    for evento, grupos in HOOKS_DEL_KIT.items():
        propios = [g for g in hooks.get(evento, []) if isinstance(g, dict) and not _es_del_kit(g)]
        hooks[evento] = propios + grupos
    datos["hooks"] = hooks
    ruta.parent.mkdir(parents=True, exist_ok=True)
    nuevo = json.dumps(datos, ensure_ascii=False, indent=2) + "\n"
    if not ruta.exists() or ruta.read_text(encoding="utf-8") != nuevo:
        ruta.write_text(nuevo, encoding="utf-8")
    return None


PUSH_SIN_FILTRO = re.compile(r"^(?P<sangria>[ \t]+)push[ \t]*:[ \t]*(\{[ \t]*\})?[ \t]*(#.*)?$")


def flujos_a_filtrar(destino):
    """Los flujos del proyecto cuyo `push:` (en forma de bloque) no filtra ramas: correrían con cada rama wip/."""
    malos = []
    carpeta = Path(destino) / ".github" / "workflows"
    for flujo in sorted(carpeta.glob("*.y*ml")) if carpeta.is_dir() else []:
        lineas = flujo.read_text(encoding="utf-8").splitlines()
        for i, linea in enumerate(lineas):
            m = PUSH_SIN_FILTRO.match(linea)
            if not m:
                continue
            sangria = len(m.group("sangria").expandtabs())
            cuerpo = []
            for siguiente in lineas[i + 1:]:
                if siguiente.strip() and len(siguiente) - len(siguiente.lstrip()) <= sangria:
                    break
                cuerpo.append(siguiente)
            if not re.search(r"\b(branches|branches-ignore|tags)\s*:", "\n".join(cuerpo)):
                malos.append(flujo.relative_to(destino).as_posix())
            break
    return malos


def ignorar_wip_en_flujos(destino):
    """Agrega `branches-ignore: ['wip/**']` a cada flujo cuyo `push:` no filtra ramas (núcleo 0.13).

    Así los respaldos del guardado automático (ramas wip/) no gastan minutos de Actions. Solo cambia la forma de
    bloque (`push:` en su propia línea); `on: push` u `on: [push, …]` se dejan y `verificar_proyecto.py` los avisa.
    Devuelve las rutas que cambió.
    """
    cambiados = []
    for rel in flujos_a_filtrar(destino):
        ruta = Path(destino) / rel
        lineas = ruta.read_bytes().decode("utf-8").splitlines(keepends=True)  # sin traducir CRLF
        for i, linea in enumerate(lineas):
            m = PUSH_SIN_FILTRO.match(linea.rstrip("\r\n"))
            if m:
                sangria = m.group("sangria")
                fin = "\r\n" if linea.endswith("\r\n") else "\n"
                lineas[i] = f"{sangria}push:{fin}"
                lineas.insert(i + 1, f"{sangria}  branches-ignore: ['wip/**']  # respaldos del guardado automático{fin}")
                break
        ruta.write_bytes("".join(lineas).encode("utf-8"))
        cambiados.append(rel)
    return cambiados


def _script_de_estado(raiz_instancia):
    """El script de estado del kit de la instancia, cargado como módulo (sin dejar __pycache__ en el kit)."""
    import importlib.util
    import sys
    ruta = Path(raiz_instancia) / "kit" / ".fabrica" / "scripts" / "estado.py"
    spec = importlib.util.spec_from_file_location("fabrica_estado_kit", ruta)
    modulo = importlib.util.module_from_spec(spec)
    antes, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(modulo)
    finally:
        sys.dont_write_bytecode = antes
    return modulo


def _tope_de_instancia(raiz_instancia):
    """El tope de historias en curso de `.fabrica/config.json` de la instancia, o 1."""
    try:
        config = json.loads((Path(raiz_instancia) / ".fabrica" / "config.json").read_text(encoding="utf-8"))
        tope = config.get("topes", {}).get("historias_en_curso_por_proyecto", 1)
    except (OSError, ValueError, AttributeError):
        return 1
    return tope if isinstance(tope, int) and tope > 0 else 1


def preparar_proyecto(raiz_instancia, destino, cliente, negocio, proyecto, nombre, propietario, version,
                      fase="descubrimiento", adoptado=False, rutas=None):
    """Crea los archivos propios iniciales que le falten al proyecto, sin pisar ninguno que ya exista.

    Devuelve las rutas creadas y, si se completó un .gitignore que ya existía, su texto anterior (o None).
    """
    raiz_instancia, destino = Path(raiz_instancia), Path(destino)
    repo, hoy, creados = f"{cliente}-{proyecto}", date.today().isoformat(), []
    datos = {"version_formato": 1, "cliente": cliente, "negocio": negocio, "proyecto": proyecto, "nombre": nombre,
             "repositorio": repo, "nucleo": version, "creado": hoy, "pausa": False,
             "direccion": propietario,  # cuenta de GitHub cuyo "intégralo" autoriza un merge (nucleo/autonomia.md)
             "motor": {"pasos_por_corrida": 1, "corridas_por_dia": 6},  # nucleo/motor.md
             # topes del proyecto (verificar_proyecto.py): los de la instancia, si los fija
             "topes": {"historias_en_curso": _tope_de_instancia(raiz_instancia), "lineas_siguiente_accion": 40},
             # dónde viven las historias y los planes; un proyecto adoptado puede usar las suyas (estado.py)
             "rutas": {"historias": "docs/historias", "planes": "docs/planes",
                       "siguiente_accion": "docs/siguiente-accion.md", "notas": "docs/notas-para-sesiones.md",
                       **(rutas or {})},
             # decisiones de la Dirección que el proyecto delegó (nucleo/autonomia.md, "Delegación por proyecto")
             "autonomia": {"integra": "direccion", "pruebas_aprobadas": "direccion", "cierra_historias": "direccion"}}
    _crear(destino, ".fabrica/proyecto.json", json.dumps(datos, ensure_ascii=False, indent=2) + "\n", creados)

    estado = json.loads((raiz_instancia / "nucleo" / "plantillas" / "estado.json").read_text(encoding="utf-8"))
    estado = {k: v for k, v in estado.items() if not k.startswith("_")}
    estado.update({"cliente": cliente, "negocio": negocio, "proyecto": proyecto, "nucleo": version, "fase": fase,
                   "semaforo": "verde", "riesgo_principal": "",
                   "actualizado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    estado["espera_direccion"]["enlace"] = (
        f"https://github.com/{propietario}/{repo}/issues?q=label%3Aespera%3Adireccion" if propietario else "")
    # Las cifras de historias salen del disco con el mismo script que las verifica (núcleo 0.12): así un proyecto
    # adoptado que ya tiene historias nace con su estado coherente.
    estado["historias"] = {**estado.get("historias", {}),
                           **_script_de_estado(raiz_instancia).cifras_de_historias(destino, {
                               "historias": datos["rutas"]["historias"], "planes": datos["rutas"]["planes"]})}
    # Un proyecto nuevo nace con la coherencia del estado exigida; uno adoptado, en modo aviso, hasta que corra
    # `estado.py --escribir` en su propio PR (lo nuevo nace apagado: nucleo/actualizaciones.md).
    estado["cifras_generadas"] = not adoptado
    _crear(destino, ".fabrica/estado.json", json.dumps(estado, ensure_ascii=False, indent=2) + "\n", creados)

    constitucion = (raiz_instancia / "nucleo" / "plantillas" / "constitucion-proyecto.md").read_text(encoding="utf-8")
    constitucion = constitucion.replace("# Constitución de <proyecto>", f"# Constitución de {nombre}", 1)
    _crear(destino, "docs/constitucion.md", constitucion.replace("<AAAA-MM-DD>", hoy, 1), creados)
    origen = "adoptado por" if adoptado else "creado desde"
    _crear(destino, "docs/bitacora.md", f"# Bitácora\n\n## {hoy}\n\n- Proyecto {origen} la fábrica (núcleo {version}).\n",
           creados)
    plantillas = raiz_instancia / "nucleo" / "plantillas"
    siguiente = (plantillas / "siguiente-accion.md").read_text(encoding="utf-8")
    _crear(destino, "docs/siguiente-accion.md", siguiente.replace("<fase>", fase, 1).replace("<AAAA-MM-DD>", hoy, 1),
           creados)
    _crear(destino, "docs/notas-para-sesiones.md", (plantillas / "notas-para-sesiones.md").read_text(encoding="utf-8"),
           creados)
    # Los hooks del kit: en un proyecto nuevo, o adoptado sin configuración de Claude propia. Si ya tiene una, no se
    # toca al adoptar (deshacer la adopción no podría restaurarla); la siguiente actualización del kit los fusiona,
    # con respaldo.
    if not adoptado:  # al adoptar no hay cómo restaurarlos si falla: los ajusta la actualización, con respaldo
        ignorar_wip_en_flujos(destino)
    if not (Path(destino) / ".claude" / "settings.json").exists():
        aviso = fusionar_hooks(destino)
        if aviso:
            print(f"Aviso: {aviso}")
        else:
            creados.append(".claude/settings.json")
    for carpeta in CARPETAS:
        if not (destino / carpeta).is_dir() or not any((destino / carpeta).iterdir()):
            _crear(destino, f"{carpeta}/.gitkeep", "", creados)
    _crear(destino, "README.md", f"# {nombre}\n\nProyecto construido con una fábrica de software. Las instrucciones "
           f"para agentes están en `AGENTS.md`; el método, en `.fabrica/nucleo/`; las historias, en "
           f"`docs/historias/`.\n", creados)
    _crear(destino, ".env.example", "# Variables de entorno del proyecto. Nunca pongas valores reales aquí.\n", creados)

    ignorar, previo = destino / ".gitignore", None
    if not ignorar.exists():
        _crear(destino, ".gitignore", GITIGNORE, creados)
    else:
        texto = ignorar.read_text(encoding="utf-8")
        tiene = {l.strip() for l in texto.splitlines()}
        faltan = [l for l in GITIGNORE.splitlines() if l.strip() and not l.startswith("#") and l.strip() not in tiene]
        if faltan:
            previo = texto
            ignorar.write_text(texto.rstrip("\n") + "\n\n# Fábrica de software\n" + "\n".join(faltan) + "\n",
                               encoding="utf-8")
    return creados, previo


def anotar_en_ficha(ficha, cliente, negocio, proyecto):
    """Agrega el proyecto a la tabla "Proyectos" de la ficha del cliente, si no está."""
    if any(f[0] == proyecto for f in tabla(ficha, "Proyectos")):
        return True
    lineas = Path(ficha).read_text(encoding="utf-8").splitlines()
    for i, linea in enumerate(lineas):
        if linea.startswith("| Proyecto | Negocio | Repositorio | Estado |"):
            j = i + 2
            while j < len(lineas) and lineas[j].startswith("|"):
                j += 1
            lineas.insert(j, f"| {proyecto} | {negocio} | `{cliente}-{proyecto}` | activo |")
            Path(ficha).write_text("\n".join(lineas) + "\n", encoding="utf-8")
            return True
    return False
