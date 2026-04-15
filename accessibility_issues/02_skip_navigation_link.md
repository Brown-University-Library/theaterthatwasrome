# A11y: Add Skip Navigation Link

**WCAG:** 2.4.1 Bypass Blocks (Level A)

## Problem

There is no skip navigation link allowing keyboard users to bypass the header, breadcrumbs, and navigation and jump directly to the main content area. This was flagged by the axe runner as `landmark-one-main` and `region` warnings, and by htmlcs as `G1,G123,G124,H69`.

Keyboard-only users must tab through the entire header on every page before reaching content.

## Affected Files

- `rome_app/templates/rome_templates/base.html` — add skip link as first child of `<body>`
- `rome_app/static/rome/css/common.css` — add visually-hidden skip link styles

## Suggested Fix

Add as first element inside `<body>` in `base.html`:

```html
<a href="#page_body" class="skip-link">Skip to main content</a>
```

Add to `common.css`:

```css
.skip-link {
    position: absolute;
    top: -40px;
    left: 0;
    background: #000;
    color: #fff;
    padding: 8px;
    z-index: 100;
}
.skip-link:focus {
    top: 0;
}
```

## WCAG Reference

- **Success Criterion:** 2.4.1 Bypass Blocks (Level A)
- **Technique:** [G1](https://www.w3.org/WAI/WCAG21/Techniques/general/G1) — Adding a link at the top of each page that goes directly to the main content area

## Related

See full assessment: `ACCESSIBILITY_REPORT.md`
