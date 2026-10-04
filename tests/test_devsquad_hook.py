"""Pruebas de comportamiento de las compuertas (hooks) de DevSquad AI.

Se ejecuta el hook como lo hace Claude Code: JSON por stdin, variable
CLAUDE_PROJECT_DIR y código de salida (2 = bloquea, mensaje por stderr).

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
HOOK = os.path.join(PLUGIN, "scripts", "devsquad_hook.py")
LANZADOR = os.path.join(PLUGIN, "bin", "devsquad-estado")
with open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
    NOMBRE = json.load(f)["name"]

PERFIL = """# Perfil DevSquad AI

- **Nombre preferido**: Ana
- **Stack**: Python
- **Archivos protegidos**: `src/runtime/`, `config/*.yaml`
- **Reglas de negocio / contexto de empresa**: N/A

## Comandos de verificación

- Lint: `true`
- Pruebas: `true`

_Última actualización: hoy_
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.p = tempfile.mkdtemp(prefix="devsquad-hook-")
        self.addCleanup(shutil.rmtree, self.p, ignore_errors=True)

    # --- ayudas
    def ruta(self, *partes):
        return os.path.join(self.p, *partes)

    def escribir(self, rel, texto):
        ruta = self.ruta(rel)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(texto)

    def leer_json(self, rel):
        with open(self.ruta(rel), encoding="utf-8") as f:
            return json.load(f)

    def estado(self, *args, esperado=0):
        r = subprocess.run([LANZADOR, "--raiz", self.p] + list(args), capture_output=True, text=True)
        self.assertEqual(r.returncode, esperado, r.stdout + r.stderr)
        return r

    def hook(self, evento, datos, agente="coder", esperado=0):
        datos = dict(datos)
        if agente is not None:
            datos["agent_type"] = agente if ("!" in agente or ":" in agente) else "%s:%s" % (NOMBRE, agente)
            datos["agent_type"] = datos["agent_type"].replace("!", "")
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.p)
        r = subprocess.run([sys.executable, HOOK, evento], input=json.dumps(datos), capture_output=True,
                           text=True, env=env)
        self.assertEqual(r.returncode, esperado, "stdout: %s\nstderr: %s" % (r.stdout, r.stderr))
        return r

    def pre(self, tool, tool_input, **kw):
        return self.hook("pretooluse", {"hook_event_name": "PreToolUse", "tool_name": tool,
                                        "tool_input": tool_input}, **kw)

    def escribe(self, rel, contenido="x = 1\n", **kw):
        return self.pre("Write", {"file_path": self.ruta(rel), "content": contenido}, **kw)

    def delega(self, destino, **kw):
        return self.pre("Agent", {"subagent_type": "%s:%s" % (NOMBRE, destino), "prompt": "p"}, **kw)

    def perfil(self, texto=PERFIL):
        self.escribir(".devsquad/perfil.md", texto)

    def docs(self, *nombres):
        for n in nombres:
            self.escribir(".devsquad/%s" % n, "# %s\n" % n)

    def track(self, estado_final="en_progreso", tareas=("1", "2")):
        """Crea un track con tareas y lo lleva al estado pedido."""
        self.estado("init")
        self.estado("crear", "inicial")
        self.escribir(".devsquad/tracks/001-inicial/plan.md", "".join("- [ ] %s T%s\n" % (t, t) for t in tareas))
        for e in ("listo", "en_progreso"):
            self.estado("transicion", e)
            if e == estado_final:
                break


class PruebasAlcance(Base):
    def test_sin_agente_no_hace_nada(self):
        self.escribe("src/a.py", agente=None)  # sin perfil y sin agent_type: pasa

    def test_agente_de_otro_espacio_de_nombres_no_se_toca(self):
        self.escribe("src/a.py", agente="otro-plugin:coder")

    def test_agente_sin_espacio_de_nombres_no_se_toca(self):
        self.escribe("src/a.py", agente="!coder")

    def test_agente_desconocido_del_plugin_no_se_toca(self):
        self.escribe("src/a.py", agente="%s:inventado" % NOMBRE)

    def test_entrada_corrupta_no_bloquea(self):
        r = subprocess.run([sys.executable, HOOK, "pretooluse"], input="no json", capture_output=True, text=True,
                           env=dict(os.environ, CLAUDE_PROJECT_DIR=self.p))
        self.assertEqual(r.returncode, 1)  # fallo propio: no bloqueante


