# Accessibility Assessment Report — The Theater That Was Rome

**Date:** 2026-04-15
**Standard:** WCAG 2.1 Level AA
**Tools Used:** pa11y 8.x (htmlcs runner + axe runner), manual template review
**Pages Tested:** `/` (Home), `/people/`, `/essays/`, `/search/`, `/login/`
**Additional Templates Reviewed Manually:** `about.html`, `biography_detail.html`, `book_detail.html`, `book_list.html`, `document_detail.html`, `documents.html`, `essay_detail.html`, `essay_list.html`, `links.html`, `new_annotation.html`, `new_record.html`, `page_detail.html`, `popup_response.html`, `print_list.html`, `result_base.html`, `search_page.html`, `shop_detail.html`, `shop_list.html`, `shops.html`, `turnstile_challenge.html`

> Pages that depend on external BDR API data (`/books/`, `/prints/`, `/about/`, `/links/`, `/shops/`) returned 404/500 in the test environment and could not be tested with pa11y. Their templates were reviewed manually for issues.

---

## Executive Summary

The site has several systemic accessibility deficiencies affecting all pages, plus page-specific issues. The most critical problems are:

1. **Missing `lang` attribute** on every `<html>` element (WCAG 3.1.1 — Level A)
2. **Color contrast failures** on header/breadcrumb text (WCAG 1.4.3 — Level AA)
3. **Missing form labels** on the search input (WCAG 1.3.1, 4.1.2 — Level A)
4. **No landmark regions** — no `<main>`, `<nav>`, `<header>`, or `<footer>` landmarks (WCAG 1.3.1 — Level A)
5. **No skip navigation link** (WCAG 2.4.1 — Level A)
6. **Missing alt text** on images across detail pages (WCAG 1.1.1 — Level A)
7. **Missing ARIA attributes** on interactive toggle buttons/expandable sections (WCAG 4.1.2 — Level A)

---

## Pa11y Automated Test Results

### Errors (Must Fix)

| Code | WCAG SC | Level | Pages Affected | Description |
|------|---------|-------|----------------|-------------|
| `H57.2` | 3.1.1 | A | All pages | `<html>` element missing `lang` attribute |
| `G18.Fail` | 1.4.3 | AA | `/people/`, `/essays/`, `/search/`, `/` | Insufficient color contrast on header breadcrumb text and links |
| `H91.InputText.Name` | 4.1.2 | A | `/search/` | Search text input has no accessible name |
| `F68` | 1.3.1 | A | `/search/` | Search form field not labelled |
| `H25.1.EmptyTitle` | 2.4.2 | A | `/login/` | Empty `<title>` element |
| `H42.2` | 1.3.1 | A | `/login/` | Empty heading tag |
| `html-has-lang` (axe) | 3.1.1 | A | All pages | Duplicate of H57.2 |
| `document-title` (axe) | 2.4.2 | A | `/login/` | Missing document title |
| `label` (axe) | 1.3.1/4.1.2 | A | `/search/` | Form element missing label |
| `color-contrast` (axe) | 1.4.3 | AA | `/`, `/people/`, `/essays/`, `/search/` | Multiple elements fail contrast ratio |
| `list` (axe) | 1.3.1 | A | `/essays/` | `<ul>` contains non-`<li>` children (`<h2>` inside `<ul>`) |

### Warnings (Should Fix)

| Code | WCAG SC | Level | Pages Affected | Description |
|------|---------|-------|----------------|-------------|
| `G145.BgImage` | 1.4.3 | AA | All pages with header | Text on background images — contrast not verifiable |
| `F24.FGColour` | 1.4.3 | AA | `/people/`, `/essays/`, `/search/` | Foreground color set without corresponding background |
| `G141` | 1.3.1 | A | `/people/`, `/essays/` | Heading hierarchy not logically nested (h3 appears before h2) |
| `H48` | 1.3.1 | A | All pages | Footer navigation section not marked up as a list |
| `landmark-one-main` (axe) | 1.3.1 | A | All pages | No `<main>` landmark |
| `region` (axe) | 1.3.1 | A | All pages | Page content not contained by landmarks |
| `heading-order` (axe) | 1.3.1 | A | `/people/`, `/essays/` | Heading levels skip (e.g., h1 → h3) |

---

## Manual Template Review Findings

### Issue 1: Missing `lang` Attribute on `<html>` (All Pages)

**WCAG 3.1.1 — Language of Page (Level A)**

