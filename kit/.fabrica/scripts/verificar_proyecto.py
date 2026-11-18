#!/usr/bin/env python3
"""Verifica un proyecto de la fábrica. Corre en la CI de cada proyecto y en local.

Uso:
    python .fabrica/scripts/verificar_proyecto.py                        revisa el kit y el estado del proyecto
    python .fabrica/scripts/verificar_proyecto.py --base origin/main     además, protege las pruebas de aceptación
    python .fabrica/scripts/verificar_proyecto.py --base main --etiquetas pruebas-aprobadas   (prueba local)

Comprueba que:
1. Existan las rutas de NUCLEO.txt y los archivos del proyecto (.fabrica/proyecto.json y .fabrica/estado.json).
2. proyecto.json y estado.json sean JSON válidos, con sus campos y los mismos identificadores.
   En proyecto.json, `rutas` (si está) solo tiene rutas dentro del proyecto, y `autonomia` (si está) solo delega lo
   delegable; si delega algo a la fábrica, docs/constitucion.md lo declara en «## Autonomía en este proyecto».
3. Con --base: si los cambios desde la base tocan pruebas/aceptacion/, el PR tenga la etiqueta pruebas-aprobadas.
   Las etiquetas se leen del evento de GitHub (GITHUB_EVENT_PATH) o de --etiquetas.
4. Con --base: avisa, sin fallar, si el cambio supera las líneas útiles recomendadas.
5. Seguridad (.fabrica/nucleo/seguridad.md). Lo nuevo entra limpio: con --base, rechaza el cambio que agrega una
   acción de GitHub sin fijar por su huella, un archivo que nadie puede leer (compilado, binario o comprimido) o código
   de un lenguaje cuyas pruebas y librerías no revisa ningún flujo de GitHub. Lo heredado se avisa sin fallar.
   Es un control mínimo: comprueba que los comandos aparezcan en los flujos, no que corran; el resto lo mira el
   revisor de seguridad.
"""
import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True  # sin __pycache__: la verificación no deja rastros en el proyecto
import estado as _estado  # noqa: E402  (el script de estado del kit: las mismas reglas de rutas)
ETIQUETA_PRUEBAS = "pruebas-aprobadas"
ETIQUETA_CONSTITUCION = "constitucion-aprobada"
# Lo que puede acompañar a un cambio de pruebas de aceptación en un PR de especificación (constitución, art. II)
SOLO_ESPECIFICACION = ("pruebas/aceptacion/", "docs/", ".fabrica/estado.json")
PRUEBAS_ACEPTACION = "pruebas/aceptacion/"
LINEAS_UTILES = 400
NO_CUENTAN = ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "poetry.lock", "uv.lock", "Cargo.lock", ".min.js")
FASES = {"descubrimiento", "especificacion", "construccion", "estabilizacion", "operacion", "cerrado"}
SEMAFOROS = {"verde", "amarillo", "rojo"}
RUTAS = ("historias", "planes", "siguiente_accion", "notas")  # .fabrica/proyecto.json, campo "rutas"
DELEGABLES = ("integra", "pruebas_aprobadas", "cierra_historias")
RIESGOS = ("bajo", "medio", "alto")
# Cómo se reconoce, en la constitución del proyecto, la línea que declara cada delegación
DECLARACION = {"integra": r"integr", "pruebas_aprobadas": r"pruebas[-_ ]aprobadas", "cierra_historias": r"\bhecho\b"}  # nucleo/autonomia.md, "Delegación por proyecto"
FLUJOS = ".github/workflows/"
# Lo que una persona no puede leer ni revisar: se genera en la CI y no se guarda en el repositorio.
NO_SE_LEEN = re.compile(r"(^|/)__pycache__/|\.(pyc|pyo|exe|dll|so|dylib|class|jar|whl|egg|zip|bin)$", re.I)
USES = re.compile(r"^\s*(?:-\s*)?uses:\s*['\"]?([^\s'\"#]+)")
FIJADA = re.compile(r"^\./|@[0-9a-f]{40}$|^docker://.+@sha256:[0-9a-f]{64}$")
# Cómo se reconoce el código de cada lenguaje, qué comando corre sus pruebas y cuál revisa sus librerías (esto último,
# solo si el proyecto tiene un manifiesto de dependencias). Un lenguaje nuevo se agrega cuando llega su primer proyecto.
LENGUAJES = {
    "Python": {
        "extensiones": (".py",),
        "pruebas": ("pytest", "unittest", "tox", "nox"),
        "manifiestos": ("pyproject.toml", "setup.py", "Pipfile", "requirements*.txt"),
        "librerias": ("pip-audit", "osv-scanner", "safety"),
    },
    "JavaScript o TypeScript": {
        "extensiones": (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"),
        "pruebas": ("npm test", "npm run test", "pnpm test", "pnpm run test", "yarn test", "vitest", "jest",
                    "node --test"),
        "manifiestos": ("package.json",),
        "librerias": ("npm audit", "pnpm audit", "yarn audit", "osv-scanner"),
    },
}
OTROS_LENGUAJES = (".go", ".rs", ".java", ".kt", ".rb", ".php", ".cs", ".swift", ".dart", ".scala", ".c", ".cpp")
SIN_CODIGO = ("docs/",)  # además de las rutas del kit (NUCLEO.txt), que se prueban en el núcleo


def preparar_consola():
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def git(*args):
    r = subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def leer_json(rel, errores):
    p = RAIZ / rel
    if not p.exists():
        errores.append(f"Falta {rel}.")
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as ex:
        errores.append(f"{rel} no es un JSON válido: {ex}")
        return None


def revisar_kit(errores):
    lista = RAIZ / "NUCLEO.txt"
    if not lista.exists():
        errores.append("Falta NUCLEO.txt: este repositorio no tiene el kit de la fábrica.")
        return
    for linea in lista.read_text(encoding="utf-8").splitlines():
        e = linea.strip()
        if not e or e.startswith("#"):
            continue
        p = RAIZ / e
        if (e.endswith("/") and not p.is_dir()) or (not e.endswith("/") and not p.is_file()):
            errores.append(f"NUCLEO.txt lista {e}, pero no existe.")


def revisar_estado(errores):
    proyecto = leer_json(".fabrica/proyecto.json", errores)
    estado = leer_json(".fabrica/estado.json", errores)
    if proyecto is not None:
        for campo in ("cliente", "negocio", "proyecto"):
            if not proyecto.get(campo):
                errores.append(f".fabrica/proyecto.json no tiene '{campo}'.")
    if estado is not None:
        for campo in ("cliente", "negocio", "proyecto", "fase", "semaforo", "historias", "actualizado"):
            if campo not in estado:
                errores.append(f".fabrica/estado.json no tiene '{campo}'.")
        if estado.get("fase") and estado["fase"] not in FASES:
            errores.append(f".fabrica/estado.json: fase '{estado['fase']}' no es válida ({', '.join(sorted(FASES))}).")
        if estado.get("semaforo") and estado["semaforo"] not in SEMAFOROS:
            errores.append(f".fabrica/estado.json: semáforo '{estado['semaforo']}' no es válido.")
    if proyecto:
        revisar_rutas(proyecto, errores)
        revisar_autonomia(proyecto, errores)
    if proyecto and estado:
        for campo in ("cliente", "negocio", "proyecto"):
            if proyecto.get(campo) != estado.get(campo):
                errores.append(f"'{campo}' no coincide entre proyecto.json y estado.json.")


def revisar_rutas(proyecto, errores):
    """`rutas` es opcional; si está, cada ruta es relativa al proyecto y no sale de él."""
    rutas = proyecto.get("rutas")
    if rutas is None:
        return
    if not isinstance(rutas, dict):
        errores.append(".fabrica/proyecto.json: 'rutas' debe ser un objeto.")
        return
    for clave, valor in rutas.items():
        if clave not in RUTAS:
            errores.append(f".fabrica/proyecto.json: 'rutas.{clave}' no existe ({', '.join(RUTAS)}).")
        elif not _estado.ruta_segura(RAIZ, valor):
            errores.append(f".fabrica/proyecto.json: 'rutas.{clave}' debe ser una ruta dentro del proyecto.")


def revisar_autonomia(proyecto, errores):
    """`autonomia` es opcional. Si delega algo a la fábrica, la constitución del proyecto debe declararlo
    (.fabrica/nucleo/autonomia.md, "Delegación por proyecto")."""
    autonomia = proyecto.get("autonomia")
    if autonomia is None:
        return
    if not isinstance(autonomia, dict):
        errores.append(".fabrica/proyecto.json: 'autonomia' debe ser un objeto.")
        return
    delegado = []
    for clave, valor in autonomia.items():
        if clave == "riesgo_maximo":
            if valor not in RIESGOS:
                errores.append(f".fabrica/proyecto.json: 'autonomia.riesgo_maximo' debe ser {', '.join(RIESGOS)}.")
            continue
        if clave not in DELEGABLES:
            errores.append(f".fabrica/proyecto.json: 'autonomia.{clave}' no se puede delegar ({', '.join(DELEGABLES)}).")
        elif valor not in ("direccion", "fabrica"):
            errores.append(f".fabrica/proyecto.json: 'autonomia.{clave}' debe ser \"direccion\" o \"fabrica\".")
        elif valor == "fabrica":
            delegado.append(clave)
    if delegado:
        constitucion = RAIZ / "docs" / "constitucion.md"
        texto = constitucion.read_text(encoding="utf-8") if constitucion.exists() else ""
        seccion = re.search(r"^## Autonomía en este proyecto[ \t]*\n(.*?)(?=^## |\Z)", texto, re.M | re.S)
        lineas = [l for l in seccion.group(1).splitlines()
                  if l.strip().startswith(("- ", "* ")) and "<" not in l
                  and not re.search(r"\b(no|nunca|ni)\b", l, re.I)] if seccion else []
        sin_declarar = [clave for clave in delegado
                        if not any(re.search(DECLARACION[clave], l, re.I) for l in lineas)]
        if sin_declarar:
            errores.append(f".fabrica/proyecto.json delega a la fábrica {', '.join(sin_declarar)}, pero docs/constitucion.md "
                           "no lo declara: falta una línea de la Dirección que lo nombre en «## Autonomía en este "
                           "proyecto».")


def cambia_la_constitucion(base, cambiados):
    """Si el cambio toca la constitución del proyecto o la autonomía declarada en proyecto.json.

    No cuenta cuando la base todavía no era un proyecto de la fábrica (la adopción o la creación del proyecto): ahí
    no había nada que proteger, y la constitución y la delegación nacen con ese PR.
    """
    rc, antes = git("show", f"{base}:.fabrica/proyecto.json")
    if rc != 0:
        return False
    if "docs/constitucion.md" in cambiados:
        return True
    if ".fabrica/proyecto.json" not in cambiados:
        return False
    try:
        previa = json.loads(antes).get("autonomia")
    except (ValueError, AttributeError):
        previa = None
    try:
        actual = json.loads((RAIZ / ".fabrica" / "proyecto.json").read_text(encoding="utf-8")).get("autonomia")
    except (OSError, ValueError, AttributeError):
        return True  # proyecto.json roto: revisar_estado ya lo informa, y no se integra sin la Dirección
    return previa != actual


def etiquetas_del_pr(explicitas):
    if explicitas is not None:
        return {e.strip() for e in explicitas.split(",") if e.strip()}
    ruta = os.environ.get("GITHUB_EVENT_PATH")
    if ruta and Path(ruta).exists():
        evento = json.loads(Path(ruta).read_text(encoding="utf-8"))
        return {e.get("name", "") for e in (evento.get("pull_request") or {}).get("labels", [])}
    return set()


def revisar_cambios(base, explicitas, errores, avisos):
    rc, salida = git("diff", "--name-only", f"{base}...HEAD")
    if rc != 0:
        errores.append(f"No se pudo comparar con la base {base}: {salida.strip()[:300]}")
        return
    cambiados = [l.strip() for l in salida.splitlines() if l.strip()]
    etiquetas = etiquetas_del_pr(explicitas)
    protegidos = [c for c in cambiados if c.startswith(PRUEBAS_ACEPTACION) and not c.endswith(".gitkeep")]
    if protegidos and ETIQUETA_PRUEBAS not in etiquetas:
        errores.append(
            f"Este cambio modifica pruebas de aceptación aprobadas ({len(protegidos)} archivo(s), por ejemplo "
            f"{protegidos[0]}). Necesita la etiqueta '{ETIQUETA_PRUEBAS}' en el PR: la pone la Dirección, o la fábrica "
            "si el proyecto se lo delegó (.fabrica/nucleo/autonomia.md).")
    if protegidos:
        codigo = [c for c in cambiados if not c.startswith(SOLO_ESPECIFICACION) and c not in SOLO_ESPECIFICACION]
        if codigo:
            errores.append(
                f"Las pruebas de aceptación aprobadas van en un PR de especificación, sin código de la aplicación, y este "
                f"cambio también toca {len(codigo)} archivo(s), por ejemplo {codigo[0]} (constitución, art. II). "
                "Sepáralo en dos PRs.")
    if cambia_la_constitucion(base, cambiados) and ETIQUETA_CONSTITUCION not in etiquetas:
        errores.append(
            f"Este cambio toca docs/constitucion.md o la autonomía de .fabrica/proyecto.json. Necesita la etiqueta "
            f"'{ETIQUETA_CONSTITUCION}', que pone solo la Dirección, y lo integra ella (.fabrica/nucleo/autonomia.md).")
    rc, numstat = git("diff", "--numstat", f"{base}...HEAD")
    total = 0
    for linea in numstat.splitlines():
        partes = linea.split("\t")
        if len(partes) == 3 and partes[0].isdigit() and not partes[2].endswith(NO_CUENTAN):
            total += int(partes[0]) + int(partes[1])
    if total > LINEAS_UTILES:
        avisos.append(f"El cambio suma {total} líneas. Sobre {LINEAS_UTILES}, conviene dividirlo (constitución, artículo VIII).")
    revisar_seguridad_del_cambio(base, errores)


def rutas_del_kit():
    lista = RAIZ / "NUCLEO.txt"
    if not lista.exists():
        return ()
    lineas = lista.read_text(encoding="utf-8").splitlines()
    return tuple(l.strip() for l in lineas if l.strip() and not l.startswith("#"))


def es_codigo_del_proyecto(ruta, kit):
    del_kit = any(ruta == e or (e.endswith("/") and ruta.startswith(e)) for e in kit)
    return not del_kit and not ruta.startswith(SIN_CODIGO)


def texto_de_los_flujos():
    carpeta = RAIZ / FLUJOS
    if not carpeta.is_dir():
        return ""
    return "\n".join(p.read_text(encoding="utf-8", errors="replace").lower()
                     for p in sorted(carpeta.iterdir()) if p.suffix in (".yml", ".yaml") and p.is_file())


def menciona(texto, comandos):
    return any(re.search(rf"(?<![\w-]){re.escape(c)}(?![\w-])", texto) for c in comandos)


def sin_huella(lineas):
    """Las acciones de GitHub que no están fijadas por la huella de su commit, sin repetir (las locales, ./, no
    cuentan)."""
    malas = (m.group(1) for m in (USES.match(l) for l in lineas) if m and not FIJADA.search(m.group(1)))
    return list(dict.fromkeys(malas))


def huecos_de_control(rutas, todos, flujos):
    """Qué le falta a la CI para los lenguajes con código en estas rutas: pruebas, y revisión de librerías si el
    proyecto tiene un manifiesto de dependencias. Devuelve (problemas, lenguajes que el control no conoce)."""
    problemas, desconocidos = [], set()
    for lenguaje, l in LENGUAJES.items():
        ejemplo = next((r for r in rutas if r.lower().endswith(l["extensiones"])), None)
        if not ejemplo:
            continue
        if not menciona(flujos, l["pruebas"]):
            problemas.append(f"hay código {lenguaje} (por ejemplo {ejemplo}) y ningún flujo de GitHub corre sus "
                             f"pruebas ({', '.join(l['pruebas'])})")
        manifiesto = next((t for t in todos
                           if any(fnmatch.fnmatch(t.rsplit("/", 1)[-1], m) for m in l["manifiestos"])), None)
        if manifiesto and not menciona(flujos, l["librerias"]):
            problemas.append(f"el proyecto declara librerías de {lenguaje} ({manifiesto}) y ningún flujo de GitHub las "
                             f"revisa ({', '.join(l['librerias'])})")
    for r in rutas:
        if r.lower().endswith(OTROS_LENGUAJES):
            desconocidos.add(r.rsplit(".", 1)[-1])
    return problemas, sorted(desconocidos)


def revisar_seguridad_del_cambio(base, errores):
    """Lo nuevo entra limpio: lo que este cambio agrega no trae acciones sin huella, archivos ilegibles ni código sin
    control."""
    rc, salida = git("-c", "core.quotepath=off", "diff", "--name-only", "--diff-filter=AMR", f"{base}...HEAD")
    if rc != 0:
        return
    nuevos = [l.strip() for l in salida.splitlines() if l.strip()]
    ilegibles = [r for r in nuevos if NO_SE_LEEN.search(r)]
    if ilegibles:
        errores.append(f"Este cambio agrega {len(ilegibles)} archivo(s) que nadie puede leer ni revisar, por ejemplo "
                       f"{ilegibles[0]}. Sácalos del repositorio y agrégalos al .gitignore: se generan en la CI.")
    rc, diff = git("diff", "-U0", f"{base}...HEAD", "--", FLUJOS)
    agregadas = [l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
    malas = sin_huella(agregadas)
    if malas:
        errores.append(f"Este cambio agrega acciones de GitHub sin fijar por la huella de su commit: "
                       f"{', '.join(malas)}. Usa el SHA completo, con la versión en un comentario.")
    kit = rutas_del_kit()
    rc, todos = git("-c", "core.quotepath=off", "ls-files")
    problemas, _ = huecos_de_control([r for r in nuevos if es_codigo_del_proyecto(r, kit)], todos.splitlines(),
                                     texto_de_los_flujos())
    for p in problemas:
        errores.append(f"Este cambio trae código sin control: {p}.")


def revisar_seguridad(avisos):
    """Lo heredado se avisa sin fallar, para que un proyecto adoptado lo corrija con su propio pedido."""
    rc, salida = git("-c", "core.quotepath=off", "ls-files")
    if rc != 0:
        return
    todos = [l.strip() for l in salida.splitlines() if l.strip()]
    ilegibles = [r for r in todos if NO_SE_LEEN.search(r)]
    if ilegibles:
        avisos.append(f"El repositorio guarda {len(ilegibles)} archivo(s) que nadie puede leer ni revisar, por ejemplo "
                      f"{ilegibles[0]}.")
    for flujo in (r for r in todos if r.startswith(FLUJOS) and (RAIZ / r).is_file()):
        malas = sin_huella((RAIZ / flujo).read_text(encoding="utf-8", errors="replace").splitlines())
        if malas:
            avisos.append(f"{flujo} usa acciones sin fijar por su huella: {', '.join(malas)}.")
    kit = rutas_del_kit()
    problemas, desconocidos = huecos_de_control([r for r in todos if es_codigo_del_proyecto(r, kit)], todos,
                                                texto_de_los_flujos())
    avisos.extend(f"Control incompleto: {p}." for p in problemas)
    if desconocidos:
        avisos.append(f"Hay código que este control no sabe revisar ({', '.join(desconocidos)}): la CI debe correr sus "
                      "pruebas y revisar sus librerías, y el revisor de seguridad lo comprueba.")


def main():
    preparar_consola()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", help="rama o commit base del PR, por ejemplo origin/main")
    ap.add_argument("--etiquetas", help="etiquetas del PR separadas por coma (para probar en local)")
    a = ap.parse_args()

    errores, avisos = [], []
    revisar_kit(errores)
    revisar_estado(errores)
    revisar_seguridad(avisos)
    if a.base:
        revisar_cambios(a.base, a.etiquetas, errores, avisos)
    for aviso in avisos:
        print(f"Aviso: {aviso}")
    if errores:
        print("Verificación del proyecto con problemas:")
        print("\n".join(f"- {e}" for e in errores))
        return 1
    print("Verificación del proyecto: todo en orden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