class PruebasPerfil(Base):
    def test_sin_perfil_se_niega_todo_menos_escribir_el_perfil(self):
        for tool, ti in (("Write", {"file_path": self.ruta("src/a.py"), "content": "x"}),
                         ("Edit", {"file_path": self.ruta("src/a.py"), "new_string": "x"}),
                         ("Bash", {"command": "ls"}),
                         ("Agent", {"subagent_type": "%s:bsa" % NOMBRE})):
            r = self.pre(tool, ti, agente="orquestador", esperado=2)
            self.assertIn("iniciar-proyecto", r.stderr, tool)
        self.pre("Write", {"file_path": self.ruta(".devsquad/perfil.md"), "content": PERFIL}, agente="orquestador")

    def test_perfil_vacio_o_sin_titulo_no_vale(self):
        self.perfil("")
        self.pre("Bash", {"command": "ls"}, esperado=2)
        self.perfil("hola")
        self.pre("Bash", {"command": "ls"}, esperado=2)

    def test_con_perfil_pasa_y_crea_estado(self):
        self.perfil()
        self.pre("Bash", {"command": "ls"})
        self.assertTrue(os.path.exists(self.ruta(".devsquad/estado.json")))

    def test_el_mensaje_dice_el_paso_siguiente(self):
        r = self.pre("Bash", {"command": "ls"}, esperado=2)
        self.assertIn("Siguiente paso", r.stderr)


class PruebasSecretosYProtegidos(Base):
    def setUp(self):
        super().setUp()
        self.perfil()
        self.track()

    def test_env_se_niega_pero_el_ejemplo_no(self):
        r = self.escribe(".env", "A=1", esperado=2)
        self.assertIn("secretos", r.stderr)
        self.escribe("config/.env.local", "A=1", esperado=2)
        self.escribe(".env.example", "A=")

    def test_llaves_en_el_contenido(self):
        for secreto in ("AKIAABCDEFGHIJKLMNOP", "sk-ant-api03-abcdefghijklmnopqrstu",
                        "-----BEGIN RSA PRIVATE KEY-----", "ghp_" + "a" * 36):
            self.escribe("src/a.py", "k = '%s'\n" % secreto, esperado=2)

    def test_edit_tambien_se_revisa(self):
        self.pre("Edit", {"file_path": self.ruta("src/a.py"), "new_string": "AKIAABCDEFGHIJKLMNOP"}, esperado=2)

    def test_protegidos_por_directorio_y_por_patron(self):
        r = self.escribe("src/runtime/motor.py", esperado=2)
        self.assertIn("protegido", r.stderr)
        self.assertIn("pregúntale", r.stderr)
        self.escribe("config/app.yaml", esperado=2)
        self.escribe("src/otro/motor.py")
        self.escribe("config/app.json")

    def test_sin_protegidos_declarados(self):
        self.perfil(PERFIL.replace("`src/runtime/`, `config/*.yaml`", "N/A"))
        self.escribe("src/runtime/motor.py")

    def test_protegidos_sin_acentos_graves(self):
        self.perfil(PERFIL.replace("`src/runtime/`, `config/*.yaml`", "src/runtime/, docs/leeme.md"))
        self.escribe("src/runtime/x.py", esperado=2)
        self.escribe("docs/leeme.md", esperado=2)


