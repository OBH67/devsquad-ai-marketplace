#!/usr/bin/env python3
"""Memoria del proyecto, nivel 1: registros atómicos + un índice que se lee con Read.

Un archivo por decisión o aprendizaje en `.devsquad/memoria/<tipo>/*.md`, con
un encabezado:

    ---
    tipo: decision            (decision | aprendizaje)
    fecha: 2026-10-04
    titulo: Usar SQLite al inicio
    etiquetas: base-de-datos, costo
    track: 001-inicial        (opcional)
    ---
    Cuerpo libre.

`indice` genera `.devsquad/memoria/indice.md` (determinista, sin fechas de
generación, para no ensuciar Git): una línea por registro y por track, con su
ruta. El agente lee el índice con Read y luego el registro que le interese.
Los niveles 2 (texto completo) y 3 (significado) quedan para después.

Uso: devsquad_memoria.py indice [--raiz RUTA]
"""
import sys

if sys.version_info < (3, 8):
    sys.stderr.write("devsquad_memoria: se requiere Python 3.8 o superior.\n")
    sys.exit(1)

import argparse
import os
import re

import devsquad_estado as E

DIR_MEMORIA = "memoria"
INDICE = "indice.md"
TIPOS = (("decision", "decisiones", "Decisiones"), ("aprendizaje", "aprendizajes", "Aprendizajes"))
ENCABEZADO = "# Índice de memoria\n\n<!-- Generado por devsquad_memoria.py; no se edita a mano. -->\n"


def ruta_memoria(raiz, *partes):
    return os.path.join(raiz, E.DIR_ESTADO, DIR_MEMORIA, *partes)


def leer_registro(ruta):
    """{'titulo', 'fecha', 'etiquetas', 'track', 'tipo'} del encabezado (con valores por defecto)."""
    datos = {}
    try:
        with open(ruta, encoding="utf-8") as f:
            texto = f.read()
    except (OSError, UnicodeDecodeError):
        texto = ""
    m = re.match(r"^---\n(.*?)\n---\s*(\n|$)", texto, re.DOTALL)
    if m:
        for linea in m.group(1).split("\n"):
            if ":" in linea:
                clave, valor = linea.split(":", 1)
                datos[clave.strip().lower()] = valor.strip()
    nombre = os.path.splitext(os.path.basename(ruta))[0]
    datos.setdefault("titulo", nombre)
    datos.setdefault("fecha", "")
    datos.setdefault("etiquetas", "")
    datos.setdefault("track", "")
    return datos


def registros(raiz):
    """{tipo: [(ruta_relativa, datos)]} ordenados por fecha y nombre."""
    salida = {}
    for tipo, carpeta, _ in TIPOS:
        base = ruta_memoria(raiz, carpeta)
        lista = []
        if os.path.isdir(base):
            for nombre in sorted(os.listdir(base)):
                if nombre.endswith(".md"):
                    ruta = os.path.join(base, nombre)
                    rel = os.path.relpath(ruta, raiz).replace(os.sep, "/")
                    lista.append((rel, leer_registro(ruta)))
        lista.sort(key=lambda r: (r[1]["fecha"], r[0]))
        salida[tipo] = lista
    return salida


def tracks(raiz):
    """[(id, titulo, estado)] de todos los tracks."""
    lista = []
    for t in E.listar_tracks(raiz):
        try:
            track = E.cargar_track(raiz, t)
            lista.append((t, track.get("titulo", t), track.get("estado", "?")))
        except E.ReglaError:
            lista.append((t, t, "ilegible"))
    return lista


def conteos(raiz):
    r = registros(raiz)
    return {"decisiones": len(r["decision"]), "aprendizajes": len(r["aprendizaje"]),
            "tracks": len(tracks(raiz)), "tracks_cerrados": sum(1 for t in tracks(raiz) if t[2] == "cerrado")}


def construir_indice(raiz):
    regs = registros(raiz)
    lista_tracks = tracks(raiz)
    c = conteos(raiz)
    lineas = [ENCABEZADO.rstrip("\n"), "",
              "Registros: %d decisiones · %d aprendizajes · %d tracks (%d cerrados)"
              % (c["decisiones"], c["aprendizajes"], c["tracks"], c["tracks_cerrados"]), "",
              "## Tracks", ""]
    lineas += ["- %s · %s · %s → %s/%s/%s/spec.md" % (t, estado, titulo, E.DIR_ESTADO, E.DIR_TRACKS, t)
               for t, titulo, estado in lista_tracks] or ["- (ninguno)"]
    for tipo, _, titulo_seccion in TIPOS:
        lineas += ["", "## %s" % titulo_seccion, ""]
        if not regs[tipo]:
            lineas.append("- (ninguno)")
        for rel, d in regs[tipo]:
            extra = []
            if d["etiquetas"]:
                extra.append("etiquetas: " + d["etiquetas"])
            if d["track"]:
                extra.append("track " + d["track"])
            lineas.append("- %s · %s%s → %s" % (d["fecha"] or "s/f", d["titulo"],
                                                (" · " + " · ".join(extra)) if extra else "", rel))
    return "\n".join(lineas) + "\n"


def escribir_indice(raiz):
    """Escribe el índice solo si cambió. Devuelve la ruta."""
    ruta = ruta_memoria(raiz, INDICE)
    nuevo = construir_indice(raiz)
    try:
        with open(ruta, encoding="utf-8") as f:
            if f.read() == nuevo:
                return ruta
    except OSError:
        pass
    E.escribir_atomico(ruta, nuevo)
    return ruta


def main(argv=None):
    p = argparse.ArgumentParser(prog="devsquad_memoria", description="Memoria del proyecto (nivel 1).")
    p.add_argument("--raiz")
    p.add_argument("cmd", choices=("indice",))
    a = p.parse_args(argv)
    raiz = E.raiz_proyecto(a.raiz)
    print(escribir_indice(raiz))
    return 0


if __name__ == "__main__":
    sys.exit(main())
