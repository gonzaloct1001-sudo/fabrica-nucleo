#!/usr/bin/env python3
"""Hook de Claude Code: guarda el trabajo al terminar cada respuesta de Claude (núcleo 0.13).

Lo registra el kit en `.claude/settings.json` como hook `Stop`. Así lo avanzado no depende de cerrar bien la sesión.
Recorre todas las copias de trabajo del repositorio (`git worktree list`): la sesión suele abrirse en la copia de la
rama principal y el trabajo vive en copias hermanas, una por historia. Guarda cada copia que tenga cambios, en su rama.

1. **Commit en local, en la rama actual,** con el mensaje «wip: guardado automático <fecha hora>». Toma lo ya
   registrado en git que cambió y los archivos nuevos que `.gitignore` permite, salvo los que parecen secretos,
   imágenes, videos, comprimidos o pesan más de 1 MB: esos se dejan fuera y se avisa. Nunca `git add -A`. Nada si la
   carpeta no es un proyecto de la fábrica (sin `.fabrica/proyecto.json`), si el proyecto
   lo apagó (`"guardado_automatico": false` en `.fabrica/proyecto.json`) o con FABRICA_SIN_GUARDADO=1; si no hay
   cambios; si git está en medio de un merge o un rebase; con HEAD suelto; o en la rama principal (`main` o
   `master`), donde nunca hace commits y lo avisa.
2. **Nada, y lo dice, si un archivo ya registrado que parece un secreto cambió** (.env, llaves, credenciales).
3. **Respaldo en GitHub, como mucho cada 30 minutos,** en la rama `wip/<rama actual>`. Esa rama no tiene PR, así que
   no dispara la CI ni gasta minutos de Actions. Antes de subir corre gitleaks en local sobre los commits que todavía
   no están en GitHub; si gitleaks no está instalado o encuentra algo, no sube y lo dice. Tampoco sube si algún flujo
   de `.github/workflows/` se activa con `push` a cualquier rama sin excluir `wip/**`, porque gastaría minutos de
   Actions. Lo que se sube a GitHub no se puede retirar, así que ante la duda no sube. El resultado queda en
   `.fabrica/trabajo/respaldo.json`, que `estado.py` muestra: nunca se cree que hay respaldo cuando no lo hay.
4. **El PR se abre aparte, con un solo commit:** antes de abrirlo se juntan los commits de la rama en uno
   (`/fin-sesion` y `construir` lo explican). La rama `wip/` es solo un respaldo.

Nunca usa --force sobre una rama de trabajo: el respaldo va a su propia rama `wip/`, que se reemplaza en cada subida.
Habla poco: un guardado que sale bien no dice nada. Un problema (cambios sueltos en la rama principal, un archivo
que parece secreto, un respaldo que no se pudo subir) se avisa una sola vez por sesión; la fecha del último respaldo
está siempre en `estado.py`.

Ante cualquier error, no detiene a Claude: el guardado es una red, no una compuerta.
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

PRINCIPALES = ("main", "master")
CADA = 1800  # segundos entre respaldos en GitHub
REGISTRO = Path(".fabrica/trabajo/respaldo.json")
NO_SUBIR = re.compile(r"\.(png|jpe?g|gif|webp|bmp|heic|ico|svgz|mp3|wav|mp4|mov|avi|zip|gz|tgz|bz2|xz|7z|rar|jar|"
                      r"war|class|exe|dll|so|dylib|wasm|pyc|o|a|db|sqlite3?|pdf|docx?|xlsx?|pptx?|woff2?|ttf|otf)$", re.I)
MAXIMO = 1_000_000  # bytes de un archivo nuevo
# Se compara solo el nombre del archivo, no la carpeta: docs/secretaria/ no es un secreto
SECRETO = re.compile(r"^(\.env(\..*)?|.*\.(pem|key|p12|pfx|keystore|jks|tfstate(\.backup)?|ppk|asc|gpg)|"
                     r"id_(rsa|dsa|ecdsa|ed25519)(\.pub)?|\.npmrc|\.netrc|\.pypirc|\.git-credentials|"
                     r"credentials?(\..*)?|service[-_]?account.*\.json|.*secret.*|.*token.*\.(json|txt|env))$", re.I)


def git(raiz, *args, tope=20):
    try:
        hecho = subprocess.run(["git", "-c", "core.quotePath=false", *args], cwd=raiz, capture_output=True,
                               encoding="utf-8", errors="replace", timeout=tope, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    return hecho.returncode, (hecho.stdout or "") + (hecho.stderr or "")


def apagado(raiz):
    if os.environ.get("FABRICA_SIN_GUARDADO") == "1":
        return True
    try:
        proyecto = json.loads((raiz / ".fabrica" / "proyecto.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(proyecto, dict) and proyecto.get("guardado_automatico") is False


def en_medio_de_algo(raiz):
    rc, gitdir = git(raiz, "rev-parse", "--git-dir")
    if rc != 0:
        return True
    carpeta = (raiz / gitdir.strip()) if not Path(gitdir.strip()).is_absolute() else Path(gitdir.strip())
    return any((carpeta / nombre).exists() for nombre in ("MERGE_HEAD", "rebase-merge", "rebase-apply",
                                                          "CHERRY_PICK_HEAD", "REVERT_HEAD"))


def _lista(salida):
    return [x for x in salida.split("\0") if x]


def es_binario(ruta):
    try:
        with open(ruta, "rb") as archivo:
            return b"\0" in archivo.read(8192)
    except OSError:
        return False


def lista_fuera(fuera):
    """Los primeros archivos que quedaron fuera, con su motivo, y cuántos más hay."""
    texto = ", ".join(f"{rel} ({motivo})" for rel, motivo in fuera[:3])
    return texto + (f" y {len(fuera) - 3} más" if len(fuera) > 3 else "")


def registrados_cambiados(raiz):
    rc, salida = git(raiz, "diff", "--name-only", "-z", "HEAD")
    return _lista(salida) if rc == 0 else []


def nuevos_permitidos(raiz):
    """Los archivos nuevos que .gitignore permite, y aparte los que se dejan fuera con su motivo."""
    rc, salida = git(raiz, "ls-files", "--others", "--exclude-standard", "-z")
    entran, fuera = [], []
    for rel in _lista(salida) if rc == 0 else []:
        ruta = Path(raiz) / rel
        if rel.startswith(".fabrica/trabajo/"):
            continue
        if SECRETO.search(Path(rel).name):
            fuera.append((rel, "parece un secreto"))
        elif NO_SUBIR.search(rel) or es_binario(ruta):
            fuera.append((rel, "es una imagen, un documento o un binario"))
        elif ruta.is_file() and ruta.stat().st_size > MAXIMO:
            fuera.append((rel, "pesa más de 1 MB"))
        else:
            entran.append(rel)
    return entran, fuera


def flujos_sin_filtro(raiz):
    """Flujos de GitHub Actions que se activan con push a cualquier rama, incluida wip/."""
    malos = []
    for flujo in sorted((Path(raiz) / ".github" / "workflows").glob("*.y*ml")):
        texto = flujo.read_text(encoding="utf-8", errors="replace")
        bloque = re.search(r"^\s*push\s*:(.*?)(?=^\s{0,2}[a-z_]+\s*:|\Z)", texto, re.M | re.S)
        if re.search(r"^\s*on\s*:\s*\[?[^\n]*\bpush\b", texto, re.M) and not bloque:
            malos.append(flujo.name)  # on: push  /  on: [push, pull_request]
        elif bloque:
            cuerpo = bloque.group(1)
            if "wip/" in cuerpo:
                continue
            todas = re.search(r"\bbranches\s*:[^\n]*['\"]?\*\*?['\"]?", cuerpo) or re.search(
                r"\bbranches\s*:\s*\n\s*-\s*['\"]?\*\*?['\"]?\s*$", cuerpo, re.M)
            if todas or "branches-ignore" in cuerpo or not re.search(r"\b(branches|tags)\s*:", cuerpo):
                malos.append(flujo.name)
        if flujo.name not in malos and re.search(r"^\s*on\s*:.*\bcreate\b|^\s{1,4}create\s*:", texto, re.M):
            malos.append(flujo.name)
    return malos


def anotar(raiz, resultado):
    ruta = Path(raiz) / REGISTRO
    try:
        anterior = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    except (OSError, ValueError):
        anterior = {}
    dato = dict(anterior, ultimo_intento=time.time(), resultado=resultado)
    if resultado == "respaldado":
        dato["ultimo_respaldo"] = time.time()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(dato, ensure_ascii=False), encoding="utf-8")


def gitleaks_limpio(raiz):
    """None si gitleaks revisó los commits que no están en GitHub y no encontró nada; si no, el motivo para no subir."""
    rangos = "HEAD --not --remotes"
    for orden in (["gitleaks", "git", "--no-banner", "--redact", f"--log-opts={rangos}", "."],
                  ["gitleaks", "detect", "--no-banner", "--redact", f"--log-opts={rangos}", "--source", "."]):
        try:
            hecho = subprocess.run(orden, cwd=raiz, capture_output=True, text=True, timeout=60, check=False)
        except FileNotFoundError:
            return "gitleaks no está instalado (ver «Puesta en marcha» en .fabrica/nucleo/motor.md)"
        except (OSError, subprocess.TimeoutExpired):
            return "gitleaks no pudo correr"
        if hecho.returncode == 0:
            return None
        if "unknown command" not in (hecho.stderr or "") + (hecho.stdout or ""):
            return "gitleaks encontró un posible secreto en los commits sin subir: revísalo antes de respaldar"
    return "gitleaks no pudo correr"


def guardar(raiz, ahora=None, respaldar=True, revisar=gitleaks_limpio):
    """Guarda y devuelve un mensaje corto de lo que hizo, o None si no hizo nada."""
    raiz = Path(raiz)
    if not (raiz / ".fabrica" / "proyecto.json").is_file() or apagado(raiz) or en_medio_de_algo(raiz):
        return None
    registrados = registrados_cambiados(raiz)
    nuevos, fuera = nuevos_permitidos(raiz)
    if not registrados and not nuevos:
        # Nada que guardar; si hay archivos que quedan fuera, se dice (una vez por sesión, en guardar_todas)
        return ("Quedaron fuera del guardado: " + lista_fuera(fuera)
                if fuera else None)
    rc, rama = git(raiz, "rev-parse", "--abbrev-ref", "HEAD")
    rama = rama.strip()
    if rc != 0 or rama == "HEAD":
        return None
    rc_d, gitdir = git(raiz, "rev-parse", "--git-dir")
    carpeta_git = Path(gitdir.strip()) if Path(gitdir.strip()).is_absolute() else raiz / gitdir.strip()
    if rc_d != 0 or (carpeta_git / "index.lock").exists():
        return None  # otra operación de git está en curso en esta copia
    if git(raiz, "diff", "--cached", "--quiet")[0] != 0:
        return None  # alguien preparó cambios a mano (git add): no se barren en un guardado
    if rama in PRINCIPALES:
        return (f"Guardado automático en pausa: hay cambios sin commit en {rama}, y ahí nunca se hacen commits. "
                "No los toqué: pásalos a una rama de trabajo.")
    sospechosos = [a for a in registrados if SECRETO.search(Path(a).name)]
    registrados = [a for a in registrados if a not in sospechosos]
    fuera += [(a, "está registrado y parece un secreto") for a in sospechosos]
    if not registrados and not nuevos:
        return "Quedaron fuera del guardado: " + lista_fuera(fuera)
    ahora = ahora or datetime.now()
    if registrados:
        git(raiz, "add", "-u", "--", *registrados)
    if nuevos:
        git(raiz, "add", "--", *nuevos)
    rc, salida = git(raiz, "commit", "-q", "-m", f"wip: guardado automático {ahora:%Y-%m-%d %H:%M}")
    if rc != 0:
        git(raiz, "reset", "-q")  # deja todo como estaba: nada preparado a medias
        primera = next((l for l in salida.splitlines() if l.strip()), "sin detalle")
        return f"Guardado automático detenido: el commit falló en {rama} ({primera[:160]})."
    mensaje = f"Guardado en local, en {rama}"
    if fuera:
        mensaje += ". Quedaron fuera: " + lista_fuera(fuera)
    if not respaldar:
        return mensaje
    try:
        registro = json.loads((raiz / REGISTRO).read_text(encoding="utf-8")) if (raiz / REGISTRO).exists() else {}
    except (OSError, ValueError):
        registro = {}
    if time.time() - float(registro.get("ultimo_intento", 0)) < CADA:
        return mensaje
    malos = flujos_sin_filtro(raiz)
    if malos:
        anotar(raiz, f"sin subir: {malos[0]} corre con push a cualquier rama")
        return (mensaje + f". SIN RESPALDO en GitHub: {malos[0]} se activa con push a cualquier rama; agrégale "
                "branches-ignore: ['wip/**'] para no gastar minutos de Actions.")
    motivo = revisar(raiz)
    if motivo:
        anotar(raiz, f"sin subir: {motivo}")
        return mensaje + f". SIN RESPALDO en GitHub: {motivo}."
    destino = f"wip/{rama}"
    if git(raiz, "push", "-q", "--force", "origin", f"HEAD:refs/heads/{destino}", tope=30)[0] != 0:
        anotar(raiz, "sin subir: falló el push")
        return mensaje + ". SIN RESPALDO en GitHub: falló la subida; se reintenta en 30 minutos."
    anotar(raiz, "respaldado")
    return mensaje + f" y respaldado en GitHub, en {destino} (sin PR ni CI)"


def copias_de_trabajo(raiz):
    """Las carpetas de todas las copias de trabajo del repositorio de `raiz`, la de `raiz` incluida."""
    rc, salida = git(raiz, "worktree", "list", "--porcelain")
    copias = [Path(l[len("worktree "):].strip()) for l in salida.splitlines() if l.startswith("worktree ")] if rc == 0 else []
    return [c for c in copias if c.is_dir()] or [Path(raiz)]


ES_AVISO = ("Guardado automático en pausa", "Guardado automático detenido", "SIN RESPALDO", "Quedaron fuera")
PLAZO = 100  # segundos para todas las copias; el hook tiene 120 en settings.json


def guardar_todas(raiz, sesion="", respaldar=True, revisar=gitleaks_limpio):
    """Guarda cada copia de trabajo con cambios y devuelve solo los avisos nuevos de esta sesión (uno por motivo).

    Los commits en local son rápidos y van siempre; el respaldo (gitleaks y push) solo si queda tiempo del plazo, para
    que el hook nunca se corte a mitad de una operación de git.
    """
    avisos, inicio = [], time.monotonic()
    for copia in copias_de_trabajo(raiz):
        queda = PLAZO - (time.monotonic() - inicio)
        mensaje = guardar(copia, respaldar=respaldar and queda > 90, revisar=revisar)
        if mensaje and any(clave in mensaje for clave in ES_AVISO):
            avisos.append(f"{copia.name}: {mensaje}")
    if not avisos:
        return []
    marca = Path(raiz) / ".fabrica" / "trabajo" / "avisos-de-sesion.json"
    try:
        vistos = json.loads(marca.read_text(encoding="utf-8")) if marca.exists() else {}
    except (OSError, ValueError):
        vistos = {}
    ya = set(vistos.get(sesion, [])) if sesion else set()
    nuevos = [a for a in avisos if re.sub(r"\d", "", a) not in ya]
    if sesion:
        vistos = {sesion: sorted(ya | {re.sub(r"\d", "", a) for a in avisos})}  # solo la sesión actual
        marca.parent.mkdir(parents=True, exist_ok=True)
        marca.write_text(json.dumps(vistos, ensure_ascii=False), encoding="utf-8")
    return nuevos


def main():
    try:
        entrada = json.loads(sys.stdin.read() or "{}")
        raiz = Path(os.environ.get("CLAUDE_PROJECT_DIR") or entrada.get("cwd") or ".")
        avisos = guardar_todas(raiz, sesion=str(entrada.get("session_id", "")))
    except Exception:  # noqa: BLE001 — una red de seguridad nunca debe detener el trabajo
        return 0
    if avisos:
        print(json.dumps({"systemMessage": "\n".join(avisos)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
