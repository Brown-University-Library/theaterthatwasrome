# A11y: Add Accessible Names to Pagination Buttons

**WCAG:** 4.1.2 Name, Role, Value (Level A)

## Problem

Pagination buttons on list pages display only a number (e.g., "1", "2", "3") without accessible context. Screen reader users hear just the number without understanding it represents a page.

## Affected Files

1. **`rome_app/templates/rome_templates/result_base.html`**:
   ```html
   <!-- Current -->
   <button id="page_button_{{i}}" class="page_button btn btn-default" onclick="show_page({{i}})">{{i}}</button>
   <!-- Fix -->
   <button id="page_button_{{i}}" class="page_button btn btn-default" onclick="show_page({{i}})" aria-label="Go to page {{i}}">{{i}}</button>
   ```

2. **`rome_app/templates/rome_templates/essay_list.html`**: Similar pagination buttons need `aria-label`

3. **`rome_app/templates/rome_templates/shop_list.html`**: Similar pagination buttons need `aria-label`

Additionally, the currently active page button should include `aria-current="page"`. This needs to be set via JavaScript when a page is selected.

## WCAG Reference

- **Success Criterion:** 4.1.2 Name, Role, Value (Level A)
- **Technique:** [ARIA14](https://www.w3.org/WAI/WCAG21/Techniques/aria/ARIA14) — Using aria-label to provide an invisible label where a visible label cannot be used

## Related

See full assessment: `ACCESSIBILITY_REPORT.md`
