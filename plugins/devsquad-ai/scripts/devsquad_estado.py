#!/usr/bin/env python3
"""devsquad-estado: estado y tracks de un proyecto DevSquad AI.

Solo biblioteca estándar. Lo usan los hooks, los agentes (con Bash) y la
Factory. Todo el estado vive en `.devsquad/` del proyecto y se versiona en Git.

Códigos de salida: 0 correcto · 1 regla violada o estado inválido (el mensaje
dice el paso que falta) · 2 uso incorrecto de la línea de comandos.
"""
import sys

if sys.version_info < (3, 8):
    sys.stderr.write("devsquad-estado: Python 3.8 or later is required.\n")
    sys.exit(1)

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import tempfile
import unicodedata

SCHEMA_VERSION = 1
DIR_ESTADO = ".devsquad"
ARCHIVO_ESTADO = "estado.json"
DIR_TRACKS = "tracks"

ESTADOS = ("borrador", "listo", "en_progreso", "en_revision", "correcciones",
           "verificado", "cerrado", "bloqueado", "cancelado")
ESTADOS_FINALES = ("cerrado", "cancelado")

# Transiciones permitidas con `transicion`. `cerrado` solo se alcanza con
# `cerrar` y `bloqueado` guarda de dónde viene para `desbloquear`.
TRANSICIONES = {
    "borrador": ("listo",),
    "listo": ("en_progreso",),
    "en_progreso": ("en_revision", "bloqueado"),
    "en_revision": ("correcciones", "verificado", "bloqueado"),
    "correcciones": ("en_revision", "bloqueado"),
    "verificado": ("correcciones",),
    "bloqueado": (),
}

# Se puede cerrar desde estos estados mientras no exista ningún gancho
# (revision.json / verificacion.json). Si existe alguno, el cierre exige el
# estado `verificado`: así las fases B y C endurecen el cierre solas, solo
# con producir sus archivos.
CIERRE_DESDE = ("en_progreso", "en_revision", "verificado")
CIERRE_CON_GANCHOS = "verificado"

# Ganchos de cierre (opcionales): si el archivo existe debe traer "aprobado": true.
GANCHOS_CIERRE = ("revision.json", "verificacion.json")

# Política de cierre de cada track (la propone el Arquitecto en arquitectura.md y la
# aprueba la persona junto con la arquitectura; queda dentro de la huella aprobada):
#   humano      criterios objetivos + aprobación humana «cierre» ligada al commit exacto.
#   automatico  el código cierra con criterios objetivos (tareas con commit, revision.json y
#               verificacion.json aprobados, estado verificado). Exige que exista el
#               agente revisor (fase C): agents/revisor.md.
POLITICAS = ("humano", "automatico")
POLITICA_DEFECTO = "humano"

# Aprobaciones humanas. Solo las fijan código (hooks / la Factory) a partir de una señal
# humana; los agentes no pueden (compuertas del hook). `fuente` dice de dónde vino.
APROBABLES = ("arquitectura", "diseno", "cierre", "comandos")
DOCUMENTOS = {"arquitectura": "arquitectura.md", "diseno": "diseno.md"}
FUENTES = ("terminal", "factory", "manual")
APROBACIONES_PARA_LISTO = ("arquitectura", "diseno")
RAIZ_PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERFIL = os.path.join(DIR_ESTADO, "perfil.md")

# Migraciones de esquema de estado.json: {version_origen: funcion(dict) -> dict}.
# Cada función devuelve el estado ya en la versión origen + 1.
MIGRACIONES = {}

SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
TRACK_ID_RE = re.compile(r"^(\d{3,})-([a-z0-9-]+)$")
TAREA_RE = re.compile(r"^(?P<pre>\s*[-*]\s+)\[(?P<marca>[ ~xX])\]\s+(?P<id>\S+)(?P<resto>.*)$")
COMMIT_RE = re.compile(r"\s*\(commit ([0-9a-fA-F]{7,40})\)\s*$")

PLANTILLA_SPEC = """# {titulo}

## Goal

(Describe the track's goal.)

## Acceptance criteria

- (One verifiable criterion per line.)
"""

PLANTILLA_PLAN = """# Plan · {titulo}

One task per line. States: `[ ]` pending, `[~]` in progress, `[x]` done.
A task is only marked done with the commit that implements it:
`- [x] 1 Task text (commit abc1234)`.
The track does not move to `listo` until this file has at least one task.

## Tasks

"""


class ReglaError(Exception):
    """A workflow rule is not met. The message says what is missing."""


# --------------------------------------------------------------------- E/S

