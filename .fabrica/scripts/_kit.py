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


def preparar_proyecto(raiz_instancia, destino, cliente, negocio, proyecto, nombre, propietario, version,
                      fase="descubrimiento", adoptado=False):
    """Crea los archivos propios iniciales que le falten al proyecto, sin pisar ninguno que ya exista.

    Devuelve las rutas creadas y, si se completó un .gitignore que ya existía, su texto anterior (o None).
    """
    raiz_instancia, destino = Path(raiz_instancia), Path(destino)
    repo, hoy, creados = f"{cliente}-{proyecto}", date.today().isoformat(), []
    datos = {"version_formato": 1, "cliente": cliente, "negocio": negocio, "proyecto": proyecto, "nombre": nombre,
             "repositorio": repo, "nucleo": version, "creado": hoy, "pausa": False,
             "direccion": propietario,  # cuenta de GitHub cuyo "intégralo" autoriza un merge (nucleo/autonomia.md)
             "motor": {"pasos_por_corrida": 1}}  # nucleo/motor.md
    _crear(destino, ".fabrica/proyecto.json", json.dumps(datos, ensure_ascii=False, indent=2) + "\n", creados)

    estado = json.loads((raiz_instancia / "nucleo" / "plantillas" / "estado.json").read_text(encoding="utf-8"))
    estado = {k: v for k, v in estado.items() if not k.startswith("_")}
    estado.update({"cliente": cliente, "negocio": negocio, "proyecto": proyecto, "nucleo": version, "fase": fase,
                   "semaforo": "verde", "riesgo_principal": "",
                   "actualizado": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    estado["espera_direccion"]["enlace"] = (
        f"https://github.com/{propietario}/{repo}/issues?q=label%3Aespera%3Adireccion" if propietario else "")
    _crear(destino, ".fabrica/estado.json", json.dumps(estado, ensure_ascii=False, indent=2) + "\n", creados)

    constitucion = (raiz_instancia / "nucleo" / "plantillas" / "constitucion-proyecto.md").read_text(encoding="utf-8")
    constitucion = constitucion.replace("# Constitución de <proyecto>", f"# Constitución de {nombre}", 1)
    _crear(destino, "docs/constitucion.md", constitucion.replace("<AAAA-MM-DD>", hoy, 1), creados)
    origen = "adoptado por" if adoptado else "creado desde"
    _crear(destino, "docs/bitacora.md", f"# Bitácora\n\n## {hoy}\n\n- Proyecto {origen} la fábrica (núcleo {version}).\n",
           creados)
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
