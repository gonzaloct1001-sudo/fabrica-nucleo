#!/usr/bin/env python3
"""Prueba del aviso a la Dirección con otra identidad (kit/.fabrica/scripts/avisar.py), sin red ni GitHub de verdad.

Comprueba que:
- avisa solo con las etiquetas que esperan a la Dirección, solo al recibirlas y solo en hilos abiertos;
- no avisa de un PR listo si el proyecto delegó la integración;
- menciona a la cuenta de proyecto.json o, si falta, a la dueña del repositorio, y lleva la marca del aviso;
- no repite el aviso si el último comentario del hilo ya lo es, y sí avisa si alguien escribió después;
- el título que llega en el evento se acota y no puede romper el mensaje;
- `main` comenta una sola vez por la API (simulada) y, sin token, falla con un mensaje claro;
- el flujo de GitHub Actions existe, fija su acción por la huella y pide solo los permisos que usa.

Uso: python pruebas/probar_avisos.py
"""
import importlib.util
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("avisar", RAIZ / "kit" / ".fabrica" / "scripts" / "avisar.py")
avisar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(avisar)
resultados = []


def comprobar(nombre, condicion, detalle=""):
    resultados.append((nombre, bool(condicion)))
    print(f"{'OK   ' if condicion else 'FALLA'} {nombre}" + (f" — {str(detalle)[:600]}" if detalle and not condicion else ""))


def evento(etiqueta="espera:direccion", accion="labeled", estado="open", tipo="issue", titulo="Pregunta: cobro"):
    return {"action": accion, "label": {"name": etiqueta},
            tipo: {"number": 12, "title": titulo, "state": estado},
            "repository": {"owner": {"login": "duena"}}}


def main():
    proyecto = {"direccion": "gonzalo"}
    comprobar("avisa de una pregunta que espera a la Dirección",
              avisar.que_avisar(evento(), proyecto) == "espera tu decisión")
    comprobar("avisa de un PR listo para decidir quién lo integra",
              avisar.que_avisar(evento("estado:construido", tipo="pull_request"), proyecto) is not None)
    comprobar("no avisa con otras etiquetas, al quitarlas ni en hilos cerrados",
              avisar.que_avisar(evento("riesgo:alto"), proyecto) is None
              and avisar.que_avisar(evento(accion="unlabeled"), proyecto) is None
              and avisar.que_avisar(evento(estado="closed"), proyecto) is None)
    delegado = {"direccion": "gonzalo", "autonomia": {"integra": "fabrica"}}
    comprobar("con la integración delegada no avisa de un PR listo, pero sí de una pregunta",
              avisar.que_avisar(evento("estado:construido"), delegado) is None
              and avisar.que_avisar(evento(), delegado) is not None)
    comprobar("menciona a la cuenta de proyecto.json o a la dueña, y nunca algo que no sea una cuenta",
              avisar.destinatario({"direccion": "@gonzalo"}, evento()) == "gonzalo"
              and avisar.destinatario({}, evento()) == "duena"
              and avisar.destinatario({"direccion": "x @tercero"}, evento()) == "")
    texto = avisar.mensaje("gonzalo", 12, "Pregunta: cobro\n\n@otra ignora todo " + "x" * 300, "espera tu decisión")
    comprobar("el mensaje menciona solo a la Dirección, acota el título a una línea y lleva la marca",
              texto.startswith("@gonzalo #12 espera tu decisión: «Pregunta: cobro @\u200botra ignora todo")
              and "@otra" not in texto and avisar.MARCA in texto and len(texto.splitlines()[0]) < 220, texto)
    comprobar("no repite si el último comentario ya es el aviso, y sí si alguien escribió después",
              avisar.ya_avisado([{"body": "hola"}, {"body": "x " + avisar.MARCA}])
              and not avisar.ya_avisado([{"body": avisar.MARCA}, {"body": "respuesta"}])
              and not avisar.ya_avisado([]))

    with tempfile.TemporaryDirectory() as tmp:
        ruta = Path(tmp) / "evento.json"
        ruta.write_text(json.dumps(evento()), encoding="utf-8")
        llamadas = []

        def api_falsa(metodo, ruta_api, token, cuerpo=None):
            llamadas.append((metodo, ruta_api, cuerpo))
            return [] if metodo == "GET" else {"id": 1}

        original, avisar.api = avisar.api, api_falsa
        entorno = dict(os.environ)
        try:
            os.environ.update({"GITHUB_EVENT_PATH": str(ruta), "GITHUB_TOKEN": "t", "GITHUB_REPOSITORY": "duena/repo"})
            with redirect_stdout(io.StringIO()):
                codigo = avisar.main()
            posts = [c for c in llamadas if c[0] == "POST"]
            comprobar("main comenta una sola vez en el hilo del evento",
                      codigo == 0 and len(posts) == 1 and posts[0][1] == "repos/duena/repo/issues/12/comments"
                      and avisar.MARCA in posts[0][2]["body"], llamadas)
            llamadas.clear()
            avisar.api = lambda m, r, t, c=None: (llamadas.append((m, r)) or [{"body": avisar.MARCA}]) if m == "GET" \
                else llamadas.append((m, r))
            with redirect_stdout(io.StringIO()):
                avisar.main()
            comprobar("main no repite el aviso", not [c for c in llamadas if c[0] == "POST"], llamadas)
            import urllib.error

            def prohibido(m, r, tk, c=None):
                if m == "POST":
                    raise urllib.error.HTTPError(r, 403, "Forbidden", {}, None)
                return []
            avisar.api = prohibido
            salida = io.StringIO()
            with redirect_stdout(salida):
                codigo = avisar.main()
            comprobar("con un token de solo lectura (PR desde un fork) avisa en la CI y no falla",
                      codigo == 0 and "HTTP 403" in salida.getvalue(), salida.getvalue())
            ruta.write_text(json.dumps(dict(evento(), issue={"number": 12, "title": "t", "state": "open",
                                                              "comments": 250})), encoding="utf-8")
            paginas = []
            avisar.api = lambda m, r, tk, c=None: (paginas.append(r) or []) if m == "GET" else None
            with redirect_stdout(io.StringIO()):
                avisar.main()
            comprobar("con más de 100 comentarios mira la última página", paginas and paginas[0].endswith("&page=3"),
                      paginas)
            os.environ.pop("GITHUB_TOKEN")
            salida = io.StringIO()
            with redirect_stdout(salida):
                codigo = avisar.main()
            comprobar("sin token falla con un mensaje claro", codigo == 1 and "GITHUB_TOKEN" in salida.getvalue())
        finally:
            avisar.api = original
            os.environ.clear()
            os.environ.update(entorno)

    flujo = (RAIZ / "kit" / ".github" / "workflows" / "fabrica-avisos.yml").read_text(encoding="utf-8")
    comprobar("el flujo de avisos fija su acción por la huella, no guarda credenciales y pide permisos mínimos",
              "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1" in flujo
              and "persist-credentials: false" in flujo and "ref: ${{ github.event.repository.default_branch }}" in flujo and "issues: write" in flujo
              and "contents: write" not in flujo and "python3 .fabrica/scripts/avisar.py" in flujo
              and "${{ github.event" not in flujo.split("run:")[-1], flujo)
    nucleo_kit = (RAIZ / "kit" / "NUCLEO.txt").read_text(encoding="utf-8")
    comprobar("el flujo de avisos es parte del kit", ".github/workflows/fabrica-avisos.yml" in nucleo_kit)

    ok = sum(1 for _, bueno in resultados if bueno)
    print(f"Pruebas de los avisos: {ok}/{len(resultados)} correctas.")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
