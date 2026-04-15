# Accessibility Report

- URL: https://library.brown.edu/projects/rome/
- Page title: The Theater that was Rome
- Scanned: 2026-04-15T14:58:15.362Z
- Violations: 3
- Incomplete: 1
- Passes: 14

## Violations

### html-has-lang

- Impact: serious
- Description: Ensure every HTML document has a lang attribute
- Help: <html> element must have a lang attribute
- Help URL: https://dequeuniversity.com/rules/axe/4.11/html-has-lang?application=playwright
- Nodes affected: 1

- Target: `html`
- Failure: Fix any of the following:   The <html> element does not have a lang attribute

### landmark-one-main

- Impact: moderate
- Description: Ensure the document has a main landmark
- Help: Document should have one main landmark
- Help URL: https://dequeuniversity.com/rules/axe/4.11/landmark-one-main?application=playwright
- Nodes affected: 1

- Target: `html`
- Failure: Fix all of the following:   Document does not have a main landmark

### region

- Impact: moderate
- Description: Ensure all page content is contained by landmarks
- Help: All page content should be contained by landmarks
- Help URL: https://dequeuniversity.com/rules/axe/4.11/region?application=playwright
- Nodes affected: 4

- Target: `h1`
- Failure: Fix any of the following:   Some page content is not contained by landmarks
- Target: `.intro`
- Failure: Fix any of the following:   Some page content is not contained by landmarks
- Target: `#page_body`
- Failure: Fix any of the following:   Some page content is not contained by landmarks
- Target: `#footer`
- Failure: Fix any of the following:   Some page content is not contained by landmarks

## Incomplete

- color-contrast: Elements must meet minimum color contrast ratio thresholds
