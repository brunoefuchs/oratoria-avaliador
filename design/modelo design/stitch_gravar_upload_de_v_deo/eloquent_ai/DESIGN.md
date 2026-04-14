# Design System Document: The Resonant Stage

## 1. Overview & Creative North Star
**Creative North Star: "The Luminescent Mentor"**

This design system moves away from the cold, analytical "dashboard" aesthetic typical of AI tools. Instead, it embraces a high-end editorial feel that balances the precision of artificial intelligence with the warmth of human coaching. 

To break the "template" look, we utilize **Intentional Asymmetry** and **Tonal Depth**. We avoid rigid, boxed-in grids in favor of overlapping elements and vast breathing room. The UI should feel like a premium stage—dark, focused, and sophisticated—where the user’s progress is illuminated by vibrant, "living" data.

---

## 2. Colors & Surface Philosophy
The palette is rooted in a nocturnal "Deep Sea" blue, providing a foundation of trust and focus, punctuated by "Bioluminescent" teals and "Golden Hour" accents.

### The "No-Line" Rule
**Traditional 1px borders are strictly prohibited for sectioning.** Structural containment must be achieved through background shifts. For example, a `surface-container-low` section sitting on a `surface` background creates a sophisticated boundary that feels organic rather than mechanical.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers—like stacked sheets of frosted glass.
*   **Base Layer:** `surface` (#0b1326) — The "stage" background.
*   **Sectioning Layer:** `surface-container-low` (#131b2e) — Large layout blocks.
*   **Interactive Layer:** `surface-container-high` (#222a3d) — Interactive cards and modules.
*   **Focus Layer:** `surface-container-highest` (#2d3449) — Overlays and active states.

### The "Glass & Gradient" Rule
To evoke a "high-tech" soul, main CTAs and hero elements should utilize subtle gradients. 
*   **The AI Pulse:** Transition from `secondary` (#45d8ed) to `primary_container` (#004d89) at a 135-degree angle.
*   **Glassmorphism:** For floating controllers or floating feedback widgets, use `surface_variant` (#2d3449) at 60% opacity with a `20px` backdrop-blur. This softens the edges and integrates the UI into the background.

---

## 3. Typography
Our typography pairing is designed for "Authoritative Encouragement."

*   **Display & Headlines (Manrope):** Use `display-lg` through `headline-sm` for high-impact coaching insights. The wide, geometric nature of Manrope feels modern and cinematic. Use negative letter-spacing (-2%) on `display-lg` to create a tighter, premium editorial feel.
*   **Body & Titles (Plus Jakarta Sans):** Chosen for its exceptional readability. Use `body-lg` for coaching feedback and `title-md` for instructional headers. 
*   **Labels (Plus Jakarta Sans):** Use `label-md` in `on_surface_variant` (#c3c6d4) for metadata.

**Editorial Tip:** Use "The Power Gap"—juxtapose a `display-sm` headline with a `body-sm` label immediately below it to create a high-contrast, modern hierarchy that guides the eye instantly to the most important data.

---

## 4. Elevation & Depth
In "The Resonant Stage," we do not use heavy shadows to create lift; we use light.

*   **Tonal Layering:** Depth is achieved by "stacking." Place a `surface_container_lowest` (#060e20) card inside a `surface_container_high` (#222a3d) section to create a "recessed" or "carved" look.
*   **Ambient Shadows:** For floating elements (Modals/Poppers), use a shadow with a blur of `40px`, an opacity of `8%`, and a color derived from `on_background` (#dae2fd). It should look like a soft glow, not a dark smudge.
*   **The "Ghost Border" Fallback:** If a boundary is required for accessibility, use the `outline_variant` (#434652) at **15% opacity**. It should be felt, not seen.

---

## 5. Components

### Buttons (The Interaction Points)
*   **Primary:** Gradient from `primary` to `primary_container`. `xl` (1.5rem) roundedness. No border. Text in `on_primary`.
*   **Secondary:** Solid `surface_container_highest`. `xl` roundedness. A "Ghost Border" of 10% `primary`. 
*   **Encouragement Action:** Use `tertiary` (#ffb954) for "Celebrate" or "Review Milestone" actions to provide a warm, human contrast to the tech-heavy teals.

### Cards & Content Modules
*   **Rule:** **Forbid the use of divider lines.** 
*   **Implementation:** Separate the speaker's "Words Per Minute" from "Tone Analysis" using `10` (2.5rem) on the Spacing Scale. If containment is needed, use a subtle shift from `surface_container_low` to `surface_container_high`.

### Input Fields (The Speech Capture)
*   **States:** Default state is a `surface_container_highest` fill. On focus, the background remains, but a `secondary` (#45d8ed) "Ghost Border" appears at 40% opacity with a subtle outer glow (4px blur).

### AI Feedback Chips
*   **Style:** `sm` (0.25rem) roundedness for a slightly more technical feel. Use `secondary_container` (#00bacd) backgrounds with `on_secondary_container` text. 

### Additional Component: The "Fluency Wave"
*   **Visual:** A custom progress component using a blurred `secondary` gradient line that flows across the bottom of a `surface_container_high` card, representing the rhythm of the user's speech.

---

## 6. Do's and Don'ts

### Do
*   **Do** use asymmetrical margins. If the left margin is `16` (4rem), try a right margin of `24` (6rem) for a modern, editorial look.
*   **Do** use `tertiary` (#ffb954) sparingly. It is a "reward" color, meant to highlight success and encouragement.
*   **Do** leverage `0.5rem` (DEFAULT) and `0.75rem` (md) roundedness for small elements, but `full` roundedness for primary CTAs to make them feel inviting.

### Don't
*   **Don't** use pure black (#000000). Always use the deep blue `surface` (#0b1326) to maintain the "Trust" theme.
*   **Don't** use 100% opaque borders. They break the fluid, high-tech glass aesthetic.
*   **Don't** crowd the interface. If an AI insight is important, give it at least `12` (3rem) of vertical spacing from other elements.