# A11y: Add ARIA Live Regions for Dynamic Content

**WCAG:** 4.1.3 Status Messages (Level AA)

## Problem

Dynamic content updates on the search page and turnstile challenge page are not communicated to assistive technology users. When search results load or errors occur, there are no ARIA live regions to announce the changes.

## Affected Files

### Search Page
- **`rome_app/templates/rome_templates/search_page.html`**:
  - `#num_results` span (line 270) — receives dynamic result count text but is not a live region
  - Book/print result containers — populated dynamically without announcement

  Fix: Add `role="status"` and `aria-live="polite"` to `#num_results`:
  ```html
  <div><span id="num_results" role="status" aria-live="polite"></span></div>
  ```

### Turnstile Challenge
- **`rome_app/templates/rome_templates/turnstile_challenge.html`**:
  - `#result` div receives error messages via JavaScript but has no live region attributes

  Fix: Add `role="alert"` to the result div:
  ```html
  <div id="result" role="alert"></div>
  ```

### Login Error
- **`rome_app/templates/rome_templates/login.html`**:
  - Error message paragraph not associated with form or announced

  Fix: Add `role="alert"`:
  ```html
  {% if form.errors %}
  <p role="alert">Your username and password didn't match. Please try again.</p>
  {% endif %}
  ```

## WCAG Reference

- **Success Criterion:** 4.1.3 Status Messages (Level AA)
- **Success Criterion:** 3.3.1 Error Identification (Level A)
- **Technique:** [ARIA22](https://www.w3.org/WAI/WCAG21/Techniques/aria/ARIA22) — Using role=status to present status messages

## Related

See full assessment: `ACCESSIBILITY_REPORT.md`