class PruebasOrdenDeFasesYTracks(Base):
    def setUp(self):
        super().setUp()
        self.perfil()

    def test_bsa_se_puede_invocar_primero(self):
        self.delega("bsa", agente="orquestador")

    def test_arquitecto_exige_requerimientos(self):
        r = self.delega("arquitecto", agente="orquestador", esperado=2)
        self.assertIn("requerimientos.md", r.stderr)
        self.assertIn("bsa", r.stderr)
        self.docs("requerimientos.md")
        self.delega("arquitecto", agente="orquestador")

    def test_disenador_exige_arquitectura(self):
        self.docs("requerimientos.md")
        self.delega("disenador", agente="orquestador", esperado=2)
        self.docs("arquitectura.md")
        self.delega("disenador", agente="orquestador")

    def test_coder_sin_diseno_se_niega(self):
        self.docs("requerimientos.md", "arquitectura.md")
        r = self.delega("coder", agente="orquestador", esperado=2)
        self.assertIn("diseno.md", r.stderr)

    def test_coder_sin_track_se_niega(self):
        self.docs("requerimientos.md", "arquitectura.md", "diseno.md")
        r = self.delega("coder", agente="orquestador", esperado=2)
        self.assertIn("track", r.stderr)

    def test_coder_con_track_en_borrador_se_niega_con_pista(self):
        self.docs("requerimientos.md", "arquitectura.md", "diseno.md")
        self.estado("init")
        self.estado("crear", "inicial")
        r = self.delega("coder", agente="orquestador", esperado=2)
        self.assertIn("borrador", r.stderr)
        self.assertIn("plan.md", r.stderr)

    def test_coder_con_track_listo_lo_pasa_a_en_progreso(self):
        self.docs("requerimientos.md", "arquitectura.md", "diseno.md")
        self.track("listo")
        self.delega("coder", agente="orquestador")
        self.assertEqual(self.leer_json(".devsquad/tracks/001-inicial/track.json")["estado"], "en_progreso")

    def test_otros_subagentes_no_se_restringen(self):
        self.pre("Agent", {"subagent_type": "Explore", "prompt": "p"}, agente="orquestador")

    def test_escribir_codigo_exige_track_en_trabajo(self):
        r = self.escribe("src/a.py", esperado=2)
        self.assertIn("track", r.stderr)
        self.track("listo")
        self.escribe("src/a.py", esperado=2)  # listo todavía no es trabajo
        self.estado("transicion", "en_progreso")
        self.escribe("src/a.py")

    def test_escribir_en_devsquad_no_exige_track(self):
        self.escribe(".devsquad/requerimientos.md", "# r\n", agente="bsa")


class PruebasSubagentStopPlaneacion(Base):
    def stop(self, agente):
        return self.hook("subagentstop", {"hook_event_name": "SubagentStop", "agent_id": "a1",
                                          "last_assistant_message": "listo"}, agente=agente)

    def setUp(self):
        super().setUp()
        self.perfil()

    def test_bsa_crea_el_track_con_slug_del_titulo(self):
        self.escribir(".devsquad/requerimientos.md", "# Sistema de Pedidos y Envíos\n")
        r = self.stop("bsa")
        self.assertIn("001-sistema-de-pedidos-y-envios", json.loads(r.stdout)["systemMessage"])
        self.assertEqual(self.leer_json(".devsquad/estado.json")["track_activo"], "001-sistema-de-pedidos-y-envios")

    def test_bsa_sin_entregable_no_crea_nada(self):
        r = self.stop("bsa")
        self.assertEqual(r.stdout.strip(), "")

    def test_bsa_con_track_abierto_no_crea_otro(self):
        self.track("listo")
        self.escribir(".devsquad/requerimientos.md", "# Otro\n")
        self.stop("bsa")
        self.assertEqual(self.leer_json(".devsquad/estado.json")["track_activo"], "001-inicial")
        self.assertFalse(os.path.exists(self.ruta(".devsquad/tracks/002-otro")))

    def test_el_track_pasa_a_listo_cuando_hay_los_tres_entregables_y_tareas(self):
        self.estado("init")
        self.estado("crear", "inicial")
        self.docs("requerimientos.md", "arquitectura.md", "diseno.md")
        r = self.stop("disenador")
        self.assertIn("sin tareas", json.loads(r.stdout)["systemMessage"])
        self.assertEqual(self.leer_json(".devsquad/tracks/001-inicial/track.json")["estado"], "borrador")
        self.escribir(".devsquad/tracks/001-inicial/plan.md", "- [ ] 1 Algo\n")
        self.stop("arquitecto")
        self.assertEqual(self.leer_json(".devsquad/tracks/001-inicial/track.json")["estado"], "listo")

    def test_planeador_con_entregables_incompletos_no_avisa(self):
        self.estado("init")
        self.estado("crear", "inicial")
        self.docs("requerimientos.md")
        self.assertEqual(self.stop("arquitecto").stdout.strip(), "")

    def test_el_orquestador_no_dispara_avances(self):
        self.estado("init")
        self.assertEqual(self.stop("orquestador").stdout.strip(), "")


