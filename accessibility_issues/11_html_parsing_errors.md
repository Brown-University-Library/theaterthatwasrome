# A11y: Fix HTML Parsing Errors in Templates

**WCAG:** 4.1.1 Parsing (Level A)

## Problem

Several templates have HTML parsing issues that may affect accessibility:

1. **Unclosed `<head>` tag**: `base.html` line 19 uses `<head>` instead of `</head>`
2. **Missing DOCTYPE**: `new_annotation.html` and `new_record.html` lack `<!DOCTYPE html>`
3. **Missing charset**: `new_annotation.html` and `new_record.html` lack `<meta charset="utf-8">`
4. **Empty title**: `popup_response.html` has an empty `<title></title>`
5. **Empty title**: Login page renders with an empty title (pa11y: `H25.1.EmptyTitle`)

## Affected Files

1. **`rome_app/templates/rome_templates/base.html`** line 19:
   ```html
   <!-- Current (broken) -->
   <head>
   <!-- Fix -->
   </head>
   ```

2. **`rome_app/templates/rome_templates/new_annotation.html`** — add before `<html>`:
   ```html
   <!DOCTYPE html>
   ```
   And inside `<head>`:
   ```html
   <meta charset="utf-8">
   <title>New Annotation — The Theater That Was Rome</title>
   ```

3. **`rome_app/templates/rome_templates/new_record.html`** — add:
   ```html
   <!DOCTYPE html>
   <html lang="en">
     <head>
       <meta charset="utf-8">
       <title>New Record — The Theater That Was Rome</title>
     </head>
   ```

4. **`rome_app/templates/rome_templates/popup_response.html`** line 3:
   ```html
   <title>Processing — The Theater That Was Rome</title>
   ```

5. **Login page**: Ensure the `{% block title %}` provides content for the login page.

## WCAG Reference

- **Success Criterion:** 4.1.1 Parsing (Level A)
- **Success Criterion:** 2.4.2 Page Titled (Level A)

## Related

See full assessment: `ACCESSIBILITY_REPORT.md`
