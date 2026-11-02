#!/usr/bin/env python3
"""Prueba de punta a punta del registro de clientes, la creación de proyectos y la protección de las pruebas.

En una instancia temporal comprueba que:
- se registra un holding con dos negocios y nace la base de cada rubro; se rechazan identificadores y rubros
  inválidos, duplicados y la reserva estricta;
- un proyecto nace con el kit completo, la copia del método, la base de su rubro (o un aviso si no la hay), su estado,
  su manifiesto y su primer commit;
- la ficha del cliente lista el proyecto, y no se crean proyectos de negocios inexistentes ni repetidos;
- la verificación del proyecto pasa en limpio;
- un cambio en pruebas/aceptacion/ sin la etiqueta pruebas-aprobadas se rechaza, y con ella se acepta;
- la actualización del kit trae el método nuevo y la base del rubro al día, y conserva lo propio del proyecto;
- la recolección de aprendizajes lista los nuevos, avisa de los datos del cliente y no repite los ya decididos;
- a un cliente registrado se le suman negocios;
- un proyecto que ya existe se adopta sin perder su historia ni lo propio, respalda lo que el kit reemplaza y, si la
  verificación falla, queda como estaba;
- en la copia del mantenedor no se pueden registrar clientes, crear ni adoptar proyectos, ni recoger aprendizajes.

Uso: python pruebas/probar_kit.py
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
import _nucleo  # noqa: E402

ENTORNO = {k: v for k, v in os.environ.items() if k != "FABRICA_ES_NUCLEO"}
ENTORNO.update({"GIT_AUTHOR_NAME": "prueba", "GIT_AUTHOR_EMAIL": "prueba@example.com",
                "GIT_COMMITTER_NAME": "prueba", "GIT_COMMITTER_EMAIL": "prueba@example.com"})
resultados = []


def comprobar(nombre, condicion, detalle=""):
    resultados.append((nombre, bool(condicion)))
    print(f"{'OK   ' if condicion else 'FALLA'} {nombre}" + (f" — {detalle[:600]}" if detalle and not condicion else ""))


def leer(p):
    """Texto de un archivo, o cadena vacía si no existe: así el caso falla en vez de cortar la prueba."""
    return Path(p).read_text(encoding="utf-8") if Path(p).is_file() else ""


def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENTORNO)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def script(inst, nombre, *args):
    return run([sys.executable, f".fabrica/scripts/{nombre}", *args], inst)


def main():
    _nucleo.preparar_consola()
    with tempfile.TemporaryDirectory(prefix="prueba-kit-") as tmp:
        inst = Path(tmp) / "instancia"
        for rel in _nucleo.archivos(RAIZ):
            (inst / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(RAIZ / rel, inst / rel)
        (inst / "clientes").mkdir()

        # Clientes
        rc, out = script(inst, "nuevo_cliente.py", "--id", "grupo-demo", "--nombre", "Grupo Demo", "--tipo", "holding",
                         "--negocio", "distribucion:logistica:Reparto a domicilio", "--negocio", "farmacia:salud")
        ficha = inst / "clientes" / "grupo-demo" / "cliente.md"
        comprobar("Registra un holding con dos negocios", rc == 0 and ficha.exists(), out)
        texto = ficha.read_text(encoding="utf-8") if ficha.exists() else ""
        comprobar("La ficha tiene nombre, tipo y negocios",
                  "# Grupo Demo" in texto and "tipo: holding" in texto and "| distribucion | logistica |" in texto
                  and "| farmacia | salud |" in texto and "<negocio>" not in texto and "<proyecto>" not in texto, texto)
        base_logistica = inst / "rubros" / "logistica" / "conocimiento.md"
        comprobar("Nace la base de cada rubro nuevo, desde la plantilla",
                  base_logistica.exists() and (inst / "rubros" / "salud" / "conocimiento.md").exists()
                  and "# Rubro: logistica" in base_logistica.read_text(encoding="utf-8"), out)
        rc, out = script(inst, "nuevo_cliente.py", "--id", "otro-cliente", "--nombre", "X", "--negocio", "x:Gas Licuado")
        comprobar("Rechaza un rubro que no es un identificador", rc != 0 and "El rubro" in out
                  and not (inst / "clientes" / "otro-cliente").exists(), out)
        rc, out = script(inst, "nuevo_cliente.py", "--id", "grupo-demo", "--nombre", "Otro", "--negocio", "x:y")
        comprobar("Rechaza un cliente repetido", rc != 0 and "ya existe" in out, out)
        rc, out = script(inst, "nuevo_cliente.py", "--id", "Mi Cliente", "--nombre", "X", "--negocio", "x:y")
        comprobar("Rechaza un identificador inválido", rc != 0 and "no es válido" in out, out)
        rc, out = script(inst, "nuevo_cliente.py", "--id", "reservado", "--nombre", "X", "--reserva", "estricta",
                         "--negocio", "x:y")
        comprobar("Un cliente con reserva estricta se deriva a otra instancia",
                  rc != 0 and "propia instancia" in out and not (inst / "clientes" / "reservado").exists(), out)

        # Proyecto
        base_logistica.write_text(base_logistica.read_text(encoding="utf-8") + "\nRegla conocida del rubro.\n",
                                  encoding="utf-8")
        rc, out = script(inst, "nuevo_proyecto.py", "--cliente", "grupo-demo", "--negocio", "distribucion",
                         "--proyecto", "plataforma", "--nombre", "Plataforma de reparto")
        proy = inst / "proyectos" / "grupo-demo-plataforma"
        comprobar("Crea el proyecto", rc == 0 and proy.is_dir(), out)
        esperados = ["AGENTS.md", "CLAUDE.md", "NUCLEO.txt", ".claude/agents/desarrollador.md",
                     ".claude/agents/revisor.md", ".claude/skills/construir/SKILL.md", ".github/workflows/fabrica.yml",
                     ".fabrica/scripts/verificar_proyecto.py", ".fabrica/nucleo/constitucion.md",
                     ".fabrica/nucleo/plantillas/historia.md", ".fabrica/proyecto.json", ".fabrica/estado.json",
                     ".fabrica/nucleo-instalado.csv", "docs/constitucion.md", "docs/bitacora.md",
                     "pruebas/aceptacion/.gitkeep", ".gitignore", ".gitattributes", ".fabrica/motor/corrida.md",
                     ".fabrica/rubro/conocimiento.md"]
        faltan = [e for e in esperados if not (proy / e).exists()]
        comprobar("El proyecto trae el kit completo", not faltan, f"faltan: {faltan}")
        comprobar("La copia del método es idéntica al núcleo",
                  (proy / ".fabrica/nucleo/constitucion.md").read_bytes() == (inst / "nucleo/constitucion.md").read_bytes())
        comprobar("El proyecto recibe la base de su rubro",
                  leer(proy / ".fabrica/rubro/conocimiento.md") == leer(base_logistica))
        datos = json.loads((proy / ".fabrica/proyecto.json").read_text(encoding="utf-8"))
        estado = json.loads((proy / ".fabrica/estado.json").read_text(encoding="utf-8"))
        comprobar("proyecto.json y estado.json identifican el proyecto",
                  datos["cliente"] == estado["cliente"] == "grupo-demo" and datos["proyecto"] == estado["proyecto"] ==
                  "plataforma" and estado["nucleo"] == _nucleo.version(RAIZ) and not any(k.startswith("_") for k in estado),
                  json.dumps(estado, ensure_ascii=False))
        comprobar("proyecto.json registra la cuenta cuyo 'intégralo' autoriza un merge", "direccion" in datos,
                  json.dumps(datos, ensure_ascii=False))
        comprobar("proyecto.json trae el presupuesto del motor (1 paso por corrida)",
                  datos.get("motor", {}).get("pasos_por_corrida") == 1, json.dumps(datos, ensure_ascii=False))
        comprobar("La constitución del proyecto lleva su nombre",
                  "# Constitución de Plataforma de reparto" in (proy / "docs/constitucion.md").read_text(encoding="utf-8"))
        rc_l, log = run(["git", "log", "--oneline"], proy)
        comprobar("El proyecto nace con su repositorio y su primer commit", rc_l == 0 and len(log.strip().splitlines()) == 1, log)
        comprobar("La ficha del cliente lista el proyecto",
                  "| plataforma | distribucion | `grupo-demo-plataforma` | activo |" in ficha.read_text(encoding="utf-8"))
        rc, out = script(inst, "nuevo_proyecto.py", "--cliente", "grupo-demo", "--negocio", "inexistente", "--proyecto", "x")
        comprobar("Rechaza un negocio que no está en la ficha", rc != 0 and "no está en la ficha" in out, out)
        rc, out = script(inst, "nuevo_proyecto.py", "--cliente", "grupo-demo", "--negocio", "distribucion",
                         "--proyecto", "plataforma")
        comprobar("Rechaza un proyecto repetido", rc != 0 and "no está vacía" in out, out)
        rc, out = script(inst, "nuevo_proyecto.py", "--cliente", "nadie", "--negocio", "x", "--proyecto", "x")
        comprobar("Rechaza un cliente no registrado", rc != 0 and "no está registrado" in out, out)
        shutil.rmtree(inst / "rubros" / "salud")
        rc, out = script(inst, "nuevo_proyecto.py", "--cliente", "grupo-demo", "--negocio", "farmacia",
                         "--proyecto", "botica", "--sin-git")
        aviso = inst / "proyectos" / "grupo-demo-botica" / ".fabrica" / "rubro" / "conocimiento.md"
        comprobar("Sin base del rubro, el proyecto recibe un aviso en su lugar y se informa",
                  rc == 0 and aviso.exists() and "todavía no tiene una base" in aviso.read_text(encoding="utf-8")
                  and "no tiene base del rubro 'salud'" in out, out)

        # Verificación del proyecto y protección de las pruebas de aceptación
        verif = [sys.executable, ".fabrica/scripts/verificar_proyecto.py"]
        rc, out = run(verif, proy)
        comprobar("La verificación del proyecto pasa en limpio", rc == 0, out)
        run(["git", "checkout", "-q", "-b", "cambio-codigo"], proy)
        (proy / "src").mkdir()
        (proy / "src" / "modulo.txt").write_text("código\n", encoding="utf-8")
        run(["git", "add", "-A"], proy)
        run(["git", "commit", "-qm", "Código"], proy)
        rc, out = run(verif + ["--base", "main", "--etiquetas", ""], proy)
        comprobar("Un cambio que no toca las pruebas de aceptación pasa sin etiqueta", rc == 0, out)
        (proy / "pruebas" / "aceptacion" / "H-001").mkdir(parents=True)
        (proy / "pruebas" / "aceptacion" / "H-001" / "caso.md").write_text("Dado… cuando… entonces…\n", encoding="utf-8")
        run(["git", "add", "-A"], proy)
        run(["git", "commit", "-qm", "Toca pruebas de aceptación"], proy)
        rc, out = run(verif + ["--base", "main", "--etiquetas", ""], proy)
        comprobar("Un cambio en pruebas de aceptación sin etiqueta se rechaza", rc != 0 and "pruebas-aprobadas" in out, out)
        rc, out = run(verif + ["--base", "main", "--etiquetas", "riesgo:alto,pruebas-aprobadas"], proy)
        comprobar("Con la etiqueta pruebas-aprobadas se acepta", rc == 0, out)
        evento = Path(tmp) / "evento.json"
        evento.write_text(json.dumps({"pull_request": {"labels": [{"name": "riesgo:alto"}]}}), encoding="utf-8")
        ENTORNO["GITHUB_EVENT_PATH"] = str(evento)
        rc, out = run(verif + ["--base", "main"], proy)
        comprobar("Lee las etiquetas del evento de GitHub (sin la etiqueta, rechaza)", rc != 0, out)
        ENTORNO.pop("GITHUB_EVENT_PATH")

        # La verificación de la instancia completa, con su cliente y su proyecto, sigue pasando
        rc, out = script(inst, "verificar.py")
        comprobar("La instancia con clientes y proyectos pasa la verificación", rc == 0, out)

        # Actualizar el kit del proyecto cuando la instancia recibe un núcleo nuevo
        run(["git", "checkout", "-q", "main"], proy)
        (proy / ".claude" / "skills" / "local-propia").mkdir(parents=True)
        (proy / ".claude" / "skills" / "local-propia" / "SKILL.md").write_text("---\nname: local-propia\n---\n",
                                                                              encoding="utf-8")
        constitucion = (proy / "docs" / "constitucion.md").read_text(encoding="utf-8") + "\nP-9. Regla propia.\n"
        (proy / "docs" / "constitucion.md").write_text(constitucion, encoding="utf-8")
        run(["git", "add", "-A"], proy)
        run(["git", "commit", "-qm", "Ajustes propios del proyecto"], proy)
        (inst / "kit" / "AGENTS.md").write_text((inst / "kit" / "AGENTS.md").read_text(encoding="utf-8")
                                                + "\nRegla nueva del kit.\n", encoding="utf-8")
        (inst / "nucleo" / "calidad.md").write_text((inst / "nucleo" / "calidad.md").read_text(encoding="utf-8")
                                                    + "\nRegla nueva del método.\n", encoding="utf-8")
        base_logistica.write_text(base_logistica.read_text(encoding="utf-8") + "\nRegla nueva del rubro.\n",
                                  encoding="utf-8")
        log = inst / "CHANGELOG.md"
        texto = log.read_text(encoding="utf-8")
        i = texto.index("\n## ") + 1
        log.write_text(texto[:i] + "## 9.9.9 · prueba\n\n- Cambio de prueba.\n\n" + texto[i:], encoding="utf-8")
        destino = "proyectos/grupo-demo-plataforma"
        rc, out = script(inst, "actualizar_kit.py", destino)
        comprobar("La vista previa del kit anuncia la versión nueva y no cambia nada",
                  rc == 0 and "→ 9.9.9" in out and "Regla nueva del kit." not in (proy / "AGENTS.md").read_text(encoding="utf-8"), out)
        (proy / "borrador.txt").write_text("sin commit\n", encoding="utf-8")
        rc, out = script(inst, "actualizar_kit.py", destino, "--aplicar")
        comprobar("No actualiza un proyecto con cambios sin commit", rc != 0 and "sin commit" in out, out)
        (proy / "borrador.txt").unlink()
        rc, out = script(inst, "actualizar_kit.py", destino, "--aplicar")
        comprobar("Actualiza el kit del proyecto", rc == 0, out)
        comprobar("Trae el cambio del kit, el del método y el de la base del rubro",
                  "Regla nueva del kit." in (proy / "AGENTS.md").read_text(encoding="utf-8")
                  and "Regla nueva del método." in (proy / ".fabrica/nucleo/calidad.md").read_text(encoding="utf-8")
                  and "Regla nueva del rubro." in (proy / ".fabrica/rubro/conocimiento.md").read_text(encoding="utf-8"))
        comprobar("Conserva lo propio del proyecto (skill local y constitución)",
                  (proy / ".claude/skills/local-propia/SKILL.md").exists()
                  and "P-9. Regla propia." in (proy / "docs/constitucion.md").read_text(encoding="utf-8"))
        datos = json.loads((proy / ".fabrica/proyecto.json").read_text(encoding="utf-8"))
        comprobar("Registra la versión nueva en proyecto.json sin tocar el resto",
                  datos["nucleo"] == "9.9.9" and datos["proyecto"] == "plataforma", json.dumps(datos, ensure_ascii=False))
        rc_l, ultimo = run(["git", "log", "-1", "--format=%s"], proy)
        rc_s, pendiente = run(["git", "status", "--porcelain"], proy)
        comprobar("Deja un commit propio y el proyecto limpio",
                  "9.9.9" in ultimo and pendiente.strip() == "", f"{ultimo} | {pendiente}")
        rc, out = run(verif, proy)
        comprobar("El proyecto actualizado pasa su verificación", rc == 0, out)

        # Recoger aprendizajes: solo docs/aprendizajes.md de cada proyecto, con avisos de limpieza
        plantilla = (inst / "nucleo" / "plantillas" / "aprendizajes.md").read_text(encoding="utf-8")
        (proy / "docs" / "aprendizajes.md").write_text(plantilla + """
