---
description: Recuperar la memoria del proyecto (decisiones, aprendizajes y tracks anteriores) sin cargarla toda — se lee el índice y solo el registro que importa. Usar cuando haga falta recordar qué se decidió sobre algo, si ya se resolvió un problema parecido, o qué pasó en un track anterior. No sirve para saber en qué se quedó el trabajo: eso lo dice el puntero de arranque y `.devsquad/estado.json`.
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

No tienes `Bash`: no uses búsquedas de texto. Búsqueda de texto completo y
por significado son niveles posteriores, aún no disponibles.

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
