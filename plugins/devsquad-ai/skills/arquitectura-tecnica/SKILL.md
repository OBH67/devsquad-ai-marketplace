---
description: Estándares para tomar decisiones de arquitectura en proyectos DevSquad AI — protocolo de selección de stack (nunca asumir Supabase/Vercel por defecto), marco de costo/impacto, seguridad por defecto, y manejo de variables de entorno. Usar siempre al definir la arquitectura de un proyecto, antes de escribir arquitectura.md.
---

# Arquitectura técnica con estándares

## Protocolo de selección de stack — nunca asumas

Un error real detectado: el arquitecto asumía Next.js + Supabase + Vercel
sin preguntar. Eso no vuelve a pasar. Antes de proponer cualquier stack:

- **Si el perfil de la persona es no técnico** (revisa
  `.devsquad/perfil.md`): ofrece el "kit básico para desplegar tu
  aplicación" como recomendación, no como default silencioso. Dilo así:
  > "Te recomiendo un paquete de herramientas gratis para empezar
  > (Next.js + Supabase + Vercel) que te permite tener tu app funcionando
  > en internet sin costo inicial. ¿Quieres que lo use, o prefieres que
  > exploremos otras opciones?"
  Si dice que sí, procede. Si duda o dice que no, pregunta qué le
  preocupa y ajusta — nunca lo impongas.

- **Si el perfil es técnico**: pregunta directamente y sin explicación de
  más, algo como "¿tienes un stack en mente, o prefieres que te
  recomiende uno según los requerimientos?". No asumas Supabase/Vercel
  solo porque es el default histórico de DevSquad AI.

## Marco de costo/impacto (obligatorio, ya definido en tu prompt de agente)

Para cada decisión no obvia: costo estimado, impacto, e impacto a futuro.
Esta skill no repite esa regla — vive en el prompt del agente porque es
innegociable — pero recuerda aplicarla también a la elección del stack
mismo, no solo a decisiones dentro de un stack ya elegido.

## Seguridad por defecto

- Activa reglas de seguridad a nivel de fila (RLS) o equivalente por
  defecto en cualquier base de datos con acceso desde el cliente — no
  como algo opcional a agregar después.
- Ninguna key con privilegios elevados (ej. service role) debe planearse
  para vivir en código que corre en el navegador.
- Aplica principio de mínimo privilegio: cada pieza del sistema debe tener
  acceso solo a lo que necesita, no más.

## Variables de entorno — anticipa, no improvises

Enumera explícitamente en `.devsquad/arquitectura.md` qué variables de
entorno va a necesitar el proyecto (nombres, para qué sirve cada una, y
si es secreta o no) — esto le da al coder y al Orquestador lo necesario
para avisar con anticipación, en vez de que la persona se entere a medio
camino.

## Conexión con la preparación del entorno

Menciona explícitamente en tu entregable qué herramientas locales va a
necesitar el stack elegido (ej. "Node.js y npm" para un stack de
JavaScript). Esto permite que se avise a la persona con anticipación,
antes de que el coder empiece — no después de que algo falle.
