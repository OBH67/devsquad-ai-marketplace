"""Pruebas de comportamiento de devsquad-estado (solo unittest).

Ejecutar desde la raíz del repositorio:
    python3 -m unittest discover -s tests -v
"""
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


class Base(unittest.TestCase):
    def setUp(self):
        self.proyecto = tempfile.mkdtemp(prefix="devsquad-prueba-")
        self.addCleanup(shutil.rmtree, self.proyecto, ignore_errors=True)

    def ejecutar(self, *args, esperado=0, entorno=None):
        env = dict(os.environ)
        env.pop("CLAUDE_PROJECT_DIR", None)
        env.update(entorno or {})
        r = subprocess.run([LANZADOR, "--raiz", self.proyecto] + list(args),
                           capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, esperado,
                         "código %s (esperado %s)\nstdout: %s\nstderr: %s"
                         % (r.returncode, esperado, r.stdout, r.stderr))
        return r

    def ruta(self, *partes):
        return os.path.join(self.proyecto, ".devsquad", *partes)

    def json(self, *partes):
        with open(self.ruta(*partes), encoding="utf-8") as f:
            return json.load(f)

    def leer(self, *partes):
        with open(self.ruta(*partes), encoding="utf-8") as f:
            return f.read()

    def escribir(self, partes, texto):
        with open(self.ruta(*partes), "w", encoding="utf-8") as f:
            f.write(texto)

    def git(self, *args):
        return subprocess.run(["git", "-C", self.proyecto] + list(args),
                              capture_output=True, text=True, check=True).stdout.strip()

    def repo_con_commit(self):
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "Prueba")
        with open(os.path.join(self.proyecto, "a.txt"), "w") as f:
            f.write("a")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "inicial")
        return self.git("rev-parse", "HEAD")

    def track_listo_en_progreso(self, tareas=("1", "2")):
        self.ejecutar("init")
        self.ejecutar("crear", "autenticacion")
        plan = "# Plan\n" + "".join("- [ ] %s Tarea %s\n" % (t, t) for t in tareas)
        self.escribir(("tracks", "001-autenticacion", "plan.md"), plan)
        self.ejecutar("transicion", "listo")
        self.ejecutar("transicion", "en_progreso")


class PruebasInicio(Base):
    def test_init_crea_estado_con_schema_version(self):
        self.ejecutar("init")
        estado = self.json("estado.json")
        self.assertEqual(estado["schema_version"], 1)
        self.assertIsNone(estado["track_activo"])

    def test_init_es_idempotente(self):
        self.ejecutar("init")
        antes = self.leer("estado.json")
        self.ejecutar("init")
        self.assertEqual(antes, self.leer("estado.json"))

    def test_sin_init_los_comandos_piden_init(self):
        r = self.ejecutar("estado", esperado=1)
        self.assertIn("devsquad-estado init", r.stderr)

    def test_raiz_por_variable_de_entorno(self):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.proyecto)
        subprocess.run([LANZADOR, "init"], env=env, cwd=tempfile.gettempdir(), check=True, capture_output=True)
        self.assertTrue(os.path.exists(self.ruta("estado.json")))


class PruebasEsquema(Base):
    def test_version_mas_nueva_se_rechaza_con_mensaje(self):
        self.ejecutar("init")
        estado = self.json("estado.json")
        estado["schema_version"] = 99
        self.escribir(("estado.json",), json.dumps(estado))
        r = self.ejecutar("estado", esperado=1)
        self.assertIn("actualiza el plugin", r.stderr)

    def test_version_mas_vieja_pide_migrar(self):
        self.ejecutar("init")
        estado = self.json("estado.json")
        estado["schema_version"] = 0
        self.escribir(("estado.json",), json.dumps(estado))
        r = self.ejecutar("estado", esperado=1)
        self.assertIn("devsquad-estado migrar", r.stderr)

    def test_migrar_en_version_vigente_no_hace_nada(self):
        self.ejecutar("init")
        r = self.ejecutar("migrar")
        self.assertIn("ya está", r.stdout)

    def test_json_corrupto_da_mensaje_claro(self):
        self.ejecutar("init")
        self.escribir(("estado.json",), "{no es json")
        r = self.ejecutar("estado", esperado=1)
        self.assertIn("no es JSON válido", r.stderr)


