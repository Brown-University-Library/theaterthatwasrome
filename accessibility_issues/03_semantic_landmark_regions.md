# A11y: Add Semantic Landmark Regions

**WCAG:** 1.3.1 Info and Relationships (Level A)

## Problem

The page uses `<div>` elements for all major structural regions instead of semantic HTML5 landmark elements. The axe runner flagged `landmark-one-main` (no `<main>` landmark) and `region` (content not in landmarks) on every tested page.

Assistive technology users cannot navigate by landmarks, which is one of the most common screen reader navigation methods.

## Affected Files

- `rome_app/templates/rome_templates/base.html`:
  - `div#page_head` → `<header id="page_head">`
  - `div.navigation` → `<nav class="navigation">`
  - `div#page_body` → `<main id="page_body">`
  - `div#footer` → `<footer id="footer">`

## WCAG Reference

- **Success Criterion:** 1.3.1 Info and Relationships (Level A)
- **Technique:** [ARIA11](https://www.w3.org/WAI/WCAG21/Techniques/aria/ARIA11) — Using ARIA landmarks to identify regions of a page

## Related

See full assessment: `ACCESSIBILITY_REPORT.md`
