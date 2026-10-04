#!/usr/bin/env python3
"""devsquad-estado: estado y tracks de un proyecto DevSquad AI.

Solo biblioteca estándar. Lo usan los hooks, los agentes (con Bash) y la
Factory. Todo el estado vive en `.devsquad/` del proyecto y se versiona en Git.

Códigos de salida: 0 correcto · 1 regla violada o estado inválido (el mensaje
dice el paso que falta) · 2 uso incorrecto de la línea de comandos.
"""
import sys

if sys.version_info < (3, 8):
    sys.stderr.write("devsquad-estado: se requiere Python 3.8 o superior.\n")
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

## Qué se quiere lograr

(Describe el objetivo del track.)

## Criterios de aceptación

- (Un criterio verificable por línea.)
"""

PLANTILLA_PLAN = """# Plan · {titulo}

Una tarea por línea. Estados: `[ ]` pendiente, `[~]` en curso, `[x]` hecha.
Una tarea solo se marca hecha con el commit que la implementa:
`- [x] 1 Texto de la tarea (commit abc1234)`.
El track no pasa a `listo` hasta que este archivo tenga al menos una tarea.

## Tareas

"""


class ReglaError(Exception):
    """Una regla del flujo no se cumple. El mensaje dice qué falta."""


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
        raise ReglaError("No existe %s." % ruta)
    except ValueError as e:
        raise ReglaError("%s no es JSON válido (%s). Corrígelo a mano o restáuralo desde Git." % (ruta, e))


def estado_nuevo():
    return {"schema_version": SCHEMA_VERSION, "track_activo": None,
            "contadores": {"stop_bloqueos": 0}, "comandos_aprobados": None}


def cargar_estado(raiz):
    ruta = ruta_estado(raiz)
    if not os.path.exists(ruta):
        raise ReglaError("No hay %s/%s en %s. Siguiente paso: ejecuta `devsquad-estado init`."
                         % (DIR_ESTADO, ARCHIVO_ESTADO, raiz))
    estado = leer_json(ruta)
    version = estado.get("schema_version") if isinstance(estado, dict) else None
    if not isinstance(version, int):
        raise ReglaError("%s no tiene un `schema_version` entero." % ruta)
    if version > SCHEMA_VERSION:
        raise ReglaError("%s tiene schema_version %d, más nuevo que el que entiende este plugin (%d). "
                         "Siguiente paso: actualiza el plugin DevSquad AI." % (ruta, version, SCHEMA_VERSION))
    if version < SCHEMA_VERSION:
        raise ReglaError("%s tiene schema_version %d y este plugin usa %d. "
                         "Siguiente paso: ejecuta `devsquad-estado migrar`." % (ruta, version, SCHEMA_VERSION))
    return estado


def cargar_track(raiz, track_id):
    ruta = os.path.join(ruta_track(raiz, track_id), "track.json")
    if not os.path.exists(ruta):
        raise ReglaError("No existe el track %s (falta %s)." % (track_id, ruta))
    track = leer_json(ruta)
    if track.get("schema_version") != SCHEMA_VERSION:
        raise ReglaError("El track %s tiene schema_version %r y se esperaba %d. "
                         "Siguiente paso: ejecuta `devsquad-estado migrar`."
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
        raise ReglaError("No hay track activo. Siguiente paso: crea uno con `devsquad-estado crear <slug>`.")
    return track_id


# ------------------------------------------------------------------- plan

def leer_plan(raiz, track_id):
    ruta = os.path.join(ruta_track(raiz, track_id), "plan.md")
    try:
        with open(ruta, encoding="utf-8") as f:
            lineas = f.read().split("\n")
    except FileNotFoundError:
        raise ReglaError("Falta %s." % ruta)
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
        raise ReglaError("El plan del track %s no tiene tareas (líneas `- [ ] <id> texto`). "
                         "Siguiente paso: agrégalas en plan.md." % track_id)
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
    m = re.search(r"^[\s>*_-]*pol[ií]tica de cierre\s*[*_]*\s*:\s*[*_`]*\s*([A-Za-záéíóúÁÉÍÓÚ]+)",
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
            dentro = sin_acentos(linea).strip().lower().lstrip("# ").startswith("comandos de verificacion")
            continue
        if dentro and re.match(r"^\s*[-*]\s", linea):
            m = re.search(r"`([^`]+)`", linea)
            if m and not m.group(1).startswith("["):
                etiqueta = re.sub(r"^\s*[-*]\s*", "", linea.split(":", 1)[0]).strip() if ":" in linea else "comando"
                comandos.append((etiqueta, m.group(1).strip()))
    return comandos


def huella_comandos(comandos):
    return hashlib.sha256("\n".join(c for _, c in comandos).encode("utf-8")).hexdigest()


def estado_aprobacion(raiz, track, objeto, estado=None):
    """('ok' | 'falta' | 'obsoleta', detalle) de una aprobación humana."""
    if objeto == "comandos":
        reg = (estado if estado is not None else cargar_estado(raiz)).get("comandos_aprobados")
        if not reg:
            return "falta", "los comandos de verificación del perfil no están aprobados"
        actual = huella_comandos(comandos_verificacion(perfil_texto(raiz)))
        if reg.get("sha256") != actual:
            return "obsoleta", "los comandos de verificación del perfil cambiaron desde que se aprobaron"
        return "ok", ""
    reg = (track.get("aprobaciones") or {}).get(objeto)
    if not reg:
        return "falta", "no hay aprobación de %s" % objeto
    if objeto == "cierre":
        if git_head(raiz) != reg.get("commit"):
            return "obsoleta", "hay commits nuevos desde la aprobación (aprobado en %s)" % str(reg.get("commit"))[:7]
        return "ok", ""
    if sha256_archivo(os.path.join(raiz, DIR_ESTADO, DOCUMENTOS[objeto])) != reg.get("sha256"):
        return "obsoleta", "%s cambió desde que se aprobó" % DOCUMENTOS[objeto]
    return "ok", ""


def comoaprobar(objeto):
    return ("la persona la da con `/%s:aprobar %s` en la terminal, o con ask_human (kind \"approval\", subject \"%s\") "
            "en la Factory" % (nombre_plugin(), objeto, objeto))


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
        print("Ya existe %s/%s; no se modificó nada." % (DIR_ESTADO, ARCHIVO_ESTADO))
    else:
        escribir_json(ruta, estado_nuevo())
        print("Creado %s/%s (schema_version %d)." % (DIR_ESTADO, ARCHIVO_ESTADO, SCHEMA_VERSION))
    if versionado_ignorado(raiz):
        sys.stderr.write("Advertencia: Git está ignorando .devsquad/. Debe versionarse "
                         "(es la memoria del proyecto): quítalo de .gitignore.\n")
    return 0


def cmd_crear(a, raiz):
    estado = cargar_estado(raiz)
    if estado.get("track_activo"):
        raise ReglaError("Hay un track abierto: %s. No se avanza hasta cerrarlo. "
                         "Siguiente paso: `devsquad-estado cerrar`." % estado["track_activo"])
    if not SLUG_RE.match(a.slug):
        raise ReglaError("El slug %r no es válido: usa minúsculas, números y guiones (ej. autenticacion)." % a.slug)
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
    print("Track %s creado (borrador) y activo." % track_id)
    return 0


def cmd_transicion(a, raiz):
    estado = cargar_estado(raiz)
    track_id = resolver_track(raiz, estado, a.track)
    track = cargar_track(raiz, track_id)
    actual, nuevo = track["estado"], a.estado
    if nuevo == "cerrado":
        raise ReglaError("Un track no se cierra con `transicion`. Siguiente paso: `devsquad-estado cerrar`.")
    if nuevo == "cancelado":
        raise ReglaError("Un track no se cancela con `transicion`. Siguiente paso: `devsquad-estado cancelar --motivo ...`.")
    if nuevo == "bloqueado":
        if actual in ("borrador", "listo") + ESTADOS_FINALES + ("bloqueado",):
            raise ReglaError("El track %s está en %s y no puede bloquearse." % (track_id, actual))
    elif nuevo not in TRANSICIONES.get(actual, ()):
        permitidas = ", ".join(TRANSICIONES.get(actual, ())) or "ninguna (usa `desbloquear`)"
        raise ReglaError("Transición no permitida: %s → %s. Desde %s se puede ir a: %s."
                         % (actual, nuevo, actual, permitidas))
    if nuevo == "listo":
        _, lineas = leer_plan(raiz, track_id)
        if not tareas_del_plan(lineas):
            raise ReglaError("El track %s no puede pasar a `listo` sin tareas en plan.md." % track_id)
        faltas = faltan_aprobaciones_para_listo(raiz, track)
        if faltas:
            raise ReglaError("El track %s no puede pasar a `listo` sin la aprobación humana de arquitectura y diseño. "
                             "Falta: %s." % (track_id, "; ".join(faltas)))
    if nuevo == "en_revision":
        abiertas = tareas_abiertas(raiz, track_id)
        if abiertas:
            raise ReglaError("No se puede pasar a revisión: faltan tareas por completar (%s)." % ", ".join(abiertas))
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
        raise ReglaError("El track %s no está bloqueado (está en %s)." % (track_id, track["estado"]))
    destino = track.get("estado_previo") or "en_progreso"
    track["estado"], track["estado_previo"] = destino, None
    guardar_track(raiz, track)
    print("Track %s desbloqueado: vuelve a %s." % (track_id, destino))
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
        raise ReglaError("La tarea %r no existe en el plan del track %s." % (a.id, track_id))
    m = TAREA_RE.match(lineas[indice])
    resto = COMMIT_RE.sub("", m.group("resto"))
    marca = {"pendiente": " ", "en_curso": "~", "hecha": "x"}[a.estado]
    if a.estado == "hecha":
        if not a.commit:
            raise ReglaError("Una tarea solo se marca hecha con el commit que la implementa. "
                             "Siguiente paso: repite con `--commit <sha>`.")
        if not re.match(r"^[0-9a-fA-F]{7,40}$", a.commit):
            raise ReglaError("El commit %r no parece un hash (7 a 40 caracteres hexadecimales)." % a.commit)
        if commit_existe(raiz, a.commit) is False:
            raise ReglaError("El commit %s no existe en este repositorio." % a.commit)
        resto += " (commit %s)" % a.commit
    elif a.commit:
        raise ReglaError("`--commit` solo se usa al marcar la tarea como hecha.")
    lineas[indice] = "%s[%s] %s%s" % (m.group("pre"), marca, a.id, resto)
    escribir_atomico(ruta, "\n".join(lineas))
    print("Tarea %s del track %s: %s." % (a.id, track_id, a.estado))
    return 0


def comprobar_ganchos(raiz, track):
    track_id = track["id"]
    presentes = [n for n in GANCHOS_CIERRE if os.path.exists(os.path.join(ruta_track(raiz, track_id), n))]
    if presentes and track["estado"] != CIERRE_CON_GANCHOS:
        raise ReglaError("El track %s tiene %s, así que solo se cierra desde el estado %s (está en %s). "
                         "Siguiente paso: completa la revisión y la verificación."
                         % (track_id, " y ".join(presentes), CIERRE_CON_GANCHOS, track["estado"]))
    for nombre in presentes:
        ruta = os.path.join(ruta_track(raiz, track_id), nombre)
        datos = leer_json(ruta)
        if not isinstance(datos, dict) or datos.get("aprobado") is not True:
            raise ReglaError("El cierre está bloqueado: %s no trae \"aprobado\": true. "
                             "Siguiente paso: corrige los hallazgos y repite la revisión o verificación." % nombre)


def verificar_criterios_objetivos(raiz, track):
    """Criterios que comprueba el código para cerrar un track. Lanza ReglaError con el primero que falle."""
    track_id = track["id"]
    if track["estado"] not in CIERRE_DESDE:
        raise ReglaError("El track %s está en %s y no puede cerrarse. Se cierra desde: %s."
                         % (track_id, track["estado"], ", ".join(CIERRE_DESDE)))
    abiertas = tareas_abiertas(raiz, track_id)
    if abiertas:
        raise ReglaError("El track %s no puede cerrarse: faltan tareas por completar (%s)."
                         % (track_id, ", ".join(abiertas)))
    _, lineas = leer_plan(raiz, track_id)
    sin_commit = [t[2] for t in tareas_del_plan(lineas) if not t[3]]
    if sin_commit:
        raise ReglaError("Hay tareas hechas sin commit registrado (%s). Siguiente paso: `devsquad-estado tarea <id> hecha --commit <sha>`."
                         % ", ".join(sin_commit))
    comprobar_ganchos(raiz, track)


def politica_de(track):
    return track.get("politica_cierre") or POLITICA_DEFECTO


def verificar_politica_de_cierre(raiz, track):
    """Parte de la política: aprobación humana ligada al commit (humano) o revisor + ganchos (automatico)."""
    track_id, politica = track["id"], politica_de(track)
    if politica == "automatico":
        if not revisor_disponible():
            raise ReglaError("El track %s tiene política de cierre `automatico`, que exige el agente revisor (fase C) y "
                             "todavía no existe. Siguiente paso: usa `humano`." % track_id)
        for n in GANCHOS_CIERRE:
            if not os.path.exists(os.path.join(ruta_track(raiz, track_id), n)):
                raise ReglaError("Política `automatico`: falta %s en el track %s." % (n, track_id))
        if track["estado"] != CIERRE_CON_GANCHOS:
            raise ReglaError("Política `automatico`: el track %s debe estar en %s (está en %s)."
                             % (track_id, CIERRE_CON_GANCHOS, track["estado"]))
        return
    estado, detalle = estado_aprobacion(raiz, track, "cierre")
    if estado != "ok":
        raise ReglaError("El track %s cumple los criterios objetivos pero tiene política de cierre `humano` y la aprobación de "
                         "cierre está %s (%s). Siguiente paso: %s." % (track_id, estado, detalle, comoaprobar("cierre")))


def motivo_no_cerrable(raiz, track):
    """None si el track puede cerrarse ya; si no, el motivo (texto)."""
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
    print("Track %s cerrado." % track_id)
    return 0


def cmd_aprobar(a, raiz):
    """Registra una aprobación humana. Lo invocan los hooks (señal humana) o la Factory; no los agentes."""
    estado = cargar_estado(raiz)
    registro = {"fuente": a.fuente, "por": a.por or "persona", "fecha": ahora_utc()}
    if a.objeto == "comandos":
        comandos = comandos_verificacion(perfil_texto(raiz))
        if not comandos:
            raise ReglaError("El perfil no declara comandos de verificación (sección «Comandos de verificación»); no hay nada que aprobar.")
        registro.update({"sha256": huella_comandos(comandos), "comandos": [c for _, c in comandos]})
        estado["comandos_aprobados"] = registro
        escribir_json(ruta_estado(raiz), estado)
        print("Aprobados los comandos de verificación del perfil: %s." % "; ".join(c for _, c in comandos))
        return 0
    track_id = resolver_track(raiz, estado, a.track)
    track = cargar_track(raiz, track_id)
    if track["estado"] in ESTADOS_FINALES:
        raise ReglaError("El track %s está %s; no admite aprobaciones." % (track_id, track["estado"]))
    aviso = ""
    if a.objeto in DOCUMENTOS:
        ruta_doc = os.path.join(raiz, DIR_ESTADO, DOCUMENTOS[a.objeto])
        huella = sha256_archivo(ruta_doc)
        if huella is None:
            raise ReglaError("No existe %s/%s: no hay nada que aprobar todavía." % (DIR_ESTADO, DOCUMENTOS[a.objeto]))
        registro["sha256"] = huella
        if a.objeto == "arquitectura":
            with open(ruta_doc, encoding="utf-8") as f:
                politica = politica_en_documento(f.read())
            if politica not in POLITICAS:
                raise ReglaError("La política de cierre %r de arquitectura.md no es válida (usa: %s)." % (politica, ", ".join(POLITICAS)))
            if politica == "automatico" and not revisor_disponible():
                raise ReglaError("La política de cierre `automatico` exige el agente revisor (fase C) y todavía no existe. "
                                 "Siguiente paso: el Arquitecto debe declarar `Política de cierre: humano` en arquitectura.md.")
            anterior = track.get("politica_cierre")
            if anterior and anterior != politica:
                aviso = " ATENCIÓN: la política de cierre cambió de `%s` a `%s`." % (anterior, politica)
            registro["politica_cierre"] = politica
            track["politica_cierre"] = politica
    else:  # cierre
        if politica_de(track) != "humano":
            raise ReglaError("El track %s tiene política `%s`: la aprobación de cierre solo aplica a `humano`." % (track_id, politica_de(track)))
        verificar_criterios_objetivos(raiz, track)
        head = git_head(raiz)
        if not head:
            raise ReglaError("La aprobación de cierre se liga al commit exacto y no hay un repositorio Git con commits en %s." % raiz)
        registro["commit"] = head
    track.setdefault("aprobaciones", {})[a.objeto] = registro
    guardar_track(raiz, track)
    print("Aprobación de %s registrada para el track %s (fuente: %s, por: %s).%s"
          % (a.objeto, track_id, registro["fuente"], registro["por"], aviso))
    return 0


def cmd_cancelar(a, raiz):
    """Cancela un track abierto: pide motivo, libera el lugar único y conserva el historial."""
    motivo = " ".join((a.motivo or "").split())
    if len(motivo) < 3:
        raise ReglaError("Cancelar exige un motivo (--motivo \"...\").")
    estado = cargar_estado(raiz)
    track_id = resolver_track(raiz, estado, a.track)
    track = cargar_track(raiz, track_id)
    if track["estado"] in ESTADOS_FINALES:
        raise ReglaError("El track %s ya está %s." % (track_id, track["estado"]))
    track["cancelacion"] = {"motivo": motivo, "estado_previo": track["estado"], "fuente": a.fuente,
                            "por": a.por or "persona", "fecha": ahora_utc()}
    track["estado"], track["estado_previo"] = "cancelado", None
    guardar_track(raiz, track)
    if estado.get("track_activo") == track_id:
        estado["track_activo"] = None
    estado.setdefault("contadores", {})["stop_bloqueos"] = 0
    escribir_json(ruta_estado(raiz), estado)
    print("Track %s cancelado (motivo: %s). Se conserva su carpeta como historial." % (track_id, motivo))
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
        print("Track activo: %s (%s) · tareas %d/%d · siguiente: %s"
              % (t["id"], t["estado"], t["tareas_hechas"], t["tareas_total"], t["siguiente_tarea"] or "—"))
    else:
        print("Sin track activo.")
    print("Tracks cerrados: %d · schema_version %d" % (datos["tracks_cerrados"], datos["schema_version"]))
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
                problemas.append("%s: el `id` de track.json (%r) no coincide con la carpeta." % (t, track.get("id")))
            if track.get("estado") not in ESTADOS:
                problemas.append("%s: estado desconocido %r." % (t, track.get("estado")))
            if track.get("estado") not in ESTADOS_FINALES:
                abiertos.append(t)
            if track.get("estado") in ("listo", "en_progreso", "en_revision", "correcciones", "verificado"):
                for o, (st, det) in ((o, estado_aprobacion(raiz, track, o, estado)) for o in APROBACIONES_PARA_LISTO):
                    if st != "ok":
                        problemas.append("%s: aprobación de %s %s (%s)." % (t, o, st, det))
            if track.get("politica_cierre") not in (None,) + POLITICAS:
                problemas.append("%s: política de cierre desconocida %r." % (t, track.get("politica_cierre")))
            if track.get("politica_cierre") == "automatico" and not revisor_disponible():
                problemas.append("%s: política `automatico` sin agente revisor (fase C)." % t)
            _, lineas = leer_plan(raiz, t)
            for _, marca, tid, con_commit in tareas_del_plan(lineas):
                if marca == "x" and not con_commit:
                    problemas.append("%s: la tarea %s está hecha sin commit registrado." % (t, tid))
        except ReglaError as e:
            problemas.append("%s: %s" % (t, e))
    if len(abiertos) > 1:
        problemas.append("Hay %d tracks abiertos (%s) y solo se permite uno." % (len(abiertos), ", ".join(abiertos)))
    if activo and activo not in abiertos:
        problemas.append("track_activo apunta a %s, que no existe o ya está cerrado o cancelado." % activo)
    if not activo and abiertos:
        problemas.append("Hay un track abierto (%s) pero estado.json no lo marca como activo." % abiertos[0])
    if versionado_ignorado(raiz):
        sys.stderr.write("Advertencia: Git está ignorando .devsquad/ y debe versionarse.\n")
    if problemas:
        for p in problemas:
            sys.stderr.write("- %s\n" % p)
        raise ReglaError("El estado del proyecto no es válido (%d problema(s))." % len(problemas))
    print("Estado válido.")
    return 0


def cmd_migrar(a, raiz):
    ruta = ruta_estado(raiz)
    estado = leer_json(ruta)
    version = estado.get("schema_version")
    if not isinstance(version, int):
        raise ReglaError("%s no tiene un `schema_version` entero." % ruta)
    if version > SCHEMA_VERSION:
        raise ReglaError("El estado es de una versión más nueva (%d) que este plugin (%d). Actualiza el plugin." % (version, SCHEMA_VERSION))
    if version == SCHEMA_VERSION:
        print("El estado ya está en la versión %d." % SCHEMA_VERSION)
        return 0
    while version < SCHEMA_VERSION:
        if version not in MIGRACIONES:
            raise ReglaError("No hay migración desde schema_version %d." % version)
        estado = MIGRACIONES[version](estado)
        version += 1
        estado["schema_version"] = version
    escribir_json(ruta, estado)
    print("Estado migrado a la versión %d." % SCHEMA_VERSION)
    return 0


def construir_parser():
    p = argparse.ArgumentParser(prog="devsquad-estado", description="Estado y tracks de DevSquad AI.")
    p.add_argument("--raiz", help="Raíz del proyecto (por defecto $CLAUDE_PROJECT_DIR o el directorio actual).")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="Crea .devsquad/estado.json.").set_defaults(f=cmd_init)
    c = sub.add_parser("crear", help="Crea un track nuevo (solo si no hay otro abierto).")
    c.add_argument("slug")
    c.add_argument("--titulo")
    c.set_defaults(f=cmd_crear)
    t = sub.add_parser("transicion", help="Cambia el estado de un track.")
    t.add_argument("estado", choices=[e for e in ESTADOS if e not in ESTADOS_FINALES])
    t.add_argument("--track")
    t.set_defaults(f=cmd_transicion)
    d = sub.add_parser("desbloquear", help="Devuelve un track bloqueado a su estado anterior.")
    d.add_argument("--track")
    d.set_defaults(f=cmd_desbloquear)
    k = sub.add_parser("tarea", help="Cambia el estado de una tarea del plan.")
    k.add_argument("id")
    k.add_argument("estado", choices=("pendiente", "en_curso", "hecha"))
    k.add_argument("--commit")
    k.add_argument("--track")
    k.set_defaults(f=cmd_tarea)
    z = sub.add_parser("cerrar", help="Cierra el track si sus tareas están completas.")
    z.add_argument("--track")
    z.set_defaults(f=cmd_cerrar)
    ap = sub.add_parser("aprobar", help="Registra una aprobación humana (lo invocan los hooks o la Factory, no los agentes).")
    ap.add_argument("objeto", choices=APROBABLES)
    ap.add_argument("--fuente", choices=FUENTES, default="manual")
    ap.add_argument("--por")
    ap.add_argument("--track")
    ap.set_defaults(f=cmd_aprobar)
    cn = sub.add_parser("cancelar", help="Cancela un track abierto, con motivo (decisión de la persona).")
    cn.add_argument("--motivo", required=True)
    cn.add_argument("--fuente", choices=FUENTES, default="manual")
    cn.add_argument("--por")
    cn.add_argument("--track")
    cn.set_defaults(f=cmd_cancelar)
    e = sub.add_parser("estado", help="Resumen del estado.")
    e.add_argument("--json", action="store_true")
    e.set_defaults(f=cmd_estado)
    sub.add_parser("validar", help="Comprueba la coherencia de .devsquad/.").set_defaults(f=cmd_validar)
    sub.add_parser("migrar", help="Actualiza estado.json al esquema vigente.").set_defaults(f=cmd_migrar)
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
