---
description: "Aprobación humana de arquitectura, diseño, comandos de verificación o cierre de un track. Solo la persona la invoca (por ejemplo /devsquad-ai:aprobar arquitectura); el modelo no puede."
disable-model-invocation: true
argument-hint: "arquitectura | diseno | comandos | cierre"
---

# Aprobar (decisión de la persona)

La persona escribió este comando. **La aprobación no la registras tú**: un hook de
DevSquad AI la procesó con código antes de que este mensaje llegara a ti, y su
resultado viene en el contexto como «RESULTADO DEL HOOK».

Argumentos recibidos: $ARGUMENTS

- Si el contexto trae el resultado del hook, díselo a la persona con tus palabras
  (qué se aprobó y en qué quedó el track) y sigue con el siguiente paso del
  puntero de arranque.
- Si el resultado dice que **no se registró**, explica el motivo tal cual y qué
  falta (por ejemplo «falta `arquitectura.md`»).
- Si no hay resultado del hook, dile a la persona que **no quedó registrada** y que
  puede ejecutar ella misma, en su terminal, `devsquad-estado aprobar <objeto> --fuente terminal`.
  Nunca digas que quedó aprobado si no viste el resultado del hook.

Objetos: `arquitectura` y `diseno` (los documentos tal como están ahora; si cambian
después, hay que aprobar de nuevo), `comandos` (los comandos de verificación del
perfil), `cierre` (el cierre del track, ligado al commit exacto).
