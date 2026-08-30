# Quantic OS — visual acceptance contract

The normal Quantic session must look and behave like a premium modern operating system, not a recovery console.

## Required visual language
- Deep graphite/navy background with restrained blue-violet depth.
- Central luminous particle `Q`, smooth and GPU-rendered.
- Semi-translucent rounded glass panels with subtle edge light and shadow depth.
- Clean antialiased typography; no bitmap/terminal typography in the normal session.
- Compact CPU/GPU/RAM cards with circular gauges and live sparklines.
- Right-hand Companion and Resource Center panels.
- Floating centered dock with Accueil, Apps, Fichiers, Compagnon, Lab, Paramètres.
- Motion is subtle and smooth; no decorative animation may block interaction.
- Native scaling for 16:9 and ultrawide displays, including 3440×1440.

## Release rejection conditions
A normal boot is rejected for release if it falls back to framebuffer/recovery UI, shows a raw terminal, lacks mouse/keyboard interaction, renders at the wrong native scale, or loses the glass/depth hierarchy.

The framebuffer implementation is recovery-only.