class PruebasSubagentStopCoder(Base):
    def stop(self, esperado=0):
        return self.hook("subagentstop", {"hook_event_name": "SubagentStop", "agent_id": "c1"},
                         agente="coder", esperado=esperado)

    def con_comandos(self, lint, pruebas="true"):
        self.perfil(PERFIL.replace("`true`\n- Pruebas: `true`", "`%s`\n- Pruebas: `%s`" % (lint, pruebas)))

    def setUp(self):
        super().setUp()
        self.perfil()
        self.track()

    def contador(self):
        return self.leer_json(".devsquad/estado.json")["contadores"]["stop_bloqueos"]

    def test_sin_comandos_declarados_avisa_y_no_bloquea(self):
        self.perfil(PERFIL.split("## Comandos")[0] + "_Última actualización: hoy_\n")
        r = self.stop()
        self.assertIn("no declara comandos de verificación", json.loads(r.stdout)["systemMessage"])

    def test_comandos_na_cuentan_como_no_declarados(self):
        self.perfil(PERFIL.replace("- Lint: `true`\n- Pruebas: `true`", "N/A"))
        self.assertIn("no declara", json.loads(self.stop().stdout)["systemMessage"])

    def test_verificacion_en_rojo_bloquea_con_la_salida(self):
        self.con_comandos("echo ERROR-DE-LINT-XYZ; exit 1")
        r = self.stop(esperado=2)
        self.assertIn("ERROR-DE-LINT-XYZ", r.stderr)
        self.assertIn("Siguiente paso", r.stderr)
        self.assertEqual(self.contador(), 1)

    def test_verificacion_en_verde_reinicia_el_contador(self):
        self.con_comandos("exit 1")
        self.stop(esperado=2)
        self.con_comandos("true")
        self.stop()
        self.assertEqual(self.contador(), 0)

    def test_tope_de_bloqueos_escala_a_la_persona(self):
        self.con_comandos("exit 1")
        for _ in range(3):
            self.stop(esperado=2)
        self.assertEqual(self.contador(), 3)
        r = self.stop()  # el cuarto intento ya no bloquea
        self.assertIn("ask_human", json.loads(r.stdout)["systemMessage"])
        self.assertEqual(self.contador(), 0)

    def test_comando_que_se_cuelga_cuenta_como_fallo(self):
        import importlib.util
        # Se prueba la función directamente para no esperar el tiempo real.
        spec = importlib.util.spec_from_file_location("devsquad_hook", HOOK)
        modulo = importlib.util.module_from_spec(spec)
        sys.path.insert(0, os.path.dirname(HOOK))
        spec.loader.exec_module(modulo)
        modulo.TIMEOUT_VERIFICACION = 1
        fallos = modulo.ejecutar_verificacion(self.p, [("lento", "sleep 5")])
        self.assertEqual(len(fallos), 1)
        self.assertIn("tiempo", fallos[0][2])

    def test_con_tareas_abiertas_el_track_no_avanza(self):
        r = self.stop()
        self.assertIn("faltan tareas", json.loads(r.stdout)["systemMessage"])
        self.assertEqual(self.leer_json(".devsquad/tracks/001-inicial/track.json")["estado"], "en_progreso")

    def test_con_todas_las_tareas_pasa_a_en_revision(self):
        for t in ("1", "2"):
            self.estado("tarea", t, "hecha", "--commit", "abcdef1")
        r = self.stop()
        self.assertIn("en_revision", json.loads(r.stdout)["systemMessage"])
        self.assertEqual(self.leer_json(".devsquad/tracks/001-inicial/track.json")["estado"], "en_revision")


