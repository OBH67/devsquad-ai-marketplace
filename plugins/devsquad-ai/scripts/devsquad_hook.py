#!/usr/bin/env python3
"""Compuertas de DevSquad AI (hooks del plugin).

Uso: devsquad_hook.py sessionstart | pretooluse | subagentstop | stop   (JSON del hook por stdin)

Solo actúa cuando `agent_type` es uno de los agentes de este plugin (el valor
llega con espacio de nombres: `<plugin>:<agente>`). En cualquier otra sesión no
hace nada. Bloquea con exit 2 y un mensaje que dice el paso que falta. Cualquier
fallo inesperado del propio hook sale con código 1 (no bloqueante): una
compuerta rota no debe dejar la sesión inutilizable.

Solo biblioteca estándar.
"""
import sys

if sys.version_info < (3, 8):
    sys.stderr.write("devsquad_hook: se requiere Python 3.8 o superior.\n")
    sys.exit(1)

import contextlib
import fnmatch
import hashlib
import io
import json
import os
import re
import subprocess
import traceback
import unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ_PLUGIN = os.path.dirname(AQUI)
sys.path.insert(0, AQUI)
import devsquad_estado as E  # noqa: E402
import devsquad_memoria as M  # noqa: E402
import devsquad_puntero as P  # noqa: E402

# Entregables de cada fase dentro de .devsquad/ y quién los produce.
ENTREGABLES = {"requerimientos.md": "bsa", "arquitectura.md": "arquitecto", "diseno.md": "disenador"}
# Qué entregables deben existir antes de delegar en cada agente (orden de fases).
REQUISITOS = {
    "bsa": (),
    "arquitecto": ("requerimientos.md",),
    "disenador": ("requerimientos.md", "arquitectura.md"),
    "coder": ("requerimientos.md", "arquitectura.md", "diseno.md"),
}
ESTADOS_DE_TRABAJO = ("en_progreso", "correcciones")
MAX_BLOQUEOS = 3            # bloqueos seguidos del coder antes de escalar a la persona
TIMEOUT_VERIFICACION = 300  # segundos por comando de verificación
PERFIL = os.path.join(E.DIR_ESTADO, "perfil.md")

PATRONES_SECRETOS = (
    (re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----"), "una llave privada"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "una llave de acceso de AWS"),
    (re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}"), "una llave de la API de Anthropic"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"), "un token de GitHub"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), "un token de Slack"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), "una llave de la API de Google"),
)
ENV_PERMITIDOS = (".env.example", ".env.sample", ".env.template", ".env.dist")


class Bloqueo(Exception):
    """La compuerta niega la acción; el mensaje va al agente."""


# ------------------------------------------------------------------ utilidades

