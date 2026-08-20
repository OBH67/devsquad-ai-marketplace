---
description: Verifica que las herramientas necesarias (Node.js, npm, git) estén instaladas antes de escribir la primera línea de código de un proyecto DevSquad AI, y guía a la persona para instalarlas — incluyendo el aviso de pedir permiso a TI si está en una computadora de trabajo con restricciones. Usar siempre antes de que el coder empiece a implementar, nunca asumir que ya están instaladas.
---

# Preparar el entorno local

No asumas que la persona ya tiene las herramientas necesarias instaladas.
Esto ya causó fricción real en un proyecto DevSquad AI: se asumió desde el
inicio que ya existían las herramientas de Node para correr `npm`, y nunca
se verificó ni se avisó con anticipación.

## Pasos

1. **Verifica qué hay instalado**, usando Bash:

```
node -v
npm -v
git --version
```

Ajusta la lista según lo que requiera el stack elegido en
`.devsquad/arquitectura.md` (por ejemplo, si se eligió Python en vez de
Node, verifica `python3 --version` en su lugar).

2. **Si todo está instalado y en una versión razonable**, dilo brevemente y
continúa — no hace falta detenerte más en esto.

3. **Si falta algo**, explica en lenguaje simple qué es y por qué se
necesita (ej. "Node es el programa que hace posible correr el código de
tu app en tu computadora — sin él no puedo mostrarte cómo se ve").
Dale el paso concreto para instalarlo (sitio oficial, no un tutorial
improvisado):
- Node.js + npm → nodejs.org (descargar la versión LTS)
- git → git-scm.com

4. **Advierte explícitamente sobre computadoras de trabajo restringidas**,
siempre, sin esperar a que falle una instalación:

> "Si estás usando una computadora de tu trabajo, es posible que no
> tengas permiso para instalar programas nuevos. Antes de intentar
> instalar esto, pregúntale a tu equipo de TI (Tecnologías de la
> Información / IT) si pueden instalarlo por ti o autorizarte para
> hacerlo. Así evitamos que te encuentres con un error de 'permiso
> denegado' a mitad del proceso."

5. **No continúes a escribir código hasta que la persona confirme que las
herramientas están listas.** Si no puede instalar algo por
restricciones de su empresa, repórtalo al Orquestador — puede que el
proyecto necesite pausar ahí hasta que TI autorice, y la persona debe
saber que ese es el motivo, no un error del sistema.

## Con alguien no técnico

No le pidas que "corra comandos" sin explicarle primero, en una frase, qué
va a pasar y por qué es seguro hacerlo.
