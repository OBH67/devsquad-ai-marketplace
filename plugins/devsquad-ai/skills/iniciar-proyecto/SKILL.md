---
description: Inicializa el perfil de la persona y del proyecto para DevSquad AI, preguntando nombre preferido, nivel técnico, idioma y reglas de negocio si aplica. Usar la primera vez que alguien trabaja con DevSquad AI en un proyecto, o cuando pida "reiniciar mi perfil" o "configurar DevSquad AI".
---

# Iniciar proyecto DevSquad AI

Crea el archivo `.devsquad/perfil.md` que todos los agentes de DevSquad AI
(orquestador, bsa, arquitecto, coder) leen para adaptar su lenguaje y nivel
de detalle.

## Pasos

1. Verifica si ya existe `.devsquad/perfil.md`. Si existe, muéstraselo a la
   persona y pregunta si quiere mantenerlo o actualizarlo — no lo
   sobrescribas sin confirmar.

2. Pregunta, de forma conversacional (una o dos preguntas a la vez, no un
   formulario largo de golpe):
   - **Nombre preferido**: ¿cómo le gustaría que se dirijan a ella?
   - **Nivel técnico**: ¿tiene experiencia con desarrollo de software, o
     prefiere que se le explique todo sin dar por hecho términos técnicos?
   - **Idioma preferido** para la conversación.
   - **Contexto de empresa** (opcional): si este proyecto es para una
     empresa, ¿hay reglas de negocio, restricciones o convenciones que
     DevSquad AI debería respetar? (ej. siempre usar cierto proveedor, no
     usar cierto tipo de dato, cumplir alguna política interna)

3. Crea la carpeta `.devsquad/` si no existe.

4. Escribe `.devsquad/perfil.md` con esta estructura:

```markdown
# Perfil DevSquad AI

- **Nombre preferido**: [nombre]
- **Nivel técnico**: [no técnico / técnico — con una frase de contexto]
- **Idioma**: [idioma]
- **Reglas de negocio / contexto de empresa**: [texto libre, o "N/A"]

_Última actualización: [fecha]_
```

5. Confirma a la persona, en una frase simple, que su perfil quedó guardado y que a partir de ahora DevSquad AI va a adaptarse a como le gusta trabajar.
6. Entrega el control de vuelta al Orquestador para que continúe con el proyecto (fase de descubrimiento con el BSA si es un proyecto nuevo).
