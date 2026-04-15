# A11y: Add Alt Text to All Images

**WCAG:** 1.1.1 Non-text Content (Level A)

## Problem

Multiple templates render `<img>` elements without `alt` attributes. This is a WCAG 1.1.1 (Level A) violation. Images inside links that lack alt text make those links completely inaccessible to screen reader users.

Additionally, the JavaScript `create_thumbnail()` function in `search_page.html` dynamically creates `<img>` elements without setting `alt` attributes.

## Affected Files

### Template Images (server-rendered)

1. **`biography_detail.html`**: `<img height='150px' src="{{page.thumb}}"/>` — add `alt="Thumbnail of page {{ num }}"`
2. **`book_detail.html`**: `<img src="{{ page.thumbnail_src }}" height="150px"/>` — add `alt="Page {{ forloop.counter }} thumbnail"`
3. **`essay_detail.html`**: `<img height="150px" src="...bdr:{{work.pid}}/"/>` — add `alt="Thumbnail of related work"`
4. **`essay_list.html`**: `<img height="80px" src="...bdr:{{work.1}}/"/>` — add `alt="Thumbnail for {{ work.0 }}"`
5. **`shop_list.html`**: `<img height="80px" src="...bdr:{{work.1}}/"/>` — add `alt="Thumbnail for related work"`
6. **`shop_detail.html`**: Images in related works sections — add appropriate `alt` text

### JavaScript-Created Images

7. **`search_page.html`** `create_thumbnail()` function (line 238): Add `thumbnail.attr('alt', 'Thumbnail for page ' + stripPid(pagepid));`

## WCAG Reference

- **Success Criterion:** 1.1.1 Non-text Content (Level A)
- **Technique:** [H37](https://www.w3.org/WAI/WCAG21/Techniques/html/H37) — Using alt attributes on img elements

## Related

See full assessment: `ACCESSIBILITY_REPORT.md`