## A-002 · Los envases se prestan
- **Tipo:** rubro
- **Qué aprendimos:** los envases retornables se controlan como activos en préstamo.
- **Evidencia:** confirmado en la épica de despacho el 2026-11-02.
- **Propuesta:** agregar la regla a la base del rubro.

## A-003 · Historias largas
- **Tipo:** método
- **Qué aprendimos:** las historias con más de cinco criterios terminan divididas en revisión.
- **Propuesta:** dividirlas antes de planificar.

## A-004 · Descuento especial
- **Tipo:** rubro
- **Qué aprendimos:** Grupo Demo da un descuento de $ 15.000 a sus clientes frecuentes.
""", encoding="utf-8")
        recoger = ["recoger_aprendizajes.py", "--local"]
        rc, out = script(inst, *recoger)
        comprobar("Lista los aprendizajes nuevos y omite la entrada de ejemplo de la plantilla",
                  rc == 0 and "Aprendizajes nuevos: 3" in out and "A-001" not in out and "[metodo]" in out, out)
        bloque_limpio = out.split("A-002", 1)[-1].split("A-003", 1)[0]
        bloque_sucio = out.split("A-004", 1)[-1]
        comprobar("Avisa del nombre del cliente y del monto, y no confunde una fecha con un teléfono",
                  "AVISO DE LIMPIEZA" not in bloque_limpio and "nombra al cliente" in bloque_sucio
                  and "un monto" in bloque_sucio and "(1 con aviso de limpieza)" in out, out)
        rc, out = script(inst, "recoger_aprendizajes.py", "--registrar", "grupo-demo-plataforma:A-002", "--decision",
                         "rubro", "--nota", "base del rubro")
        rc2, out2 = script(inst, *recoger)
        comprobar("Una decisión registrada no se vuelve a recoger",
                  rc == 0 and (inst / "instancia" / "aprendizajes-recogidos.csv").exists()
                  and "Aprendizajes nuevos: 2" in out2 and "A-002" not in out2, out + out2)
        rc, out = script(inst, "recoger_aprendizajes.py", "--registrar", "grupo-demo-plataforma:A-002", "--decision",
                         "descartado")
        comprobar("No registra dos veces el mismo aprendizaje", rc != 0 and "ya tiene una decisión" in out, out)

        # Sumar un negocio a un cliente que ya existe
        rc, out = script(inst, "nuevo_cliente.py", "--id", "grupo-demo", "--agregar", "--negocio",
                         "muebles:mobiliario:Venta de muebles")
        comprobar("Suma un negocio a un cliente registrado y crea la base de su rubro",
                  rc == 0 and "| muebles | mobiliario | Venta de muebles |" in ficha.read_text(encoding="utf-8")
                  and (inst / "rubros" / "mobiliario" / "conocimiento.md").exists(), out)
        rc, out = script(inst, "nuevo_cliente.py", "--id", "grupo-demo", "--agregar", "--negocio", "muebles:mobiliario")
        comprobar("No suma un negocio repetido", rc != 0 and "ya tiene el negocio" in out, out)
        rc, out = script(inst, "nuevo_cliente.py", "--id", "nadie", "--agregar", "--negocio", "x:y")
        comprobar("No suma negocios a un cliente no registrado", rc != 0 and "no está registrado" in out, out)

        # Adoptar un proyecto que ya existe, con choques de rutas y archivos propios
        viejo = Path(tmp) / "tienda-vieja"
        propios_viejo = {"README.md": "# Tienda propia\n", "CLAUDE.md": "Reglas propias del proyecto.\n",
                         ".claude/agents/analista.md": "agente propio\n", ".claude/agents/dev-movil.md": "propio\n",
                         ".claude/skills/propia/SKILL.md": "---\nname: propia\n---\n",
                         ".github/pull_request_template.md": "plantilla propia\n",
                         ".github/workflows/ci.yml": "# CI propia\n", "docs/01-descubrimiento/venta.md": "notas\n",
                         ".gitignore": "node_modules/\n.env\n", "src/app.txt": "código\n"}
        for rel, texto in propios_viejo.items():
            (viejo / rel).parent.mkdir(parents=True, exist_ok=True)
            (viejo / rel).write_text(texto, encoding="utf-8")
        run(["git", "init", "-q", "-b", "master"], viejo)
        run(["git", "add", "-A"], viejo)
        run(["git", "commit", "-qm", "Historia propia"], viejo)
        adoptar = ["adoptar_proyecto.py", str(viejo), "--cliente", "grupo-demo", "--negocio", "muebles",
                   "--proyecto", "tienda", "--fase", "especificacion"]
        rc, out = script(inst, *adoptar)
        comprobar("La vista previa de la adopción muestra choques y propios, y no cambia nada",
                  rc == 0 and "CLAUDE.md" in out and ".claude/agents/analista.md" in out
                  and ".github/pull_request_template.md" in out and ".claude/agents/dev-movil.md" in out
                  and "renómbralo a grupo-demo-tienda" in out
                  and (viejo / "CLAUDE.md").read_text(encoding="utf-8") == "Reglas propias del proyecto.\n", out)
        (viejo / "borrador.txt").write_text("sin commit\n", encoding="utf-8")
        rc, out = script(inst, *adoptar, "--aplicar")
        comprobar("No adopta un proyecto con cambios sin commit", rc != 0 and "sin commit" in out, out)
        (viejo / "borrador.txt").unlink()
        rc, out = script(inst, *adoptar, "--aplicar")
        datos = json.loads((viejo / ".fabrica/proyecto.json").read_text(encoding="utf-8")) if rc == 0 else {}
        comprobar("Adopta el proyecto con el kit, su ficha y la base de su rubro",
                  rc == 0 and (viejo / "AGENTS.md").exists() and (viejo / ".fabrica/nucleo/constitucion.md").exists()
                  and "# Rubro: mobiliario" in (viejo / ".fabrica/rubro/conocimiento.md").read_text(encoding="utf-8")
                  and datos.get("proyecto") == "tienda", out)
        estado_v = json.loads((viejo / ".fabrica/estado.json").read_text(encoding="utf-8")) if rc == 0 else {}
        comprobar("El estado del proyecto adoptado parte en la fase indicada", estado_v.get("fase") == "especificacion")
        comprobar("No pisa el código, el README, docs/, la CI propia ni sus agentes y skills propios",
                  all((viejo / r).read_text(encoding="utf-8") == propios_viejo[r] for r in
                      ("README.md", "src/app.txt", "docs/01-descubrimiento/venta.md", ".github/workflows/ci.yml",
                       ".claude/agents/dev-movil.md", ".claude/skills/propia/SKILL.md")))
        respaldo = next((viejo / ".fabrica" / "respaldo-nucleo").glob("*"), None)
        comprobar("Respalda lo que el kit reemplaza, también el choque de mayúsculas",
                  respaldo is not None and leer(respaldo / "CLAUDE.md") == "Reglas propias del proyecto.\n"
                  and leer(respaldo / ".claude/agents/analista.md") == "agente propio\n"
                  and (respaldo / ".github/pull_request_template.md").exists()
                  and leer(viejo / "CLAUDE.md") == leer(inst / "kit/CLAUDE.md"))
        nombres_github = {x.name for x in (viejo / ".github").iterdir() if x.is_file() and "template" in x.name.lower()}
        rc_g, indice = run(["git", "ls-files", ".github"], viejo)
        plantillas_git = {n for n in (l.rsplit("/", 1)[-1] for l in indice.splitlines()) if "template" in n.lower()}
        comprobar("Tras un choque de mayúsculas queda solo la plantilla del kit, en el disco y en el índice de git",
                  nombres_github == {"PULL_REQUEST_TEMPLATE.md"} and plantillas_git == {"PULL_REQUEST_TEMPLATE.md"},
                  f"disco: {nombres_github} | git: {plantillas_git}")
        ignorar = (viejo / ".gitignore").read_text(encoding="utf-8")
        comprobar("Al .gitignore solo le agrega líneas", ignorar.startswith("node_modules/\n.env\n")
                  and ".fabrica/respaldo-nucleo/" in ignorar and ignorar.count(".env\n") == 1, ignorar)
        rc_s, pendiente = run(["git", "status", "--porcelain"], viejo)
        rc_l, log = run(["git", "log", "--oneline"], viejo)
        comprobar("Deja un commit propio, conserva la historia y el proyecto queda limpio",
                  pendiente.strip() == "" and len(log.strip().splitlines()) == 2 and "Adopta" in log, log + pendiente)
        comprobar("La ficha del cliente lista el proyecto adoptado",
                  "| tienda | muebles | `grupo-demo-tienda` | activo |" in ficha.read_text(encoding="utf-8"))
        rc, out = run(verif, viejo)
        comprobar("El proyecto adoptado pasa su verificación", rc == 0, out)
        rc, out = script(inst, *adoptar, "--aplicar")
        comprobar("No adopta dos veces el mismo proyecto", rc != 0 and "ya es un proyecto de la fábrica" in out, out)
        rc, out = script(inst, "actualizar_kit.py", str(viejo), "--aplicar")
        comprobar("El proyecto adoptado se actualiza como cualquier otro y conserva lo propio",
                  rc == 0 and (viejo / ".claude/agents/dev-movil.md").exists()
                  and (viejo / ".claude/skills/propia/SKILL.md").exists(), out)

        # Si la verificación falla, la adopción se deshace entera
        roto = Path(tmp) / "roto"
        for rel, texto in {"CLAUDE.md": "Reglas del roto.\n", ".fabrica/estado.json": "{roto",
                           ".gitignore": "dist/\n"}.items():
            (roto / rel).parent.mkdir(parents=True, exist_ok=True)
            (roto / rel).write_text(texto, encoding="utf-8")
        run(["git", "init", "-q", "-b", "main"], roto)
        run(["git", "add", "-A"], roto)
        run(["git", "commit", "-qm", "Roto"], roto)
        rc, out = script(inst, "adoptar_proyecto.py", str(roto), "--cliente", "grupo-demo", "--negocio", "muebles",
                         "--proyecto", "roto", "--aplicar")
        rc_s, pendiente = run(["git", "status", "--porcelain", "--ignored"], roto)
        comprobar("Si la verificación falla, deshace la adopción y deja el proyecto como estaba",
                  rc != 0 and "se deshizo" in out and pendiente.strip() == ""
                  and (roto / "CLAUDE.md").read_text(encoding="utf-8") == "Reglas del roto.\n"
                  and (roto / ".gitignore").read_text(encoding="utf-8") == "dist/\n"
                  and "| roto |" not in ficha.read_text(encoding="utf-8"), out + pendiente)

        # En la copia del mantenedor, se niega
        run(["git", "init", "-q", "-b", "main"], inst)
        run(["git", "config", "fabrica.mantenedor", "true"], inst)
        rc, out = script(inst, "nuevo_cliente.py", "--id", "otro", "--nombre", "Otro", "--negocio", "x:y")
        comprobar("En el núcleo no se registran clientes", rc != 0 and "núcleo que mantienes" in out, out)
        rc, out = script(inst, "nuevo_proyecto.py", "--cliente", "grupo-demo", "--negocio", "farmacia", "--proyecto", "y")
        comprobar("En el núcleo no se crean proyectos", rc != 0 and "núcleo que mantienes" in out, out)
        rc, out = script(inst, "recoger_aprendizajes.py", "--local")
        comprobar("En el núcleo no se recogen aprendizajes", rc != 0 and "núcleo que mantienes" in out, out)
        rc, out = script(inst, "adoptar_proyecto.py", str(Path(tmp) / "tienda-vieja"), "--cliente", "grupo-demo",
                         "--negocio", "muebles", "--proyecto", "otra")
        comprobar("En el núcleo no se adoptan proyectos", rc != 0 and "núcleo que mantienes" in out, out)

    fallas = [n for n, ok in resultados if not ok]
    print(f"\nPruebas del kit: {len(resultados) - len(fallas)}/{len(resultados)} correctas.")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
