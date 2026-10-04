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
- `estado.md` — formato anterior; la 0.6.0 lo reemplaza por `estado.json` y
  `tracks/` (ver abajo) y ya no se escribe.
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
- **Aprobación humana** (ver más abajo): el track no pasa a `listo` sin la
  aprobación de la persona de la arquitectura y del diseño; los comandos de
  verificación del perfil solo se ejecutan si ella los aprobó; y el cierre se
  rige por la política de cierre del track.
- `estado.json` y `track.json` (donde viven las aprobaciones) no los edita el
  modelo, y `devsquad-estado aprobar|cancelar` no lo ejecutan los agentes.
- **Orden de fases**: BSA → Arquitecto → Diseñador → Coder (según los
  entregables en `.devsquad/`). Delegar en el coder pasa el track de `listo`
  a `en_progreso`.
- **Track**: el código del proyecto solo se escribe con un track en
  `en_progreso` o `correcciones`.
- **Archivos protegidos** (los del perfil) y **secretos** (`.env*`, llaves).
- **El coder no termina en rojo**: ejecuta los «Comandos de verificación» del
  perfil; tras 3 bloqueos seguidos escala a la persona.
- **Revisión del resultado del coder**: como el coder tiene `Bash`
  (`echo X > .env`, `sed -i`), al terminar se revisa lo que cambió en Git
  respecto a lo que ya estaba cambiado al delegarle: un `.env*` real (aunque
  esté en `.gitignore`), patrones de secretos o archivos protegidos
  modificados. Bloquea con el mismo tope de 3 bloqueos.
- Al terminar cada agente de planeación o el coder, el hook avanza el track con
  `devsquad-estado`. **`Stop` solo informa** (por ejemplo «espera la aprobación
  de cierre»): nunca cierra ni bloquea.

Requieren `python3`; si falta, los hooks fallan sin bloquear (límite conocido).

> **Alcance de las compuertas.** Son **barandales contra errores del modelo,
> no una frontera de seguridad**. Con `Bash` un agente (o alguien que lo
> instruya) puede esquivarlas: la revisión del resultado atrapa lo habitual
> pero no lo deliberado (un archivo fuera del proyecto, un secreto en un
> formato desconocido, un comando que reescribe el historial de Git, etc.).
> Para aislar de verdad al agente hace falta aislamiento del sistema operativo
> (usuario sin privilegios, sin credenciales a su alcance), no hooks.

### Aprobaciones humanas, política de cierre y cancelar

Lo que decide la persona solo lo registra el **código** (los hooks o la
Factory), nunca el modelo:

| Qué | Cómo la da la persona (terminal) | En la Factory |
|---|---|---|
| Arquitectura | `/devsquad-ai:aprobar arquitectura` | `ask_human` con `kind: "approval"`, `subject: "arquitectura"` |
| Diseño | `/devsquad-ai:aprobar diseno` | `subject: "diseno"` |
| Comandos de verificación del perfil | `/devsquad-ai:aprobar comandos` | `subject: "comandos"` |
| Cierre del track | `/devsquad-ai:aprobar cierre` | `subject: "cierre"` |
| Cancelar un track | `/devsquad-ai:cancelar <motivo>` | `ask_human` con `kind: "cancel"` |

En la terminal un hook `UserPromptSubmit` ve el texto que la persona teclea (el
modelo no puede producirlo; las skills `aprobar` y `cancelar` no son invocables
por el modelo). En la Factory, la Factory ejecuta
`devsquad-estado aprobar <objeto> --fuente factory --por <usuario>` al recibir
la respuesta (el contrato de `ask_human` se implementa en la Factory).

- Las aprobaciones de arquitectura y diseño llevan la **huella SHA-256** del
  documento: si cambia, la aprobación queda **obsoleta**. La de comandos, la
  huella de la lista de comandos. La de cierre, el **commit exacto** (`HEAD`):
  commits nuevos la vuelven obsoleta.
- **Política de cierre** de cada track (`track.json`, `politica_cierre`): la
  propone el Arquitecto en `arquitectura.md` (`**Política de cierre**: humano`),
  la aprueba la persona con la arquitectura y queda dentro de la huella
  aprobada; el modelo no puede cambiarla.
  - `humano` (por defecto): criterios objetivos (tareas con commit y, si
    existen `revision.json`/`verificacion.json`, estado `verificado` y
    aprobados) **más** la aprobación de cierre. Al aprobarla, el código cierra.
  - `automatico`: el código cierra solo con los criterios objetivos.
    **Se rechaza mientras no exista el agente revisor** (fase C).
- `devsquad-estado cancelar --motivo ...` (o `/devsquad-ai:cancelar`): el track
  pasa a `cancelado`, queda libre el lugar único y se conserva el historial
  (`cancelacion` con motivo, estado previo, quién y cuándo).

### Arranque atómico y memoria

- Al empezar, reanudar, limpiar (`/clear`) o compactar la conversación, el
  hook `SessionStart` inyecta un **puntero** de unas pocas líneas generado por
  script (`scripts/devsquad_puntero.py`, tope duro de 10.000 caracteres): track
  activo y su estado, siguiente tarea, último commit, bloqueos, memoria
  disponible y el siguiente paso sugerido. «¿En qué me quedé?» es una consulta
  exacta sobre el estado, no una búsqueda. (`PreCompact` no puede inyectar
  contexto; tras compactar lo repone `SessionStart`.)
- **Memoria, nivel 1**: un archivo por decisión o aprendizaje en
  `.devsquad/memoria/{decisiones,aprendizajes}/`, y un índice generado
  (`.devsquad/memoria/indice.md`) que el agente lee con Read; la skill
  `buscar-memoria` explica cómo. El Orquestador no tiene `Bash`. Los niveles 2
  (texto completo) y 3 (significado) quedan para más adelante.

### Script `devsquad-estado`

Cambia y valida ese estado: `devsquad-estado init | crear | transicion |
tarea | aprobar | cancelar | cerrar | estado | validar | migrar` (`--help` para el detalle). Es un
script de Python 3.8+ sin dependencias; el plugin lo pone en el `PATH` de la
herramienta Bash. **Límite conocido:** necesita `python3` (y `sh`); sin ellos,
por ejemplo en Windows sin Python, falla con un mensaje claro.

No necesitas tocar estos archivos manualmente; el equipo de agentes los lee
y actualiza por ti.
