# Changelog

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
