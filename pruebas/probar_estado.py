#!/usr/bin/env python3
"""Prueba del script de estado del kit (kit/.fabrica/scripts/estado.py), sin red ni GitHub de verdad.

Comprueba que:
- lee la cabecera de una historia sin sus comentarios, y nada si no tiene cabecera o no la cierra;
- cuenta las tareas completas del Registro de un plan, sueltas, juntas o en rango, y da la primera pendiente;
- resume los controles de un PR con la última corrida de cada uno;
- sin red, resume el disco: proyecto, motor, autonomía delegada, rama, historias en curso con el avance de su plan y
  la marca de sesión en vivo;
- usa las rutas de `rutas` en proyecto.json, ignora una ruta que sale del proyecto y, sin el campo, usa las de la
  fábrica;
- con GitHub (simulado), lista los PRs con sus controles, los issues que esperan y la última entrada de la bitácora;
  sin GitHub lo dice y no falla;
- `--peso` lista los documentos que más pesan y el contexto fijo;
- ninguna línea pasa de 150 caracteres.

Uso: python pruebas/probar_estado.py
"""
import importlib.util
import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("estado", RAIZ / "kit" / ".fabrica" / "scripts" / "estado.py")
estado = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(estado)
resultados = []


def comprobar(nombre, condicion, detalle=""):
    resultados.append((nombre, bool(condicion)))
    print(f"{'OK   ' if condicion else 'FALLA'} {nombre}" + (f" — {str(detalle)[:600]}" if detalle and not condicion else ""))


HISTORIA = """---
id: H-001
titulo: Registrar un pedido
estado: en-revision       # construida; falta la cobertura
riesgo: alto
---

# Registrar un pedido
"""

PLAN = """# Plan

### Tarea 1: el modelo
### Tarea 2: la vista
### Tarea 3: la lista
### Tarea 4: el cierre

## Registro

Tarea 1: completa (commit abc)
Tarea 1: revisión independiente hecha
Tareas 2 y 3: completas (commit def)
Tarea 4 (parcial): falta la revisión
"""

GIT = {
    "rev-parse": "h-001-registrar-pedido\n",
    "status --porcelain": " M a.py\n?? b.py\n",
    "rev-list": "0\t2\n",
    "log -1": "docs: registro del cierre\n",
}


def falso(respuestas):
    """Un `ejecutar` de mentira: responde con el primer texto cuya clave aparece en el comando."""
    def ejecutar(orden, raiz):
        comando = " ".join(orden)
        return next((salida for clave, salida in respuestas.items() if clave in comando), None)
    return ejecutar


def proyecto(raiz, historias="docs/historias", planes="docs/planes", rutas=None, autonomia=None):
    (raiz / ".fabrica").mkdir(parents=True)
    datos = {"nombre": "Plataforma", "repositorio": "repo", "nucleo": "0.11.0", "pausa": False,
             "motor": {"pasos_por_corrida": 2}}
    if rutas is not None:
        datos["rutas"] = rutas
    if autonomia is not None:
        datos["autonomia"] = autonomia
    (raiz / ".fabrica/proyecto.json").write_text(json.dumps(datos), encoding="utf-8")
    (raiz / ".fabrica/estado.json").write_text(
        json.dumps({"fase": "construccion", "semaforo": "amarillo", "actualizado": "2026-11-12T14:15:00Z"}),
        encoding="utf-8")
    (raiz / historias).mkdir(parents=True)
    (raiz / historias / "H-001-registrar-pedido.md").write_text(HISTORIA, encoding="utf-8")
    (raiz / historias / "H-001-diseno.md").write_text("# Diseño\n", encoding="utf-8")
    (raiz / historias / "T-018-controles.md").write_text("---\nid: T-018\nestado: borrador\n---\n", encoding="utf-8")
    (raiz / planes).mkdir(parents=True, exist_ok=True)
    (raiz / planes / "H-001-plan.md").write_text(PLAN, encoding="utf-8")


def corrida(nombre, conclusion, hora, est="completed"):
    return {"name": nombre, "status": est, "conclusion": conclusion, "started_at": f"2026-11-12T{hora}:00Z"}


