# Changelog

## [0.5.1] — Fix: sesión mostraba proyecto de otra carpeta al pedir "proyecto nuevo"

Bug real reportado en uso: alguien creó una carpeta nueva para un proyecto
distinto, pero la sesión de Claude Code seguía abierta en la carpeta del
proyecto anterior. El Orquestador leyó y mostró el `.devsquad/estado.md`
real de ese proyecto anterior (comportamiento técnicamente correcto: la
sesión sigue apuntando ahí), pero nunca dijo explícitamente que el problema
era la carpeta, y ofreció opciones (archivar, proyecto nuevo, descartar,
continuar) que no resuelven una sesión anclada al lugar equivocado.

### Corregido
- Nueva sección **"Verificación de carpeta de trabajo"** en el Orquestador,
  que corre antes que cualquier otra cosa, incluso antes de leer
  `.devsquad/perfil.md`. Si la persona menciona un proyecto nuevo o una
  carpeta distinta y lo que hay en el `.devsquad/estado.md` de la carpeta
  actual no coincide, el Orquestador ahora lo dice primero, con la ruta
  completa de la carpeta en la que está parado, y explica que una sesión de
  Claude Code no puede cambiar de carpeta por sí sola — hace falta abrir
  una terminal nueva dentro de la carpeta correcta. Las opciones de cómo
  proceder solo se ofrecen después de confirmar si fue un error de carpeta
  o una decisión real.
- `README.md`: nueva sección **"Cómo iniciar un proyecto nuevo, separado
  del anterior"** con los pasos correctos (carpeta nueva → terminal nueva
  dentro de ella → `claude` ahí), y se corrige el conteo de agentes (decía
  4, ya son 5 desde que se agregó el Diseñador en 0.2.0) y la lista, que no
  incluía al Diseñador.

## [0.5.0] — Estándares técnicos reales de arquitectura, backend y frontend

> Nota de mantenimiento: `plugin.json` se había quedado en `0.3.0` aunque
> el CHANGELOG ya documentaba `0.4.0`. Se corrige aquí a `0.5.0` para que
> vuelva a reflejar la última versión publicada.

Profundiza la parte técnica de Arquitecto, Coder y Diseñador con
estándares de la industria, sin convertirlos en checklists que abrumen a
un POC pequeño ni a una persona no técnica — todo pasa por el marco de
costo/impacto ya existente.

### Agregado
- **Skill `estandares-backend`** (Coder): principios SOLID, Clean
  Architecture y separación en capas, diseño de APIs (códigos HTTP,
  OpenAPI/Swagger), autenticación (OAuth2/JWT), validación y control de
  acceso, pruebas automatizadas (unitarias/integración/e2e), CI/CD,
  rendimiento (índices, rate limiting) y observabilidad. Incluye una
  **rúbrica cuantificable de calidad de código** (100 puntos: correctitud,
  seguridad, SOLID, pruebas, legibilidad) con un umbral mínimo de 80/100
  para considerar un incremento "terminado" — responde directamente al
  pedido de poder calificar objetivamente si un código está bien hecho.
- **Skill `estandares-frontend`** (Diseñador y Coder): accesibilidad
  (WCAG: HTML semántico, ARIA, navegación por teclado), diseño responsivo
  con breakpoints, sistemas de diseño con Atomic Design, jerarquía visual
  y feedback de interacción, rendimiento de frontend, y leyes de UX (Ley
  de Hick, Ley de Fitts).
- **Skill `arquitectura-tecnica` ampliada** (Arquitecto): definición de
  atributos no funcionales (ANF), análisis de compromisos estilo ATAM
  aplicado de forma proporcional (nombrar el trade-off, no un proceso
  formal completo), patrones de arquitectura y descomposición modular, y
  estándares de calidad de referencia (ISO/IEC 25010, ISO/IEC 5055, CMMI,
  IEEE 730) — estos últimos marcados explícitamente como opcionales según
  el tamaño del proyecto, nunca obligatorios por defecto.
- El Arquitecto ahora documenta explícitamente en `arquitectura.md` los
  atributos no funcionales objetivo, el patrón de arquitectura elegido, y
  el compromiso de calidad de cada decisión no obvia.
- El Diseñador ahora define también breakpoints responsivos, agrupa
  componentes con Atomic Design, y aplica las leyes de UX al definir
  layout — todo documentado en `diseno.md`.
