---
description: Recuperar la memoria del proyecto (decisiones, aprendizajes y tracks anteriores) sin cargarla toda — se lee el índice y solo el registro que importa; en la Factory, también la de proyectos anteriores con mcp__factory__buscar_memoria. Usar cuando haga falta recordar qué se decidió sobre algo, si ya se resolvió un problema parecido, o qué pasó en un track anterior. No sirve para saber en qué se quedó el trabajo (eso lo dicen el puntero de arranque y `.devsquad/estado.json`).
---

# Buscar en la memoria del proyecto (nivel 1: índice)

Dos preguntas distintas, dos herramientas distintas:

- **«¿En qué me quedé?»** es una consulta exacta: respóndela con el puntero de
  arranque o leyendo `.devsquad/estado.json` y el `plan.md` del track activo.
  No la busques en la memoria: un registro viejo podría contradecirla.
- **«¿Qué decidimos sobre X?» / «¿ya resolvimos algo parecido?»**: usa esta
  skill.

## Cómo

1. Lee el índice con Read: `.devsquad/memoria/indice.md` (la ruta absoluta
   viene en el puntero de arranque). Lo genera un script; no lo edites. Trae
   una línea por track, decisión y aprendizaje, con fecha, título, etiquetas y
   la ruta del archivo.
2. Elige por el título y las etiquetas los registros que puedan responder, y
   lee **solo esos** con Read. Nunca leas toda la carpeta de memoria.
3. Cuando cites algo de la memoria, di de qué registro viene y su fecha: puede
   estar desactualizado frente al estado actual del proyecto.
4. Si el índice no tiene nada relacionado, dilo: no inventes un recuerdo.

No tienes `Bash`: no uses búsquedas de texto. En una terminal normal, la
búsqueda de texto completo y por significado no están disponibles; en la
Factory sí (abajo).

## En la Factory: `mcp__factory__buscar_memoria` (niveles 2 y 3)

Si tienes la herramienta `mcp__factory__buscar_memoria`, estás en la AI
Software Factory y la memoria es más grande que este proyecto: decisiones
registradas, ADRs y aprendizajes de **proyectos anteriores**, con búsqueda por
palabras y por significado.

1. Llámala con `consulta` en lenguaje natural («cómo cobramos los pedidos en
   restaurantes», «por qué se eligió Postgres»). Opcional: `tipo` (decision,
   adr, learning, pattern, document, preference) y `limite`.
2. Cada resultado trae su origen (p. ej. `DEC-0003 · taqueria-001` o la ruta del
   archivo), fecha, confianza y, si se conoce, cómo salió. Cita ese origen.
3. Es referencia, no orden: si el contexto de este proyecto es distinto, dilo
   y decide con criterio. Lo marcado OBSOLETO no se reutiliza.
4. Para «¿en qué me quedé?» sigue valiendo el puntero de arranque, no la
   memoria.

## Cómo se guarda un registro (para quien escribe memoria)

Un archivo por registro en `.devsquad/memoria/decisiones/` o
`.devsquad/memoria/aprendizajes/`, con un encabezado:

```
---
tipo: decision            (decision | aprendizaje)
fecha: 2026-10-04
titulo: Usar SQLite al inicio
etiquetas: base-de-datos, costo
track: 001-inicial        (opcional)
---
Qué se decidió, por qué, y qué alternativas se descartaron.
```

El índice se regenera solo al empezar la sesión y cuando termina un agente.