def nombre_plugin():
    with open(os.path.join(RAIZ_PLUGIN, ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
        return json.load(f)["name"]


def agentes_del_plugin():
    carpeta = os.path.join(RAIZ_PLUGIN, "agents")
    return {f[:-3] for f in os.listdir(carpeta) if f.endswith(".md")}


def rol_de(agent_type):
    """Nombre corto del agente si es de este plugin; si no, None."""
    if not agent_type or ":" not in agent_type:
        return None
    espacio, nombre = agent_type.split(":", 1)
    return nombre if espacio == nombre_plugin() and nombre in agentes_del_plugin() else None


def estado_cli(raiz, *args):
    """Ejecuta devsquad-estado en el mismo proceso. Devuelve (código, stdout, stderr)."""
    salida, error = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(error):
        try:
            codigo = E.main(["--raiz", raiz] + list(args))
        except SystemExit as e:  # argparse
            codigo = e.code if isinstance(e.code, int) else 2
    return codigo, salida.getvalue().strip(), error.getvalue().strip()


def ruta_relativa(raiz, ruta):
    """Ruta relativa al proyecto con '/', o None si queda fuera de él."""
    absoluta = os.path.abspath(ruta if os.path.isabs(ruta) else os.path.join(raiz, ruta))
    rel = os.path.relpath(absoluta, raiz)
    return None if rel == ".." or rel.startswith(".." + os.sep) else rel.replace(os.sep, "/")


def sin_acentos(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def leer_texto(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            return f.read()
    except (OSError, UnicodeDecodeError):
        return None


# --------------------------------------------------------------------- perfil

def perfil_texto(raiz):
    return leer_texto(os.path.join(raiz, PERFIL))


def perfil_valido(raiz):
    texto = perfil_texto(raiz)
    return bool(texto and re.search(r"^# Perfil DevSquad AI\b", texto, re.MULTILINE))


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


def rutas_protegidas(texto):
    """Patrones de la línea «Archivos protegidos» del perfil (y sus continuaciones)."""
    lineas = (texto or "").split("\n")
    for i, linea in enumerate(lineas):
        m = re.match(r"^\s*[-*]\s+\*\*Archivos protegidos\*\*\s*:(.*)$", linea)
        if not m:
            continue
        bloque = [m.group(1)]
        for sig in lineas[i + 1:]:
            if re.match(r"^\s*[-*]\s+\*\*", sig) or re.match(r"^#{1,6}\s", sig) or not sig.strip():
                break
            bloque.append(sig)
        crudo = "\n".join(bloque)
        tokens = re.findall(r"`([^`]+)`", crudo)
        if not tokens:
            tokens = [t for t in re.split(r"[,;\n]", crudo)]
        patrones = []
        for t in tokens:
            t = t.strip().strip("-* ").strip()
            if t and t.upper() != "N/A" and not t.startswith("["):
                patrones.append(t)
        return patrones
    return []


def es_protegido(rel, patrones):
    for p in patrones:
        base = p.rstrip("/")
        if rel == base or rel.startswith(base + "/") or fnmatch.fnmatch(rel, p):
            return p
    return None


# ----------------------------------------------------------------- compuertas

def es_env_secreto(rel):
    nombre = os.path.basename(rel)
    return (nombre == ".env" or nombre.startswith(".env.")) and nombre not in ENV_PERMITIDOS


def contenido_de_escritura(ti):
    return (ti.get("content") or "") + "\n" + (ti.get("new_string") or "")


def track_activo(raiz):
    """(id, datos) del track activo o (None, None)."""
    try:
        estado = E.cargar_estado(raiz)
    except E.ReglaError:
        return None, None
    tid = estado.get("track_activo")
    if not tid:
        return None, None
    try:
        return tid, E.cargar_track(raiz, tid)
    except E.ReglaError:
        return tid, None


def compuerta_perfil(raiz, tool, rel):
    if perfil_valido(raiz):
        return
    if tool in ("Write", "Edit") and rel == PERFIL.replace(os.sep, "/"):
        return
    raise Bloqueo("Falta el perfil del proyecto (%s). Sin perfil no se puede delegar, escribir ni ejecutar "
                  "comandos. Siguiente paso: usa la skill `iniciar-proyecto` para crearlo." % PERFIL)


def compuerta_secretos(rel, ti):
    if es_env_secreto(rel):
        raise Bloqueo("No se escriben archivos de secretos (%s). Siguiente paso: guarda las llaves fuera del "
                      "repositorio y deja un `.env.example` solo con los nombres de las variables." % rel)
    texto = contenido_de_escritura(ti)
    for patron, que in PATRONES_SECRETOS:
        if patron.search(texto):
            raise Bloqueo("El contenido a escribir en %s parece incluir %s. Siguiente paso: quita el valor, "
                          "usa una variable de entorno y pídele la llave a la persona por un canal seguro." % (rel, que))


def compuerta_protegidos(raiz, rel):
    patron = es_protegido(rel, rutas_protegidas(perfil_texto(raiz)))
    if patron:
        raise Bloqueo("%s está protegido por el perfil (patrón `%s`). Siguiente paso: detente y pregúntale a la "
                      "persona si autoriza el cambio; no lo modifiques ni lo regeneres." % (rel, patron))


def compuerta_orden_de_fases(raiz, destino):
    faltan = [f for f in REQUISITOS.get(destino, ()) if not os.path.exists(os.path.join(raiz, E.DIR_ESTADO, f))]
    if faltan:
        pasos = ", ".join("`%s` (lo produce %s)" % (f, ENTREGABLES[f]) for f in faltan)
        raise Bloqueo("No se puede delegar en %s todavía: faltan %s. Siguiente paso: completa esa fase primero." % (destino, pasos))


def compuerta_track_para_coder(raiz):
    tid, track = track_activo(raiz)
    if not tid or not track:
        raise Bloqueo("No hay un track activo, así que el coder no tiene trabajo definido. Siguiente paso: "
                      "completa la planeación (el track nace al terminar el BSA y pasa a `listo` cuando plan.md tiene tareas).")
    if track["estado"] == "listo":
        codigo, _, err = estado_cli(raiz, "transicion", "en_progreso")
        if codigo != 0:
            raise Bloqueo(err)
        return
    if track["estado"] not in ESTADOS_DE_TRABAJO:
        raise Bloqueo("El track %s está en %s y el coder solo trabaja en %s. Siguiente paso: haz avanzar el track "
                      "(%s)." % (tid, track["estado"], " o ".join(ESTADOS_DE_TRABAJO), pista_de_estado(track["estado"])))


def pista_de_estado(estado):
    return {
        "borrador": "completa requerimientos, arquitectura y diseño, y escribe las tareas en plan.md",
        "en_revision": "espera la revisión o ciérralo si ya terminó",
        "verificado": "ciérralo con `devsquad-estado cerrar`",
        "bloqueado": "resuelve el bloqueo y ejecuta `devsquad-estado desbloquear`",
        "cerrado": "crea un track nuevo con el BSA",
    }.get(estado, "revisa `devsquad-estado estado`")


def compuerta_track_para_escribir(raiz, rel):
    tid, track = track_activo(raiz)
    if not tid or not track or track["estado"] not in ESTADOS_DE_TRABAJO:
        estado = track["estado"] if track else "sin track activo"
        raise Bloqueo("No se escribe código del proyecto (%s) fuera de un track en %s (estado actual: %s). "
                      "Siguiente paso: %s." % (rel, " o ".join(ESTADOS_DE_TRABAJO), estado,
                                               pista_de_estado(track["estado"]) if track else "crea y planea un track"))


def pretooluse(data, raiz, rol):
    tool, ti = data.get("tool_name"), data.get("tool_input") or {}
    rel = None
    if tool in ("Write", "Edit") and ti.get("file_path"):
        rel = ruta_relativa(raiz, ti["file_path"])
    compuerta_perfil(raiz, tool, rel)
    if not os.path.exists(E.ruta_estado(raiz)):
        estado_cli(raiz, "init")
    if tool in ("Write", "Edit") and rel is not None:
        compuerta_secretos(rel, ti)
        compuerta_protegidos(raiz, rel)
        if not rel.startswith(E.DIR_ESTADO + "/"):
            compuerta_track_para_escribir(raiz, rel)
    if tool == "Agent":
        sub = ti.get("subagent_type") or ""
        destino = sub.split(":", 1)[1] if sub.startswith(nombre_plugin() + ":") else None
        if destino in REQUISITOS:
            compuerta_orden_de_fases(raiz, destino)
        if destino == "coder":
            compuerta_track_para_coder(raiz)
            guardar_linea_base(raiz)


# ------------------------------------------------- resultado del coder (Git)

def git(raiz, *args):
    """Salida de git como bytes, o None si git no está o no es un repositorio."""
    try:
        r = subprocess.run(["git", "-C", raiz] + list(args), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except OSError:
        return None
    return r.stdout if r.returncode == 0 else None


def rutas_cambiadas(raiz):
    """Rutas con cambios según Git (modificadas, nuevas, borradas) más los .env* ignorados.

    Los .env* suelen estar en .gitignore, así que `git status` no los ve.
    Devuelve None si no se puede consultar Git.
    """
    estado = git(raiz, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    if estado is None:
        return None
    rutas, entradas = set(), estado.decode("utf-8", "replace").split("\0")
    i = 0
    while i < len(entradas):
        e = entradas[i]
        i += 1
        if len(e) < 4:
            continue
        rutas.add(e[3:])
        if e[0] in "RC":  # renombrado/copiado: la ruta de origen va en la entrada siguiente
            if i < len(entradas) and entradas[i]:
                rutas.add(entradas[i])
            i += 1
    ignorados = git(raiz, "ls-files", "-o", "-i", "--exclude-standard", "-z") or b""
    for r in ignorados.decode("utf-8", "replace").split("\0"):
        if r and es_env_secreto(r):
            rutas.add(r)
    return {r for r in rutas if not r.startswith(E.DIR_ESTADO + "/")}


def huella(raiz, rel):
    try:
        with open(os.path.join(raiz, rel), "rb") as f:
            return hashlib.sha1(f.read()).hexdigest()
    except OSError:
        return "borrado"


def instantanea(raiz):
    """{ruta: huella} de lo que ya está cambiado ahora, o None sin Git."""
    rutas = rutas_cambiadas(raiz)
    return None if rutas is None else {r: huella(raiz, r) for r in sorted(rutas)}


def guardar_linea_base(raiz):
    """Al delegar en el coder: lo que ya estaba cambiado no se le atribuye."""
    base = instantanea(raiz)
    if base is None:
        return
    estado = E.cargar_estado(raiz)
    estado["linea_base_git"] = base
    E.escribir_json(E.ruta_estado(raiz), estado)


def revisar_cambios(raiz):
    """Revisa lo que el coder cambió respecto a la línea base.

    Devuelve (violaciones, avisos). Atrapa lo que Bash hace sin pasar por
    Write/Edit (`echo X > .env`, `sed -i`...).
    """
    actual = instantanea(raiz)
    if actual is None:
        return [], ["Aviso: no es un repositorio Git (o falta git); no se pudo revisar el resultado del coder "
                    "contra secretos y archivos protegidos."]
    base = E.cargar_estado(raiz).get("linea_base_git") or {}
    protegidos = rutas_protegidas(perfil_texto(raiz))
    violaciones = []
    for rel, h in actual.items():
        if base.get(rel) == h:
            continue
        existe = h != "borrado"
        patron = es_protegido(rel, protegidos)
        if patron:
            violaciones.append("%s: archivo protegido por el perfil (`%s`) modificado. Revierte el cambio "
                               "(`git checkout -- %s`) y pregunta a la persona." % (rel, patron, rel))
        if existe and es_env_secreto(rel):
            violaciones.append("%s: archivo de secretos. Elimínalo y deja solo un `.env.example` con los nombres "
                               "de las variables." % rel)
        elif existe:
            texto = leer_texto(os.path.join(raiz, rel)) or ""
            for patron_s, que in PATRONES_SECRETOS:
                if patron_s.search(texto):
                    violaciones.append("%s: parece incluir %s. Quita el valor y usa una variable de entorno." % (rel, que))
                    break
    return violaciones, []


# --------------------------------------------------------------- SubagentStop

def titulo_desde_requerimientos(raiz):
    """Primer `# título` de requerimientos.md sin el prefijo «Requerimientos —», o '' si no hay."""
    texto = leer_texto(os.path.join(raiz, E.DIR_ESTADO, "requerimientos.md")) or ""
    m = re.search(r"^#\s+(.+)$", texto, re.MULTILINE)
    if not m:
        return ""
    titulo = re.sub(r"^(requerimientos|requisitos)\b\s*[:\-—–]*\s*(de(l)?\s+)?", "", m.group(1).strip(), flags=re.IGNORECASE)
    return (titulo or m.group(1)).strip()


def slug_desde_titulo(titulo, maximo=40):
    """Slug en minúsculas sin acentos, cortado en límite de palabra; 'iteracion' si no queda nada."""
    palabras = re.sub(r"[^a-z0-9]+", "-", sin_acentos(titulo).lower()).strip("-").split("-")
    slug = ""
    for palabra in palabras:
        candidato = (slug + "-" + palabra) if slug else palabra
        if len(candidato) > maximo:
            break
        slug = candidato
    return slug or "iteracion"


def avanzar_planeacion(raiz, rol):
    mensajes = []
    existe = lambda f: os.path.exists(os.path.join(raiz, E.DIR_ESTADO, f))
    if not os.path.exists(E.ruta_estado(raiz)):
        estado_cli(raiz, "init")
    tid, track = track_activo(raiz)
    if rol == "bsa" and existe("requerimientos.md") and not tid:
        titulo = titulo_desde_requerimientos(raiz)
        args = ["crear", slug_desde_titulo(titulo)] + (["--titulo", titulo[:120]] if titulo else [])
        codigo, out, err = estado_cli(raiz, *args)
        mensajes.append(out if codigo == 0 else "No se pudo crear el track: " + err)
        tid, track = track_activo(raiz)
    if track and track["estado"] == "borrador" and all(existe(f) for f in ENTREGABLES):
        codigo, out, err = estado_cli(raiz, "transicion", "listo")
        mensajes.append(out if codigo == 0 else
                        "El track %s no pasa a `listo`: %s" % (tid, err.replace("devsquad-estado: ", "")))
    return mensajes


def ejecutar_verificacion(raiz, comandos):
    """Devuelve la lista de fallos [(etiqueta, comando, cola_de_salida)]."""
    fallos = []
    for etiqueta, comando in comandos:
        try:
            r = subprocess.run(comando, shell=True, cwd=raiz, capture_output=True, text=True,
                               timeout=TIMEOUT_VERIFICACION)
            if r.returncode != 0:
                fallos.append((etiqueta, comando, (r.stdout + r.stderr).strip()[-1500:]))
        except subprocess.TimeoutExpired:
            fallos.append((etiqueta, comando, "Se agotó el tiempo (%d s)." % TIMEOUT_VERIFICACION))
    return fallos


def verificar_coder(raiz):
    """Bloquea (Bloqueo) si falla la verificación o el resultado viola las reglas.

    Devuelve mensajes informativos si no hay nada que bloquear. Los fallos de
    verificación y las violaciones comparten el mismo tope de bloqueos.
    """
    violaciones, avisos = revisar_cambios(raiz)
    comandos = comandos_verificacion(perfil_texto(raiz))
    if not comandos:
        avisos.append("Aviso: el perfil no declara comandos de verificación; no se pudo comprobar el trabajo del "
                      "coder. Agrega la sección «Comandos de verificación» a %s." % PERFIL)
    fallos = ejecutar_verificacion(raiz, comandos) if comandos else []
    estado = E.cargar_estado(raiz)
    contadores = estado.setdefault("contadores", {})
    previos = contadores.get("stop_bloqueos", 0)
    if not fallos and not violaciones:
        contadores["stop_bloqueos"] = 0
        E.escribir_json(E.ruta_estado(raiz), estado)
        return avisos
    detalle = "\n".join(["- %s" % v for v in violaciones] + ["- %s (`%s`):\n%s" % f for f in fallos])
    if previos >= MAX_BLOQUEOS:
        contadores["stop_bloqueos"] = 0
        E.escribir_json(E.ruta_estado(raiz), estado)
        return ["La verificación sigue fallando tras %d intentos; se deja terminar al coder y se escala a la persona. "
                "Siguiente paso: pregúntale cómo proceder (ask_human). Problemas:\n%s" % (MAX_BLOQUEOS, detalle)]
    contadores["stop_bloqueos"] = previos + 1
    E.escribir_json(E.ruta_estado(raiz), estado)
    raise Bloqueo("La verificación falló (intento %d de %d); no puedes terminar con el código en rojo. "
                  "Siguiente paso: corrige lo siguiente y vuelve a terminar.\n%s" % (previos + 1, MAX_BLOQUEOS, detalle))


def avanzar_coder(raiz):
    tid, track = track_activo(raiz)
    if not track or track["estado"] not in ESTADOS_DE_TRABAJO:
        return []
    try:
        abiertas = E.tareas_abiertas(raiz, tid)
    except E.ReglaError as e:
        return ["Aviso: %s" % e]
    if abiertas:
        return ["Track %s: faltan tareas por completar (%s)." % (tid, ", ".join(abiertas))]
    codigo, out, err = estado_cli(raiz, "transicion", "en_revision")
    return [out if codigo == 0 else err]


def subagentstop(data, raiz, rol):
    if not perfil_valido(raiz):
        return []
    try:
        if rol == "coder":
            mensajes = verificar_coder(raiz)
            return mensajes + avanzar_coder(raiz)
        if rol in ("bsa", "arquitecto", "disenador"):
            return avanzar_planeacion(raiz, rol)
        return []
    finally:
        M.escribir_indice(raiz)  # el índice de memoria refleja siempre el estado vigente


# --------------------------------------------------------------- SessionStart

def sessionstart(data, raiz, rol):
    """Puntero de arranque (<= 10.000 caracteres) como contexto de la conversación.

    Se dispara en startup, resume, clear y compact (PreCompact no puede inyectar
    contexto; tras compactar es SessionStart con source=compact el que lo repone).
    """
    if os.path.isdir(os.path.join(raiz, E.DIR_ESTADO)):
        M.escribir_indice(raiz)
    return P.generar(raiz)


# ----------------------------------------------------------------------- Stop

def stop(data, raiz, rol):
    if data.get("agent_id") or not os.path.exists(E.ruta_estado(raiz)):
        return []
    tid, track = track_activo(raiz)
    if track and track["estado"] in ("en_revision", "verificado"):
        codigo, out, _ = estado_cli(raiz, "cerrar")
        return [out] if codigo == 0 else []
    return []


# ----------------------------------------------------------------------- main

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0] not in ("sessionstart", "pretooluse", "subagentstop", "stop"):
        sys.stderr.write("Uso: devsquad_hook.py sessionstart|pretooluse|subagentstop|stop\n")
        return 1
    try:
        data = json.load(sys.stdin)
        rol = rol_de(data.get("agent_type"))
        if rol is None:
            return 0
        raiz = os.path.abspath(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd())
        if argv[0] == "pretooluse":
            pretooluse(data, raiz, rol)
            return 0
        if argv[0] == "sessionstart":
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart",
                                                     "additionalContext": sessionstart(data, raiz, rol)}},
                             ensure_ascii=False))
            return 0
        mensajes = (subagentstop if argv[0] == "subagentstop" else stop)(data, raiz, rol)
        if mensajes:
            # Solo systemMessage: `additionalContext` en Stop/SubagentStop re-dispara al agente (comprobado).
            print(json.dumps({"systemMessage": "DevSquad AI: " + " | ".join(mensajes)}, ensure_ascii=False))
        return 0
    except Bloqueo as b:
        sys.stderr.write("DevSquad AI bloqueó la acción. %s\n" % b)
        return 2
    except Exception:  # fallo del propio hook: no bloquea
        sys.stderr.write("devsquad_hook falló (no bloqueante):\n" + traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())
