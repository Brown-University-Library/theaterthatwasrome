# Accessibility Issues

This directory contains individual issue descriptions for WCAG 2.1 accessibility deficiencies identified in the accessibility assessment.

Each file is formatted as a GitHub issue and can be used to create issues in the repository's issue tracker.

## Issues Summary

| # | File | WCAG Level | Title |
|---|------|------------|-------|
| 1 | `01_missing_lang_attribute.md` | A | Add `lang` attribute to all HTML elements |
| 2 | `02_skip_navigation_link.md` | A | Add skip navigation link |
| 3 | `03_semantic_landmark_regions.md` | A | Add semantic landmark regions |
| 4 | `04_color_contrast_failures.md` | AA | Fix color contrast failures |
| 5 | `05_missing_form_labels.md` | A | Add labels to form inputs |
| 6 | `06_missing_image_alt_text.md` | A | Add alt text to all images |
| 7 | `07_aria_toggle_buttons.md` | A | Add ARIA attributes to toggle buttons |
| 8 | `08_heading_hierarchy.md` | A | Fix heading hierarchy |
| 9 | `09_iframe_titles.md` | A | Add title to iframe elements |
| 10 | `10_aria_live_regions.md` | AA | Add ARIA live regions for dynamic content |
| 11 | `11_html_parsing_errors.md` | A | Fix HTML parsing errors |
| 12 | `12_pagination_accessible_names.md` | A | Add accessible names to pagination buttons |

## Creating Issues

To create GitHub issues from these files, you can use the GitHub CLI:

```bash
for f in accessibility_issues/[0-9]*.md; do
    title=$(head -1 "$f" | sed 's/^# //')
    gh issue create --title "$title" --body-file "$f" --label "accessibility"
done
```

## Full Report

See `ACCESSIBILITY_REPORT.md` in the project root for the complete assessment.
