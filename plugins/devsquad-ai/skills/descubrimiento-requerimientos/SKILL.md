---
description: Buenas prácticas para levantar requerimientos e historias de usuario de calidad (criterios INVEST, priorización estilo MoSCoW, banco de preguntas de descubrimiento) en proyectos DevSquad AI. Usar siempre al traducir una idea en requerimientos, antes de pasar el trabajo al arquitecto.
---

# Descubrimiento de requerimientos de calidad

## Criterios de una buena historia de usuario (INVEST)

Usa esto como checklist interno — no le muestres estas siglas a la
persona, tradúcelas a preguntas naturales:

- **Independiente**: ¿esta funcionalidad se puede construir sin depender
  de que otra esté lista primero? Si no, dilo explícitamente.
- **Negociable**: no la redactes como una especificación rígida; deja
  espacio para que el arquitecto decida el cómo.
- **Valiosa**: ¿qué gana la persona con esto? Si no puedes contestar en una
  frase, probablemente falta contexto — pregunta más.
- **Estimable**: debe quedar clara qué tan grande es (chica/mediana/grande
  a ojo, no en horas).
- **Small (pequeña)**: si una historia suena a "proyecto completo", pártela
  en varias.
- **Testable**: debe quedar claro cómo alguien sabría que ya funciona.

## Priorización (v1 vs. futuro)

Clasifica cada historia en una de estas categorías, y sé explícito sobre
por qué algo no es v1:
- **Debe estar en v1**: sin esto, la app no cumple su propósito mínimo.
- **Debería estar, pero puede esperar**: mejora la experiencia, no es
  crítico para el primer uso.
- **Podría estar en el futuro**: una idea válida, pero lejana.
- **No por ahora**: fuera de alcance por decisión, no por olvido.

## Banco de preguntas de descubrimiento

Úsalas como punto de partida, adaptadas a cada idea, una a la vez:
- ¿Quién va a usar esto? ¿Alguien más además de ti?
- ¿Qué es lo mínimo que tiene que hacer para ya serte útil?
- ¿Cómo resuelves esto hoy, sin la app? (revela el verdadero problema)
- ¿Hay algo parecido que ya conozcas o uses, como referencia?
- ¿Qué pasaría si esto no existiera — qué tan grave sería?
- ¿Hay restricciones que ya sepas? (tiempo, presupuesto, quién más está
  involucrado)

## Definición de "terminado" para el entregable

`.devsquad/requerimientos.md` no está completo si:
- Alguna historia no tiene claro el "para qué" (el beneficio).
- No hay al menos una separación explícita entre v1 y futuro.
- Quedó una ambigüedad sin marcar como pregunta abierta.
