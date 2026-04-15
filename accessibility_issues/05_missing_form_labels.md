# A11y: Add Labels to Form Inputs

**WCAG:** 1.3.1 Info and Relationships (Level A), 4.1.2 Name, Role, Value (Level A)

## Problem

The search input on the search page has no associated label, `aria-label`, or `title` attribute. Both pa11y runners flagged this: htmlcs reported `F68` and `H91.InputText.Name`, axe reported `label`.

Screen reader users have no indication of what the input field is for.

## Affected Files

### Search Page
- `rome_app/templates/rome_templates/search_page.html` line 268:
  ```html
  <!-- Current -->
  <input type="text" id="search" onkeyup="inputKeyUp(event)">
  <!-- Fix -->
  <label for="search">Search books and prints</label>
  <input type="text" id="search" onkeyup="inputKeyUp(event)">
  ```

### Login Page
- `rome_app/templates/rome_templates/login.html` — form uses `<table>` layout; replace with CSS-based layout and ensure labels are properly associated via `<label for="...">`:
  ```html
  <!-- Fix: Replace table with div-based layout -->
  <div>
    {{ form.username.label_tag }}
    {{ form.username }}
  </div>
  <div>
    {{ form.password.label_tag }}
    {{ form.password }}
  </div>
  ```

## WCAG Reference

- **Success Criterion:** 1.3.1 Info and Relationships (Level A)
- **Success Criterion:** 4.1.2 Name, Role, Value (Level A)
- **Technique:** [H44](https://www.w3.org/WAI/WCAG21/Techniques/html/H44) — Using label elements to associate text labels with form controls

## Related

See full assessment: `ACCESSIBILITY_REPORT.md`
