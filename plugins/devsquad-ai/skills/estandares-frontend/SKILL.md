---
description: Estándares técnicos de frontend para DevSquad AI — accesibilidad (WCAG), diseño responsivo, sistemas de diseño y Atomic Design, jerarquía visual, feedback de interacción, rendimiento, y leyes de UX (Hick, Fitts). Usar siempre que el Diseñador defina el sistema de diseño o el Coder implemente interfaces.
---

# Estándares de frontend (DevSquad AI)

## Antes de implementar o diseñar interfaz

Consulta (con WebSearch si hace falta) la documentación oficial vigente del
framework de frontend elegido (React, Next.js, Angular, u otro) y de
cualquier librería de UI que se use — las convenciones y APIs cambian entre
versiones mayores; no asumas que lo que sabes de memoria sigue vigente.

## Accesibilidad (WCAG) — no negociable

- **HTML semántico**: usa las etiquetas que corresponden a su función
  (`button` para acciones, `nav` para navegación, encabezados en orden
  jerárquico), no `div` genéricos con JavaScript encima.
- **Roles y atributos ARIA** donde el HTML semántico no baste (ej.
  componentes custom tipo modal, tabs, dropdown).
- **Navegación completa por teclado**: todo elemento clickeable debe ser
  alcanzable y operable con Tab/Enter/Espacio, con foco visible en todo
  momento.
- **Contraste mínimo 4.5:1** — ya definido en la skill `diseno-ui`; esta
  skill lo hereda, no lo repite.

## Diseño responsivo

- Define breakpoints estándar (móvil, tablet, escritorio) y verifica que el
  layout no se rompa en ninguno — no solo que se vea bien en la pantalla
  donde se diseñó o implementó.

## Sistemas de diseño y Atomic Design

- Organiza los componentes de UI en niveles reutilizables (átomos: botón,
  input; moléculas: campo con etiqueta y error; organismos: formulario
  completo) en vez de duplicar estilos y estructura pantalla por pantalla.
  Esto reduce inconsistencia y facilita mantener en un solo lugar la
  paleta y tipografía que definió el Diseñador.

## Jerarquía visual y feedback

- Guía la atención con contraste, tamaño y espaciado (padding/márgenes) —
  no todo en la pantalla puede pesar lo mismo.
- Da retroalimentación inmediata a cualquier interacción: estados de
  carga, éxito y error visibles, nunca un botón que "no hace nada" mientras
  procesa.

## Rendimiento de frontend

- Evita cargar recursos innecesarios (imágenes sin optimizar, librerías
  completas cuando solo se usa una función); usa las herramientas de
  optimización que ya trae el framework elegido (lazy loading, code
  splitting) cuando el proyecto lo justifique.

## Leyes de UX aplicadas

- **Ley de Hick**: menos opciones visibles a la vez reducen la carga
  cognitiva — si una pantalla tiene muchas acciones posibles, prioriza y
  esconde las secundarias en vez de mostrarlas todas con el mismo peso.
- **Ley de Fitts**: los elementos interactivos importantes (el botón
  principal de una pantalla) deben ser grandes y estar cerca de donde el
  usuario ya tiene la atención o el cursor — no pequeños ni lejos del
  flujo natural de la tarea.

## Con alguien no técnico

No uses estos nombres (WCAG, Atomic Design, Ley de Hick) al hablar con la
persona — son criterios internos de calidad, no algo que ella deba
decidir. Si algo de esto afecta una decisión que sí le toca a ella (ej.
"esta pantalla tiene demasiadas opciones, ¿cuáles son las 3 más
importantes?"), tradúcelo a una pregunta simple.
