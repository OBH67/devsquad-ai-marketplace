#!/usr/bin/env python3
"""Puntero de arranque: unas pocas líneas generadas por script, no el estado completo.

«¿En qué me quedé?» es una consulta exacta sobre el estado estructurado, no
una búsqueda: este script la responde con un tamaño casi fijo (tope duro de
10.000 caracteres, el límite que admite un hook para `additionalContext`) y
da las rutas para leer el detalle con Read.

Uso: devsquad_puntero.py [--raiz RUTA]
"""
import sys

if sys.version_info < (3, 8):
    sys.stderr.write("devsquad_puntero: Python 3.8 or later is required.\n")
    sys.exit(1)

import argparse
import os
import re
import subprocess

import devsquad_estado as E
import devsquad_memoria as M

MAX_CARACTERES = 10000
PERFIL = "%s/perfil.md" % E.DIR_ESTADO
ENTREGABLES = (("requerimientos.md", "bsa"), ("arquitectura.md", "arquitecto"), ("diseno.md", "disenador"))


def recortar(texto, n):
    texto = " ".join(str(texto).split())
    return texto if len(texto) <= n else texto[: n - 1] + "…"


def ultimo_commit(raiz):
    try:
        r = subprocess.run(["git", "-C", raiz, "log", "-1", "--format=%h %s"], capture_output=True, text=True)
    except OSError:
        return "no Git"
    return recortar(r.stdout, 100) if r.returncode == 0 and r.stdout.strip() else "no commits"


def perfil_ok(raiz):
    try:
        with open(os.path.join(raiz, PERFIL), encoding="utf-8") as f:
            return bool(re.search(r"^# (?:DevSquad AI Profile|Perfil DevSquad AI)\b", f.read(), re.MULTILINE))
    except (OSError, UnicodeDecodeError):
        return False


def tareas(raiz, track_id):
    """[(id, marca, texto)] del plan del track."""
    try:
        _, lineas = E.leer_plan(raiz, track_id)
    except E.ReglaError:
        return []
    salida = []
    for i, _, _, _ in E.tareas_del_plan(lineas):
        m = E.TAREA_RE.match(lineas[i])
        salida.append((m.group("id"), m.group("marca").lower(), E.COMMIT_RE.sub("", m.group("resto")).strip()))
    return salida


def siguiente_paso(raiz, track):
    if not perfil_ok(raiz):
        return "create the profile with the `iniciar-proyecto` skill (without a profile the gates deny everything)."
    faltan = [(f, a) for f, a in ENTREGABLES if not os.path.exists(os.path.join(raiz, E.DIR_ESTADO, f))]
    if track is None:
        return "delegate to `%s` (`%s` is missing)." % (faltan[0][1], faltan[0][0]) if faltan else \
               "define a new track with the BSA."
    estado = track["estado"]
    if estado == "borrador":
        if faltan:
            return "delegate to `%s` (`%s` is missing)." % (faltan[0][1], faltan[0][0])
        try:
            if not E.tareas_del_plan(E.leer_plan(raiz, track["id"])[1]):
                return "ask the `arquitecto` for the tasks in `plan.md`."
        except E.ReglaError:
            pass
        sin = [o for o in E.APROBACIONES_PARA_LISTO if E.estado_aprobacion(raiz, track, o)[0] != "ok"]
        if sin:
            return ("wait for the human approval of %s (do not record it yourself): %s." % (", ".join(sin), E.comoaprobar(sin[0])))
        return "the track moves to `listo` as soon as the last approval is recorded."
    if estado in ("en_progreso", "correcciones", "en_revision", "verificado"):
        motivo = E.motivo_no_cerrable(raiz, track)
        if motivo is None:
            return "the track meets the criteria and closes by itself."
        if E.cumple_criterios_objetivos(raiz, track) and E.politica_de(track) == "humano":
            return "the track meets the criteria and is waiting for the human closing approval: %s." % E.comoaprobar("cierre")
    return {
        "listo": "delegate to `coder` (the hook moves the track to `en_progreso`).",
        "en_progreso": "continue with the `coder` until the tasks are complete.",
        "correcciones": "continue with the `coder` on the corrections.",
        "en_revision": "wait for the review.",
        "verificado": "complete the track closing.",
        "bloqueado": "resolve the block with the person.",
    }.get(estado, "review the state.")


def generar(raiz, maximo=MAX_CARACTERES):
    raiz = os.path.abspath(raiz)
    lineas = ["DevSquad AI · startup pointer (script-generated; the detail is in the paths below)",
              "Project: %s · Working folder: %s" % (recortar(os.path.basename(raiz), 80), raiz),
              "Profile: %s" % ("ok (%s)" % PERFIL if perfil_ok(raiz) else "MISSING (%s)" % PERFIL)]
    track, tid = None, None
    if os.path.exists(E.ruta_estado(raiz)):
        try:
            estado = E.cargar_estado(raiz)
            tid = estado.get("track_activo")
            track = E.cargar_track(raiz, tid) if tid else None
        except E.ReglaError as e:
            lineas.append("State: UNREADABLE (%s)" % recortar(e, 200))
    else:
        lineas.append("State: no %s/%s yet" % (E.DIR_ESTADO, E.ARCHIVO_ESTADO))
    if track:
        ts = tareas(raiz, tid)
        hechas = sum(1 for t in ts if t[1] == "x")
        sig = next((t for t in ts if t[1] != "x"), None)
        lineas.append("Active track: %s (%s) · %s · tasks %d/%d" % (tid, track["estado"], recortar(track.get("titulo", ""), 80),
                                                                     hechas, len(ts)))
        ap = E.resumen_aprobaciones(raiz, track, estado)
        lineas.append("Human approvals: architecture %s · design %s · verification commands %s · closing %s · closing policy: %s"
                      % (E.txt_aprobacion(ap["arquitectura"]), E.txt_aprobacion(ap["diseno"]), E.txt_aprobacion(ap["comandos"]),
                         E.txt_aprobacion(ap["cierre"]), E.politica_de(track)))
        lineas.append("Next task: %s" % ("%s \"%s\"" % (sig[0], recortar(sig[2], 120)) if sig else "—"))
        lineas.append("Blockers: %s" % ("the track is blocked (before: %s)" % (track.get("estado_previo") or "?")
                                         if track["estado"] == "bloqueado" else "none"))
        lineas.append("Track detail: %s" % os.path.join(raiz, E.DIR_ESTADO, E.DIR_TRACKS, tid))
    else:
        lineas.append("Active track: none")
    lineas.append("Last commit: %s" % ultimo_commit(raiz))
    c = M.conteos(raiz)
    lineas.append("Memory: %d decisions, %d learnings, %d closed tracks → index (read it with Read, no Bash): %s"
                  % (c["decisiones"], c["aprendizajes"], c["tracks_cerrados"], M.ruta_memoria(raiz, M.INDICE)))
    lineas.append("Full state: %s" % E.ruta_estado(raiz))
    lineas.append("Suggested next step: %s" % siguiente_paso(raiz, track))
    texto = "\n".join(lineas)
    return texto if len(texto) <= maximo else texto[: maximo - 1] + "…"


def main(argv=None):
    p = argparse.ArgumentParser(prog="devsquad_puntero", description="DevSquad AI startup pointer.")
    p.add_argument("--raiz")
    a = p.parse_args(argv)
    print(generar(E.raiz_proyecto(a.raiz)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
