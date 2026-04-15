# A11y: Add `lang` Attribute to All HTML Elements

**WCAG:** 3.1.1 Language of Page (Level A)

## Problem

Every `<html>` element in the project is missing the `lang` attribute. This was detected by both pa11y htmlcs runner (`H57.2`) and axe runner (`html-has-lang`) on all tested pages.

Screen readers cannot determine the language of the page, leading to incorrect pronunciation of content.

## Affected Files

- `rome_app/templates/rome_templates/base.html` line 3: `<html>` → `<html lang="en">`
- `rome_app/templates/rome_templates/new_annotation.html` line 3: `<html>` → `<html lang="en">`
- `rome_app/templates/rome_templates/new_record.html` line 1: `<html>` → `<html lang="en">`
- `rome_app/templates/rome_templates/popup_response.html` line 2: `<html>` → `<html lang="en">`

## WCAG Reference

- **Success Criterion:** 3.1.1 Language of Page (Level A)
- **Technique:** [H57](https://www.w3.org/WAI/WCAG21/Techniques/html/H57) — Using the language attribute on the HTML element

## Related

See full assessment: `ACCESSIBILITY_REPORT.md`
