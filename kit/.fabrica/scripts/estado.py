#!/usr/bin/env python3
"""Estado del proyecto en pocas líneas, para empezar una sesión o una corrida sin releer el repositorio.

Uso, desde la raíz del proyecto:
    python .fabrica/scripts/estado.py            estado completo; consulta GitHub con `gh api` (solo REST)
    python .fabrica/scripts/estado.py --sin-red  solo lo que está en el disco
    python .fabrica/scripts/estado.py --peso     los documentos que más pesan cuando un agente los lee
    python .fabrica/scripts/estado.py --consumo  minutos, agentes y documentos por historia, desde la bitácora
    python .fabrica/scripts/estado.py --publicar  publica el estado en el issue «Estado del proyecto» (lo usa la CI)
    python .fabrica/scripts/estado.py --escribir [--sin-red]
                                                 rehace las cifras de .fabrica/estado.json (núcleo 0.12)

Solo lee, salvo con --publicar (escribe el issue «Estado del proyecto») y con --escribir: entonces cambia únicamente las cifras de .fabrica/estado.json (las historias por
estado, lo que espera a la Dirección y la fecha), y conserva los campos de criterio (fase, semáforo, próxima entrega y
riesgo principal). Solo --publicar escribe en GitHub: el cuerpo del issue «Estado del proyecto». Usa la biblioteca
estándar, `git` y, si está, `gh`.

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
RUTAS_POR_DEFECTO = {"historias": "docs/historias", "planes": "docs/planes",
                     "siguiente_accion": "docs/siguiente-accion.md"}
PRINCIPALES = ("origin/main", "origin/master", "main", "master")
# `en-construccion` no está en el ciclo: lo usaban proyectos anteriores al kit y se acepta como `en-curso`.
EN_CURSO = ("listo", "en-curso", "en-construccion", "en-revision")
CONTEXTO_FIJO = ("AGENTS.md", "CLAUDE.md")
TITULO_BITACORA = "Bitácora de corridas"
ETIQUETA_PAUSA = "motor:pausa"  # en la bitácora de corridas: detiene el motor desde el teléfono (nucleo/motor.md)
# Cómo se cuenta cada estado de una historia en las cifras de estado.json (B1). El resto solo suma al total.
CIFRAS = {"hecho": "hechas", "en-curso": "en_curso", "en-construccion": "en_curso", "en-revision": "en_revision",
          "bloqueado": "bloqueadas"}
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


def leer_plan(raiz: Path, rutas: Dict[str, str], identificador: str) -> str:
    """El texto del plan de una historia, en cualquiera de sus dos formatos.

    Formato partido (núcleo 0.13): `<planes>/<id>/plan.md`, un `tarea-NN.md` por tarea y `registro.md`. Formato de un
    solo archivo: `<planes>/<id>-plan.md`. Devuelve "" si no hay plan.
    """
    carpeta = raiz / rutas["planes"] / identificador
    if (carpeta / "plan.md").is_file():
        partes = [leer(carpeta / "plan.md")]
        partes += [leer(tarea) for tarea in sorted(carpeta.glob("tarea-*.md"))]
        partes.append(leer(carpeta / "registro.md"))
        return "\n\n".join(partes)
    return leer(raiz / rutas["planes"] / f"{identificador}-plan.md")


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
        plan = leer_plan(raiz, rutas, identificador)
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


def cifras_de_historias(raiz: Path, rutas: Dict[str, str]) -> Dict[str, int]:
    """Las historias del disco por estado, con las claves de `historias` en estado.json."""
    cuentas = {"total": 0, "hechas": 0, "en_curso": 0, "en_revision": 0, "bloqueadas": 0}
    for ruta in sorted((raiz / rutas["historias"]).glob("*.md")):
        cabecera = leer_cabecera(leer(ruta))
        if not cabecera.get("id"):
            continue
        cuentas["total"] += 1
        clave = CIFRAS.get(cabecera.get("estado", ""))
        if clave:
            cuentas[clave] += 1
    return cuentas


def _autonomia(proyecto: dict) -> str:
    """La autonomía delegada al proyecto (nucleo/autonomia.md, "Delegación por proyecto"), en pocas palabras."""
    autonomia = proyecto.get("autonomia") if isinstance(proyecto.get("autonomia"), dict) else {}
    delegado = [clave for clave in ("integra", "pruebas_aprobadas", "cierra_historias") if autonomia.get(clave) == "fabrica"]
    if not delegado:
        return "autonomía: decide la Dirección"
    tope = f" hasta riesgo {autonomia.get('riesgo_maximo', 'bajo')}" if "integra" in delegado else ""
    return "autonomía delegada: " + ", ".join(delegado) + tope


def _fecha(segundos: int) -> str:
    from datetime import datetime, timezone
    return datetime.fromtimestamp(segundos, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def siguiente_accion_vieja(raiz: Path, rutas: Dict[str, str], ejecutar: Ejecutar) -> List[str]:
    """Un aviso si la siguiente acción es anterior a lo último integrado en la rama principal (núcleo 0.13).

    La siguiente acción se escribe a mano: es lo que queda viejo cuando una sesión se corta. Compara la fecha del último
    commit que la tocó con la del último commit de la rama principal.
    """
    rel = rutas["siguiente_accion"]
    if not (raiz / rel).is_file():
        return []
    principal = next((r for r in PRINCIPALES if ejecutar(["git", "rev-parse", "--verify", "-q", r], raiz)), None)
    if not principal:
        return []
    del_archivo = (ejecutar(["git", "log", "-1", "--format=%ct", "--", rel], raiz) or "").strip()
    integrado = (ejecutar(["git", "log", "-1", "--format=%ct", principal], raiz) or "").strip()
    if not (del_archivo.isdigit() and integrado.isdigit()) or int(del_archivo) >= int(integrado) - 60:
        return []
    return [f"AVISO: {rel} es del {_fecha(int(del_archivo))} y lo último integrado en {principal} es del "
            f"{_fecha(int(integrado))}. Revísalo: puede no decir lo que toca ahora."]


def respaldo(raiz: Path) -> List[str]:
    """El último respaldo del guardado automático en GitHub (hook_guardado.py), o que no lo hay (núcleo 0.13)."""
    registro = leer_json(raiz / ".fabrica/trabajo/respaldo.json")
    if not registro:
        return []
    ultimo = registro.get("ultimo_respaldo")
    cuando = _fecha(int(ultimo)) if isinstance(ultimo, (int, float)) else "nunca"
    resultado = str(registro.get("resultado", ""))
    if resultado.startswith("sin subir"):
        return [f"AVISO: respaldo en GitHub ({cuando}); el último intento quedó {resultado}."]
    return [f"Respaldo en GitHub: {cuando}."]


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
        *siguiente_accion_vieja(raiz, rutas_del_proyecto(proyecto, raiz), ejecutar),
        *respaldo(raiz),
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
    pausa = [f"MOTOR EN PAUSA: la bitácora de corridas tiene la etiqueta {ETIQUETA_PAUSA}"] if motor_en_pausa(propios) else []
    preguntas = sum(1 for uno in propios if str(uno.get("title", "")).startswith("Pregunta:"))
    lineas_de_asunto = [
        f"  #{uno['number']}  {','.join(_etiquetas(uno, 'estado:', 'espera:'))}  {uno.get('title', '')}"
        for uno in propios
        if _etiquetas(uno, "estado:", "espera:")
    ]
    return [
        *pausa,
        f"PR abiertos: {len(prs)}",
        *_acotar(lineas_de_pr),
        f"Issues abiertos: {len(propios)} | esperan a la Dirección: {esperan} | preguntas: {preguntas}",
        *_acotar(lineas_de_asunto),
        *_bitacora(propios, raiz, ejecutar),
    ]


def motor_en_pausa(asuntos: List[dict]) -> bool:
    """Si la bitácora de corridas tiene la etiqueta de pausa (C4)."""
    return any(str(uno.get("title", "")).startswith(TITULO_BITACORA) and ETIQUETA_PAUSA in _etiquetas(uno)
               for uno in asuntos)


def escribir(raiz: Path, ejecutar: Ejecutar = correr, *, con_red: bool = True, ahora: Optional[str] = None) -> List[str]:
    """Rehace las cifras de .fabrica/estado.json y devuelve qué cambió. Conserva los campos de criterio."""
    from datetime import datetime, timezone

    ruta = raiz / ".fabrica/estado.json"
    estado = leer_json(ruta)
    if not estado:
        return [f"No se puede escribir: falta {ruta.relative_to(raiz).as_posix()} o no es un JSON válido."]
    proyecto = leer_json(raiz / ".fabrica/proyecto.json")
    cambios = []
    nuevas = cifras_de_historias(raiz, rutas_del_proyecto(proyecto, raiz))
    antes = estado.get("historias") if isinstance(estado.get("historias"), dict) else {}
    if any(antes.get(clave) != valor for clave, valor in nuevas.items()):
        cambios.append(f"historias: {json.dumps(antes, ensure_ascii=False)} -> {json.dumps(nuevas, ensure_ascii=False)}")
    estado["historias"] = {**antes, **nuevas}
    if con_red:
        asuntos = _api("issues?state=open&labels=espera:direccion&per_page=100", raiz, ejecutar)
        if isinstance(asuntos, list):
            cantidad = sum(1 for uno in asuntos if "pull_request" not in uno)
            espera = estado.get("espera_direccion") if isinstance(estado.get("espera_direccion"), dict) else {}
            if espera.get("cantidad") != cantidad:
                cambios.append(f"espera_direccion: {espera.get('cantidad')} -> {cantidad}")
            estado["espera_direccion"] = {**espera, "cantidad": cantidad}
        else:
            cambios.append("espera_direccion: sin cambio (GitHub no disponible)")
    # Desde aquí la CI exige que las cifras coincidan con el disco (verificar_proyecto.py, coherencia del estado)
    estado["cifras_generadas"] = True
    estado["actualizado"] = ahora or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ruta.write_text(json.dumps(estado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return cambios or ["Las cifras ya estaban al día; solo cambió la fecha."]


CONSUMO = re.compile(r"^-?\s*Consumo:\s*(.+)$", re.M)
HISTORIA = re.compile(r"\b([A-Z]+-\d{3,})\b")


def leer_consumo(texto: str) -> List[Tuple[str, int, Counter, int]]:
    """Las líneas «Consumo:» de una entrada de la bitácora: (historia, minutos, agentes por modelo, tokens leídos).

    Formato (corrida.md, "La bitácora de corridas"):
    `- Consumo: H-012 · 34 min · agentes: sonnet ×2, opus ×1 · leídos: 6 documentos, ~41.000 tokens`
    """
    lecturas = []
    for linea in CONSUMO.findall(texto):
        historia = HISTORIA.search(linea)
        minutos = re.search(r"(\d+)\s*min", linea)
        tokens = re.search(r"~?\s*([\d.]+)\s*tokens", linea)
        agentes: Counter = Counter()
        tramo = re.search(r"agentes:\s*([^·]+)", linea)
        for modelo, cuantos in re.findall(r"([a-z]+)\s*[×x]\s*(\d+)", tramo.group(1) if tramo else ""):
            agentes[modelo] += int(cuantos)
        lecturas.append((historia.group(1) if historia else "sin historia", int(minutos.group(1)) if minutos else 0,
                         agentes, int(tokens.group(1).replace(".", "")) if tokens else 0))
    return lecturas


def consumo(raiz: Path, ejecutar: Ejecutar = correr) -> List[str]:
    """El consumo por historia, sumado desde las líneas «Consumo:» de la bitácora de corridas (A1)."""
    asuntos = _api("issues?state=all&per_page=100", raiz, ejecutar)
    if not isinstance(asuntos, list):
        return ["GitHub: no disponible. El consumo sale de la bitácora de corridas, que vive en GitHub."]
    bitacora = next((uno for uno in asuntos if str(uno.get("title", "")).startswith(TITULO_BITACORA)), None)
    if not bitacora:
        return ["No hay bitácora de corridas todavía."]
    totales: Dict[str, list] = {}
    for pagina in range(1, 11):
        comentarios = _api(f"issues/{bitacora['number']}/comments?per_page=100&page={pagina}", raiz, ejecutar)
        if not isinstance(comentarios, list) or not comentarios:
            break
        for comentario in comentarios:
            for historia, minutos, agentes, tokens in leer_consumo(str(comentario.get("body", ""))):
                fila = totales.setdefault(historia, [0, 0, Counter(), 0])
                fila[0] += 1
                fila[1] += minutos
                fila[2].update(agentes)
                fila[3] += tokens
    if not totales:
        return ["La bitácora no tiene líneas «Consumo:» todavía (las agrega cada corrida desde el núcleo 0.13)."]
    lineas = ["Consumo por historia, sumado desde la bitácora de corridas:"]
    for historia, (veces, minutos, agentes, tokens) in sorted(totales.items(), key=lambda par: -par[1][1]):
        modelos = ", ".join(f"{modelo} ×{cuantos}" for modelo, cuantos in sorted(agentes.items())) or "sin agentes"
        miles = f"{tokens:,}".replace(",", ".")
        lineas.append(f"  {historia}  {veces} registro(s) · {minutos} min · agentes: {modelos} · ~{miles} tokens leídos")
    return lineas


TITULO_ESTADO = "Estado del proyecto"
ETIQUETA_ESTADO = "fabrica:estado"  # marca el issue de estado: se busca por ella, aunque haya cientos de issues


def publicar(raiz: Path, ejecutar: Ejecutar = correr, ahora: Optional[str] = None) -> List[str]:
    """Calcula el estado y lo deja en el cuerpo del issue «Estado del proyecto», que crea si falta (núcleo 0.13).

    Lo corre el flujo `.github/workflows/fabrica-estado.yml` al integrar algo que cambia el estado y una vez al día,
    así que el estado vivo nunca depende de que una sesión se cierre bien. El issue dice lo que había en ese momento.
    """
    from datetime import datetime, timezone

    # La rama y los cambios locales de la máquina que calcula no dicen nada del proyecto: fuera
    lineas = [linea for linea in reunir(raiz, ejecutar) if not linea.startswith("Rama:")]
    if any(linea.startswith("GitHub: no disponible") for linea in lineas):
        return ["No se publicó: GitHub no está disponible."]
    ahora = ahora or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    cuerpo = (f"Calculado el {ahora} desde las historias del repositorio y desde GitHub. Este texto lo rehace GitHub "
              "Actions cada vez que algo cambia: no lo edites.\n\n```\n" + "\n".join(lineas) + "\n```\n")
    asuntos = _api(f"issues?state=open&labels={ETIQUETA_ESTADO}&per_page=10", raiz, ejecutar)
    existente = next((uno for uno in asuntos or [] if isinstance(uno, dict) and "pull_request" not in uno
                      and uno.get("title") == TITULO_ESTADO), None)
    if not existente:  # uno de antes de la etiqueta: se busca por título una vez y se le pone la etiqueta
        asuntos = _api("issues?state=open&per_page=100", raiz, ejecutar)
        existente = next((uno for uno in asuntos or [] if isinstance(uno, dict) and "pull_request" not in uno
                          and uno.get("title") == TITULO_ESTADO), None)
        if existente:
            ejecutar(["gh", "api", "-X", "POST", f"{API}/issues/{existente['number']}/labels", "-f",
                      f"labels[]={ETIQUETA_ESTADO}"], raiz)
    if existente:
        hecho = ejecutar(["gh", "api", "-X", "PATCH", f"{API}/issues/{existente['number']}", "-f", f"body={cuerpo}"],
                         raiz)
        return [f"Estado publicado en #{existente['number']}." if hecho is not None else "No se pudo publicar."]
    hecho = ejecutar(["gh", "api", "-X", "POST", f"{API}/issues", "-f", f"title={TITULO_ESTADO}", "-f", f"body={cuerpo}",
                      "-f", f"labels[]={ETIQUETA_ESTADO}"], raiz)
    return ["Estado publicado en un issue nuevo." if hecho is not None else "No se pudo publicar."]


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
    analizador = argparse.ArgumentParser(description="Estado del proyecto en pocas líneas.")
    analizador.add_argument("--sin-red", action="store_true", help="no consulta GitHub: solo lo que está en el disco")
    analizador.add_argument("--peso", action="store_true", help="lista los documentos que más pesan al leerlos")
    analizador.add_argument("--consumo", action="store_true",
                            help="suma minutos, agentes y documentos leídos por historia, desde la bitácora")
    analizador.add_argument("--publicar", action="store_true",
                            help="publica el estado en el issue «Estado del proyecto» (lo usa la CI)")
    analizador.add_argument("--escribir", action="store_true",
                            help="rehace las cifras de .fabrica/estado.json desde el disco (y GitHub, si hay red)")
    opciones = analizador.parse_args(argumentos)
    if hasattr(sys.stdout, "reconfigure"):
        # Con la salida redirigida, Windows usaría su página de códigos y rompería los acentos.
        sys.stdout.reconfigure(errors="replace", **({} if sys.stdout.isatty() else {"encoding": "utf-8"}))
    if opciones.escribir:
        lineas = escribir(raiz, con_red=not opciones.sin_red)
    elif opciones.publicar:
        lineas = publicar(raiz)
    elif opciones.consumo:
        lineas = consumo(raiz)
    elif opciones.peso:
        lineas = peso(raiz)
    else:
        lineas = reunir(raiz, con_red=not opciones.sin_red)
    print("\n".join(lineas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