class PruebasTracks(Base):
    def test_crear_track_numera_y_lo_deja_activo(self):
        self.ejecutar("init")
        self.ejecutar("crear", "autenticacion")
        self.assertEqual(self.json("estado.json")["track_activo"], "001-autenticacion")
        track = self.json("tracks", "001-autenticacion", "track.json")
        self.assertEqual((track["schema_version"], track["estado"]), (1, "borrador"))
        for nombre in ("spec.md", "plan.md"):
            self.assertTrue(os.path.exists(self.ruta("tracks", "001-autenticacion", nombre)))

    def test_no_se_abre_otro_track_con_uno_abierto(self):
        self.ejecutar("init")
        self.ejecutar("crear", "uno")
        r = self.ejecutar("crear", "dos", esperado=1)
        self.assertIn("001-uno", r.stderr)
        self.assertIn("cerrarlo", r.stderr)
        self.assertFalse(os.path.exists(self.ruta("tracks", "002-dos")))

    def test_slug_invalido(self):
        self.ejecutar("init")
        self.ejecutar("crear", "Con Espacios", esperado=1)

    def test_listo_exige_tareas(self):
        self.ejecutar("init")
        self.ejecutar("crear", "uno")
        self.escribir(("tracks", "001-uno", "plan.md"), "# Plan sin tareas\n")
        r = self.ejecutar("transicion", "listo", esperado=1)
        self.assertIn("sin tareas", r.stderr)

    def test_transicion_no_permitida_lista_las_permitidas(self):
        self.ejecutar("init")
        self.ejecutar("crear", "uno")
        r = self.ejecutar("transicion", "en_progreso", esperado=1)
        self.assertIn("borrador → en_progreso", r.stderr)
        self.assertIn("listo", r.stderr)

    def test_revision_exige_tareas_completas(self):
        self.track_listo_en_progreso()
        r = self.ejecutar("transicion", "en_revision", esperado=1)
        self.assertIn("faltan tareas", r.stderr)

    def test_bloquear_y_desbloquear_vuelve_al_estado_previo(self):
        self.track_listo_en_progreso()
        self.ejecutar("transicion", "bloqueado")
        self.assertEqual(self.json("tracks", "001-autenticacion", "track.json")["estado"], "bloqueado")
        self.ejecutar("crear", "otro", esperado=1)  # bloqueado sigue ocupando el lugar
        self.ejecutar("desbloquear")
        self.assertEqual(self.json("tracks", "001-autenticacion", "track.json")["estado"], "en_progreso")

    def test_cerrado_solo_con_cerrar(self):
        self.track_listo_en_progreso()
        r = self.ejecutar("transicion", "cerrado", esperado=2)  # argparse: no es opción válida
        self.assertIn("invalid choice", r.stderr)


class PruebasTareasYCierre(Base):
    def test_tarea_hecha_exige_commit(self):
        self.track_listo_en_progreso()
        r = self.ejecutar("tarea", "1", "hecha", esperado=1)
        self.assertIn("--commit", r.stderr)

    def test_tarea_hecha_registra_el_commit_real(self):
        sha = self.repo_con_commit()
        self.track_listo_en_progreso()
        self.ejecutar("tarea", "1", "hecha", "--commit", sha[:7])
        plan = self.leer("tracks", "001-autenticacion", "plan.md")
        self.assertIn("- [x] 1 Tarea 1 (commit %s)" % sha[:7], plan)

    def test_commit_inexistente_se_rechaza_en_un_repo(self):
        self.repo_con_commit()
        self.track_listo_en_progreso()
        r = self.ejecutar("tarea", "1", "hecha", "--commit", "deadbeef", esperado=1)
        self.assertIn("no existe", r.stderr)

    def test_tarea_inexistente(self):
        self.track_listo_en_progreso()
        self.ejecutar("tarea", "9", "hecha", "--commit", "abcdef1", esperado=1)

    def test_volver_a_pendiente_quita_el_commit(self):
        self.track_listo_en_progreso()
        self.ejecutar("tarea", "1", "hecha", "--commit", "abcdef1")  # sin repo git: no se puede comprobar
        self.ejecutar("tarea", "1", "pendiente")
        plan = self.leer("tracks", "001-autenticacion", "plan.md")
        self.assertIn("- [ ] 1 Tarea 1\n", plan)
        self.assertNotIn("commit", plan.split("Tarea 1")[1].split("\n")[0])

    def test_cierre_con_tareas_abiertas_se_niega(self):
        self.track_listo_en_progreso()
        self.ejecutar("tarea", "1", "hecha", "--commit", "abcdef1")
        r = self.ejecutar("cerrar", esperado=1)
        self.assertIn("faltan tareas", r.stderr)
        self.assertIn("2", r.stderr)
        self.assertEqual(self.json("estado.json")["track_activo"], "001-autenticacion")

    def test_cierre_exitoso_libera_el_lugar(self):
        self.track_listo_en_progreso()
        for t in ("1", "2"):
            self.ejecutar("tarea", t, "hecha", "--commit", "abcdef1")
        self.ejecutar("cerrar")
        self.assertIsNone(self.json("estado.json")["track_activo"])
        self.assertEqual(self.json("tracks", "001-autenticacion", "track.json")["estado"], "cerrado")
        self.ejecutar("crear", "segundo")
        self.assertEqual(self.json("estado.json")["track_activo"], "002-segundo")

    def test_plan_sin_tareas_no_se_cierra(self):
        self.track_listo_en_progreso()
        self.escribir(("tracks", "001-autenticacion", "plan.md"), "# vacío\n")
        r = self.ejecutar("cerrar", esperado=1)
        self.assertIn("no tiene tareas", r.stderr)

    def test_cierre_desde_borrador_se_niega(self):
        self.ejecutar("init")
        self.ejecutar("crear", "uno")
        self.ejecutar("cerrar", esperado=1)

    def _completar(self):
        self.track_listo_en_progreso(tareas=("1",))
        self.ejecutar("tarea", "1", "hecha", "--commit", "abcdef1")

    def _verificado(self):
        self._completar()
        self.ejecutar("transicion", "en_revision")
        self.ejecutar("transicion", "verificado")

    def test_gancho_presente_exige_estado_verificado(self):
        self._completar()
        self.escribir(("tracks", "001-autenticacion", "revision.json"), json.dumps({"aprobado": True}))
        r = self.ejecutar("cerrar", esperado=1)
        self.assertIn("verificado", r.stderr)
        self.assertIn("revision.json", r.stderr)

    def test_gancho_revision_rechazada_bloquea(self):
        self._verificado()
        self.escribir(("tracks", "001-autenticacion", "revision.json"), json.dumps({"aprobado": False}))
        r = self.ejecutar("cerrar", esperado=1)
        self.assertIn("revision.json", r.stderr)

    def test_gancho_verificacion_ilegible_bloquea(self):
        self._verificado()
        self.escribir(("tracks", "001-autenticacion", "verificacion.json"), "no json")
        self.ejecutar("cerrar", esperado=1)

    def test_ganchos_aprobados_dejan_cerrar_desde_verificado(self):
        self._verificado()
        for n in ("revision.json", "verificacion.json"):
            self.escribir(("tracks", "001-autenticacion", n), json.dumps({"aprobado": True}))
        self.ejecutar("cerrar")

    def test_sin_ganchos_se_cierra(self):
        self._completar()
        self.ejecutar("cerrar")