def raiz_proyecto(arg):
    return os.path.abspath(arg or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def ruta_estado(raiz):
    return os.path.join(raiz, DIR_ESTADO, ARCHIVO_ESTADO)


def ruta_track(raiz, track_id):
    return os.path.join(raiz, DIR_ESTADO, DIR_TRACKS, track_id)


def escribir_atomico(ruta, texto):
    carpeta = os.path.dirname(ruta)
    os.makedirs(carpeta, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=carpeta, prefix=".tmp-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
        # mkstemp crea el archivo con permiso solo para su dueño (0600). Estos archivos son el estado del proyecto y se
        # comparten (la persona, la Factory y los agentes pueden ser usuarios distintos): se les da el permiso normal
        # de un archivo de texto, 0666 menos el umask de quien escribe.
        mascara = os.umask(0)
        os.umask(mascara)
        os.chmod(tmp, 0o666 & ~mascara)
        os.replace(tmp, ruta)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def escribir_json(ruta, datos):
    escribir_atomico(ruta, json.dumps(datos, indent=2, ensure_ascii=False) + "\n")


def leer_json(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise ReglaError("%s does not exist." % ruta)
    except ValueError as e:
        raise ReglaError("%s is not valid JSON (%s). Fix it by hand or restore it from Git." % (ruta, e))


def estado_nuevo():
    return {"schema_version": SCHEMA_VERSION, "track_activo": None,
            "contadores": {"stop_bloqueos": 0}, "comandos_aprobados": None}


def cargar_estado(raiz):
    ruta = ruta_estado(raiz)
    if not os.path.exists(ruta):
        raise ReglaError("There is no %s/%s in %s. Next step: run `devsquad-estado init`."
                         % (DIR_ESTADO, ARCHIVO_ESTADO, raiz))
    estado = leer_json(ruta)
    version = estado.get("schema_version") if isinstance(estado, dict) else None
    if not isinstance(version, int):
        raise ReglaError("%s has no integer `schema_version`." % ruta)
    if version > SCHEMA_VERSION:
        raise ReglaError("%s has schema_version %d, newer than this plugin understands (%d). "
                         "Next step: update the DevSquad AI plugin." % (ruta, version, SCHEMA_VERSION))
    if version < SCHEMA_VERSION:
        raise ReglaError("%s has schema_version %d and this plugin uses %d. "
                         "Next step: run `devsquad-estado migrar`." % (ruta, version, SCHEMA_VERSION))
    return estado


def cargar_track(raiz, track_id):
    ruta = os.path.join(ruta_track(raiz, track_id), "track.json")
    if not os.path.exists(ruta):
        raise ReglaError("Track %s does not exist (%s is missing)." % (track_id, ruta))
    track = leer_json(ruta)
    if track.get("schema_version") != SCHEMA_VERSION:
        raise ReglaError("Track %s has schema_version %r and %d was expected. "
                         "Next step: run `devsquad-estado migrar`."
                         % (track_id, track.get("schema_version"), SCHEMA_VERSION))
    return track


def guardar_track(raiz, track):
    escribir_json(os.path.join(ruta_track(raiz, track["id"]), "track.json"), track)


def listar_tracks(raiz):
    base = os.path.join(raiz, DIR_ESTADO, DIR_TRACKS)
    if not os.path.isdir(base):
        return []
    return sorted(d for d in os.listdir(base)
                  if TRACK_ID_RE.match(d) and os.path.isdir(os.path.join(base, d)))


def resolver_track(raiz, estado, pedido):
    track_id = pedido or estado.get("track_activo")
    if not track_id:
        raise ReglaError("There is no active track. Next step: create one with `devsquad-estado crear <slug>`.")
    return track_id


# ------------------------------------------------------------------- plan

def leer_plan(raiz, track_id):
    ruta = os.path.join(ruta_track(raiz, track_id), "plan.md")
    try:
        with open(ruta, encoding="utf-8") as f:
            lineas = f.read().split("\n")
    except FileNotFoundError:
        raise ReglaError("%s is missing." % ruta)
    return ruta, lineas


def tareas_del_plan(lineas):
    """Devuelve [(indice_de_linea, marca, id, tiene_commit)]."""
    tareas = []
    for i, linea in enumerate(lineas):
        m = TAREA_RE.match(linea)
        if m:
            tareas.append((i, m.group("marca").lower(), m.group("id"),
                           bool(COMMIT_RE.search(m.group("resto")))))
    return tareas


def tareas_abiertas(raiz, track_id):
    _, lineas = leer_plan(raiz, track_id)
    tareas = tareas_del_plan(lineas)
    if not tareas:
        raise ReglaError("The plan of track %s has no tasks (lines `- [ ] <id> text`). "
                         "Next step: add them in plan.md." % track_id)
    return [t[2] for t in tareas if t[1] != "x"]


def commit_existe(raiz, sha):
    """True/False; None si no se puede comprobar (sin git o fuera de un repo)."""
    try:
        r = subprocess.run(["git", "-C", raiz, "cat-file", "-e", sha + "^{commit}"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return None
    if r.returncode == 0:
        return True
    dentro = subprocess.run(["git", "-C", raiz, "rev-parse", "--is-inside-work-tree"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return False if dentro.returncode == 0 else None


def versionado_ignorado(raiz):
    """True si Git ignora .devsquad/; None si no se puede comprobar."""
    try:
        r = subprocess.run(["git", "-C", raiz, "check-ignore", "-q", DIR_ESTADO + "/" + ARCHIVO_ESTADO],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return None
    return {0: True, 1: False}.get(r.returncode)


# -------------------------------------------------------------- aprobaciones

def ahora_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sin_acentos(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def sha256_archivo(ruta):
    try:
        with open(ruta, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None


def revisor_disponible():
    """El agente revisor existe en el plugin (fase C). Se deriva de los archivos, no de una bandera."""
    return os.path.exists(os.path.join(RAIZ_PLUGIN, "agents", "revisor.md"))


def politica_en_documento(texto):
    """Política de cierre declarada en arquitectura.md («Política de cierre: humano»); humano si no hay."""
    m = re.search(r"^[\s>*_-]*(?:closing policy|pol[ií]tica de cierre)\s*[*_]*\s*:\s*[*_`]*\s*([A-Za-záéíóúÁÉÍÓÚ]+)",
                  texto or "", re.IGNORECASE | re.MULTILINE)
    if not m:
        return POLITICA_DEFECTO
    return sin_acentos(m.group(1)).lower()


def git_head(raiz):
    """Hash completo de HEAD, o None si no hay Git/commits."""
    try:
        r = subprocess.run(["git", "-C", raiz, "rev-parse", "HEAD"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           universal_newlines=True)
    except OSError:
        return None
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def perfil_texto(raiz):
    try:
        with open(os.path.join(raiz, PERFIL), encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


def comandos_verificacion(texto):
    """[(etiqueta, comando)] de la sección «Comandos de verificación» del perfil."""
    comandos, dentro = [], False
    for linea in (texto or "").split("\n"):
        if re.match(r"^#{1,6}\s", linea):
            dentro = sin_acentos(linea).strip().lower().lstrip("# ").startswith(("verification commands", "comandos de verificacion"))
            continue
        if dentro and re.match(r"^\s*[-*]\s", linea):
            m = re.search(r"`([^`]+)`", linea)
            if m and not m.group(1).startswith("["):
                etiqueta = re.sub(r"^\s*[-*]\s*", "", linea.split(":", 1)[0]).strip() if ":" in linea else "command"
                comandos.append((etiqueta, m.group(1).strip()))
    return comandos


def huella_comandos(comandos):
    return hashlib.sha256("\n".join(c for _, c in comandos).encode("utf-8")).hexdigest()


def estado_aprobacion(raiz, track, objeto, estado=None):
    """('ok' | 'falta' | 'obsoleta', detalle) de una aprobación humana."""
    if objeto == "comandos":
        reg = (estado if estado is not None else cargar_estado(raiz)).get("comandos_aprobados")
        if not reg:
            return "falta", "the profile's verification commands are not approved"
        actual = huella_comandos(comandos_verificacion(perfil_texto(raiz)))
        if reg.get("sha256") != actual:
            return "obsoleta", "the profile's verification commands changed since they were approved"
        return "ok", ""
    reg = (track.get("aprobaciones") or {}).get(objeto)
    if not reg:
        return "falta", "there is no approval for %s" % objeto
    if objeto == "cierre":
        if git_head(raiz) != reg.get("commit"):
            return "obsoleta", "there are new commits since the approval (approved at %s)" % str(reg.get("commit"))[:7]
        return "ok", ""
    if sha256_archivo(os.path.join(raiz, DIR_ESTADO, DOCUMENTOS[objeto])) != reg.get("sha256"):
        return "obsoleta", "%s changed since it was approved" % DOCUMENTOS[objeto]
    return "ok", ""


# Los estados de una aprobación son identificadores ('ok' | 'falta' | 'obsoleta'); esto es solo cómo se muestran.
TEXTO_APROBACION = {"ok": "ok", "falta": "missing", "obsoleta": "stale"}


def txt_aprobacion(estado):
    return TEXTO_APROBACION.get(estado, estado)


def comoaprobar(objeto):
    return ("the person gives it with `/%s:aprobar %s` in the terminal, or with ask_human (kind \"approval\", subject \"%s\") "
            "in the Factory" % (nombre_plugin(), objeto, objeto))


def nombre_plugin():
    try:
        with open(os.path.join(RAIZ_PLUGIN, ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
            return json.load(f)["name"]
    except (OSError, ValueError, KeyError):
        return "devsquad-ai"


def resumen_aprobaciones(raiz, track, estado=None):
    """{objeto: 'ok'|'falta'|'obsoleta'} de todas las aprobaciones."""
    return {o: estado_aprobacion(raiz, track, o, estado)[0] for o in APROBABLES}


def faltan_aprobaciones_para_listo(raiz, track):
    faltas = []
    for o in APROBACIONES_PARA_LISTO:
        estado, detalle = estado_aprobacion(raiz, track, o)
        if estado != "ok":
            faltas.append("%s (%s; %s)" % (o, detalle, comoaprobar(o)))
    return faltas


# ---------------------------------------------------------------- comandos

def cmd_init(a, raiz):
    ruta = ruta_estado(raiz)
    if os.path.exists(ruta):
        cargar_estado(raiz)
        print("%s/%s already exists; nothing was changed." % (DIR_ESTADO, ARCHIVO_ESTADO))
    else:
        escribir_json(ruta, estado_nuevo())
        print("Created %s/%s (schema_version %d)." % (DIR_ESTADO, ARCHIVO_ESTADO, SCHEMA_VERSION))
    if versionado_ignorado(raiz):
        sys.stderr.write("Warning: Git is ignoring .devsquad/. It must be versioned "
                         "(it is the project's memory): remove it from .gitignore.\n")
    return 0


def cmd_crear(a, raiz):
    estado = cargar_estado(raiz)
    if estado.get("track_activo"):
        raise ReglaError("There is an open track: %s. Nothing moves forward until it is closed. "
                         "Next step: `devsquad-estado cerrar`." % estado["track_activo"])
    if not SLUG_RE.match(a.slug):
        raise ReglaError("The slug %r is not valid: use lowercase letters, numbers and hyphens (e.g. authentication)." % a.slug)
    numeros = [int(TRACK_ID_RE.match(t).group(1)) for t in listar_tracks(raiz)]
    track_id = "%03d-%s" % (max(numeros, default=0) + 1, a.slug)
    titulo = a.titulo or a.slug.replace("-", " ").capitalize()
    carpeta = ruta_track(raiz, track_id)
    escribir_atomico(os.path.join(carpeta, "spec.md"), PLANTILLA_SPEC.format(titulo=titulo))
    escribir_atomico(os.path.join(carpeta, "plan.md"), PLANTILLA_PLAN.format(titulo=titulo))
    guardar_track(raiz, {"schema_version": SCHEMA_VERSION, "id": track_id, "titulo": titulo,
                         "estado": "borrador", "estado_previo": None})
    estado["track_activo"] = track_id
    escribir_json(ruta_estado(raiz), estado)
    print("Track %s created (borrador) and active." % track_id)
    return 0


def cmd_transicion(a, raiz):
    estado = cargar_estado(raiz)
    track_id = resolver_track(raiz, estado, a.track)
    track = cargar_track(raiz, track_id)
    actual, nuevo = track["estado"], a.estado
    if nuevo == "cerrado":
        raise ReglaError("A track is not closed with `transicion`. Next step: `devsquad-estado cerrar`.")
    if nuevo == "cancelado":
        raise ReglaError("A track is not cancelled with `transicion`. Next step: `devsquad-estado cancelar --motivo ...`.")
    if nuevo == "bloqueado":
        if actual in ("borrador", "listo") + ESTADOS_FINALES + ("bloqueado",):
            raise ReglaError("Track %s is in %s and cannot be blocked." % (track_id, actual))
    elif nuevo not in TRANSICIONES.get(actual, ()):
        permitidas = ", ".join(TRANSICIONES.get(actual, ())) or "none (use `desbloquear`)"
        raise ReglaError("Transition not allowed: %s → %s. From %s you can go to: %s."
                         % (actual, nuevo, actual, permitidas))
    if nuevo == "listo":
        _, lineas = leer_plan(raiz, track_id)
        if not tareas_del_plan(lineas):
            raise ReglaError("Track %s cannot move to `listo` without tasks in plan.md." % track_id)
        faltas = faltan_aprobaciones_para_listo(raiz, track)
        if faltas:
            raise ReglaError("Track %s cannot move to `listo` without the human approval of architecture and design. "
                             "Missing: %s." % (track_id, "; ".join(faltas)))
    if nuevo == "en_revision":
        abiertas = tareas_abiertas(raiz, track_id)
        if abiertas:
            raise ReglaError("It cannot move to review: tasks still to complete (%s)." % ", ".join(abiertas))
    track["estado_previo"] = actual if nuevo == "bloqueado" else None
    track["estado"] = nuevo
    guardar_track(raiz, track)
    print("Track %s: %s → %s." % (track_id, actual, nuevo))
    return 0


def cmd_desbloquear(a, raiz):
    estado = cargar_estado(raiz)
    track_id = resolver_track(raiz, estado, a.track)
    track = cargar_track(raiz, track_id)
    if track["estado"] != "bloqueado":
        raise ReglaError("Track %s is not blocked (it is in %s)." % (track_id, track["estado"]))
    destino = track.get("estado_previo") or "en_progreso"
    track["estado"], track["estado_previo"] = destino, None
    guardar_track(raiz, track)
    print("Track %s unblocked: back to %s." % (track_id, destino))
    return 0


def cmd_tarea(a, raiz):
    estado = cargar_estado(raiz)
    track_id = resolver_track(raiz, estado, a.track)
    ruta, lineas = leer_plan(raiz, track_id)
    for i, _, tid, _ in tareas_del_plan(lineas):
        if tid == a.id:
            indice = i
            break
    else:
        raise ReglaError("Task %r does not exist in the plan of track %s." % (a.id, track_id))
    m = TAREA_RE.match(lineas[indice])
    resto = COMMIT_RE.sub("", m.group("resto"))
    marca = {"pendiente": " ", "en_curso": "~", "hecha": "x"}[a.estado]
    if a.estado == "hecha":
        if not a.commit:
            raise ReglaError("A task is only marked done with the commit that implements it. "
                             "Next step: repeat with `--commit <sha>`.")
        if not re.match(r"^[0-9a-fA-F]{7,40}$", a.commit):
            raise ReglaError("The commit %r does not look like a hash (7 to 40 hexadecimal characters)." % a.commit)
        if commit_existe(raiz, a.commit) is False:
            raise ReglaError("Commit %s does not exist in this repository." % a.commit)
        resto += " (commit %s)" % a.commit
    elif a.commit:
        raise ReglaError("`--commit` is only used when marking the task as done.")
    lineas[indice] = "%s[%s] %s%s" % (m.group("pre"), marca, a.id, resto)
    escribir_atomico(ruta, "\n".join(lineas))
    print("Task %s of track %s: %s." % (a.id, track_id, a.estado))
    return 0


def comprobar_ganchos(raiz, track):
    track_id = track["id"]
    presentes = [n for n in GANCHOS_CIERRE if os.path.exists(os.path.join(ruta_track(raiz, track_id), n))]
    if presentes and track["estado"] != CIERRE_CON_GANCHOS:
        raise ReglaError("Track %s has %s, so it can only be closed from state %s (it is in %s). "
                         "Next step: complete the review and the verification."
                         % (track_id, " y ".join(presentes), CIERRE_CON_GANCHOS, track["estado"]))
    for nombre in presentes:
        ruta = os.path.join(ruta_track(raiz, track_id), nombre)
        datos = leer_json(ruta)
        if not isinstance(datos, dict) or datos.get("aprobado") is not True:
            raise ReglaError("The closing is blocked: %s does not carry \"aprobado\": true. "
                             "Next step: fix the findings and repeat the review or verification." % nombre)


def verificar_criterios_objetivos(raiz, track):
    """Criteria the code checks to close a track. Raises ReglaError with the first that fails."""
    track_id = track["id"]
    if track["estado"] not in CIERRE_DESDE:
        raise ReglaError("Track %s is in %s and cannot be closed. It is closed from: %s."
                         % (track_id, track["estado"], ", ".join(CIERRE_DESDE)))
    abiertas = tareas_abiertas(raiz, track_id)
    if abiertas:
        raise ReglaError("Track %s cannot be closed: tasks still to complete (%s)."
                         % (track_id, ", ".join(abiertas)))
    _, lineas = leer_plan(raiz, track_id)
    sin_commit = [t[2] for t in tareas_del_plan(lineas) if not t[3]]
    if sin_commit:
        raise ReglaError("There are tasks done without a recorded commit (%s). Next step: `devsquad-estado tarea <id> hecha --commit <sha>`."
                         % ", ".join(sin_commit))
    comprobar_ganchos(raiz, track)


def politica_de(track):
    return track.get("politica_cierre") or POLITICA_DEFECTO


def verificar_politica_de_cierre(raiz, track):
    """Parte de la política: aprobación humana ligada al commit (humano) o revisor + ganchos (automatico)."""
    track_id, politica = track["id"], politica_de(track)
    if politica == "automatico":
        if not revisor_disponible():
            raise ReglaError("Track %s has closing policy `automatico`, which requires the reviewer agent (phase C) and "
                             "it does not exist yet. Next step: use `humano`." % track_id)
        for n in GANCHOS_CIERRE:
            if not os.path.exists(os.path.join(ruta_track(raiz, track_id), n)):
                raise ReglaError("Policy `automatico`: %s is missing in track %s." % (n, track_id))
        if track["estado"] != CIERRE_CON_GANCHOS:
            raise ReglaError("Policy `automatico`: track %s must be in %s (it is in %s)."
                             % (track_id, CIERRE_CON_GANCHOS, track["estado"]))
        return
    estado, detalle = estado_aprobacion(raiz, track, "cierre")
    if estado != "ok":
        raise ReglaError("Track %s meets the objective criteria but has closing policy `humano` and the closing approval "
                         "is %s (%s). Next step: %s." % (track_id, txt_aprobacion(estado), detalle, comoaprobar("cierre")))


def motivo_no_cerrable(raiz, track):
    """None if the track can be closed now; otherwise the reason (text)."""
    try:
        verificar_criterios_objetivos(raiz, track)
        verificar_politica_de_cierre(raiz, track)
    except ReglaError as e:
        return str(e)
    return None


def cumple_criterios_objetivos(raiz, track):
    try:
        verificar_criterios_objetivos(raiz, track)
    except ReglaError:
        return False
    return True


def cmd_cerrar(a, raiz):
    estado = cargar_estado(raiz)
    track_id = resolver_track(raiz, estado, a.track)
    track = cargar_track(raiz, track_id)
    verificar_criterios_objetivos(raiz, track)
    verificar_politica_de_cierre(raiz, track)
    track["estado"], track["estado_previo"] = "cerrado", None
    guardar_track(raiz, track)
    if estado.get("track_activo") == track_id:
        estado["track_activo"] = None
    estado.setdefault("contadores", {})["stop_bloqueos"] = 0
    escribir_json(ruta_estado(raiz), estado)
    print("Track %s closed." % track_id)
    return 0


def cmd_aprobar(a, raiz):
    """Registra una aprobación humana. Lo invocan los hooks (señal humana) o la Factory; no los agentes."""
    estado = cargar_estado(raiz)
    registro = {"fuente": a.fuente, "por": a.por or "person", "fecha": ahora_utc()}
    if a.objeto == "comandos":
        comandos = comandos_verificacion(perfil_texto(raiz))
        if not comandos:
            raise ReglaError("The profile declares no verification commands (\"Verification commands\" section); there is nothing to approve.")
        registro.update({"sha256": huella_comandos(comandos), "comandos": [c for _, c in comandos]})
        estado["comandos_aprobados"] = registro
        escribir_json(ruta_estado(raiz), estado)
        print("Approved the profile's verification commands: %s." % "; ".join(c for _, c in comandos))
        return 0
    track_id = resolver_track(raiz, estado, a.track)
    track = cargar_track(raiz, track_id)
    if track["estado"] in ESTADOS_FINALES:
        raise ReglaError("Track %s is %s; it does not accept approvals." % (track_id, track["estado"]))
    aviso = ""
    if a.objeto in DOCUMENTOS:
        ruta_doc = os.path.join(raiz, DIR_ESTADO, DOCUMENTOS[a.objeto])
        huella = sha256_archivo(ruta_doc)
        if huella is None:
            raise ReglaError("%s/%s does not exist: there is nothing to approve yet." % (DIR_ESTADO, DOCUMENTOS[a.objeto]))
        registro["sha256"] = huella
        if a.objeto == "arquitectura":
            with open(ruta_doc, encoding="utf-8") as f:
                politica = politica_en_documento(f.read())
            if politica not in POLITICAS:
                raise ReglaError("The closing policy %r in arquitectura.md is not valid (use: %s)." % (politica, ", ".join(POLITICAS)))
            if politica == "automatico" and not revisor_disponible():
                raise ReglaError("The closing policy `automatico` requires the reviewer agent (phase C) and it does not exist yet. "
                                 "Next step: the Architect must declare `Closing policy: humano` in arquitectura.md.")
            anterior = track.get("politica_cierre")
            if anterior and anterior != politica:
                aviso = " ATTENTION: the closing policy changed from `%s` to `%s`." % (anterior, politica)
            registro["politica_cierre"] = politica
            track["politica_cierre"] = politica
    else:  # cierre
        if politica_de(track) != "humano":
            raise ReglaError("Track %s has policy `%s`: the closing approval only applies to `humano`." % (track_id, politica_de(track)))
        verificar_criterios_objetivos(raiz, track)
        head = git_head(raiz)
        if not head:
            raise ReglaError("The closing approval is tied to the exact commit and there is no Git repository with commits in %s." % raiz)
        registro["commit"] = head
    track.setdefault("aprobaciones", {})[a.objeto] = registro
    guardar_track(raiz, track)
    print("Approval of %s recorded for track %s (source: %s, by: %s).%s"
          % (a.objeto, track_id, registro["fuente"], registro["por"], aviso))
    return 0


def cmd_cancelar(a, raiz):
    """Cancels an open track: requires a reason, frees the single slot and keeps the history."""
    motivo = " ".join((a.motivo or "").split())
    if len(motivo) < 3:
        raise ReglaError("Cancelling requires a reason (--motivo \"...\").")
    estado = cargar_estado(raiz)
    track_id = resolver_track(raiz, estado, a.track)
    track = cargar_track(raiz, track_id)
    if track["estado"] in ESTADOS_FINALES:
        raise ReglaError("Track %s is already %s." % (track_id, track["estado"]))
    track["cancelacion"] = {"motivo": motivo, "estado_previo": track["estado"], "fuente": a.fuente,
                            "por": a.por or "person", "fecha": ahora_utc()}
    track["estado"], track["estado_previo"] = "cancelado", None
    guardar_track(raiz, track)
    if estado.get("track_activo") == track_id:
        estado["track_activo"] = None
    estado.setdefault("contadores", {})["stop_bloqueos"] = 0
    escribir_json(ruta_estado(raiz), estado)
    print("Track %s cancelled (reason: %s). Its folder is kept as history." % (track_id, motivo))
    return 0


def resumen(raiz):
    estado = cargar_estado(raiz)
    datos = {"schema_version": estado["schema_version"], "track_activo": None, "tracks_cerrados": 0,
             "tracks_cancelados": 0}
    for t in listar_tracks(raiz):
        track = cargar_track(raiz, t)
        if track["estado"] == "cerrado":
            datos["tracks_cerrados"] += 1
        if track["estado"] == "cancelado":
            datos["tracks_cancelados"] += 1
        if t == estado.get("track_activo"):
            _, lineas = leer_plan(raiz, t)
            tareas = tareas_del_plan(lineas)
            datos["track_activo"] = {
                "id": t, "titulo": track["titulo"], "estado": track["estado"],
                "tareas_total": len(tareas),
                "tareas_hechas": sum(1 for x in tareas if x[1] == "x"),
                "siguiente_tarea": next((x[2] for x in tareas if x[1] != "x"), None)}
    return datos


def cmd_estado(a, raiz):
    datos = resumen(raiz)
    if a.json:
        print(json.dumps(datos, indent=2, ensure_ascii=False))
        return 0
    t = datos["track_activo"]
    if t:
        print("Active track: %s (%s) · tasks %d/%d · next: %s"
              % (t["id"], t["estado"], t["tareas_hechas"], t["tareas_total"], t["siguiente_tarea"] or "—"))
    else:
        print("No active track.")
    print("Closed tracks: %d · schema_version %d" % (datos["tracks_cerrados"], datos["schema_version"]))
    return 0


def cmd_validar(a, raiz):
    problemas = []
    estado = cargar_estado(raiz)
    activo = estado.get("track_activo")
    abiertos = []
    for t in listar_tracks(raiz):
        try:
            track = cargar_track(raiz, t)
            if track.get("id") != t:
                problemas.append("%s: the `id` in track.json (%r) does not match the folder." % (t, track.get("id")))
            if track.get("estado") not in ESTADOS:
                problemas.append("%s: unknown state %r." % (t, track.get("estado")))
            if track.get("estado") not in ESTADOS_FINALES:
                abiertos.append(t)
            if track.get("estado") in ("listo", "en_progreso", "en_revision", "correcciones", "verificado"):
                for o, (st, det) in ((o, estado_aprobacion(raiz, track, o, estado)) for o in APROBACIONES_PARA_LISTO):
                    if st != "ok":
                        problemas.append("%s: approval of %s %s (%s)." % (t, o, txt_aprobacion(st), det))
            if track.get("politica_cierre") not in (None,) + POLITICAS:
                problemas.append("%s: unknown closing policy %r." % (t, track.get("politica_cierre")))
            if track.get("politica_cierre") == "automatico" and not revisor_disponible():
                problemas.append("%s: policy `automatico` without a reviewer agent (phase C)." % t)
            _, lineas = leer_plan(raiz, t)
            for _, marca, tid, con_commit in tareas_del_plan(lineas):
                if marca == "x" and not con_commit:
                    problemas.append("%s: task %s is done without a recorded commit." % (t, tid))
        except ReglaError as e:
            problemas.append("%s: %s" % (t, e))
    if len(abiertos) > 1:
        problemas.append("There are %d open tracks (%s) and only one is allowed." % (len(abiertos), ", ".join(abiertos)))
    if activo and activo not in abiertos:
        problemas.append("track_activo points to %s, which does not exist or is already closed or cancelled." % activo)
    if not activo and abiertos:
        problemas.append("There is an open track (%s) but estado.json does not mark it as active." % abiertos[0])
    if versionado_ignorado(raiz):
        sys.stderr.write("Warning: Git is ignoring .devsquad/ and it must be versioned.\n")
    if problemas:
        for p in problemas:
            sys.stderr.write("- %s\n" % p)
        raise ReglaError("The project state is not valid (%d problem(s))." % len(problemas))
    print("State is valid.")
    return 0


def cmd_migrar(a, raiz):
    ruta = ruta_estado(raiz)
    estado = leer_json(ruta)
    version = estado.get("schema_version")
    if not isinstance(version, int):
        raise ReglaError("%s has no integer `schema_version`." % ruta)
    if version > SCHEMA_VERSION:
        raise ReglaError("The state is from a newer version (%d) than this plugin (%d). Update the plugin." % (version, SCHEMA_VERSION))
    if version == SCHEMA_VERSION:
        print("The state is already at version %d." % SCHEMA_VERSION)
        return 0
    while version < SCHEMA_VERSION:
        if version not in MIGRACIONES:
            raise ReglaError("There is no migration from schema_version %d." % version)
        estado = MIGRACIONES[version](estado)
        version += 1
        estado["schema_version"] = version
    escribir_json(ruta, estado)
    print("State migrated to version %d." % SCHEMA_VERSION)
    return 0


def construir_parser():
    p = argparse.ArgumentParser(prog="devsquad-estado", description="DevSquad AI state and tracks.")
    p.add_argument("--raiz", help="Project root (default $CLAUDE_PROJECT_DIR or the current directory).")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="Creates .devsquad/estado.json.").set_defaults(f=cmd_init)
    c = sub.add_parser("crear", help="Creates a new track (only if none is open).")
    c.add_argument("slug")
    c.add_argument("--titulo")
    c.set_defaults(f=cmd_crear)
    t = sub.add_parser("transicion", help="Changes a track's state.")
    t.add_argument("estado", choices=[e for e in ESTADOS if e not in ESTADOS_FINALES])
    t.add_argument("--track")
    t.set_defaults(f=cmd_transicion)
    d = sub.add_parser("desbloquear", help="Returns a blocked track to its previous state.")
    d.add_argument("--track")
    d.set_defaults(f=cmd_desbloquear)
    k = sub.add_parser("tarea", help="Changes the state of a plan task.")
    k.add_argument("id")
    k.add_argument("estado", choices=("pendiente", "en_curso", "hecha"))
    k.add_argument("--commit")
    k.add_argument("--track")
    k.set_defaults(f=cmd_tarea)
    z = sub.add_parser("cerrar", help="Closes the track if its tasks are complete.")
    z.add_argument("--track")
    z.set_defaults(f=cmd_cerrar)
    ap = sub.add_parser("aprobar", help="Records a human approval (invoked by the hooks or the Factory, not by the agents).")
    ap.add_argument("objeto", choices=APROBABLES)
    ap.add_argument("--fuente", choices=FUENTES, default="manual")
    ap.add_argument("--por")
    ap.add_argument("--track")
    ap.set_defaults(f=cmd_aprobar)
    cn = sub.add_parser("cancelar", help="Cancels an open track, with a reason (the person's decision).")
    cn.add_argument("--motivo", required=True)
    cn.add_argument("--fuente", choices=FUENTES, default="manual")
    cn.add_argument("--por")
    cn.add_argument("--track")
    cn.set_defaults(f=cmd_cancelar)
    e = sub.add_parser("estado", help="State summary.")
    e.add_argument("--json", action="store_true")
    e.set_defaults(f=cmd_estado)
    sub.add_parser("validar", help="Checks the consistency of .devsquad/.").set_defaults(f=cmd_validar)
    sub.add_parser("migrar", help="Updates estado.json to the current schema.").set_defaults(f=cmd_migrar)
    return p


def main(argv=None):
    args = construir_parser().parse_args(argv)
    try:
        return args.f(args, raiz_proyecto(args.raiz))
    except ReglaError as e:
        sys.stderr.write("devsquad-estado: %s\n" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
