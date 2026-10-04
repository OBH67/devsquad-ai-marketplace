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
import json
import os
import re
import subprocess
import tempfile

SCHEMA_VERSION = 1
DIR_ESTADO = ".devsquad"
ARCHIVO_ESTADO = "estado.json"
DIR_TRACKS = "tracks"

ESTADOS = ("borrador", "listo", "en_progreso", "en_revision", "correcciones",
           "verificado", "cerrado", "bloqueado")

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
            "contadores": {"stop_bloqueos": 0}}


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
    if nuevo == "bloqueado":
        if actual in ("borrador", "listo", "cerrado", "bloqueado"):
            raise ReglaError("El track %s está en %s y no puede bloquearse." % (track_id, actual))
    elif nuevo not in TRANSICIONES.get(actual, ()):
        permitidas = ", ".join(TRANSICIONES.get(actual, ())) or "ninguna (usa `desbloquear`)"
        raise ReglaError("Transición no permitida: %s → %s. Desde %s se puede ir a: %s."
                         % (actual, nuevo, actual, permitidas))
    if nuevo == "listo":
        _, lineas = leer_plan(raiz, track_id)
        if not tareas_del_plan(lineas):
            raise ReglaError("El track %s no puede pasar a `listo` sin tareas en plan.md." % track_id)
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


def cmd_cerrar(a, raiz):
    estado = cargar_estado(raiz)
    track_id = resolver_track(raiz, estado, a.track)
    track = cargar_track(raiz, track_id)
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
    track["estado"], track["estado_previo"] = "cerrado", None
    guardar_track(raiz, track)
    if estado.get("track_activo") == track_id:
        estado["track_activo"] = None
    estado.setdefault("contadores", {})["stop_bloqueos"] = 0
    escribir_json(ruta_estado(raiz), estado)
    print("Track %s cerrado." % track_id)
    return 0


def resumen(raiz):
    estado = cargar_estado(raiz)
    datos = {"schema_version": estado["schema_version"], "track_activo": None, "tracks_cerrados": 0}
    for t in listar_tracks(raiz):
        track = cargar_track(raiz, t)
        if track["estado"] == "cerrado":
            datos["tracks_cerrados"] += 1
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
            if track.get("estado") != "cerrado":
                abiertos.append(t)
            _, lineas = leer_plan(raiz, t)
            for _, marca, tid, con_commit in tareas_del_plan(lineas):
                if marca == "x" and not con_commit:
                    problemas.append("%s: la tarea %s está hecha sin commit registrado." % (t, tid))
        except ReglaError as e:
            problemas.append("%s: %s" % (t, e))
    if len(abiertos) > 1:
        problemas.append("Hay %d tracks abiertos (%s) y solo se permite uno." % (len(abiertos), ", ".join(abiertos)))
    if activo and activo not in abiertos:
        problemas.append("track_activo apunta a %s, que no existe o ya está cerrado." % activo)
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
    t.add_argument("estado", choices=[e for e in ESTADOS if e != "cerrado"])
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
