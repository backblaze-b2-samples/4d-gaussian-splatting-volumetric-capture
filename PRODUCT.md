# Product

## Register

product

## Users

Volumetric-capture / VFX engineers and AI/3D practitioners building a dynamic 4D
reconstruction pipeline, plus AI coding agents scaffolding one. Their context: they film
a moving scene with dozens of synchronized cameras and need durable, cheap, S3-compatible
object storage for the huge fan-out of intermediate and final artifacts — source video,
thousands of extracted frames, calibration, multi-GB training checkpoints, and the final
splat model. They want a working, engineering-minded scaffold that talks to Backblaze B2
out of the box, runs the CPU stages anywhere, and gates the CUDA training tail cleanly.

## Product Purpose

A capture-to-B2 pipeline (Next.js 16 + React 19 + Tailwind v4 + shadcn/ui frontend,
FastAPI backend) that turns synchronized multi-camera video into a hustvl/4DGaussians
`multipleview` dataset and a trained, time-varying Gaussian-Splatting model, with every
input and derived artifact versioned in Backblaze B2. The primary entity is a **Session**
whose record is a JSON manifest in B2 (no database). Success = a user can create a session,
run it to stage a real multipleview dataset + init cloud on B2, see the write-amplification
fan-out, and — on a CUDA host — train and export a real splat, never a faked one.

## Maturity and Support Boundary

This is a maintained open-source template/sample, not a complete hosted SaaS product or a
managed 4D-reconstruction service; it bundles no GPU compute. It is built with
production-minded controls and can be adapted for production use with caution, but adopters
own product-specific validation, security, deployment, and operations. Repository defects
and feature requests go through the public GitHub issue tracker; B2 account, billing,
service, and API questions go through Backblaze Support. The template/sample itself is not
covered by the Backblaze service level agreement, and no SLA is provided for the repository
software.

## Brand Personality

Confident, precise, quietly professional. Voice is direct and free of hype ("Stop
wiring boilerplate and start building"). The interface should feel like a modern
developer tool — considered, calm, trustworthy — not a marketing showpiece. It is a
**neutral foundation** that others rebrand: the design carries craft through restraint,
not through a strong opinionated identity of its own.

## Anti-references

- **Generic AI/SaaS slop.** No gradient text, hero-metric templates, identical
  icon-card grids, tracked uppercase eyebrows, or decorative glassmorphism. These are
  the exact 2026 AI tells this kit exists to help builders avoid.
- **Over-branded / loud.** No heavy brand-color drenching, decorative motion, or flashy
  effects. It is scaffolding to be rebranded, not a hero page.
- **Toy / prototype feel.** No missing states, inconsistent components, or placeholder
  polish. Must read as polished, dependable scaffolding.
- **Enterprise-drab.** No Bootstrap-era gray boxes or dense-but-lifeless admin-panel
  look. Considered, like modern dev tools (Linear, GitHub Primer, Stripe).

## Design Principles

- **Practice what you preach.** The kit itself must model the engineering quality it
  asks agents to produce. Slop here propagates into every project built on it.
- **Neutral foundation, easy to rebrand.** Identity lives in tokens (`globals.css`) and
  one config file. Screens are built from the shared UI kit so a rebrand is a token
  swap, not a rewrite.
- **Earned familiarity over novelty.** Use standard, trusted affordances (top bar +
  side nav, command palette, data tables). The tool disappears into the task.
- **Every state is designed.** Default, hover, focus, active, disabled, loading (skeleton),
  empty (teaches the interface), and error (says what's wrong + offers retry) — never
  half-shipped.
- **Consistency is the feature.** One button vocabulary, one form-control set, one icon
  style across every screen. Divergence is a bug.

## Accessibility & Inclusion

Target **WCAG 2.1 AA**. Body text ≥ 4.5:1, large/bold text ≥ 3:1, visible focus
indicators on every interactive element, full keyboard navigation, correct semantic
landmarks and heading order, labelled form controls, and a `prefers-reduced-motion`
alternative for every animation. Full light and dark theme parity.
