---
description: "Cancelar el track abierto, con motivo. Solo la persona lo invoca (por ejemplo /devsquad-ai:cancelar cambió el alcance); el modelo no puede."
disable-model-invocation: true
argument-hint: "motivo de la cancelación"
---

# Cancelar el track (decisión de la persona)

La persona escribió este comando. **La cancelación no la registras tú**: un hook de
DevSquad AI la procesó con código antes de que este mensaje llegara a ti, y su
resultado viene en el contexto como «RESULTADO DEL HOOK».

Argumentos recibidos (el motivo): $ARGUMENTS

- Si el resultado dice que el track quedó cancelado, confírmaselo a la persona: el
  historial se conserva, el lugar único queda libre y se puede abrir un track nuevo.
- Si dice que no se canceló (por ejemplo, falta el motivo), dile por qué.
- Si no hay resultado del hook, dile que **no quedó cancelado** y que puede ejecutar
  ella misma `devsquad-estado cancelar --motivo "..." --fuente terminal`.