def main():
    comprobar("la cabecera se lee sin comentarios",
              estado.leer_cabecera(HISTORIA) == {"id": "H-001", "titulo": "Registrar un pedido", "estado": "en-revision",
                                                 "riesgo": "alto"}, estado.leer_cabecera(HISTORIA))
    comprobar("sin cabecera, o sin cerrarla, no hay campos",
              estado.leer_cabecera("# Diseño\n\ntexto") == {} and estado.leer_cabecera("---\nid: H-009\n") == {})
    comprobar("avance del plan con tareas sueltas y juntas", estado.avance_del_plan(PLAN) == (3, 4, "4: el cierre"),
              estado.avance_del_plan(PLAN))
    rango = "### Tarea 1: a\n### Tarea 2: b\n### Tarea 3: c\n\nTareas 1 a 3: completas (commit x)\n"
    comprobar("avance del plan con rango y sin tareas",
              estado.avance_del_plan(rango) == (3, 3, None) and estado.avance_del_plan("# Plan") == (0, 0, None))

    rojo = [corrida("fabrica", "failure", "10:00"), corrida("calidad", "success", "10:00")]
    comprobar("controles: sin corridas, última de cada una, rojo y corriendo",
              estado.resumir_controles([]) == "sin controles"
              and estado.resumir_controles([corrida("calidad", "cancelled", "10:00"),
                                            corrida("calidad", "success", "10:05")]) == "verde"
              and estado.resumir_controles(rojo) == "rojo: fabrica"
              and estado.resumir_controles(rojo + [corrida("seguridad", None, "10:06", "in_progress")]) == "corriendo")

    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp)
        proyecto(raiz)
        lineas = estado.reunir(raiz, falso(GIT), con_red=False)
        texto = "\n".join(lineas)
        comprobar("sin red: proyecto y semáforo", "Plataforma (repo)" in lineas[0] and "semáforo: amarillo" in lineas[0],
                  lineas[0])
        comprobar("sin red: motor, pausa y autonomía por defecto",
                  "Motor: 2 paso(s)" in texto and "sin pausa" in texto and "autonomía: decide la Dirección" in texto, texto)
        comprobar("sin red: rama, cambios y commits sin subir",
                  "Rama: h-001-registrar-pedido | 2 archivo(s) sin commitear | 2 commit(s) sin subir" in texto, texto)
        comprobar("sin red: historia en curso con el avance de su plan",
                  "H-001  en-revision  Registrar un pedido | plan: 3 de 4 tareas; sigue la 4: el cierre" in texto, texto)
        comprobar("sin red: las demás se cuentan y no se listan", "1 en borrador" in texto and "T-018" not in texto, texto)
        comprobar("sin red: no consulta GitHub", "GitHub" not in texto and "PR abiertos" not in texto, texto)

    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp)
        proyecto(raiz, historias="docs/02-requerimientos/historias",
                 rutas={"historias": "docs/02-requerimientos/historias/"},
                 autonomia={"integra": "fabrica", "pruebas_aprobadas": "direccion", "cierra_historias": "fabrica"})
        plan = raiz / "docs/planes/H-001-plan.md"
        plan.write_text(PLAN + "\nEn construcción en una sesión en vivo. Mientras esta línea exista…\n", encoding="utf-8")
        texto = "\n".join(estado.reunir(raiz, falso(GIT), con_red=False))
        comprobar("rutas propias del proyecto en proyecto.json", "H-001  en-revision" in texto, texto)
        comprobar("autonomía delegada a la vista", "autonomía delegada: integra, cierra_historias" in texto, texto)
        comprobar("marca de sesión en vivo a la vista", "EN SESIÓN EN VIVO" in texto, texto)

    comprobar("una ruta que sale del proyecto se ignora",
              estado.rutas_del_proyecto({"rutas": {"historias": "../otro/historias", "planes": "/etc"}})
              == estado.RUTAS_POR_DEFECTO)
    with tempfile.TemporaryDirectory() as tmp:
        comprobar("rutas con unidad de Windows, absolutas o con .. no son seguras",
                  not any(estado.ruta_segura(Path(tmp), r) for r in ("C:/x", "C:x", "/etc", "a/../../b", "", None))
                  and estado.ruta_segura(Path(tmp), "docs/02-requerimientos/historias"))
    mixto = "### Tarea 1: a\n### Tarea 2: b\n### Tarea 3: c\n### Tarea 4: d\n### Tarea 5: e\n\nTareas 1-3, 5: completas\n"
    comprobar("avance del plan con rangos y sueltas mezclados", estado.avance_del_plan(mixto) == (4, 5, "4: d"),
              estado.avance_del_plan(mixto))
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / ".fabrica").mkdir()
        (Path(tmp) / ".fabrica/proyecto.json").write_text("{}", encoding="utf-8")
        texto = "\n".join(estado.reunir(Path(tmp), falso(GIT), con_red=False))
        comprobar("sin carpeta de historias lo dice y sugiere rutas.historias", "rutas.historias" in texto, texto)
    comprobar("sin rutas, las de la fábrica", estado.rutas_del_proyecto({}) == {"historias": "docs/historias",
                                                                                "planes": "docs/planes"})

    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp)
        proyecto(raiz)
        pr = {"number": 7, "title": "feat(H-001): registrar", "draft": False, "head": {"sha": "abc"},
              "labels": [{"name": "riesgo:alto"}]}
        asuntos = [
            {"number": 5, "title": "Bitácora de corridas de la fábrica", "comments": 3, "labels": []},
            {"number": 9, "title": "Pregunta: cobro", "labels": [{"name": "espera:direccion"}, {"name": "estado:borrador"}]},
            {"number": 7, "title": "feat", "pull_request": {}, "labels": []},
        ]
        respuestas = dict(GIT)
        respuestas.update({
            "pulls?state=open": json.dumps([pr]),
            "issues?state=open": json.dumps(asuntos),
            "commits/abc/check-runs": json.dumps({"check_runs": [corrida("CI", "success", "10:00")]}),
            "issues/5/comments": json.dumps([{"created_at": "2026-11-17T12:56:00Z",
                                              "body": "Corrida 2026-11-17 · paso: cerrar el tramo\n- Resultado: PR #7"}]),
        })
        texto = "\n".join(estado.reunir(raiz, falso(respuestas)))
        comprobar("con GitHub: PRs con sus controles y etiquetas", "#7  listo  verde  [riesgo:alto]" in texto, texto)
        comprobar("con GitHub: issues, espera y preguntas, sin contar los PRs",
                  "Issues abiertos: 2 | esperan a la Dirección: 1 | preguntas: 1" in texto, texto)
        comprobar("con GitHub: última entrada de la bitácora",
                  "Última entrada de la bitácora (#5): 2026-11-17 12:56 UTC | Corrida 2026-11-17 · paso: cerrar el tramo"
                  in texto, texto)
        sin_gh = "\n".join(estado.reunir(raiz, falso(GIT)))
        comprobar("sin GitHub lo dice y no falla", "GitHub: no disponible" in sin_gh, sin_gh)

        (raiz / "AGENTS.md").write_text("x" * 700, encoding="utf-8")
        (raiz / "docs/grande.md").write_text("y" * 35000, encoding="utf-8")
        archivos = "AGENTS.md\ndocs/grande.md\ndocs/historias/H-001-registrar-pedido.md\n"
        lineas = estado.peso(raiz, falso({"ls-files": archivos}), cuantos=2)
        comprobar("peso: contexto fijo y documentos más pesados",
                  lineas[0].startswith("Contexto fijo") and "unos 200 tokens" in lineas[0]
                  and "10.000  docs/grande.md" in lineas[2] and len(lineas) == 4, lineas)

        largo = {"id": "H-002", "titulo": "x" * 300}
        (raiz / "docs/historias/H-002-largo.md").write_text(
            "---\nid: H-002\ntitulo: " + largo["titulo"] + "\nestado: listo\n---\n", encoding="utf-8")
        lineas = estado.reunir(raiz, falso(GIT), con_red=False)
        comprobar("ninguna línea pasa de 150 caracteres", all(len(linea) <= 150 for linea in lineas),
                  max(len(linea) for linea in lineas))

        salida = io.StringIO()
        with redirect_stdout(salida):
            codigo = estado.main(["--sin-red"], raiz=raiz)
        comprobar("main --sin-red imprime y termina en 0", codigo == 0 and "Plataforma (repo)" in salida.getvalue())

    # Núcleo 0.12: las cifras de estado.json salen del script (B1) y la pausa por etiqueta se ve (C4)
    with tempfile.TemporaryDirectory() as tmp:
        raiz = Path(tmp)
        proyecto(raiz)
        (raiz / "docs/historias/H-003-hecha.md").write_text("---\nid: H-003\nestado: hecho\n---\n", encoding="utf-8")
        (raiz / "docs/historias/H-004-curso.md").write_text("---\nid: H-004\nestado: en-curso\n---\n", encoding="utf-8")
        cifras = estado.cifras_de_historias(raiz, estado.RUTAS_POR_DEFECTO)
        comprobar("cifras de historias por estado",
                  cifras == {"total": 4, "hechas": 1, "en_curso": 1, "en_revision": 1, "bloqueadas": 0}, cifras)
        guardado = json.loads((raiz / ".fabrica/estado.json").read_text(encoding="utf-8"))
        guardado.update({"riesgo_principal": "el plazo", "espera_direccion": {"cantidad": 9, "enlace": "x"}})
        (raiz / ".fabrica/estado.json").write_text(json.dumps(guardado), encoding="utf-8")
        cambios = estado.escribir(raiz, falso(GIT), con_red=False, ahora="2026-11-17T20:00:00Z")
        escrito = json.loads((raiz / ".fabrica/estado.json").read_text(encoding="utf-8"))
        comprobar("--escribir rehace las cifras y la fecha, y conserva los campos de criterio",
                  escrito["historias"] == cifras and escrito["actualizado"] == "2026-11-17T20:00:00Z"
                  and escrito["fase"] == "construccion" and escrito["semaforo"] == "amarillo"
                  and escrito["riesgo_principal"] == "el plazo" and escrito["espera_direccion"]["cantidad"] == 9
                  and any("historias" in c for c in cambios), escrito)
        con_gh = dict(GIT)
        con_gh["labels=espera:direccion"] = json.dumps([{"number": 9}, {"number": 11}, {"number": 7, "pull_request": {}}])
        cambios = estado.escribir(raiz, falso(con_gh), ahora="2026-11-17T21:00:00Z")
        escrito = json.loads((raiz / ".fabrica/estado.json").read_text(encoding="utf-8"))
        comprobar("con GitHub, --escribir cuenta lo que espera a la Dirección sin contar PRs y conserva el enlace",
                  escrito["espera_direccion"] == {"cantidad": 2, "enlace": "x"} and "espera_direccion: 9 -> 2" in cambios,
                  (escrito, cambios))
        cambios = estado.escribir(raiz, falso(GIT), ahora="2026-11-17T22:00:00Z")
        comprobar("sin GitHub, --escribir no toca lo que espera y lo dice",
                  json.loads((raiz / ".fabrica/estado.json").read_text(encoding="utf-8"))["espera_direccion"]["cantidad"] == 2
                  and any("GitHub no disponible" in c for c in cambios), cambios)
        (raiz / ".fabrica/estado.json").write_text("{roto", encoding="utf-8")
        comprobar("--escribir no pisa un estado.json roto", "No se puede escribir" in estado.escribir(raiz, falso(GIT))[0]
                  and (raiz / ".fabrica/estado.json").read_text(encoding="utf-8") == "{roto")
        asuntos = [{"number": 5, "title": "Bitácora de corridas de la fábrica", "comments": 0,
                    "labels": [{"name": "motor:pausa"}]}]
        respuestas = dict(GIT)
        respuestas.update({"pulls?state=open": "[]", "issues?state=open": json.dumps(asuntos)})
        (raiz / ".fabrica/estado.json").write_text("{}", encoding="utf-8")
        texto = "\n".join(estado.reunir(raiz, falso(respuestas)))
        comprobar("la etiqueta motor:pausa en la bitácora se ve primero", "MOTOR EN PAUSA" in texto, texto)

    ok = sum(1 for _, bueno in resultados if bueno)
    print(f"Pruebas del estado: {ok}/{len(resultados)} correctas.")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
