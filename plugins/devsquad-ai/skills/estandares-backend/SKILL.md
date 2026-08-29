---
description: Estándares técnicos de backend para DevSquad AI — SOLID, Clean Architecture, separación en capas, diseño de APIs (códigos HTTP, OpenAPI/Swagger), seguridad (OAuth2/JWT, validación de entradas, control de acceso), pruebas automatizadas, CI/CD, rendimiento (índices, rate limiting) y observabilidad, más una rúbrica cuantificable de calidad de código. Usar siempre que el Coder implemente lógica de servidor/backend.
---

# Estándares de backend (DevSquad AI)

## Antes de escribir código de backend

Consulta (con WebSearch si hace falta) la documentación oficial vigente del
lenguaje, framework y librerías que definió el Arquitecto en
`.devsquad/arquitectura.md` — las mejores prácticas cambian de versión a
versión; no asumas que lo que sabes de memoria sigue siendo la forma
recomendada hoy.

## Arquitectura y diseño de código

- **Principios SOLID**: cada clase/módulo con una responsabilidad, abierto
  a extensión y cerrado a modificación, interfaces pequeñas y específicas,
  y dependencia de abstracciones en vez de implementaciones concretas.
- **Clean Architecture / separación en capas**: separa controladores
  (entrada HTTP), servicios (lógica de negocio) y repositorios (acceso a
  datos). La lógica de negocio no debe depender de detalles de framework
  ni de la base de datos específica.
- **Design patterns con criterio**: usa el patrón adecuado (Factory,
  Strategy, Repository, etc.) cuando resuelve un problema real de tu
  código — no los fuerces donde una función simple basta. Sobre-ingeniería
  también es un defecto de calidad, no solo la falta de estructura.
- **APIs estandarizadas**: usa los códigos de estado HTTP correctos (200,
  201, 400, 401, 403, 404, 409, 422, 500 — no todo es 200 o 500), define
  contratos claros (OpenAPI/Swagger cuando el proyecto lo justifique), y
  mantén nombres de rutas/recursos consistentes.

## Seguridad (no negociable)

- **Autenticación robusta**: OAuth2 o JWT con expiración y renovación
  correctas — nunca sesiones sin expiración ni tokens eternos.
- **Validación y sanitización de toda entrada**: previene inyección SQL,
  XSS y ataques similares. La validación de cliente nunca reemplaza la del
  servidor.
- **Control de acceso**: cada endpoint restringido según el rol/permiso del
  usuario autenticado — nunca confíes en que el cliente "no va a mandar"
  una petición no autorizada.
- Esto se suma a (no reemplaza) las reglas de seguridad de secretos ya
  definidas en la skill `implementacion-calidad`.

## Pruebas y calidad de código

- **Pruebas automatizadas**: unitarias para lógica de negocio, de
  integración para la interacción entre capas, y end-to-end para los
  flujos críticos — antes de dar por terminado un incremento importante.
- **Code review con calificación cuantificable**: antes de marcar un
  incremento como listo, evalúalo (tú mismo, o pide al Orquestador que lo
  revise) contra esta rúbrica de 100 puntos:

  | Criterio | Puntos |
  |---|---|
  | Correctitud funcional (cumple la historia, sin errores de compilación/lint) | 30 |
  | Seguridad (sin secretos hardcodeados, validación server-side, sin vulnerabilidades obvias tipo OWASP Top 10) | 20 |
  | Adherencia a SOLID / Clean Architecture (responsabilidades separadas, bajo acoplamiento) | 20 |
  | Pruebas automatizadas (cubren camino feliz y al menos un caso de error) | 20 |
  | Legibilidad y documentación (nombres claros, comentarios donde la lógica no es obvia) | 10 |

  Un incremento no está "terminado" si saca menos de 80/100, o si el
  renglón de Seguridad no está en su puntaje máximo. Si no alcanza,
  reporta explícitamente qué falta en vez de declararlo listo.
- **Integración continua (CI/CD)**: si el proyecto ya tiene repositorio
  configurado, automatiza pruebas y despliegue (ej. GitHub Actions) — pero
  aplica el marco de costo/impacto del Arquitecto antes de agregar esta
  infraestructura a un POC pequeño; para un prototipo de un solo uso puede
  ser sobre-ingeniería.

## Rendimiento y monitoreo

- **Índices en base de datos**: en las columnas que se consultan o filtran
  con frecuencia — sin esperar a que una consulta lenta se vuelva un
  problema reportado.
- **Rate limiting**: protege endpoints públicos contra abuso, sobre todo
  los de autenticación y los que disparan operaciones costosas.
- **Observabilidad**: registra errores de forma estructurada y, si el
  proyecto lo justifica, expón métricas básicas (tiempo de respuesta, tasa
  de error) — proporcional al tamaño del proyecto, no por defecto en todo.

## Con alguien no técnico

No le muestres esta rúbrica ni esta jerga. Tradúcelo a una frase: "antes de
darte esto por terminado, lo revisé contra una lista de calidad interna
(seguridad, pruebas, que el código sea mantenible) y pasó" — o, si no
pasó, explica en una frase qué le falta y qué vas a hacer al respecto.
