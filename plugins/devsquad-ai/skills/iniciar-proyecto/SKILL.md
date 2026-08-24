---
description: Inicializa el perfil de la persona y del proyecto para DevSquad AI, preguntando nombre preferido, nivel técnico, idioma, stack, archivos protegidos y reglas de negocio si aplica. Usar la primera vez que alguien trabaja con DevSquad AI en un proyecto, o cuando pida "reiniciar mi perfil" o "configurar DevSquad AI".
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
   - **Stack**: ¿el stack ya está decidido, o quiere que el Arquitecto lo
     proponga? Si ya está decidido, pídele que lo describa en sus propias
     palabras: lenguaje, frameworks, dónde corre (su computadora, un
     servidor, la nube), y restricciones duras (ej. "sin APIs de pago",
     "todo local", "solo lo que ya está aprobado en mi empresa"). Guarda lo
     que diga tal cual lo describió, sin traducirlo a tus propios términos
     ni completarlo con herramientas que ella no mencionó.
   - **Archivos protegidos**: ¿hay código o archivos ya terminados que no
     deben regenerarse? Si la pregunta no le queda clara, da ejemplos: "un
     runtime que ya depuraste y funciona", "un archivo de configuración que
     ya quedó bien", "un módulo que ya está probado y no quieres que nadie
     toque". Guárdalo como lista de rutas o patrones (ej. `src/runtime/`,
     `config/*.yaml`).
   - **Contexto de empresa** (opcional): si este proyecto es para una
     empresa, ¿hay reglas de negocio, restricciones o convenciones que
     DevSquad AI debería respetar? (ej. siempre usar cierto proveedor, no
     usar cierto tipo de dato, cumplir alguna política interna)

   Las preguntas de **Stack** y **Archivos protegidos** son independientes
   del nivel técnico: hazlas siempre, a cualquier persona. Alguien técnico
   puede querer igual que le propongan el stack, y alguien no técnico puede
   traer una restricción real de su empresa o un archivo que no se debe
   tocar.

3. Antes de continuar, confírmale a la persona en una frase lo que
   entendiste de cada uno de esos dos puntos, y espera que lo valide o lo
   corrija — no interpretes en silencio y avances. Por ejemplo: "Entendí
   que tu stack es Python con Ollama corriendo local, sin servicios de
   pago, ¿correcto?" y "Entendí que no debo tocar `src/runtime/` ni
   `config/settings.yaml`, ¿correcto?".

4. Crea la carpeta `.devsquad/` si no existe.

5. Escribe `.devsquad/perfil.md` con esta estructura:

```markdown
# Perfil DevSquad AI

- **Nombre preferido**: [nombre]
- **Nivel técnico**: [no técnico / técnico — con una frase de contexto]
- **Idioma**: [idioma]
- **Stack**: [descripción tal cual la dio la persona, incluyendo
  restricciones duras — o "Sin decidir: lo propone el Arquitecto"]
- **Archivos protegidos**: [lista de rutas o patrones que no deben
  modificarse ni regenerarse, o "N/A"]
- **Reglas de negocio / contexto de empresa**: [texto libre, o "N/A"]

_Última actualización: [fecha]_
```

6. Confirma a la persona, en una frase simple, que su perfil quedó guardado y que a partir de ahora DevSquad AI va a adaptarse a como le gusta trabajar.
7. Entrega el control de vuelta al Orquestador para que continúe con el proyecto (fase de descubrimiento con el BSA si es un proyecto nuevo).
