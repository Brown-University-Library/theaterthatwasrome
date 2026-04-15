# A11y: Add Title to Iframe Elements

**WCAG:** 2.4.1 Bypass Blocks (Level A), 4.1.2 Name, Role, Value (Level A)

## Problem

Iframe elements are used for image viewing on annotation and page detail pages but have no `title` attribute. Screen reader users cannot determine the purpose of these iframes.

## Affected Files

1. **`rome_app/templates/rome_templates/new_annotation.html`** line 39:
   ```html
   <!-- Current -->
   <iframe src="{{image_link}}" width="98%" height="800" ...></iframe>
   <!-- Fix -->
   <iframe src="{{image_link}}" width="98%" height="800" title="Image viewer" ...></iframe>
   ```

2. **`rome_app/templates/rome_templates/page_detail.html`**:
   ```html
   <!-- Current -->
   <iframe src={{ det_img_view_src}} ...></iframe>
   <!-- Fix -->
   <iframe src="{{ det_img_view_src }}" title="Page image viewer" ...></iframe>
   ```

## WCAG Reference

- **Success Criterion:** 2.4.1 Bypass Blocks (Level A)
- **Success Criterion:** 4.1.2 Name, Role, Value (Level A)
- **Technique:** [H64](https://www.w3.org/WAI/WCAG21/Techniques/html/H64) — Using the title attribute of the iframe element

## Related

See full assessment: `ACCESSIBILITY_REPORT.md`