class PruebasResultadoDelCoder(Base):
    """El coder tiene Bash: `echo X > .env` o `sed -i` no pasan por Write/Edit.

    El SubagentStop revisa lo que cambió en Git. Son barandales contra errores
    del modelo, no una frontera de seguridad frente a Bash.
    """

    def git_(self, *args):
        subprocess.run(["git", "-C", self.p] + list(args), check=True, capture_output=True)

    def setUp(self):
        super().setUp()
        self.perfil()
        self.docs("requerimientos.md", "arquitectura.md", "diseno.md")
        self.escribir("src/runtime/motor.py", "x = 1\n")
        self.escribir("config/app.yaml", "a: 1\n")
        self.escribir("src/app.py", "y = 1\n")
        self.escribir(".gitignore", ".env\n")
        self.git_("init", "-q")
        self.git_("config", "user.email", "t@example.com")
        self.git_("config", "user.name", "Prueba")
        self.git_("add", "-A")
        self.git_("commit", "-q", "-m", "base")
        self.track()

    def delegar(self):
        self.delega("coder", agente="orquestador")

    def stop(self, esperado=0):
        return self.hook("subagentstop", {"hook_event_name": "SubagentStop", "agent_id": "c1"},
                         agente="coder", esperado=esperado)

    def contador(self):
        return self.leer_json(".devsquad/estado.json")["contadores"]["stop_bloqueos"]

    def test_env_creado_por_bash_aunque_este_en_gitignore(self):
        self.delegar()
        self.escribir(".env", "TOKEN=1\n")  # equivale a `echo TOKEN=1 > .env`
        r = self.stop(esperado=2)
        self.assertIn(".env", r.stderr)
        self.assertIn("secretos", r.stderr)
        os.remove(self.ruta(".env"))
        self.stop()

    def test_env_example_no_se_marca(self):
        self.delegar()
        self.escribir(".env.example", "TOKEN=\n")
        self.stop()

    def test_env_que_ya_existia_antes_no_se_atribuye_al_coder(self):
        self.escribir(".env", "TOKEN=real\n")  # la persona ya lo tenía
        self.delegar()
        self.stop()
        self.escribir(".env", "TOKEN=otro\n")  # pero si el coder lo cambia, sí
        self.stop(esperado=2)

    def test_protegido_modificado_con_sed(self):
        self.delegar()
        self.escribir("src/runtime/motor.py", "x = 2\n")  # equivale a `sed -i`
        r = self.stop(esperado=2)
        self.assertIn("src/runtime/motor.py", r.stderr)
        self.assertIn("git checkout", r.stderr)

    def test_protegido_por_patron_y_archivo_nuevo(self):
        self.delegar()
        self.escribir("config/otro.yaml", "b: 2\n")
        self.stop(esperado=2)
        os.remove(self.ruta("config/otro.yaml"))
        self.escribir("src/runtime/nuevo.py", "z = 1\n")
        self.stop(esperado=2)

    def test_protegido_borrado(self):
        self.delegar()
        os.remove(self.ruta("config/app.yaml"))
        self.stop(esperado=2)

    def test_protegido_modificado_antes_de_delegar_no_se_atribuye(self):
        self.escribir("src/runtime/motor.py", "x = 99\n")  # cambio previo de la persona
        self.delegar()
        self.stop()

    def test_secreto_en_el_contenido_de_un_archivo_nuevo(self):
        self.delegar()
        self.escribir("src/config.py", "KEY = 'AKIAABCDEFGHIJKLMNOP'\n")
        r = self.stop(esperado=2)
        self.assertIn("src/config.py", r.stderr)
        self.assertIn("AWS", r.stderr)

    def test_cambio_normal_pasa(self):
        self.delegar()
        self.escribir("src/app.py", "y = 2\n")
        self.escribir("src/nuevo.py", "z = 3\n")
        self.stop()

    def test_los_archivos_de_devsquad_no_cuentan(self):
        self.delegar()
        self.escribir(".devsquad/arquitectura.md", "# cambiado AKIAABCDEFGHIJKLMNOP\n")
        self.stop()

    def test_comparte_el_tope_de_tres_bloqueos(self):
        self.delegar()
        self.escribir(".env", "A=1\n")
        for _ in range(3):
            self.stop(esperado=2)
        self.assertEqual(self.contador(), 3)
        r = self.stop()
        self.assertIn("ask_human", json.loads(r.stdout)["systemMessage"])
        self.assertEqual(self.contador(), 0)

    def test_violacion_y_verificacion_en_rojo_se_reportan_juntas(self):
        self.perfil(PERFIL.replace("- Lint: `true`", "- Lint: `echo LINT-ROJO; exit 1`"))
        self.delegar()
        self.escribir(".env", "A=1\n")
        r = self.stop(esperado=2)
        self.assertIn(".env", r.stderr)
        self.assertIn("LINT-ROJO", r.stderr)

    def test_sin_git_avisa_y_no_bloquea(self):
        shutil.rmtree(self.ruta(".git"))
        r = self.stop()
        self.assertIn("no es un repositorio Git", json.loads(r.stdout)["systemMessage"])

    def test_sin_comandos_las_violaciones_bloquean_igual(self):
        self.perfil(PERFIL.split("## Comandos")[0] + "_Última actualización: hoy_\n")
        self.delegar()
        self.escribir("src/runtime/motor.py", "x = 3\n")
        self.stop(esperado=2)