class PruebasValidarYEstado(Base):
    def test_validar_estado_sano(self):
        self.track_listo_en_progreso()
        self.ejecutar("validar")

    def test_validar_detecta_dos_tracks_abiertos(self):
        self.track_listo_en_progreso()
        carpeta = self.ruta("tracks", "002-intruso")
        os.makedirs(carpeta)
        self.escribir(("tracks", "002-intruso", "track.json"),
                      json.dumps({"schema_version": 1, "id": "002-intruso", "titulo": "x",
                                  "estado": "borrador", "estado_previo": None}))
        self.escribir(("tracks", "002-intruso", "plan.md"), "- [ ] 1 x\n")
        r = self.ejecutar("validar", esperado=1)
        self.assertIn("solo se permite uno", r.stderr)

    def test_validar_detecta_tarea_hecha_sin_commit(self):
        self.track_listo_en_progreso()
        self.escribir(("tracks", "001-autenticacion", "plan.md"), "- [x] 1 editada a mano\n")
        r = self.ejecutar("validar", esperado=1)
        self.assertIn("sin commit", r.stderr)

    def test_estado_json_resume_el_track_activo(self):
        self.track_listo_en_progreso()
        datos = json.loads(self.ejecutar("estado", "--json").stdout)
        activo = datos["track_activo"]
        self.assertEqual((activo["id"], activo["tareas_total"], activo["siguiente_tarea"]),
                         ("001-autenticacion", 2, "1"))

    def test_advierte_si_git_ignora_devsquad(self):
        self.repo_con_commit()
        with open(os.path.join(self.proyecto, ".gitignore"), "w") as f:
            f.write(".devsquad/\n")
        r = self.ejecutar("init")
        self.assertIn("ignorando .devsquad", r.stderr)

    def test_no_advierte_si_se_versiona(self):
        self.repo_con_commit()
        r = self.ejecutar("init")
        self.assertNotIn("ignorando", r.stderr)


class PruebasLanzador(unittest.TestCase):
    def test_sin_python3_falla_con_mensaje_claro(self):
        vacio = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, vacio, ignore_errors=True)
        r = subprocess.run(["/bin/sh", LANZADOR, "estado"], capture_output=True, text=True,
                           env={"PATH": vacio})
        self.assertEqual(r.returncode, 127)
        self.assertIn("python3", r.stderr)
        self.assertIn("Windows", r.stderr)

    def test_el_script_corre_con_cada_python_disponible(self):
        script = os.path.join(PLUGIN, "scripts", "devsquad_estado.py")
        probados = 0
        for version in ("3.8", "3.9", "3.10", "3.11", "3.12", "3.13"):
            exe = shutil.which("python" + version)
            if not exe:
                continue
            probados += 1
            tmp = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
            r = subprocess.run([exe, script, "--raiz", tmp, "init"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, "python%s: %s" % (version, r.stderr))
        if not probados:
            self.skipTest("no hay intérpretes python3.X con versión explícita")


if __name__ == "__main__":
    unittest.main()
