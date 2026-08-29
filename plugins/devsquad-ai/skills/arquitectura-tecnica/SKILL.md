---
description: Estándares para tomar decisiones de arquitectura en proyectos DevSquad AI — protocolo de selección de stack (nunca asumir Supabase/Vercel por defecto), marco de costo/impacto, atributos no funcionales y compromisos de calidad (estilo ATAM), patrones de arquitectura y descomposición modular, estándares de calidad de referencia (ISO/IEC 25010, ISO/IEC 5055, CMMI, IEEE 730), seguridad por defecto, y manejo de variables de entorno. Usar siempre al definir la arquitectura de un proyecto, antes de escribir arquitectura.md.
---

# Arquitectura técnica con estándares

## Protocolo de selección de stack — nunca asumas

Un error real detectado: el arquitecto asumía Next.js + Supabase + Vercel
sin preguntar. Eso no vuelve a pasar. Antes de proponer cualquier stack:

- **Si el perfil de la persona es no técnico** (revisa
  `.devsquad/perfil.md`): ofrece el "kit básico para desplegar tu
  aplicación" como recomendación, no como default silencioso. Dilo así:
  > "Te recomiendo un paquete de herramientas gratis para empezar
  > (Next.js + Supabase + Vercel) que te permite tener tu app funcionando
  > en internet sin costo inicial. ¿Quieres que lo use, o prefieres que
  > exploremos otras opciones?"
  Si dice que sí, procede. Si duda o dice que no, pregunta qué le
  preocupa y ajusta — nunca lo impongas.

- **Si el perfil es técnico**: pregunta directamente y sin explicación de
  más, algo como "¿tienes un stack en mente, o prefieres que te
  recomiende uno según los requerimientos?". No asumas Supabase/Vercel
  solo porque es el default histórico de DevSquad AI.

- **Si el perfil ya declara un stack**, este protocolo de preguntas no
  aplica — ver la jerarquía de decisión en el prompt del agente
  Arquitecto.

## Marco de costo/impacto (obligatorio, ya definido en tu prompt de agente)

Para cada decisión no obvia: costo estimado, impacto, e impacto a futuro.
Esta skill no repite esa regla — vive en el prompt del agente porque es
innegociable — pero recuerda aplicarla también a la elección del stack
mismo, no solo a decisiones dentro de un stack ya elegido, y a cualquier
estándar de proceso (CMMI, IEEE 730) que consideres adoptar más abajo.

## Atributos no funcionales (ANF)

Antes de aterrizar la arquitectura, identifica métricas objetivo, aunque
sea de forma aproximada: tiempo de respuesta esperado, disponibilidad,
concurrencia esperada (¿cuántas personas lo van a usar a la vez?). Con
alguien no técnico, no le pidas estos términos — pregúntale en su idioma
("¿esto lo vas a usar solo tú, o varias personas al mismo tiempo?", "¿qué
tan grave sería que tardara unos segundos en responder?") y traduce tú la
respuesta a un ANF. Documenta lo que salga, aunque sea una frase por
atributo — no hace falta un proceso formal para un proyecto pequeño.

## Análisis de compromisos (estilo ATAM)

Para decisiones de arquitectura no triviales, nombra explícitamente qué
atributo de calidad favorecen y cuál sacrifican (ej. "cachear esto lo hace
más rápido, pero los datos pueden tardar unos segundos en reflejar
cambios"; "más validaciones de seguridad agregan un paso extra al flujo
del usuario"). Esta es la esencia de un Architecture Tradeoff Analysis
Method (ATAM) aplicada de forma proporcional: no es un proceso formal
completo con stakeholders y escenarios documentados salvo que la persona
lo pida explícitamente — es el hábito de decir el trade-off en voz alta en
vez de dejarlo implícito.

## Patrones de arquitectura y descomposición modular

- Elige el patrón (monolito modular, capas, eventos, microservicios) según
  la complejidad real del proyecto, no por moda. Para la mayoría de
  proyectos de DevSquad AI (ver "Límite de alcance" en el prompt del
  agente), un monolito modular bien separado es más apropiado que
  microservicios — solo justifica algo más complejo si los requerimientos
  genuinamente lo piden, y pasa esa decisión por el marco de costo/impacto.
- Dentro de ese patrón, divide el sistema en componentes/capas con alta
  cohesión y bajo acoplamiento (ej. presentación, lógica de negocio,
  acceso a datos — ver skill `estandares-backend` para el detalle de
  separación en capas) para facilitar pruebas y mantenimiento. Documenta
  esta división en la estructura de carpetas del entregable.

## Estándares de calidad de referencia

Úsalos como marco de referencia, no como checklist obligatoria a imponer
en todo proyecto — su aplicación también pasa por el marco de
costo/impacto:

- **ISO/IEC 25010**: define características de calidad del producto
  (fiabilidad, eficiencia de rendimiento, seguridad, mantenibilidad,
  usabilidad, compatibilidad, portabilidad). Úsalo como checklist mental
  al revisar que la arquitectura no descuidó ninguna dimensión de calidad,
  incluso en proyectos pequeños.
- **ISO/IEC 5055**: mide la estructura interna del código (no solo que
  "funcione") para asegurar seguridad y fiabilidad. Pásale esta expectativa
  al Coder — se conecta con la rúbrica de calidad de la skill
  `estandares-backend`.
- **CMMI** e **IEEE 730**: son estándares de proceso y de aseguramiento de
  calidad más propios de organizaciones grandes con requisitos de
  cumplimiento. Menciónalos como referencia si la persona pertenece a una
  empresa que los exige, pero no los impongas como proceso obligatorio en
  proyectos pequeños o POCs — sería un costo desproporcionado para lo que
  se está construyendo.

## Seguridad por defecto

- Activa reglas de seguridad a nivel de fila (RLS) o equivalente por
  defecto en cualquier base de datos con acceso desde el cliente — no
  como algo opcional a agregar después.
- Ninguna key con privilegios elevados (ej. service role) debe planearse
  para vivir en código que corre en el navegador.
- Aplica principio de mínimo privilegio: cada pieza del sistema debe tener
  acceso solo a lo que necesita, no más.

## Variables de entorno — anticipa, no improvises

Enumera explícitamente en `.devsquad/arquitectura.md` qué variables de
entorno va a necesitar el proyecto (nombres, para qué sirve cada una, y
si es secreta o no) — esto le da al coder y al Orquestador lo necesario
para avisar con anticipación, en vez de que la persona se entere a medio
camino.

## Conexión con la preparación del entorno

Menciona explícitamente en tu entregable qué herramientas locales va a
necesitar el stack elegido (ej. "Node.js y npm" para un stack de
JavaScript). Esto permite que se avise a la persona con anticipación,
antes de que el coder empiece — no después de que algo falle.
