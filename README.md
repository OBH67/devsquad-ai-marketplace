# DevSquad AI

Equipo de agentes SDLC para Claude Code.

Incluye 5 agentes:

- **Orquestador** (Sonnet · esfuerzo medio) — director de proyecto, punto de entrada único.
- **BSA** (Sonnet · esfuerzo xhigh) — traduce tu idea en requerimientos claros.
- **Arquitecto** (Opus · esfuerzo alto) — define la arquitectura, siempre explicando costo e
  impacto de cada decisión. Sobre el stack sigue una jerarquía: si tú ya
  declaraste uno al configurar tu perfil, ese stack manda y el Arquitecto
  diseña sobre él sin cuestionarlo; si no declaraste ninguno, él lo propone
  y lo justifica según tus requerimientos.
- **Diseñador** (Sonnet · esfuerzo alto) — define paleta, tipografía, layout, accesibilidad y
  responsividad antes de que se escriba código, para que nadie improvise
  el diseño visual mientras programa.
- **Coder** (Sonnet · esfuerzo alto) — implementa el código siguiendo lo ya definido, y se
  detiene a preguntar antes de tocar cualquier archivo que hayas marcado
  como protegido.

## Instalación

Necesitas la app de escritorio o CLI de Claude Code instalada.

### Desde GitHub

```
/plugin marketplace add <tu-usuario>/devsquad-ai-marketplace
/plugin install devsquad-ai@devsquad-ai-marketplace
/reload-plugins
```

### Desde una copia local

```
/plugin marketplace add /ruta/completa/a/devsquad-ai-marketplace
/plugin install devsquad-ai@devsquad-ai-marketplace
/reload-plugins
```

Reinicia Claude Code una vez. Al volver a abrir el proyecto, el Orquestador
se activa automáticamente como agente principal.

## Primer uso

La primera vez que hables con Claude Code en un proyecto nuevo, el
Orquestador va a pedirte unos datos básicos (cómo te gusta que te llamen, tu
nivel técnico, tu idioma preferido). Esto es para que todos los agentes se
adapten a cómo te gusta trabajar — no necesitas saber nada técnico para
responder estas preguntas.

También te va a preguntar dos cosas sobre el proyecto, sin importar tu nivel
técnico:

- **Si el stack ya está decidido** o prefieres que el Arquitecto lo
  proponga. Si ya lo tienes, descríbelo con tus palabras (lenguaje,
  frameworks, dónde corre, y restricciones duras como "todo local" o "sin
  APIs de pago") y el equipo se ajusta a eso.
- **Si hay código o archivos ya terminados** que no deben regenerarse (por
  ejemplo, un runtime que ya depuraste o un archivo de configuración que ya
  funciona). Quedan marcados como protegidos y ningún agente los toca sin
  preguntarte primero.

Después de eso, simplemente cuéntale tu idea de proyecto como se la
contarías a una persona. El Orquestador se encarga de coordinar al resto del
equipo.

## Cómo iniciar un proyecto nuevo, separado del anterior (importante)

Una sesión de Claude Code queda anclada a la carpeta donde la abriste — no
cambia de proyecto solo porque le digas "empecemos algo nuevo" en el chat,
porque no puede moverse de carpeta por su cuenta.

Si quieres un proyecto totalmente aparte del que ya tienes en curso:

1. Crea (o ubica) la carpeta nueva en tu explorador de archivos.
2. Abre una terminal **dentro de esa carpeta nueva** (no reuses la ventana
   donde ya estabas trabajando en el otro proyecto).
3. Corre `claude` ahí para iniciar una sesión nueva.

Si en vez de eso sigues escribiéndole en la misma conversación de antes, el
Orquestador va a seguir viendo el estado de tu proyecto anterior — y, si
detecta que lo que le describes no coincide con ese proyecto, te va a
avisar explícitamente en qué carpeta está parado para que puedas corregirlo,
en vez de mezclar los dos proyectos.

## Qué esperar en esta versión

Esta versión cubre: descubrimiento de requerimientos (BSA), diseño de
arquitectura con transparencia de costos (Arquitecto), sistema de diseño
(Diseñador), e implementación con estándares técnicos de backend y
frontend (Coder). Todavía **no** incluye (ver `CHANGELOG.md`):

- Reviewer, Cybersecurity, QA y Deployment como agentes separados.
- Sistema de hand-off de sesión más robusto.
- Guía paso a paso de extracción segura de API keys/tokens.

Repórtale a Omar cualquier punto donde el Orquestador no supo qué hacer o
donde una explicación no quedó clara — eso es exactamente lo que esta fase
de prueba busca descubrir.

## Estructura de archivos que genera el proyecto

DevSquad AI crea una carpeta `.devsquad/` dentro de tu proyecto. **Se
versiona en Git**: es la memoria del proyecto (no la agregues a `.gitignore`).
Contiene:

- `perfil.md` — tu perfil (nivel técnico, idioma, preferencias, stack
  declarado y archivos protegidos).
- `requerimientos.md` — lo que definió el BSA.
- `arquitectura.md` — lo que definió el Arquitecto.
- `diseno.md` — lo que definió el Diseñador.
- `estado.md` — en qué va el proyecto y qué falta (formato anterior; la
  0.6.0 lo reemplaza por `estado.json` y `tracks/`, ver abajo).
- `estado.json` — estado legible por máquina, con `schema_version`.
- `tracks/NNN-nombre/` — una unidad de trabajo: `track.json` (estado),
  `spec.md` (qué y criterios de aceptación) y `plan.md` (tareas `[ ]` `[~]`
  `[x]`, cada una hecha con el commit que la implementa). Solo hay un track
  abierto a la vez: no se abre otro hasta cerrar el actual.

### Compuertas (hooks del plugin)

Lo obligatorio lo hace cumplir el código, no la memoria del modelo
(`hooks/hooks.json` + `scripts/devsquad_hook.py`). Solo actúan sobre los
agentes de este plugin; bloquean con un mensaje que dice el paso que falta:

- **Perfil primero**: sin `.devsquad/perfil.md` no se delega, escribe ni ejecuta.
- **Orden de fases**: BSA → Arquitecto → Diseñador → Coder (según los
  entregables en `.devsquad/`). Delegar en el coder pasa el track de `listo`
  a `en_progreso`.
- **Track**: el código del proyecto solo se escribe con un track en
  `en_progreso` o `correcciones`.
- **Archivos protegidos** (los del perfil) y **secretos** (`.env*`, llaves).
- **El coder no termina en rojo**: ejecuta los «Comandos de verificación» del
  perfil; tras 3 bloqueos seguidos escala a la persona.
- Al terminar cada agente de planeación o el coder, el hook avanza el track con
  `devsquad-estado`; al terminar la sesión cierra el track si ya se puede.

Requieren `python3`; si falta, los hooks fallan sin bloquear (límite conocido).

### Script `devsquad-estado`

Cambia y valida ese estado: `devsquad-estado init | crear | transicion |
tarea | cerrar | estado | validar | migrar` (`--help` para el detalle). Es un
script de Python 3.8+ sin dependencias; el plugin lo pone en el `PATH` de la
herramienta Bash. **Límite conocido:** necesita `python3` (y `sh`); sin ellos,
por ejemplo en Windows sin Python, falla con un mensaje claro.

No necesitas tocar estos archivos manualmente; el equipo de agentes los lee
y actualiza por ti.