- El Coder ahora tiene la herramienta **WebSearch**: antes de aplicar un
  patrón o convención, verifica si sigue siendo la práctica recomendada en
  la versión actual del lenguaje/framework/librería en uso, en vez de
  confiar solo en lo que sabe de memoria.

### Cambiado
- El Coder ahora usa `estandares-backend` y/o `estandares-frontend` según
  la capa que esté tocando, además de la skill general
  `implementacion-calidad` (que queda como la capa transversal: secretos,
  incrementos pequeños, manejo de errores).
- `diseno-ui` ahora se referencia junto con `estandares-frontend` en vez
  de duplicar accesibilidad/responsividad/Atomic Design — `diseno-ui` se
  queda enfocada en paleta, tipografía, contraste y estados.

## [0.4.0] — Soporte de stack declarado y archivos protegidos

> Nota de versionado: esta entrada se pidió como `[0.2.0]`, pero ese número
> ya existe más abajo (["Aprendizajes de la primera prueba real
> end-to-end"](#020--aprendizajes-de-la-primera-prueba-real-end-to-end)) y
> la última versión publicada es `0.3.0`. Se numeró como `0.4.0` para no
> duplicar historial. El título es el solicitado.

Cierra tres huecos detectados al exponer DevSquad AI a un caso que el diseño
original no contemplaba: una persona técnica que ya llega con su propio
stack decidido (ej. Python + Ollama local, sin nube) y con código terminado
que no debe regenerarse.

### Agregado
- **Pregunta de stack en la inicialización** (`iniciar-proyecto`): ahora se
  pregunta si el stack ya está decidido o si lo propone el Arquitecto. Si ya
  está decidido, la persona lo describe en sus palabras (lenguaje,
  frameworks, dónde corre, restricciones duras como "sin APIs de pago" o
  "todo local") y se guarda tal cual, sin traducirlo ni completarlo.
- **Pregunta de archivos protegidos en la inicialización**: se pregunta si
  hay código o archivos ya terminados que no deben regenerarse, con ejemplos
  para quien no entienda la pregunta, y se guardan como lista de rutas o
  patrones.
- Ambas preguntas son **independientes del nivel técnico**: alguien técnico
  puede querer igual que le propongan el stack, y alguien no técnico puede
  traer una restricción real de su empresa.
- `.devsquad/perfil.md` ahora incluye dos campos nuevos: **Stack** y
  **Archivos protegidos**.
- El skill de inicialización debe **confirmar en una frase lo que entendió**
  de cada uno de esos dos campos antes de continuar — no interpretar en
  silencio y avanzar.
- Nueva sección **"Archivos protegidos"** en el Coder: antes de escribir o
  modificar cualquier archivo, revisa esa lista del perfil; si hay
  coincidencia, se detiene y pregunta explícitamente en vez de editar o
  regenerar por su cuenta, aunque crea que lo está mejorando.

### Cambiado
- **El Arquitecto ya no tiene un stack por defecto hardcodeado.** Ahora
  sigue una jerarquía de decisión: (1) si `.devsquad/perfil.md` declara un
  stack, ese stack es autoritativo y no se cuestiona ni se ofrecen
  alternativas por cuenta propia; (2) si no hay stack declarado, el
  Arquitecto propone, y Next.js + Supabase + Vercel sigue siendo un default
  razonable pero debe justificarse según los requerimientos, no aplicarse
  automáticamente. La regla de transparencia de costo/impacto no cambia y
  aplica en ambos casos.
- **El "Límite de alcance" del Arquitecto ahora se mide por complejidad
  operativa, no por tipo de proyecto.** Antes excluía todo lo que no fuera
  "funcionalidad básica de tipo ERP/CRM". Ahora el dominio es libre (un
  pipeline local de agentes de IA, una herramienta de datos, un CLI o un ERP
  simple son igual de válidos) y lo que queda fuera es la orquestación
  distribuida a escala productiva (Kubernetes multi-nodo, service mesh,
  colas de mensajería de alto volumen). El archivo incluye un ejemplo de
  cada lado.
- **El Orquestador ahora pasa el contexto de "Stack" y "Archivos
  protegidos"** explícitamente al delegar en arquitecto o coder, en vez de
  asumir que el subagente los va a leer por su cuenta — mismo principio que
  ya aplicaba al resto del perfil, porque cada subagente arranca sin memoria
  de la conversación.
- `README.md`: la descripción del Arquitecto ya no implica un default
  incondicional de Next.js + Supabase + Vercel.

## [0.3.0] — Experiencia de usuario y skills especializadas

### Agregado
- **Progreso siempre visible**: el Orquestador ahora mantiene una lista de
  fases con TodoWrite, anuncia cada delegación antes de hacerla, y da
  señales de vida durante trabajo largo. Antes, la persona quedaba perdida
  después de las preguntas iniciales sin saber qué estaba pasando.
- **Fase de preparación del entorno**: nueva skill `preparar-entorno` que
  verifica que Node/npm/git (o lo que requiera el stack) estén instalados
  antes de escribir código, guía la instalación, y avisa explícitamente
  sobre pedir autorización a TI en computadoras de trabajo restringidas.
- **Skill dedicada por agente**, con estándares y mejores prácticas:
  - `descubrimiento-requerimientos` (BSA): criterios INVEST, priorización,
    banco de preguntas, definición de "terminado".
  - `arquitectura-tecnica` (Arquitecto): protocolo de selección de stack,
    seguridad por defecto (RLS, mínimo privilegio), documentación de
    variables de entorno.
  - `diseno-ui` (Diseñador): paleta con propósito, contraste mínimo 4.5:1,
    tipografía, estados vacío/error.
  - `implementacion-calidad` (Coder): incrementos pequeños, manejo de
    errores, validación en cliente y servidor, seguridad de secretos.
  - `comunicacion-progreso` (Orquestador): estándares de qué comunicar
    antes, durante y después de cada fase.

### Cambiado
- **El stack ya no se asume.** El Arquitecto ahora pregunta: a personas no
  técnicas les ofrece el kit básico de despliegue como recomendación
  explícita ("¿quieres que lo use?"), y a personas técnicas les pregunta
  directamente qué stack buscan. Antes daba por hecho Next.js + Supabase +
  Vercel sin consultar.
- El Arquitecto ahora documenta en su entregable qué herramientas locales y
  qué variables de entorno necesitará el proyecto, para poder avisar con
  anticipación.

## [0.2.0] — Aprendizajes de la primera prueba real end-to-end

Basado en la retrospectiva de la app "Mis Gastos" (primer proyecto de
prueba completo, de idea a app funcionando localmente).

### Agregado
- Nuevo agente **Diseñador UX/UI** (`disenador`, Opus), colocado entre
  Arquitecto y Coder. Define paleta, tipografía, layout y estados de cada
  pantalla antes de que se escriba código — el diseño anterior era pobre
  porque nadie era dueño de estas decisiones.
- El Coder ahora lee y sigue `.devsquad/diseno.md` como parte obligatoria
  de su contexto, y tiene instrucción explícita de eliminar estilos
  heredados de la plantilla base que contradigan el diseño definido.

### Corregido (bugs de comportamiento encontrados en la prueba real)
- El Orquestador ya no debe adjuntar archivos `.env*` ni ningún archivo
  con contraseñas/keys/tokens como adjunto — antes lo hizo sin que se lo
  pidieran, exponiendo una service role key.
- El Orquestador ahora advierte de forma proactiva, antes de pedirle a la
  persona que copie salida de terminal, que no la pegue en el chat si
  incluye secretos — antes solo corregía después de que ocurría.
- El Orquestador ahora debe hacer una verificación visual (si tiene
  herramienta de navegador disponible) antes de decir "ya puedes probarlo"
  por primera vez — un bug de contraste llegó a producción de prueba
  porque nadie lo revisó visualmente antes de la entrega.

## [0.1.0] — Fase 1 (prototipo interno)

### Agregado
- Agente Orquestador (Opus) como punto de entrada y director de proyecto.
- Agente BSA (Sonnet) para descubrimiento de requerimientos.
- Agente Arquitecto (Opus) con regla de transparencia de costo/impacto.
- Agente Coder (Sonnet) para implementación siguiendo el diseño acordado.
- Skill de inicialización de perfil (`iniciar-proyecto`).
- Marketplace local instalable vía `/plugin marketplace add`.

### Pendiente (fases siguientes)
- Agentes Reviewer, Cybersecurity, QA y Deployment.
- Guía de extracción segura de API keys/tokens.
