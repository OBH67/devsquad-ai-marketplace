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
    sys.stderr.write("devsquad_puntero: se requiere Python 3.8 o superior.\n")
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
        return "sin Git"
    return recortar(r.stdout, 100) if r.returncode == 0 and r.stdout.strip() else "sin commits"


def perfil_ok(raiz):
    try:
        with open(os.path.join(raiz, PERFIL), encoding="utf-8") as f:
            return bool(re.search(r"^# Perfil DevSquad AI\b", f.read(), re.MULTILINE))
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
        return "crear el perfil con la skill `iniciar-proyecto` (sin perfil las compuertas niegan todo)."
    faltan = [(f, a) for f, a in ENTREGABLES if not os.path.exists(os.path.join(raiz, E.DIR_ESTADO, f))]
    if track is None:
        return "delegar en `%s` (falta `%s`)." % (faltan[0][1], faltan[0][0]) if faltan else \
               "definir un track nuevo con el BSA."
    estado = track["estado"]
    if estado == "borrador":
        if faltan:
            return "delegar en `%s` (falta `%s`)." % (faltan[0][1], faltan[0][0])
        try:
            if not E.tareas_del_plan(E.leer_plan(raiz, track["id"])[1]):
                return "pedirle al `arquitecto` las tareas de `plan.md`."
        except E.ReglaError:
            pass
        sin = [o for o in E.APROBACIONES_PARA_LISTO if E.estado_aprobacion(raiz, track, o)[0] != "ok"]
        if sin:
            return ("esperar la aprobación humana de %s (no la registres tú): %s." % (", ".join(sin), E.comoaprobar(sin[0])))
        return "el track pasa a `listo` en cuanto se registre la última aprobación."
    if estado in ("en_progreso", "correcciones", "en_revision", "verificado"):
        motivo = E.motivo_no_cerrable(raiz, track)
        if motivo is None:
            return "el track cumple los criterios y se cierra solo."
        if E.cumple_criterios_objetivos(raiz, track) and E.politica_de(track) == "humano":
            return "el track cumple los criterios y espera la aprobación humana de cierre: %s." % E.comoaprobar("cierre")
    return {
        "listo": "delegar en `coder` (el hook pasa el track a `en_progreso`).",
        "en_progreso": "continuar con el `coder` hasta completar las tareas.",
        "correcciones": "continuar con el `coder` con las correcciones.",
        "en_revision": "esperar la revisión.",
        "verificado": "completar el cierre del track.",
        "bloqueado": "resolver el bloqueo con la persona.",
    }.get(estado, "revisar el estado.")


def generar(raiz, maximo=MAX_CARACTERES):
    raiz = os.path.abspath(raiz)
    lineas = ["DevSquad AI · puntero de arranque (generado por script; el detalle está en las rutas de abajo)",
              "Proyecto: %s · Carpeta de trabajo: %s" % (recortar(os.path.basename(raiz), 80), raiz),
              "Perfil: %s" % ("ok (%s)" % PERFIL if perfil_ok(raiz) else "FALTA (%s)" % PERFIL)]
    track, tid = None, None
    if os.path.exists(E.ruta_estado(raiz)):
        try:
            estado = E.cargar_estado(raiz)
            tid = estado.get("track_activo")
            track = E.cargar_track(raiz, tid) if tid else None
        except E.ReglaError as e:
            lineas.append("Estado: ILEGIBLE (%s)" % recortar(e, 200))
    else:
        lineas.append("Estado: sin %s/%s todavía" % (E.DIR_ESTADO, E.ARCHIVO_ESTADO))
    if track:
        ts = tareas(raiz, tid)
        hechas = sum(1 for t in ts if t[1] == "x")
        sig = next((t for t in ts if t[1] != "x"), None)
        lineas.append("Track activo: %s (%s) · %s · tareas %d/%d" % (tid, track["estado"], recortar(track.get("titulo", ""), 80),
                                                                     hechas, len(ts)))
        ap = E.resumen_aprobaciones(raiz, track, estado)
        lineas.append("Aprobaciones humanas: arquitectura %s · diseño %s · comandos de verificación %s · cierre %s · política de cierre: %s"
                      % (ap["arquitectura"], ap["diseno"], ap["comandos"], ap["cierre"], E.politica_de(track)))
        lineas.append("Siguiente tarea: %s" % ("%s \"%s\"" % (sig[0], recortar(sig[2], 120)) if sig else "—"))
        lineas.append("Bloqueos: %s" % ("el track está bloqueado (antes: %s)" % (track.get("estado_previo") or "?")
                                         if track["estado"] == "bloqueado" else "ninguno"))
        lineas.append("Detalle del track: %s" % os.path.join(raiz, E.DIR_ESTADO, E.DIR_TRACKS, tid))
    else:
        lineas.append("Track activo: ninguno")
    lineas.append("Último commit: %s" % ultimo_commit(raiz))
    c = M.conteos(raiz)
    lineas.append("Memoria: %d decisiones, %d aprendizajes, %d tracks cerrados → índice (léelo con Read, sin Bash): %s"
                  % (c["decisiones"], c["aprendizajes"], c["tracks_cerrados"], M.ruta_memoria(raiz, M.INDICE)))
    lineas.append("Estado completo: %s" % E.ruta_estado(raiz))
    lineas.append("Siguiente paso sugerido: %s" % siguiente_paso(raiz, track))
    texto = "\n".join(lineas)
    return texto if len(texto) <= maximo else texto[: maximo - 1] + "…"


def main(argv=None):
    p = argparse.ArgumentParser(prog="devsquad_puntero", description="Puntero de arranque de DevSquad AI.")
    p.add_argument("--raiz")
    a = p.parse_args(argv)
    print(generar(E.raiz_proyecto(a.raiz)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
