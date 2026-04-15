# A11y: Fix Heading Hierarchy

**WCAG:** 1.3.1 Info and Relationships (Level A)

## Problem

The heading structure is not logically nested across several pages. The pa11y htmlcs runner flagged `G141` (heading not logically nested) and the axe runner flagged `heading-order` on `/people/` and `/essays/`.

Specific issues:
1. Pages jump from `<h1>` to `<h3>`, skipping `<h2>`
2. `<h2>` elements are placed inside `<ul>` elements (invalid nesting, flagged by axe as `list` error on `/essays/`)
3. The `<h1>` in `base.html` is used for breadcrumbs rather than the page title
4. Empty heading tag on the login page (flagged as `H42.2`)

## Affected Files

- `rome_app/templates/rome_templates/base.html`: `<h1>` used for breadcrumbs
- `rome_app/templates/rome_templates/biography_list.html`: h1 → h3 (skips h2)
- `rome_app/templates/rome_templates/essay_list.html`: `<h2>` inside `<ul>` elements
- `rome_app/templates/rome_templates/result_base.html`: h3 used without preceding h2
- `rome_app/templates/rome_templates/login.html`: Empty heading tag

## Suggested Fix

1. Move `<h2>` elements outside of `<ul>` containers
2. Ensure heading levels increment by one (h1 → h2 → h3)
3. Consider using breadcrumb navigation (`<nav aria-label="Breadcrumb">`) separately from the page heading
4. Remove or populate empty heading tags

## WCAG Reference

- **Success Criterion:** 1.3.1 Info and Relationships (Level A)
- **Technique:** [G141](https://www.w3.org/WAI/WCAG21/Techniques/general/G141) — Organizing a page using headings

## Related

See full assessment: `ACCESSIBILITY_REPORT.md`
