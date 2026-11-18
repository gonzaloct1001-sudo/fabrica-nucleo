#!/usr/bin/env python3
"""Estado del proyecto en pocas líneas, para empezar una sesión o una corrida sin releer el repositorio.

Uso, desde la raíz del proyecto:
    python .fabrica/scripts/estado.py            estado completo; consulta GitHub con `gh api` (solo REST)
    python .fabrica/scripts/estado.py --sin-red  solo lo que está en el disco
    python .fabrica/scripts/estado.py --peso     los documentos que más pesan cuando un agente los lee

Solo lee: no cambia ningún archivo ni escribe en GitHub. Usa la biblioteca estándar, `git` y, si está, `gh`.

Las rutas de las historias y de los planes salen de `rutas` en `.fabrica/proyecto.json`; sin ese campo, se usan
`docs/historias` y `docs/planes`. Nació en un proyecto de la fábrica y pasó al kit en el núcleo 0.11.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Callable, Dict, List, Optional, Tuple

RAIZ = Path(__file__).resolve().parents[2]
RUTAS_POR_DEFECTO = {"historias": "docs/historias", "planes": "docs/planes"}
# `en-construccion` no está en el ciclo: lo usaban proyectos anteriores al kit y se acepta como `en-curso`.
EN_CURSO = ("listo", "en-curso", "en-construccion", "en-revision")
CONTEXTO_FIJO = ("AGENTS.md", "CLAUDE.md")
TITULO_BITACORA = "Bitácora de corridas"
API = "repos/{owner}/{repo}"
ANCHO = 150
MAXIMO_POR_LISTA = 8

TITULO_DE_TAREA = re.compile(r"^#{2,4} Tarea (\d+): (.+)$", re.MULTILINE)
TAREAS_COMPLETAS = re.compile(r"^Tareas? ([\d ,ya-]+): completas?\b", re.MULTILINE)

Ejecutar = Callable[[List[str], Path], Optional[str]]


def correr(orden: List[str], raiz: Path) -> Optional[str]:
    """La salida de un comando, o None si no existe, falla o demora más de 20 segundos."""
    try:
        hecho = subprocess.run(orden, cwd=raiz, capture_output=True, encoding="utf-8", errors="replace", timeout=20,
                               check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return hecho.stdout if hecho.returncode == 0 else None


def leer(ruta: Path) -> str:
    try:
        return ruta.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def leer_json(ruta: Path) -> dict:
    try:
        dato = json.loads(leer(ruta) or "{}")
    except ValueError:
        return {}
    return dato if isinstance(dato, dict) else {}


def ruta_segura(raiz: Path, valor: object) -> bool:
    """Si `valor` es una ruta relativa que queda dentro de `raiz`, en Linux y en Windows, también tras resolver enlaces."""
    if not isinstance(valor, str) or not valor.strip():
        return False
    texto = valor.strip()
    if PurePosixPath(texto).is_absolute() or PureWindowsPath(texto).anchor or ".." in PureWindowsPath(texto).parts:
        return False
    try:
        (Path(raiz) / texto).resolve().relative_to(Path(raiz).resolve())
    except (ValueError, OSError):
        return False
    return True


def rutas_del_proyecto(proyecto: dict, raiz: Path = RAIZ) -> Dict[str, str]:
    """Las rutas de historias y planes: las de `rutas` en proyecto.json, o las de la fábrica.

    Una ruta que sale del proyecto se ignora (`ruta_segura`): el script nunca lee fuera del repositorio.
    """
    propias = proyecto.get("rutas") if isinstance(proyecto.get("rutas"), dict) else {}
    rutas = dict(RUTAS_POR_DEFECTO)
    for clave in RUTAS_POR_DEFECTO:
        valor = propias.get(clave)
        if ruta_segura(raiz, valor):
            rutas[clave] = valor.strip().rstrip("/")
    return rutas


def leer_cabecera(texto: str) -> Dict[str, str]:
    """Los campos simples de la cabecera `---` de una historia, sin sus comentarios."""
    if not texto.startswith("---"):
        return {}
    campos: Dict[str, str] = {}
    for linea in texto.splitlines()[1:]:
        if linea.strip() == "---":
            return campos
        clave, dos_puntos, valor = linea.partition(":")
        if dos_puntos and clave.strip().isidentifier():
            campos[clave.strip()] = re.sub(r"\s+#.*$", "", valor).strip()
    return {}


def avance_del_plan(texto: str) -> Tuple[int, int, Optional[str]]:
    """Tareas completas, tareas del plan y la primera pendiente, según el Registro del plan."""
    titulos = {int(numero): titulo.strip() for numero, titulo in TITULO_DE_TAREA.findall(texto)}
    completas = set()
    for lista in TAREAS_COMPLETAS.findall(texto):
        for desde, hasta in re.findall(r"(\d+)(?:\s*(?:a|-)\s*(\d+))?", lista):
            completas.update(range(int(desde), int(hasta or desde) + 1))
    pendientes = sorted(set(titulos) - completas)
    siguiente = f"{pendientes[0]}: {titulos[pendientes[0]]}" if pendientes else None
    return len(set(titulos) & completas), len(titulos), siguiente


def en_sesion_en_vivo(texto_del_plan: str) -> bool:
    """Si el Registro del plan tiene la marca de una sesión en vivo, que la corrida programada respeta."""
    return "En construcción en una sesión en vivo" in texto_del_plan


def resumir_controles(corridas: List[dict]) -> str:
    """El último resultado de cada control de un PR, en pocas palabras."""
    ultimas: Dict[str, dict] = {}
    for corrida in sorted(corridas, key=lambda una: una.get("started_at") or ""):
        ultimas[corrida.get("name", "?")] = corrida
    if not ultimas:
        return "sin controles"
    if any(corrida.get("status") != "completed" for corrida in ultimas.values()):
        return "corriendo"
    buenos = ("success", "skipped", "neutral")
    rojos = sorted(nombre for nombre, corrida in ultimas.items() if corrida.get("conclusion") not in buenos)
    return f"rojo: {', '.join(rojos)}" if rojos else "verde"


def _rama(raiz: Path, ejecutar: Ejecutar) -> str:
    rama = (ejecutar(["git", "rev-parse", "--abbrev-ref", "HEAD"], raiz) or "?").strip()
    cambios = len((ejecutar(["git", "status", "--porcelain"], raiz) or "").splitlines())
    partes = [f"Rama: {rama}", f"{cambios} archivo(s) sin commitear" if cambios else "sin cambios locales"]
    cuenta = (ejecutar(["git", "rev-list", "--left-right", "--count", "@{u}...HEAD"], raiz) or "").split()
    if len(cuenta) == 2:
        por_traer, sin_subir = cuenta
        if por_traer != "0":
            partes.append(f"{por_traer} commit(s) por traer")
        if sin_subir != "0":
            partes.append(f"{sin_subir} commit(s) sin subir")
        if por_traer == sin_subir == "0":
            partes.append("al día con el remoto")
    ultimo = (ejecutar(["git", "log", "-1", "--format=%s"], raiz) or "").strip()
    if ultimo:
        partes.append(f"último commit: {ultimo}")
    return " | ".join(partes)


def _historias(raiz: Path, rutas: Dict[str, str]) -> List[str]:
    if not (raiz / rutas["historias"]).is_dir():
        return [f"Historias: no existe {rutas['historias']}/. Si el proyecto las guarda en otra carpeta, ponla en "
                "`rutas.historias` de .fabrica/proyecto.json."]
    en_curso: List[str] = []
    demas: Counter = Counter()
    for ruta in sorted((raiz / rutas["historias"]).glob("*.md")):
        cabecera = leer_cabecera(leer(ruta))
        if not cabecera.get("id"):
            continue
        identificador, estado = cabecera["id"], cabecera.get("estado", "?")
        if estado not in EN_CURSO:
            demas[estado] += 1
            continue
        linea = f"  {identificador}  {estado}  {cabecera.get('titulo', '')}"
        plan = leer(raiz / rutas["planes"] / f"{identificador}-plan.md")
        if plan:
            hechas, total, siguiente = avance_del_plan(plan)
            linea += f" | plan: {hechas} de {total} tareas" + (f"; sigue la {siguiente}" if siguiente else "; completo")
            if en_sesion_en_vivo(plan):
                linea += " | EN SESIÓN EN VIVO"
        else:
            linea += " | sin plan"
        en_curso.append(linea)
    resto = ", ".join(f"{cuantas} en {estado}" for estado, cuantas in sorted(demas.items())) or "ninguna"
    return [f"Historias en curso en el disco: {len(en_curso)} (las demás: {resto})", *en_curso]


def _autonomia(proyecto: dict) -> str:
    """La autonomía delegada al proyecto (nucleo/autonomia.md, "Delegación por proyecto"), en pocas palabras."""
    autonomia = proyecto.get("autonomia") if isinstance(proyecto.get("autonomia"), dict) else {}
    delegado = [clave for clave in ("integra", "pruebas_aprobadas", "cierra_historias") if autonomia.get(clave) == "fabrica"]
    if not delegado:
        return "autonomía: decide la Dirección"
    tope = f" hasta riesgo {autonomia.get('riesgo_maximo', 'bajo')}" if "integra" in delegado else ""
    return "autonomía delegada: " + ", ".join(delegado) + tope


def estado_local(raiz: Path, ejecutar: Ejecutar) -> List[str]:
    proyecto = leer_json(raiz / ".fabrica/proyecto.json")
    estado = leer_json(raiz / ".fabrica/estado.json")
    motor = proyecto.get("motor")
    pasos = motor.get("pasos_por_corrida", "?") if isinstance(motor, dict) else "?"
    pausa = "EN PAUSA: no empezar trabajo nuevo" if proyecto.get("pausa") else "sin pausa"
    nombre = f"{proyecto.get('nombre', '?')} ({proyecto.get('repositorio', '?')})"
    return [
        f"{nombre} | núcleo {proyecto.get('nucleo', '?')} | fase: {estado.get('fase', '?')}"
        + f" | semáforo: {estado.get('semaforo', '?')}",
        f"Motor: {pasos} paso(s) por corrida | {pausa} | {_autonomia(proyecto)}"
        + f" | estado.json del {str(estado.get('actualizado', '?'))[:10]}",
        _rama(raiz, ejecutar),
        *_historias(raiz, rutas_del_proyecto(proyecto, raiz)),
    ]


def _api(ruta: str, raiz: Path, ejecutar: Ejecutar) -> object:
    salida = ejecutar(["gh", "api", f"{API}/{ruta}"], raiz)
    try:
        return json.loads(salida) if salida else None
    except ValueError:
        return None


def _etiquetas(asunto: dict, *prefijos: str) -> List[str]:
    nombres = [str(etiqueta.get("name", "")) for etiqueta in asunto.get("labels", [])]
    return [nombre for nombre in nombres if not prefijos or nombre.startswith(prefijos)]


def _acotar(lineas: List[str]) -> List[str]:
    sobran = len(lineas) - MAXIMO_POR_LISTA
    return lineas if sobran <= 0 else [*lineas[:MAXIMO_POR_LISTA], f"  ... y {sobran} más"]


def _bitacora(asuntos: List[dict], raiz: Path, ejecutar: Ejecutar) -> List[str]:
    bitacora = next((uno for uno in asuntos if str(uno.get("title", "")).startswith(TITULO_BITACORA)), None)
    if not bitacora or not bitacora.get("comments"):
        return []
    numero = bitacora["number"]
    ultimo = _api(f"issues/{numero}/comments?per_page=1&page={bitacora['comments']}", raiz, ejecutar)
    if not isinstance(ultimo, list) or not ultimo:
        return []
    cuando = str(ultimo[0].get("created_at", ""))[:16].replace("T", " ")
    primera = next((linea.strip("#* ") for linea in str(ultimo[0].get("body", "")).splitlines() if linea.strip()), "")
    return [f"Última entrada de la bitácora (#{numero}): {cuando} UTC | {primera}"]


def estado_github(raiz: Path, ejecutar: Ejecutar) -> List[str]:
    prs = _api("pulls?state=open&per_page=100", raiz, ejecutar)
    asuntos = _api("issues?state=open&per_page=100", raiz, ejecutar)
    if not isinstance(prs, list) or not isinstance(asuntos, list):
        return ["GitHub: no disponible (falta `gh`, su sesión o la red). Lo de arriba sale solo del disco."]

    def controles(pr: dict) -> str:
        dato = _api(f"commits/{pr['head']['sha']}/check-runs?per_page=100", raiz, ejecutar)
        return resumir_controles(dato.get("check_runs", [])) if isinstance(dato, dict) else "controles: sin dato"

    prs = sorted(prs, key=lambda pr: pr["number"])
    with ThreadPoolExecutor(max_workers=6) as grupo:
        resultados = list(grupo.map(controles, prs))
    lineas_de_pr = [
        f"  #{pr['number']}  {'borrador' if pr.get('draft') else 'listo'}  {resultado}"
        f"  [{','.join(_etiquetas(pr))}]  {pr.get('title', '')}"
        for pr, resultado in zip(prs, resultados)
    ]
    propios = sorted((uno for uno in asuntos if "pull_request" not in uno), key=lambda uno: uno["number"])
    esperan = sum(1 for uno in propios if "espera:direccion" in _etiquetas(uno))
    preguntas = sum(1 for uno in propios if str(uno.get("title", "")).startswith("Pregunta:"))
    lineas_de_asunto = [
        f"  #{uno['number']}  {','.join(_etiquetas(uno, 'estado:', 'espera:'))}  {uno.get('title', '')}"
        for uno in propios
        if _etiquetas(uno, "estado:", "espera:")
    ]
    return [
        f"PR abiertos: {len(prs)}",
        *_acotar(lineas_de_pr),
        f"Issues abiertos: {len(propios)} | esperan a la Dirección: {esperan} | preguntas: {preguntas}",
        *_acotar(lineas_de_asunto),
        *_bitacora(propios, raiz, ejecutar),
    ]


def reunir(raiz: Path, ejecutar: Ejecutar = correr, *, con_red: bool = True) -> List[str]:
    """El estado del proyecto, una línea por dato y nunca más de 150 caracteres por línea."""
    lineas = estado_local(raiz, ejecutar)
    if con_red:
        lineas += estado_github(raiz, ejecutar)
    return [linea if len(linea) <= ANCHO else linea[: ANCHO - 3] + "..." for linea in lineas]


def peso(raiz: Path, ejecutar: Ejecutar = correr, cuantos: int = 12) -> List[str]:
    """Los documentos versionados que más pesan al leerlos, a razón de un token cada 3,5 caracteres."""
    rutas = (ejecutar(["git", "ls-files", "--", "*.md"], raiz) or "").splitlines()
    pesos = sorted(((int(len(leer(raiz / ruta)) / 3.5), ruta) for ruta in rutas if ruta.strip()), reverse=True)
    pesos = [(tokens, ruta) for tokens, ruta in pesos if tokens]
    fijo = sum(tokens for tokens, ruta in pesos if ruta in CONTEXTO_FIJO)

    def miles(numero: int) -> str:
        return f"{numero:,}".replace(",", ".")

    return [
        f"Contexto fijo de cada sesión ({' y '.join(CONTEXTO_FIJO)}): unos {miles(fijo)} tokens",
        f"Los {min(cuantos, len(pesos))} documentos que más pesan al leerlos (tokens aproximados):",
        *(f"  {miles(tokens):>8}  {ruta}" for tokens, ruta in pesos[:cuantos]),
    ]


def main(argumentos: Optional[List[str]] = None, raiz: Path = RAIZ) -> int:
    analizador = argparse.ArgumentParser(description="Estado del proyecto en pocas líneas. Solo lee.")
    analizador.add_argument("--sin-red", action="store_true", help="no consulta GitHub: solo lo que está en el disco")
    analizador.add_argument("--peso", action="store_true", help="lista los documentos que más pesan al leerlos")
    opciones = analizador.parse_args(argumentos)
    if hasattr(sys.stdout, "reconfigure"):
        # Con la salida redirigida, Windows usaría su página de códigos y rompería los acentos.
        sys.stdout.reconfigure(errors="replace", **({} if sys.stdout.isatty() else {"encoding": "utf-8"}))
    lineas = peso(raiz) if opciones.peso else reunir(raiz, con_red=not opciones.sin_red)
    print("\n".join(lineas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
