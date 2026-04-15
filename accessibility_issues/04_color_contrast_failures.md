# A11y: Fix Color Contrast Failures

**WCAG:** 1.4.3 Contrast Minimum (Level AA)

## Problem

Multiple elements fail the minimum color contrast ratio. The axe runner reported `color-contrast` errors on `/`, `/people/`, `/essays/`, and `/search/`. The htmlcs runner flagged `G18.Fail` and `G145.BgImage` warnings.

Specific failures identified:

1. **Header breadcrumb links**: white (`#fff`) text on `#70675d` background — ratio ~2.9:1 (needs 3:1 for large text, 4.5:1 for normal text)
2. **Breadcrumb separator**: `color:#000` on `#70675d` background — ratio ~3.4:1
3. **Body links**: `#805525` on `#E8C577` background — ratio ~2.8:1 (needs 4.5:1)
4. **Result item links**: `#89775D` on `#F2D69E` background — ratio ~2.6:1

Users with low vision cannot read text that lacks sufficient contrast.

## Affected Files

- `rome_app/static/rome/css/common.css`:
  - `a` color `#805525` — needs to be darker (e.g., `#5a3a18`)
  - `h1 a` color `#fff` on `#70675d` background — consider darkening background or increasing font weight
  - `div#page_head h1` background color `#70675d`
  - Breadcrumb separator inline style `color:#000`
- `rome_app/templates/rome_templates/base.html` line 26 — inline `color:#000`

## WCAG Reference

- **Success Criterion:** 1.4.3 Contrast (Minimum) (Level AA)
- **Technique:** [G18](https://www.w3.org/WAI/WCAG21/Techniques/general/G18) — Ensuring that a contrast ratio of at least 4.5:1 exists between text and background
- **Tool:** Use [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/) to verify all color combinations

## Related

See full assessment: `ACCESSIBILITY_REPORT.md`
