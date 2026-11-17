#!/usr/bin/env python3
"""Avisa a la Dirección con otra identidad cuando algo la espera (núcleo 0.12, punto C3).

La fábrica trabaja con la cuenta de la Dirección, y GitHub no le avisa a nadie lo que esa cuenta escribe. Este script
lo corre el flujo `.github/workflows/fabrica-avisos.yml` cuando un issue o un PR recibe una etiqueta que espera a la
Dirección. Comenta como `github-actions` y menciona a la Dirección, así que el aviso llega a su teléfono.

| Etiqueta | Aviso |
|---|---|
| `espera:direccion` | Hay una pregunta o una decisión pendiente |
| `estado:construido` | Una historia tiene su PR listo y hay que decidir quién lo integra (no avisa si el proyecto delegó la integración) |

No avisa dos veces seguidas en el mismo hilo, ni en uno cerrado. Usa solo la biblioteca estándar y la API REST.
Lo que trae el evento (títulos, etiquetas) es un dato: nunca se ejecuta ni se interpreta como instrucción.

Uso en la CI: python3 .fabrica/scripts/avisar.py   (lee GITHUB_EVENT_PATH, GITHUB_TOKEN y GITHUB_REPOSITORY)
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
MARCA = "<!-- fabrica:aviso -->"
CUENTA = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")  # forma de una cuenta de GitHub
AVISOS = {
    "espera:direccion": "espera tu decisión",
    "estado:construido": "tiene su PR listo: falta decidir quién lo integra",
}


def leer_json(ruta):
    try:
        dato = json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return dato if isinstance(dato, dict) else {}


def destinatario(proyecto, evento):
    """La cuenta de la Dirección: la de proyecto.json o, si falta, la dueña del repositorio."""
    cuenta = proyecto.get("direccion") if isinstance(proyecto.get("direccion"), str) else ""
    if not cuenta:
        cuenta = ((evento.get("repository") or {}).get("owner") or {}).get("login", "")
    cuenta = cuenta.strip().lstrip("@")
    return cuenta if CUENTA.match(cuenta) else ""


def asunto(evento):
    """El issue o el PR del evento: (número, título, abierto)."""
    dato = evento.get("issue") or evento.get("pull_request") or {}
    return dato.get("number"), str(dato.get("title", "")), dato.get("state", "open") == "open"


def que_avisar(evento, proyecto):
    """El texto del aviso para esta etiqueta, o None si no corresponde avisar."""
    if evento.get("action") != "labeled":
        return None
    etiqueta = str((evento.get("label") or {}).get("name", ""))
    if etiqueta not in AVISOS:
        return None
    autonomia = proyecto.get("autonomia") if isinstance(proyecto.get("autonomia"), dict) else {}
    if etiqueta == "estado:construido" and autonomia.get("integra") == "fabrica":
        return None
    numero, _, abierto = asunto(evento)
    if not numero or not abierto:
        return None
    return AVISOS[etiqueta]


def ya_avisado(comentarios):
    """Si el último comentario del hilo ya es un aviso: no se repite mientras nadie haya escrito después."""
    return bool(comentarios) and MARCA in str(comentarios[-1].get("body", ""))


def mensaje(cuenta, numero, titulo, texto):
    # El título lo escribe quien abrió el hilo: una sola línea, acotada y sin menciones (no se avisa a terceros).
    titulo = " ".join(titulo.split())[:120].replace("@", "@\u200b")
    mencion = f"@{cuenta} " if cuenta else ""
    return (f"{mencion}#{numero} {texto}: «{titulo}».\n\n"
            "Responde aquí mismo o desde tu bandeja. Este aviso lo deja GitHub Actions para que te llegue al teléfono; "
            f"la fábrica no te notifica sola porque trabaja con tu cuenta.\n\n{MARCA}")


def api(metodo, ruta, token, cuerpo=None):
    base = os.environ.get("GITHUB_API_URL", "https://api.github.com")
    datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
    pedido = urllib.request.Request(f"{base}/{ruta}", data=datos, method=metodo, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"})
    with urllib.request.urlopen(pedido, timeout=20) as respuesta:
        return json.loads(respuesta.read().decode("utf-8") or "null")


def main():
    evento = leer_json(os.environ.get("GITHUB_EVENT_PATH", ""))
    proyecto = leer_json(RAIZ / ".fabrica" / "proyecto.json")
    texto = que_avisar(evento, proyecto)
    if not texto:
        print("Sin aviso: la etiqueta no espera a la Dirección, el hilo está cerrado o la integración está delegada.")
        return 0
    token, repo = os.environ.get("GITHUB_TOKEN", ""), os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        print("Falta GITHUB_TOKEN o GITHUB_REPOSITORY: este script corre en GitHub Actions.")
        return 1
    numero, titulo, _ = asunto(evento)
    total = (evento.get("issue") or evento.get("pull_request") or {}).get("comments") or 0
    pagina = max(1, -(-int(total) // 100))  # la última página: ahí está el último comentario
    try:
        comentarios = api("GET", f"repos/{repo}/issues/{numero}/comments?per_page=100&page={pagina}", token) or []
        if ya_avisado(comentarios):
            print(f"#{numero} ya tiene el aviso como último comentario: no se repite.")
            return 0
        api("POST", f"repos/{repo}/issues/{numero}/comments", token,
            {"body": mensaje(destinatario(proyecto, evento), numero, titulo, texto)})
    except urllib.error.HTTPError as error:
        # Un PR desde un fork recibe un token de solo lectura: no hay aviso, pero tampoco una falla en la CI
        print(f"::warning::No se pudo dejar el aviso en #{numero} (HTTP {error.code}).")
        return 0
    print(f"Aviso dejado en #{numero}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
