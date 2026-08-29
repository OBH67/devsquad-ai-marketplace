---
description: Checklist y principios de diseño visual con valor real (color, tipografía, layout, contraste) para usar al crear el sistema de diseño de un proyecto DevSquad AI, o al implementar/revisar código que debe seguir ese diseño. Para accesibilidad (WCAG), responsividad, Atomic Design y leyes de UX, ver la skill `estandares-frontend`. Usar siempre al generar diseño.md, y al verificar contraste/legibilidad antes de entregar una app al usuario.
---

# Diseño UI con valor real (DevSquad AI)

Un diseño genérico (gris/azul por defecto, tipografía del sistema, sin
personalidad) no cumple el objetivo de DevSquad AI. El objetivo es que
cada proyecto se sienta diseñado a propósito para lo que es, no como una
plantilla sin pensar.

Esta skill cubre paleta, tipografía, contraste y estados. Para
accesibilidad técnica (WCAG, ARIA, teclado), diseño responsivo, Atomic
Design y leyes de UX (Hick, Fitts), usa junto con esta la skill
`estandares-frontend`.

## Principios no negociables

1. **Paleta con propósito, no default.** Define 4–6 colores con su valor
   hexadecimal exacto: primario, secundario, uno o dos de acento, y los
   semánticos (éxito/error/advertencia). Cada color debe tener una razón
   ligada al proyecto, no ser "el azul de siempre".
2. **Tipografía con personalidad.** Elige una fuente para títulos/display
   y otra (o la misma familia con otro peso) para texto de cuerpo. Evita
   la fuente por defecto del framework sin haberlo decidido a propósito.
3. **Contraste verificado, no asumido.** Todo par texto/fondo debe cumplir
   mínimo **4.5:1** de contraste (WCAG AA) para texto normal, 3:1 para
   texto grande. Calcula o estima este número explícitamente para cada
   combinación que definas — no lo des por hecho "porque se ve bien en la
   pantalla en la que lo diseñaste".
4. **Un solo modo de color, a propósito.** Decide explícitamente si el
   proyecto tiene modo claro, oscuro, o ambos. Si el framework/plantilla
   base trae estilos de modo oscuro por defecto (esto ya causó un bug real
   en un proyecto DevSquad AI: CSS de dark-mode heredado del starter
   template de Next.js, aplicado de forma inconsistente), dilo
   explícitamente en el entregable y pide que ese CSS heredado se elimine
   o se declare de forma consistente — no se puede dejar "a medias".
5. **Estados, no solo la pantalla feliz.** Define cómo se ve cada pantalla
   clave vacía, cargando, y con error — no solo con datos de ejemplo
   perfectos.
6. **Un elemento memorable, el resto disciplinado.** Elige una cosa (un
   color de acento, una forma, una micro-interacción) que le dé
   personalidad al proyecto, y mantén todo lo demás quieto alrededor de
   ese elemento.

## Checklist de verificación antes de entregar al Coder

- [ ] Paleta con hex exactos y su propósito, no solo nombres ("terracota"
      sin el hex no sirve para implementar).
- [ ] Contraste de cada combinación texto/fondo verificado ≥ 4.5:1.
- [ ] Tipografías nombradas explícitamente (nombre real, no "una fuente
      moderna").
- [ ] Modo claro/oscuro decidido explícitamente, no dejado a la plantilla
      base.
- [ ] Cada pantalla del proyecto tiene su estado vacío/error descrito.
- [ ] Ver también el checklist de accesibilidad y responsividad de
      `estandares-frontend`.

## Checklist de verificación antes de entregar al usuario (para Orquestador/Coder)

Esta sección se usa DESPUÉS de implementar, antes de decirle a la persona
"ya puedes probarlo":

- [ ] Si hay herramienta de navegador/captura de pantalla disponible,
      tómala y revisa visualmente que el texto sea legible sobre su fondo
      en cada pantalla — no asumas que compilar sin errores significa que
      se ve bien.
- [ ] Confirma que no quedó ningún estilo de la plantilla base sin usar o
      contradictorio con la paleta definida en `diseño.md`.