**Files affected:**
- `base.html` line 3: `<html>` — no `lang` attribute
- `new_annotation.html` line 3: `<html>` — no `lang` attribute
- `new_record.html` line 1: `<html>` — no `lang` attribute
- `popup_response.html` line 2: `<html>` — no `lang` attribute

**Impact:** Screen readers cannot determine the language of the page, leading to incorrect pronunciation of content.

**Fix:** Add `lang="en"` to all `<html>` elements.

---

### Issue 2: No Skip Navigation Link (All Pages)

**WCAG 2.4.1 — Bypass Blocks (Level A)**

**File affected:** `base.html`

**Impact:** Keyboard users must tab through the entire header, breadcrumb, and navigation on every page before reaching main content.

**Fix:** Add a skip link as the first element in `<body>`: `<a href="#page_body" class="skip-link">Skip to main content</a>` with appropriate visually-hidden-but-focusable CSS.

---

### Issue 3: No Landmark Regions (All Pages)

**WCAG 1.3.1 — Info and Relationships (Level A)**

**File affected:** `base.html`

The page structure uses `<div>` elements for all major regions:
- `div#page_head` should be `<header>`
- `div.navigation` should be `<nav>`
- `div#page_body` should be `<main>`
- `div#footer` should be `<footer>`

**Impact:** Assistive technology users cannot navigate by landmarks, which is one of the most common AT navigation methods.

**Fix:** Replace structural `<div>` elements with semantic HTML5 elements (`<header>`, `<nav>`, `<main>`, `<footer>`).

---

### Issue 4: Color Contrast Failures (All Pages with Header)

**WCAG 1.4.3 — Contrast (Minimum) (Level AA)**

**Files affected:**
- `common.css`: `h1 a` color `#fff` on background `#70675d` — contrast ratio ~2.9:1 (minimum 4.5:1 required for normal text, 3:1 for large text at 24px — this is borderline)
- `common.css`: Breadcrumb separator `<span style="color:#000;">` on the same `#70675d` background — ratio ~3.4:1
- Various links using `#805525` on `#E8C577` background — ratio ~2.8:1 (fails)
- `#89775D` link color on `#F2D69E` background — ratio ~2.6:1 (fails)

**Impact:** Users with low vision cannot read text that lacks sufficient contrast.

**Fix:** Darken link colors or lighten backgrounds to meet 4.5:1 ratio (or 3:1 for large text). For example:
- Change body link color from `#805525` to `#5a3a18` or darker
- Verify all color combinations with a contrast checker

---

### Issue 5: Missing Form Labels on Search Page

**WCAG 1.3.1 — Info and Relationships (Level A)**
**WCAG 4.1.2 — Name, Role, Value (Level A)**

**File affected:** `search_page.html` line 268

```html
<input type="text" id="search" onkeyup="inputKeyUp(event)">
```

The search input has no `<label>`, no `aria-label`, and no `title` attribute.

**Impact:** Screen reader users have no indication of what the input field is for.

**Fix:** Add `<label for="search">Search</label>` or `aria-label="Search books and prints"` to the input.

---

### Issue 6: Missing `alt` Text on Images (Multiple Detail Pages)

**WCAG 1.1.1 — Non-text Content (Level A)**

**Files affected:**
- `biography_detail.html`: `<img height='150px' src="{{page.thumb}}"/>` — no `alt`
- `book_detail.html`: `<img src="{{ page.thumbnail_src }}" height="150px"/>` — no `alt`
- `essay_detail.html`: `<img height="150px" src="...bdr:{{work.pid}}/"/>` — no `alt`
- `essay_list.html`: `<img height="80px" src="...bdr:{{work.1}}/"/>` — no `alt`
- `shop_list.html`: `<img height="80px" src="...bdr:{{work.1}}/"/>` — no `alt`
- `shop_detail.html`: images in related works — no `alt`
- `search_page.html` (JavaScript): dynamically created `<img>` thumbnails — no `alt`

**Impact:** Screen reader users get no information about the images. Links containing only images become completely inaccessible.

**Fix:** Add meaningful `alt` text to all `<img>` elements. For thumbnails, use descriptive text like `alt="Thumbnail of page {{ forloop.counter }}"` or `alt="Thumbnail of {{ work.title }}"`. For decorative images, use `alt=""`.

---

### Issue 7: Missing ARIA Attributes on Expandable/Collapsible Sections

**WCAG 4.1.2 — Name, Role, Value (Level A)**

**Files affected:**
- `biography_detail.html`: `<button>˅</button>` toggle — no `aria-label`, `aria-expanded`, or `aria-controls`
- `book_detail.html`: Essay toggle — no ARIA attributes
- `essay_detail.html`: `<button>˅</button>` — no ARIA attributes
- `page_detail.html`: `<button>˅</button>` — no ARIA attributes