class PruebasStop(Base):
    def stop(self, **extra):
        datos = {"hook_event_name": "Stop"}
        datos.update(extra)
        return self.hook("stop", datos, agente="orquestador")

    def setUp(self):
        super().setUp()
        self.perfil()
        self.track()

    def test_cierra_el_track_en_revision_con_tareas_completas(self):
        for t in ("1", "2"):
            self.estado("tarea", t, "hecha", "--commit", "abcdef1")
        self.estado("transicion", "en_revision")
        r = self.stop()
        self.assertIn("cerrado", json.loads(r.stdout)["systemMessage"])
        self.assertIsNone(self.leer_json(".devsquad/estado.json")["track_activo"])

    def test_no_cierra_con_ganchos_sin_verificar(self):
        for t in ("1", "2"):
            self.estado("tarea", t, "hecha", "--commit", "abcdef1")
        self.estado("transicion", "en_revision")
        self.escribir(".devsquad/tracks/001-inicial/revision.json", json.dumps({"aprobado": True}))
        self.assertEqual(self.stop().stdout.strip(), "")
        self.assertEqual(self.leer_json(".devsquad/estado.json")["track_activo"], "001-inicial")

    def test_nunca_bloquea_el_stop(self):
        self.stop()  # track en_progreso con tareas abiertas: exit 0

    def test_un_subagente_no_cierra_tracks(self):
        for t in ("1", "2"):
            self.estado("tarea", t, "hecha", "--commit", "abcdef1")
        self.estado("transicion", "en_revision")
        self.stop(agent_id="x")
        self.assertEqual(self.leer_json(".devsquad/estado.json")["track_activo"], "001-inicial")


class PruebasConfiguracionDelPlugin(unittest.TestCase):
    def test_hooks_json_tiene_la_clave_hooks_y_los_tres_eventos(self):
        with open(os.path.join(PLUGIN, "hooks", "hooks.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertEqual(list(cfg.keys()), ["hooks"])
        self.assertEqual(set(cfg["hooks"]), {"PreToolUse", "SubagentStop", "Stop"})
        matcher = cfg["hooks"]["PreToolUse"][0]["matcher"]
        for tool in ("Agent", "Write", "Edit", "Bash"):
            self.assertIn(tool, matcher.split("|"))

    def test_los_comandos_de_hooks_apuntan_a_scripts_que_existen(self):
        with open(os.path.join(PLUGIN, "hooks", "hooks.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        for eventos in cfg["hooks"].values():
            for grupo in eventos:
                for h in grupo["hooks"]:
                    ruta = h["args"][0].replace("${CLAUDE_PLUGIN_ROOT}", PLUGIN)
                    self.assertTrue(os.path.exists(ruta), ruta)


if __name__ == "__main__":
    unittest.main()
