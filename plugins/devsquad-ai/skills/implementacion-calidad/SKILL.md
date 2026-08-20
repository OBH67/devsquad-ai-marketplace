---
description: Estándares de calidad, seguridad y buenas prácticas de código para la fase de implementación en proyectos DevSquad AI — incrementos pequeños, manejo de errores, validación de entradas, gestión de secretos, y verificación de entorno antes de empezar. Usar siempre al implementar código.
---

# Calidad de implementación

## Antes de escribir la primera línea de código

Usa la skill `preparar-entorno` — verifica que las herramientas necesarias
estén instaladas antes de empezar. No lo saltes nunca, incluso si parece
obvio que ya deberían estar instaladas.

## Estándares de código

- **Incrementos pequeños y verificables.** Construye y muestra una pieza a
  la vez, no todo el proyecto de un solo golpe.
- **Maneja errores explícitamente.** Nunca dejes un error silenciado o
  ignorado — al menos regístralo o muéstralo de forma clara.
- **Valida toda entrada de usuario** en formularios o inputs, tanto del
  lado del cliente (para experiencia) como del servidor (para seguridad
  real — la validación de cliente nunca es suficiente por sí sola).
- **Legibilidad antes que "cleverness".** Prioriza código que cualquier
  otro desarrollador (o tú mismo en seis meses) pueda entender rápido.

## Seguridad de secretos (no negociable)

- Nunca hardcodees credenciales, API keys o tokens en el código fuente.
- Usa variables de entorno, siguiendo exactamente lo que ya se documentó
  en `.devsquad/arquitectura.md`.
- Nunca escribas tú mismo un secreto real (contraseña, PIN, key) en un
  archivo — eso lo hace la persona manualmente, siempre.
- Nunca adjuntes ni muestres el contenido completo de un archivo `.env*`
  a la persona.

## Diseño visual

Sigue `.devsquad/diseno.md` al pie de la letra para colores, tipografía y
layout — no improvises. Usa la skill `diseno-ui` como referencia rápida de
contraste mínimo (4.5:1). Elimina cualquier estilo heredado de la
plantilla base que no esté alineado con el diseño definido (esto ya causó
un bug real de contraste ilegible).

## Definición de "terminado" para un incremento

Un incremento no está listo para mostrarse a la persona si:
- No compila o tiene errores de tipos/lint.
- No se verificó visualmente (si hay herramienta disponible) que el texto
  sea legible.
- Contiene algo hardcodeado que debería ser una variable de entorno.
- No se explicó, en una frase simple, qué es lo que la persona debería
  probar.