**Impact:** Screen reader users cannot determine the purpose or state of toggle buttons. They see a button labelled only with a down arrow character.

**Fix:** Add `aria-label="Toggle section"`, `aria-expanded="false"` (toggled via JS), and `aria-controls="target-id"` to each toggle button. Add `aria-hidden` to collapsed content.

---

### Issue 8: Heading Hierarchy Issues (Multiple Pages)

**WCAG 1.3.1 — Info and Relationships (Level A)**

**Files affected:**
- `base.html`: Uses `<h1>` for breadcrumb/page title in header
- `result_base.html`, `biography_list.html`, `essay_list.html`: Jump from `<h1>` to `<h3>` (skipping `<h2>`)
- `essay_list.html`: `<h2>` elements placed inside `<ul>` elements (invalid nesting)

**Impact:** Screen reader users rely on heading hierarchy for navigation. Skipped levels and incorrect nesting create confusion.

**Fix:** Ensure headings follow a sequential order (h1 → h2 → h3). Move `<h2>` elements outside of `<ul>` containers.

---

### Issue 9: Missing `<title>` on `<iframe>` Elements

**WCAG 2.4.1 — Bypass Blocks (Level A)**
**WCAG 4.1.2 — Name, Role, Value (Level A)**

**Files affected:**
- `new_annotation.html` line 39: `<iframe src="{{image_link}}" ...>` — no `title`
- `page_detail.html`: `<iframe src={{ det_img_view_src}} ...>` — no `title`

**Impact:** Screen reader users cannot determine the purpose of the iframe.

**Fix:** Add `title="Image viewer"` to each `<iframe>`.

---

### Issue 10: Table Layout for Forms

**WCAG 1.3.1 — Info and Relationships (Level A)**

**File affected:** `login.html` lines 11-20

The login form uses a `<table>` for layout instead of semantic form markup.

**Impact:** Screen readers may announce this as a data table, confusing users about the form structure.

**Fix:** Replace `<table>` layout with CSS-based form layout using `<div>` or `<fieldset>` with `<legend>`.

---

### Issue 11: Login Error Message Not Programmatically Associated

**WCAG 3.3.1 — Error Identification (Level A)**

**File affected:** `login.html` lines 5-6

Error message `<p>Your username and password didn't match...</p>` is not associated with the form fields via `aria-describedby` or `role="alert"`.

**Impact:** Screen reader users may not be notified of the error.

**Fix:** Add `role="alert"` to the error paragraph, and consider `aria-describedby` on the relevant form fields.

---

### Issue 12: Dynamic Search Results Not Announced

**WCAG 4.1.3 — Status Messages (Level AA)**

**File affected:** `search_page.html`

Search results are loaded dynamically via JavaScript but no ARIA live region is used. The `#num_results` span and result containers lack `aria-live` attributes.

**Impact:** Screen reader users are not informed when search results appear.

**Fix:** Add `aria-live="polite"` and `role="status"` to the `#num_results` element. Consider adding `aria-live="polite"` to the results containers.

---

### Issue 13: Dynamically Created Images Missing `alt` Text (Search Page)

**WCAG 1.1.1 — Non-text Content (Level A)**

**File affected:** `search_page.html` JavaScript `create_thumbnail()` function (lines 216-258)

Thumbnails created via JavaScript have no `alt` attribute set.

**Impact:** Screen reader users get no information about dynamically loaded images.

**Fix:** In the `create_thumbnail()` function, add `thumbnail.attr('alt', 'Thumbnail for page ' + stripPid(pagepid));`

---

### Issue 14: Missing `DOCTYPE` and `<meta charset>` in Standalone Templates

**Best Practice / WCAG 4.1.1 — Parsing (Level A)**

**Files affected:**
- `new_annotation.html`: No `<!DOCTYPE html>`, no `<meta charset>`
- `new_record.html`: No `<!DOCTYPE html>`, no `<meta charset>`

**Fix:** Add `<!DOCTYPE html>` and `<meta charset="utf-8">` to all standalone HTML templates.

---

### Issue 15: Links Opening in New Windows Without Warning

**WCAG 3.2.5 — Change on Request (Level AAA) / Best Practice**

**Files affected:**
- `search_page.html`: `page_link.attr('target', '_blank');` — no indication to user
- `document_detail.html`: PDF links open in new window

**Fix:** Add visual indicator and `aria-label` text such as `"(opens in new window)"` for links with `target="_blank"`. Add `rel="noopener noreferrer"` for security.

