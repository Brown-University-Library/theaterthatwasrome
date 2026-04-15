# A11y: Add ARIA Attributes to Toggle Buttons and Expandable Content

**WCAG:** 4.1.2 Name, Role, Value (Level A)

## Problem

Multiple detail pages have toggle buttons that expand/collapse content sections. These buttons:
- Contain only a down-arrow character (`˅`) with no accessible label
- Lack `aria-expanded` state
- Lack `aria-controls` linking to the content they toggle
- The content they toggle lacks `aria-hidden` when collapsed

Screen reader users cannot determine the purpose or state of these controls.

## Affected Files

1. **`biography_detail.html`**: `<button>˅</button>` — toggle for biography sections
2. **`book_detail.html`**: Essay section toggle
3. **`essay_detail.html`**: `<button>˅</button>` — toggle for detail sections
4. **`page_detail.html`**: `<button>˅</button>` — toggle for essays section

## Suggested Fix

For each toggle button:

```html
<!-- Before -->
<button>˅</button>

<!-- After -->
<button aria-label="Toggle details" aria-expanded="false" aria-controls="detail-section-id">˅</button>
```

Update JavaScript toggle functions to:
1. Toggle `aria-expanded` between `"true"` and `"false"`
2. Toggle `aria-hidden` on the controlled content
3. Update button text/icon to reflect state

## WCAG Reference

- **Success Criterion:** 4.1.2 Name, Role, Value (Level A)
- **Technique:** [ARIA5](https://www.w3.org/WAI/WCAG21/Techniques/aria/ARIA5) — Using WAI-ARIA state and property attributes to expose the state of a user interface component

## Related

See full assessment: `ACCESSIBILITY_REPORT.md`
