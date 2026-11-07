# Third-party notices

The page uses no third-party packages. Some of its interface ideas and numbers are ported by hand from the open-source projects below. These are plain JavaScript and CSS rewrites of React components, and nothing from them is installed or loaded. Each project is MIT-licensed, and its notice is reproduced here as the licence requires.

| What on our page | Ported from | Files read |
|---|---|---|
| Rolling counter on the answer numbers (digit strips, a spring per column, a 45 ms stagger, motion blur, edge fade) | bencho, `blocks/rolling-counter` | `Counter.tsx`, `Counter.css` |
| Tilt on the hero picture (sinks under the pointer, dent and rim shading, a tightening shadow, the spring maths) | bencho, `blocks/tilt` | `Tilt.tsx`, `Tilt.css` |
| Sliders (20 px pill track, fill that ends under the thumb, a primary pill thumb with a lighter pill inside), used on the stock, exchange-rate and "ask on another date" sliders; the same shape drawn in SVG for the stock runway and the order timeline lanes | morphin-ui, `registry/morphin/ui/slider` | `slider-variants.ts`, `slider.tsx` |
| Cards and badges on the "When to order" cards (filled card, 28 px superellipse corners, 24 px padding; soft status badges) | morphin-ui, `registry/morphin/ui/card`, `badge` | `card-variants.ts`, `badge-variants.ts` |
| Track colour of the timeline and runway lanes (foreground at low opacity, capped pill radius) | morphin-ui, `registry/morphin/ui/bar-chart` | `bar-chart-variants.ts` |
| Liquid toggle on the 30-minute re-check (inverting track, stretching drop) | bencho, `blocks/liq-toggle` | `Toggle.css` (the stretch is approximated in CSS without the SVG goo filter) |
| Dock falloff on the three answer cards | bencho, `blocks/dock` | `GlassDock.tsx` |
| Border beam while a check runs (conic stroke, colourful palette, mask, 1.96 s spin, 12 s hue drift) | libraries.dev, `packages/border-beam` ("md" size, stroke layer only) | `src/styles.ts`, `src/BorderBeam.tsx` |
| Shapes and type scale (pill controls, superellipse corner, Inter, warm neutrals and pure black) | morphin-ui (design tokens as documented; no code copied) | README and docs |

The landing page's section order follows useorigin.com, at Khoa's request: a hero with a fanned stack of answer cards, a value line with a strip of names, a feature grid, two text-and-picture rows (one with a dark panel) and a dark call to action. Only the structure is borrowed. No code, copy, images, fonts, colours or logos come from that site. The page could only be read as text from the build environment, so its exact look was not copied.

The libraries.dev machine-learning models (`Magnet.mfxl`, `VoicePosition.mfxl`) have a separate model licence. We do not use them.

## bencho

MIT License

Copyright (c) 2026 Lorenzo Cabra

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

Not covered by this licence: the Bencho name and the goat mark, and the
photographs shown on bencho.dev (none are included here). Third-party
material keeps its own licence; see THIRD_PARTY.md.

## libraries.dev

MIT License

Copyright (c) 2026 Jakub Antalik

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## morphin-ui

https://github.com/sikkeep/morphinui. Ported by hand to plain CSS and SVG; nothing from it (React, Tailwind, Base UI, GSAP) is installed or loaded.

MIT License

Copyright (c) 2026 Ivan Oliinyk

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
