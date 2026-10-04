"""Pruebas del arranque atómico: puntero (SessionStart) y memoria nivel 1 (índice).

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
SCRIPTS = os.path.join(PLUGIN, "scripts")
HOOK = os.path.join(SCRIPTS, "devsquad_hook.py")
PUNTERO = os.path.join(SCRIPTS, "devsquad_puntero.py")
MEMORIA = os.path.join(SCRIPTS, "devsquad_memoria.py")
LANZADOR = os.path.join(PLUGIN, "bin", "devsquad-estado")
with open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
    NOMBRE = json.load(f)["name"]
MAX = 10000

PERFIL = "# Perfil DevSquad AI\n\n- **Nombre preferido**: Ana\n- **Archivos protegidos**: N/A\n"


class Base(unittest.TestCase):
    def setUp(self):
        self.p = tempfile.mkdtemp(prefix="devsquad-arranque-")
        self.addCleanup(shutil.rmtree, self.p, ignore_errors=True)

    def ruta(self, *partes):
        return os.path.join(self.p, *partes)

    def escribir(self, rel, texto):
        os.makedirs(os.path.dirname(self.ruta(rel)), exist_ok=True)
        with open(self.ruta(rel), "w", encoding="utf-8") as f:
            f.write(texto)

    def leer(self, rel):
        with open(self.ruta(rel), encoding="utf-8") as f:
            return f.read()

    def estado(self, *args, esperado=0):
        r = subprocess.run([LANZADOR, "--raiz", self.p] + list(args), capture_output=True, text=True)
        self.assertEqual(r.returncode, esperado, r.stdout + r.stderr)
        return r

    def puntero(self):
        r = subprocess.run([sys.executable, PUNTERO, "--raiz", self.p], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.rstrip("\n")

    def sessionstart(self, source="startup", agente="orquestador", esperado=0):
        datos = {"hook_event_name": "SessionStart", "source": source}
        if agente:
            datos["agent_type"] = "%s:%s" % (NOMBRE, agente) if ":" not in agente else agente
        r = subprocess.run([sys.executable, HOOK, "sessionstart"], input=json.dumps(datos), capture_output=True,
                           text=True, env=dict(os.environ, CLAUDE_PROJECT_DIR=self.p))
        self.assertEqual(r.returncode, esperado, r.stderr)
        return r

    def proyecto_con_track(self):
        self.escribir(".devsquad/perfil.md", PERFIL)
        self.estado("init")
        self.estado("crear", "pedidos", "--titulo", "Gestión de pedidos")
        self.escribir(".devsquad/tracks/001-pedidos/plan.md", "## Tareas\n- [ ] 1 Crear el modelo\n- [ ] 2 Validar horario\n")

    def aprobar_planeacion(self):
        self.escribir(".devsquad/arquitectura.md", "# A\n\nPolítica de cierre: humano\n")
        self.escribir(".devsquad/diseno.md", "# D\n")
        self.estado("aprobar", "arquitectura", "--fuente", "terminal")
        self.estado("aprobar", "diseno", "--fuente", "terminal")


class PruebasPuntero(Base):
    def test_proyecto_sin_nada(self):
        t = self.puntero()
        self.assertIn("Perfil: FALTA", t)
        self.assertIn("iniciar-proyecto", t)
        self.assertIn("Track activo: ninguno", t)
        self.assertIn(self.p, t)

    def test_con_perfil_sin_estado_sugiere_bsa(self):
        self.escribir(".devsquad/perfil.md", PERFIL)
        t = self.puntero()
        self.assertIn("Perfil: ok", t)
        self.assertIn("delegar en `bsa`", t)

    def test_track_en_borrador_sin_tareas_pide_tareas_al_arquitecto(self):
        self.proyecto_con_track()
        self.escribir(".devsquad/tracks/001-pedidos/plan.md", "## Tareas\n")
        for f in ("requerimientos", "arquitectura", "diseno"):
            self.escribir(".devsquad/%s.md" % f, "# x\n")
        t = self.puntero()
        self.assertIn("Track activo: 001-pedidos (borrador) · Gestión de pedidos · tareas 0/0", t)
        self.assertIn("pedirle al `arquitecto` las tareas", t)

    def test_track_en_borrador_con_tareas_espera_la_aprobacion_humana(self):
        self.proyecto_con_track()
        for f in ("requerimientos", "arquitectura", "diseno"):
            self.escribir(".devsquad/%s.md" % f, "# x\n")
        t = self.puntero()
        self.assertIn("Siguiente tarea: 1 \"Crear el modelo\"", t)
        self.assertIn("Aprobaciones humanas: arquitectura falta · diseño falta", t)
        self.assertIn("esperar la aprobación humana de arquitectura, diseno (no la registres tú)", t)
        self.assertIn("/devsquad-ai:aprobar arquitectura", t)
        self.aprobar_planeacion()
        self.assertIn("Aprobaciones humanas: arquitectura ok · diseño ok", self.puntero())

    def test_cumplidos_los_criterios_espera_la_aprobacion_de_cierre(self):
        self.proyecto_con_track()
        self.aprobar_planeacion()
        self.estado("transicion", "listo")
        self.estado("transicion", "en_progreso")
        for t in ("1", "2"):
            self.estado("tarea", t, "hecha", "--commit", "abcdef1")
        self.estado("transicion", "en_revision")
        t = self.puntero()
        self.assertIn("espera la aprobación humana de cierre", t)
        self.assertIn("política de cierre: humano", t)

    def test_track_en_progreso_con_tareas_hechas(self):
        self.proyecto_con_track()
        self.aprobar_planeacion()
        self.estado("transicion", "listo")
        self.estado("transicion", "en_progreso")
        self.estado("tarea", "1", "hecha", "--commit", "abcdef1")
        t = self.puntero()
        self.assertIn("(en_progreso)", t)
        self.assertIn("tareas 1/2", t)
        self.assertIn("Siguiente tarea: 2 \"Validar horario\"", t)
        self.assertIn("Bloqueos: ninguno", t)

    def test_track_bloqueado_lo_dice(self):
        self.proyecto_con_track()
        self.aprobar_planeacion()
        self.estado("transicion", "listo")
        self.estado("transicion", "en_progreso")
        self.estado("transicion", "bloqueado")
        self.assertIn("el track está bloqueado (antes: en_progreso)", self.puntero())

    def test_ultimo_commit_de_git(self):
        subprocess.run(["git", "-C", self.p, "init", "-q"], check=True)
        self.escribir("a.txt", "a")
        subprocess.run(["git", "-C", self.p, "add", "-A"], check=True)
        subprocess.run(["git", "-C", self.p, "-c", "user.name=t", "-c", "user.email=t@e.c", "commit", "-q", "-m",
                        "Primer commit"], check=True)
        self.assertIn("Último commit: ", self.puntero())
        self.assertIn("Primer commit", self.puntero())

    def test_sin_git(self):
        self.assertIn("Último commit: sin Git", self.puntero()) if shutil.which("git") is None else \
            self.assertRegex(self.puntero(), "Último commit: (sin Git|sin commits)")

    def test_tamano_acotado_aunque_los_datos_sean_enormes(self):
        self.escribir(".devsquad/perfil.md", PERFIL)
        self.estado("init")
        self.estado("crear", "x", "--titulo", "T" * 50000)
        self.escribir(".devsquad/tracks/001-x/plan.md", "- [ ] 1 %s\n" % ("larga " * 20000))
        os.makedirs(self.ruta("carpeta-" + "n" * 100), exist_ok=True)
        t = self.puntero()
        self.assertLessEqual(len(t), MAX)
        self.assertLess(len(t), 2500)  # y en la práctica son unas pocas líneas

    def test_el_tope_duro_corta_aunque_algo_se_desborde(self):
        sys.path.insert(0, SCRIPTS)
        import devsquad_puntero as P
        self.escribir(".devsquad/perfil.md", PERFIL)
        t = P.generar(self.p, maximo=300)
        self.assertLessEqual(len(t), 300)
        self.assertTrue(t.endswith("…"))

    def test_estado_ilegible_no_rompe_el_arranque(self):
        self.escribir(".devsquad/perfil.md", PERFIL)
        self.escribir(".devsquad/estado.json", "{roto")
        self.assertIn("Estado: ILEGIBLE", self.puntero())

    def test_no_hay_rutas_ni_nombres_fijos(self):
        t = self.puntero()
        self.assertNotIn("/home/", t.replace(self.p, ""))
        self.assertIn(os.path.basename(self.p), t)


class PruebasSessionStart(Base):
    def contexto(self, r):
        salida = json.loads(r.stdout)["hookSpecificOutput"]
        self.assertEqual(salida["hookEventName"], "SessionStart")
        return salida["additionalContext"]

    def test_inyecta_el_puntero_en_cada_origen(self):
        self.proyecto_con_track()
        for origen in ("startup", "resume", "clear", "compact"):
            ctx = self.contexto(self.sessionstart(origen))
            self.assertIn("Track activo: 001-pedidos", ctx, origen)
            self.assertLessEqual(len(ctx), MAX)

    def test_el_puntero_trae_la_ruta_del_indice_para_leerlo_con_read(self):
        self.proyecto_con_track()
        ctx = self.contexto(self.sessionstart())
        self.assertIn(self.ruta(".devsquad", "memoria", "indice.md"), ctx)
        self.assertTrue(os.path.exists(self.ruta(".devsquad", "memoria", "indice.md")))

    def test_otro_agente_o_sesion_sin_agente_no_recibe_nada(self):
        self.proyecto_con_track()
        self.assertEqual(self.sessionstart(agente=None).stdout.strip(), "")
        self.assertEqual(self.sessionstart(agente="otro-plugin:orquestador").stdout.strip(), "")

    def test_en_un_proyecto_nuevo_no_crea_carpetas(self):
        ctx = self.contexto(self.sessionstart())
        self.assertIn("FALTA", ctx)
        self.assertFalse(os.path.exists(self.ruta(".devsquad")))

    def test_el_hook_esta_configurado_para_los_cuatro_origenes(self):
        with open(os.path.join(PLUGIN, "hooks", "hooks.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        grupo = cfg["hooks"]["SessionStart"][0]
        self.assertEqual(set(grupo["matcher"].split("|")), {"startup", "resume", "clear", "compact"})
        self.assertNotIn("PreCompact", cfg["hooks"])  # PreCompact no puede inyectar contexto


class PruebasMemoria(Base):
    def indice(self):
        r = subprocess.run([sys.executable, MEMORIA, "--raiz", self.p, "indice"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return self.leer(".devsquad/memoria/indice.md")

    def registro(self, carpeta, nombre, fecha, titulo, etiquetas="", track=""):
        enc = "---\ntipo: x\nfecha: %s\ntitulo: %s\netiquetas: %s\ntrack: %s\n---\nCuerpo.\n" % (fecha, titulo, etiquetas, track)
        self.escribir(".devsquad/memoria/%s/%s.md" % (carpeta, nombre), enc)

    def test_indice_vacio(self):
        i = self.indice()
        self.assertIn("0 decisiones · 0 aprendizajes · 0 tracks", i)
        self.assertEqual(i.count("(ninguno)"), 3)

    def test_indice_lista_registros_con_ruta_y_etiquetas(self):
        self.registro("decisiones", "2026-10-04-sqlite", "2026-10-04", "Usar SQLite al inicio", "base-de-datos, costo", "001-pedidos")
        self.registro("decisiones", "2026-10-01-api", "2026-10-01", "API REST")
        self.registro("aprendizajes", "a1", "2026-10-05", "Los .env no se versionan")
        i = self.indice()
        self.assertIn("2 decisiones · 1 aprendizajes", i)
        self.assertIn("- 2026-10-04 · Usar SQLite al inicio · etiquetas: base-de-datos, costo · track 001-pedidos "
                      "→ .devsquad/memoria/decisiones/2026-10-04-sqlite.md", i)
        self.assertLess(i.index("API REST"), i.index("Usar SQLite"))  # ordenados por fecha

    def test_indice_incluye_los_tracks_con_su_estado(self):
        self.proyecto_con_track()
        i = self.indice()
        self.assertIn("- 001-pedidos · borrador · Gestión de pedidos → .devsquad/tracks/001-pedidos/spec.md", i)

    def test_registro_sin_encabezado_usa_el_nombre_de_archivo(self):
        self.escribir(".devsquad/memoria/decisiones/sin-encabezado.md", "solo texto\n")
        self.assertIn("sin-encabezado", self.indice())

    def test_el_indice_es_determinista_y_no_se_reescribe_si_no_cambia(self):
        self.proyecto_con_track()
        a = self.indice()
        mtime = os.path.getmtime(self.ruta(".devsquad/memoria/indice.md"))
        b = self.indice()
        self.assertEqual(a, b)
        self.assertEqual(mtime, os.path.getmtime(self.ruta(".devsquad/memoria/indice.md")))

    def test_el_puntero_cuenta_la_memoria(self):
        self.proyecto_con_track()
        self.registro("decisiones", "d1", "2026-10-04", "Algo")
        self.assertIn("Memoria: 1 decisiones, 0 aprendizajes, 0 tracks cerrados", self.puntero())

    def test_el_indice_se_regenera_al_terminar_un_agente(self):
        self.proyecto_con_track()
        self.registro("decisiones", "d1", "2026-10-04", "Decisión nueva")
        subprocess.run([sys.executable, HOOK, "subagentstop"], check=True, capture_output=True, text=True,
                       input=json.dumps({"hook_event_name": "SubagentStop", "agent_id": "a",
                                         "agent_type": "%s:orquestador" % NOMBRE}),
                       env=dict(os.environ, CLAUDE_PROJECT_DIR=self.p))
        self.assertIn("Decisión nueva", self.leer(".devsquad/memoria/indice.md"))


class PruebasPrompts(unittest.TestCase):
    """Los prompts deben coincidir con la realidad: el estado vive en estado.json y lo avanzan los hooks."""

    def textos(self):
        for carpeta in ("agents", "skills"):
            for raiz, _, archivos in os.walk(os.path.join(PLUGIN, carpeta)):
                for a in archivos:
                    if a.endswith(".md"):
                        ruta = os.path.join(raiz, a)
                        with open(ruta, encoding="utf-8") as f:
                            yield os.path.relpath(ruta, PLUGIN), f.read()

    def test_ningun_prompt_menciona_todowrite_ni_estado_md(self):
        for ruta, texto in self.textos():
            self.assertNotIn("TodoWrite", texto, ruta)
            self.assertNotIn("estado.md", texto, ruta)

    def test_el_arquitecto_escribe_las_tareas_del_plan(self):
        with open(os.path.join(PLUGIN, "agents", "arquitecto.md"), encoding="utf-8") as f:
            t = f.read()
        self.assertIn("track_activo", t)
        self.assertIn("plan.md", t)
        self.assertIn("- [ ] <id> <texto>", t)

    def test_el_orquestador_no_tiene_bash_y_sabe_leer_el_puntero(self):
        with open(os.path.join(PLUGIN, "agents", "orquestador.md"), encoding="utf-8") as f:
            t = f.read()
        tools = [l for l in t.split("\n") if l.startswith("tools:")][0]
        self.assertNotIn("Bash", tools)
        self.assertIn("puntero de arranque", t)
        self.assertIn("buscar-memoria", t)

    def test_frontmatter_sin_dos_puntos_ni_almohadilla_sin_comillas(self):
        """La CI valida el frontmatter como YAML (con pyyaml, que aquí no está): `clave: a: b` no es válido."""
        for ruta, texto in self.textos():
            if not texto.startswith("---\n"):
                continue
            for linea in texto[4:texto.index("\n---", 4)].split("\n"):
                if ":" not in linea or linea.startswith((" ", "-")):
                    continue
                valor = linea.split(":", 1)[1].strip()
                if valor and valor[0] not in "\"'":
                    self.assertNotIn(": ", valor, "%s: %s" % (ruta, linea[:80]))
                    self.assertNotIn(" #", valor, "%s: %s" % (ruta, linea[:80]))

    def test_las_skills_de_decision_humana_no_las_puede_invocar_el_modelo(self):
        for nombre in ("aprobar", "cancelar"):
            with open(os.path.join(PLUGIN, "skills", nombre, "SKILL.md"), encoding="utf-8") as f:
                t = f.read()
            self.assertIn("\ndisable-model-invocation: true\n", t[:t.index("\n---", 4)], nombre)

    def test_el_orquestador_sabe_pedir_las_aprobaciones_en_cada_modo(self):
        with open(os.path.join(PLUGIN, "agents", "orquestador.md"), encoding="utf-8") as f:
            t = f.read()
        for texto in ("/devsquad-ai:aprobar arquitectura", "/devsquad-ai:aprobar cierre", 'kind: "approval"',
                      "/devsquad-ai:cancelar", "no las registras tú"):
            self.assertIn(texto, t)

    def test_el_arquitecto_declara_la_politica_de_cierre_y_solo_humano(self):
        with open(os.path.join(PLUGIN, "agents", "arquitecto.md"), encoding="utf-8") as f:
            t = f.read()
        self.assertIn("**Política de cierre**: humano", t)
        self.assertIn("única disponible hoy", t)

    def test_la_skill_de_memoria_existe(self):
        self.assertTrue(os.path.exists(os.path.join(PLUGIN, "skills", "buscar-memoria", "SKILL.md")))


if __name__ == "__main__":
    unittest.main()
