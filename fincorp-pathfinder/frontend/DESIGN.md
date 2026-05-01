---
name: Technical Precision
colors:
  surface: '#fff8f5'
  surface-dim: '#e9d7cb'
  surface-bright: '#fff8f5'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#fff1e9'
  surface-container: '#fdeade'
  surface-container-high: '#f7e5d9'
  surface-container-highest: '#f2dfd3'
  on-surface: '#231a13'
  on-surface-variant: '#554336'
  inverse-surface: '#392e26'
  inverse-on-surface: '#ffede3'
  outline: '#887364'
  outline-variant: '#dbc2b0'
  surface-tint: '#904d00'
  primary: '#8d4b00'
  on-primary: '#ffffff'
  primary-container: '#b15f00'
  on-primary-container: '#fffbff'
  inverse-primary: '#ffb77d'
  secondary: '#82542c'
  on-secondary: '#ffffff'
  secondary-container: '#fdbf8f'
  on-secondary-container: '#784c25'
  tertiary: '#006096'
  on-tertiary: '#ffffff'
  tertiary-container: '#007abd'
  on-tertiary-container: '#fdfcff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdcc3'
  primary-fixed-dim: '#ffb77d'
  on-primary-fixed: '#2f1500'
  on-primary-fixed-variant: '#6e3900'
  secondary-fixed: '#ffdcc3'
  secondary-fixed-dim: '#f7ba8a'
  on-secondary-fixed: '#2f1500'
  on-secondary-fixed-variant: '#673d17'
  tertiary-fixed: '#cee5ff'
  tertiary-fixed-dim: '#96ccff'
  on-tertiary-fixed: '#001d32'
  on-tertiary-fixed-variant: '#004a75'
  background: '#fff8f5'
  on-background: '#231a13'
  surface-variant: '#f2dfd3'
typography:
  headline-xl:
    fontFamily: Geist Mono
    fontSize: 48px
    fontWeight: '600'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Geist Mono
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Geist Mono
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: 0em
  body-sm:
    fontFamily: Geist Mono
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
    letterSpacing: 0em
  label-caps:
    fontFamily: Geist Mono
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1.0'
    letterSpacing: 0.08em
  code-data:
    fontFamily: Geist Mono
    fontSize: 14px
    fontWeight: '500'
    lineHeight: '1.0'
    letterSpacing: 0em
spacing:
  base-unit: 4px
  container-max: 1440px
  gutter: 24px
  margin-page: 48px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style

The design system is anchored in the concept of "Financial Engineering." It rejects the softness of consumer fintech in favor of a high-utility, technical aesthetic that mirrors developer tools and high-frequency trading terminals. The brand personality is authoritative, transparent, and uncompromisingly precise. 

The visual language draws from **Minimalism** and **Modern Brutalism**, utilizing a strict grid and monochromatic foundations punctuated by a singular, functional highlight color. This approach builds trust through clarity, suggesting that every decimal point and data visualization is handled with mathematical exactitude. The target audience is the sophisticated borrower and financial professional who values efficiency and data density over decorative flair.

## Colors

The color palette is architected to facilitate focus. The primary amber (oklch(0.6660 0.1790 58.3180)) is used sparingly as a functional signal for action, progress, and critical data points. 

The primary workspace utilizes a "Near-White" background to minimize eye strain during long sessions, while the navigation and structural sidebars use a "Near-Black" to create a definitive frame for the content. Dividers use a desaturated, low-opacity version of the primary amber, creating a cohesive structural "blueprint" feel across the interface without overwhelming the user's cognitive load.

## Typography

This design system utilizes **Geist Mono** exclusively. As a monospaced typeface, it provides inherent alignment for numerical data—a critical requirement for a fintech platform. The fixed character width ensures that columns of figures remain perfectly stacked, facilitating quick vertical scanning of loan terms, interest rates, and amortization schedules.

Hierarchy is established through scale and weight rather than font variance. Headlines use semi-bold weights with tight letter spacing for a dense, impactful look. Body text prioritizes readability with generous line heights. Labels are presented in uppercase with increased letter spacing to serve as clear metadata markers.

## Layout & Spacing

The layout is built on a rigid **12-column fixed grid** that emphasizes structural integrity. All spacing follows a strict 4px baseline, ensuring that every element—from the height of an input field to the padding of a container—is a multiple of the base unit.

High whitespace is used strategically to separate complex data modules. Rather than using shadows or depth to group items, this design system relies on clear alignment and the use of 1px amber dividers. These dividers act as the "scaffolding" of the UI, creating a blueprint-like appearance that reinforces the platform's focus on precision.

## Elevation & Depth

This design system employs a **Flat Aesthetic**. There are no shadows, blurs, or gradients. Depth is communicated exclusively through:

1.  **High-Contrast Layering:** Light content areas sit against a dark sidebar, creating a clear functional distinction.
2.  **Color Blocking:** Actionable elements use the primary amber to "pop" forward against the neutral background.
3.  **Structural Framing:** 1px solid borders and dividers define the boundaries of containers. 

When an element is in an active or hovered state, visual feedback is provided through color inversion or weight changes rather than traditional elevation cues.

## Shapes

The shape language is strictly **Sharp (0px radius)**. Every container, button, input, and tooltip must have 90-degree corners. This lack of rounding eliminates the "friendly" softness typical of modern web design, opting instead for a professional, CAD-inspired look that suggests industrial-grade reliability. 

All interactive regions are defined by these hard edges, reinforcing the grid-based logic of the entire system.

## Components

### Buttons
Buttons are solid, sharp-edged blocks. The primary action button is Amber with Black text. Secondary buttons are outlined with a 1px divider-colored border and use Ghost Mono text.

### Inputs
Input fields are styled as simple 1px bottom-bordered elements or fully boxed containers with no rounding. Labels sit strictly above the input in the `label-caps` style. Focus states are indicated by a weight increase in the border and a change in border color to the primary Amber.

### Chips & Tags
Chips are rectangular blocks with no radius. They use a low-saturation background color to denote categories without distracting from the primary actions.

### Cards & Modules
Cards do not have shadows. They are defined by a 1px border or a subtle background color shift. They should always align perfectly with the 12-column grid.

### Data Visualization
Charts and graphs must use the primary Amber for the main data series. Grid lines within charts should match the subtle amber dividers used in the layout to ensure a unified visual language. All axes and tooltips must use the `code-data` typography style.