---

### Issue 16: Turnstile CAPTCHA Status Messages

**WCAG 4.1.3 — Status Messages (Level AA)**

**File affected:** `turnstile_challenge.html`

JavaScript error messages are injected into a `<div id="result">` without `role="alert"` or `aria-live`.

**Fix:** Add `role="alert"` or `aria-live="assertive"` to the result div.

---

### Issue 17: Pagination Buttons Missing Accessible Names

**WCAG 4.1.2 — Name, Role, Value (Level A)**

**Files affected:**
- `result_base.html`: `<button id="page_button_{{i}}" ...>{{i}}</button>` — no `aria-label`
- `essay_list.html`, `shop_list.html`: Similar pagination buttons

**Impact:** Screen readers announce only the number, without context that it's a page number.

**Fix:** Add `aria-label="Go to page {{i}}"` and `aria-current="page"` for the active page.

---

### Issue 18: Footer Navigation Not Marked as List

**WCAG 1.3.1 — Info and Relationships (Level A)**

**File affected:** `base.html` lines 57-61

The footer contains navigation links (Brown University, STG) but is not semantically marked up.

**Fix:** Wrap footer content in `<footer>` element. Use a list or `<nav>` for the footer links.

---

### Issue 19: Unclosed `<head>` Tag in Base Template

**WCAG 4.1.1 — Parsing (Level A)**

**File affected:** `base.html` line 19

The `<head>` section uses `<head>` as a closing tag instead of `</head>`.

**Impact:** Invalid HTML may cause rendering or accessibility issues.

**Fix:** Change line 19 from `<head>` to `</head>`.

---

## Summary of Issues by WCAG Level

### Level A Violations (Must Fix — 14 issues)

| # | Issue | WCAG SC | Scope |
|---|-------|---------|-------|
| 1 | Missing `lang` attribute | 3.1.1 | All pages |
| 5 | Missing form labels (search) | 1.3.1, 4.1.2 | Search page |
| 6 | Missing image `alt` text | 1.1.1 | Detail pages, search |
| 7 | Missing ARIA on toggles | 4.1.2 | Detail pages |
| 8 | Heading hierarchy issues | 1.3.1 | Multiple pages |
| 9 | Missing `title` on iframes | 2.4.1, 4.1.2 | Annotation, page detail |
| 10 | Table layout for forms | 1.3.1 | Login |
| 11 | Error messages not associated | 3.3.1 | Login |
| 13 | Dynamic images missing `alt` | 1.1.1 | Search |
| 14 | Missing DOCTYPE/charset | 4.1.1 | Annotation, new record |
| 17 | Pagination missing names | 4.1.2 | List pages |
| 18 | Footer not semantic | 1.3.1 | All pages |
| 19 | Unclosed `<head>` tag | 4.1.1 | All pages |
| 3 | No landmark regions | 1.3.1 | All pages |

### Level AA Violations (Should Fix — 4 issues)

| # | Issue | WCAG SC | Scope |
|---|-------|---------|-------|
| 2 | No skip navigation link | 2.4.1 | All pages |
| 4 | Color contrast failures | 1.4.3 | All pages |
| 12 | Dynamic results not announced | 4.1.3 | Search |
| 16 | CAPTCHA status not announced | 4.1.3 | Turnstile |

### Level AAA / Best Practice (Consider — 1 issue)

| # | Issue | WCAG SC | Scope |
|---|-------|---------|-------|
| 15 | New window links no warning | 3.2.5 | Search, documents |

---

## Recommendations — Priority Order

1. **Immediate (Level A — blocks basic access):**
   - Add `lang="en"` to all `<html>` elements
   - Fix unclosed `<head>` tag in `base.html`
   - Add semantic landmarks (`<header>`, `<nav>`, `<main>`, `<footer>`)
   - Add `alt` text to all images
   - Add labels to all form inputs
   - Add `title` to iframes

2. **High Priority (Level A/AA — significant barriers):**
   - Add skip navigation link
   - Fix color contrast ratios
   - Add ARIA attributes to toggle buttons
   - Fix heading hierarchy
   - Add `aria-live` regions for dynamic content

3. **Medium Priority (Level AA — usability improvements):**
   - Replace table layout in login form
   - Associate error messages with form fields
   - Add accessible names to pagination buttons
   - Add DOCTYPE and charset to standalone templates

4. **Lower Priority (Best practices):**
   - Warn users about links opening in new windows
   - Add `rel="noopener noreferrer"` to external links
