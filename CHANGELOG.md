# Changelog

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
