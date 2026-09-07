---
name: Luminous Workspace
colors:
  surface: '#111319'
  surface-dim: '#111319'
  surface-bright: '#37393f'
  surface-container-lowest: '#0c0e13'
  surface-container-low: '#191b21'
  surface-container: '#1e1f25'
  surface-container-high: '#282a30'
  surface-container-highest: '#33353a'
  on-surface: '#e2e2e9'
  on-surface-variant: '#e3bebe'
  inverse-surface: '#e2e2e9'
  inverse-on-surface: '#2e3036'
  outline: '#aa8989'
  outline-variant: '#5b4041'
  surface-tint: '#ffb3b5'
  primary: '#ffb3b5'
  on-primary: '#680019'
  primary-container: '#ff5167'
  on-primary-container: '#5b0015'
  inverse-primary: '#bb1238'
  secondary: '#7bd0ff'
  on-secondary: '#00354a'
  secondary-container: '#00a6e0'
  on-secondary-container: '#00374d'
  tertiary: '#ddb7ff'
  on-tertiary: '#490080'
  tertiary-container: '#b76dff'
  on-tertiary-container: '#400071'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdada'
  primary-fixed-dim: '#ffb3b5'
  on-primary-fixed: '#40000c'
  on-primary-fixed-variant: '#920027'
  secondary-fixed: '#c4e7ff'
  secondary-fixed-dim: '#7bd0ff'
  on-secondary-fixed: '#001e2c'
  on-secondary-fixed-variant: '#004c69'
  tertiary-fixed: '#f0dbff'
  tertiary-fixed-dim: '#ddb7ff'
  on-tertiary-fixed: '#2c0051'
  on-tertiary-fixed-variant: '#6900b3'
  background: '#111319'
  on-background: '#e2e2e9'
  surface-variant: '#33353a'
typography:
  display-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.4'
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  label-mono:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.2'
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 13px
    fontWeight: '500'
    lineHeight: '1.2'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 16px
  margin-page: 24px
  panel-padding: 20px
  stack-gap: 12px
---

## Brand & Style
The design system embodies an ultra-premium, high-performance studio environment tailored for Web3D creators. The brand personality is sophisticated, technical, and immersive, functioning as a "dark room" where the user's content is the primary light source. 

The aesthetic blends **Modern Glassmorphism** with **Technical Precision**. It utilizes deep obsidian surfaces, subtle radial gradients that mimic studio softboxes, and hyper-sharp accents to evoke a sense of professional mastery and future-forward innovation.

## Colors
The palette is anchored by a deep slate/black background (#080a0f) to maximize contrast for 3D assets. 
- **Primary (Radiant Coral):** Used for critical calls to action and active states.
- **Secondary (Electric Cyan):** Used for selection highlights and transform handles.
- **Tertiary (Violet Glow):** Reserved for specialized telemetry and creative mode indicators.
- **Neutral/Surface:** The "Glass" surface (rgba(15, 20, 32, 0.85)) is applied to all floating panels to provide depth without visual clutter.

## Typography
The typography system balances approachable modernity with technical rigor. 
- **Plus Jakarta Sans** is the primary driver for UI navigation and content, chosen for its soft yet professional geometry.
- **JetBrains Mono** is utilized exclusively for telemetry, coordinate systems, and metric readouts to maintain a developer-friendly, precise feel.
- High-contrast weights are used for headlines to stand out against blurred backgrounds, while labels use slightly increased tracking for legibility at small sizes.

## Layout & Spacing
The design system utilizes a **Fluid-Floating Model**. Panels do not sit flush against the viewport edges; instead, they float with a 16px-24px margin, creating a "software-within-a-space" feel. 

The layout relies on a 4px baseline grid for micro-spacing. Component groups use a 12px gap for tight logical grouping, while major sections are separated by 24px. The central "Viewport" is expansive, with tools docked in semi-transparent floating containers that minimize their footprint.

## Elevation & Depth
Depth is achieved through **Optical Refraction** rather than traditional drop shadows.
- **Layer 0 (Background):** Solid #080a0f with a subtle radial gradient (Top Left, 40% opacity secondary color).
- **Layer 1 (Floating Panels):** Background blur (18px) with a 1px solid border (rgba(255,255,255,0.08)).
- **Layer 2 (Popovers/Modals):** Increased blur (32px) and a subtle outer glow using the primary color at 5% opacity to indicate focus.
- **Occlusion:** When panels overlap, the blur effect compounds, naturally creating a sense of physical stacking.

## Shapes
The shape language is defined by **Soft Geometric Precision**. 
- Standard panels and input containers use a 16px (rounded-2xl) radius to soften the technical nature of the app.
- Navigation elements and buttons use a "Pill" shape (full rounding) to differentiate them from functional data panels.
- Icons should be housed in circular or rounded-square containers with a consistent 1.5px stroke weight.

## Components
- **Buttons:** Primary buttons use a solid coral-to-violet gradient. Secondary buttons use a glass background with a subtle white border.
- **Sleek Sliders:** Track is a thin 2px line; the thumb is a glowing 12px circle with the accent color.
- **Glass Panels:** Used for all sidebars and property inspectors. Must have a 1px top-light border highlight to simulate physical glass thickness.
- **Floating Pill Nav:** A horizontal bar at the top or bottom center, using a dark glass background and high-contrast icons.
- **Toggle Switches:** Small, pill-shaped housings with a sliding circular thumb that glows electric cyan when "on."
- **Data Inputs:** Dark, recessed backgrounds (rgba(0,0,0,0.2)) with 16px rounded corners and an active border-glow state.