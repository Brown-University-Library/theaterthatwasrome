# Adding a New Book to The Theater That Was Rome

_Workflow assessment: 2026-08-31. TTWR code references checked: 2026-10-28._

## Contents

- [Overview](#overview)
- [Who does what](#who-does-what)
- [How automatic discovery works](#how-automatic-discovery-works)
- [Adding a book](#adding-a-book)
- [Required BDR records](#required-bdr-records)
- [Verification](#verification)
- [Optional Django-admin work](#optional-django-admin-work)
- [Troubleshooting](#troubleshooting)
- [Code references and scope](#code-references-and-scope)

## Overview

Adding a book starts in the Brown Digital Repository (BDR). The Theater That Was Rome (TTWR) reads book and page-image records from BDR; its Django database stores related editorial content. Once a book and its page images have the required metadata, relationships, collection membership, public access, and working images, BDR indexing makes them available to TTWR automatically.

A normal book addition does not require a TTWR code change or a local Django Book record.

This guide uses placeholders for collection identifiers and service addresses. Use the collection configured by `settings.TTWR_COLLECTION_PID`, and confirm the corresponding ingest-tool selection with the repository team. TTWR login access and BDR deposit/edit access are separate; the person adding a book needs the appropriate repository permissions.

## Who does what

- The person preparing the book supplies metadata, scans, page order, and publication requirements.
- The repository ingest tool, such as BDR Workshop, creates the parent book and its child page-image records.
- BDR stores the records, prepares image versions for viewing, and indexes metadata and relationships for searches and API responses.
- BDR image services supply thumbnails and zoomable images.
- TTWR reads the resulting records and displays the book, pages, and associated editorial content.
- TTWR's Django admin manages biographies, essays, documents, shops, genres, and roles. It does not ingest books or page images.

The overall sequence is:

```text
Prepare book metadata, page metadata, images, and page order
        |
        v
Stage and ingest the parent book with its child images
        |
        v
Wait for BDR image processing and indexing
        |
        v
Check metadata, relationships, access, images, and order
        |
        v
Confirm that the complete book appears in TTWR
```

Where the repository workflow supports it, assemble and check the records before making them public. Coordinate publication so readers encounter a complete book.

## How automatic discovery works

TTWR builds the book list when a reader requests it. `book_list()` calls `Book.search()`, which uses the BDR Collection API with these criteria:

```text
collection: settings.TTWR_COLLECTION_PID
query: genre_aat:book*
object_type: implicit-set
discover: BDR_PUBLIC
```

The selected book-list filter can further narrow the results. Use the **All** filter when checking a newly added book.

For a book's pages, TTWR reads the parent Item API response's `relations.hasPart` list. BDR derives this list from child records with an `isPartOf` relationship to the parent and public display access, ordered by their pagination values. `Book.pages()` uses the returned order for the thumbnail grid; page navigation also follows the parent response's order.

TTWR constructs thumbnail and zoom-viewer links from each page's persistent identifier (PID). BDR image services provide the image content. TTWR does not copy the images into its local database or run a separate book-import job.

## Adding a book

### 1. Confirm the collection and repository access

Confirm that the ingest tool's selected collection corresponds to `settings.TTWR_COLLECTION_PID` for the intended TTWR instance. An ingest tool may use a collection number different from the collection PID, so confirm the mapping rather than copying one into the other field.

Arrange BDR deposit/edit access and agree on publication timing with the repository team. Follow their current ingest instructions for tool access and permission requirements.

### 2. Prepare images, metadata, and page order

Prepare:

- One master image for each page or opening that should be independently viewable in TTWR.
- Book-level MODS metadata, including the primary title and the Art & Architecture Thesaurus (AAT) genre `books`.
- Contributors and roles, dates, identifiers, alternate titles, notes, and rights statements as appropriate.
- Separate MODS metadata for every page image, including its title, resource type, and visual description.
- A unique numeric order value for each page.
- Confirmation that the material may be displayed publicly.

Record each page's visual description in its own MODS metadata:

```xml
<mods:note type="image_accessibility_alt_text">A concise description of this page image.</mods:note>
```

This fragment belongs inside a complete MODS document with the MODS namespace declared. Follow the current metadata profile's requirements for the description's content and length.

For Workshop's filename-based grouping, a batch can look like this:

```text
samplebook.mods
samplebook_01.mods
samplebook_01.tif
samplebook_02.mods
samplebook_02.tif
```

In this layout, the parent identifier has no underscore. Each child adds one underscore and a numeric suffix. Workshop uses that suffix as the child's `page_number`. Supply distinct child metadata so every image has its own accessibility description.

### 3. Stage the parent and children together

Using the current Workshop staff procedure:

1. Upload the parent MODS, child MODS, and child images together.
2. Confirm that all files uploaded successfully and their File Groups are ready.
3. Select the parent File Group for ingest and include its children using the recursive option.
4. Select the confirmed TTWR collection and the access settings appropriate to the agreed publication timing.
5. Decide whether pages should appear independently in repository discovery results. TTWR needs public display access for pages, but separate public discovery is optional.
6. Queue the ingest and check that both the parent and all children finish.

For this layout, Workshop creates a metadata-only `ImplicitSet` parent. Each child receives its own PID, an `isPartOf` relationship to the parent, and a numeric `page_number`. The normal compound ingest also assigns the selected collection to the parent and children.

### 4. Check the book and page records

Use the [required BDR records](#required-bdr-records) tables below. Confirm that the parent has the book metadata and that each child has its own image, metadata, parent relationship, and page number.

The page list should contain the intended image records. Keep other related material separate from that list.

### 5. Check relationships and order

After indexing, the child's parent relationship appears as `rel_is_part_of_ssim`, and its page number appears as `rel_has_pagination_ssim`. BDR uses these child fields to assemble the parent's ordered `relations.hasPart` response.

Compare the returned page list with the expected image sequence. Every intended page should appear once, with a numeric, unique order value. Correct ordering through the repository's child-reordering procedure or by updating the child page numbers, then wait for indexing.

The parent response's `hasPart` list is derived from child records; it is not a separate list to maintain manually on the parent.

### 6. Check images and accessibility descriptions

Inspect every page's thumbnail and zoom viewer. Confirm that the correct image loads, its orientation is correct, and the detailed viewer displays the image's accessibility description.

BDR normally creates image versions such as a JP2 and thumbnail during processing. A working image-service response is the useful final check: the thumbnail service may also obtain an image from the IIIF image service when a stored thumbnail is unavailable.

### 7. Confirm public access and completed processing

For publication, the parent needs public discovery and public display access. Each child needs public display access. Independent public discovery of individual pages is optional.

Repository ingest, image processing, and indexing can finish at different times. Wait until the public Item API returns the complete parent and child records, the parent lists all pages in order, and all image viewers work. If records were assembled with restricted access, check the public responses again after publication and reindexing.

### 8. Verify the book in TTWR

Follow the [TTWR checks](#ttwr-checks) below. Confirm the book list, thumbnail grid, page details, image viewers, and previous/next navigation. Add any optional editorial connections after the book and pages are available.

## Required BDR records

These tables describe the final indexed records and API responses that support TTWR. Some values come from submitted metadata; others are generated by the ingest tool, BDR indexing, or the Item API.

### Parent book

| Value | Purpose |
| --- | --- |
| Metadata-only `ImplicitSet` parent, indexed as `object_type: implicit-set` | Matches the object type used by `Book.search()`. |
| Membership in `settings.TTWR_COLLECTION_PID` | Places the book in the collection queried by TTWR. |
| Public discovery and display access | Allows the book to appear in search results and its details to be retrieved publicly. |
| AAT genre `books`, indexed in `genre_aat` | Matches the book-list query `genre_aat:book*`. |
| MODS primary title, indexed as `primary_title` | Supplies the title for display and sorting. |
| Item API `brief.title` | Supplies the book title used on page-detail views. |
| Ordered `relations.hasPart` | Supplies the page list and navigation order. |
| Generated BDR `uri` | Supplies the book's repository link. |

Contributors, dates, alternate titles, and notes improve display and help readers identify the book.

### Child page image

| Value | Purpose |
| --- | --- |
| Image content, indexed as `object_type: image` | Supplies an independently viewable page image. |
| `isPartOf` relationship, indexed as `rel_is_part_of_ssim` | Connects the page to its parent book. |
| Numeric, unique `page_number`, indexed as `rel_has_pagination_ssim` | Supplies page order and the page label. |
| Public display access | Allows the child to appear in the public parent response and image viewers. |
| TTWR collection membership | Keeps the image in the same collection through the normal compound ingest. |
| Stored source/master image and working IIIF image service | Supports zoom viewing. |
| Working thumbnail endpoint | Supplies the image displayed in thumbnail grids. |
| Child MODS description indexed as `image_accessibility_alt_text_ssi` | Supplies the visual description displayed by the detailed BDR viewer. |
| Generated BDR `uri` | Supplies the page's repository link. |

The Item API can also return `relations.hasAnnotation`. The repository manages that relationship when annotations are added; the person ingesting a new book does not need to create an annotation or populate this list manually.

## Verification

The examples below are address patterns, not shell commands. Replace the placeholders with values for the intended instance:

- `BDR_BASE_URL`: the repository's public base URL, without a trailing slash.
- `TTWR_BASE_URL`: TTWR's public base URL, including any application path prefix and without a trailing slash.
- `BOOK_PID` and `PAGE_PID`: full repository PIDs, including their prefix.
- `BOOK_ID` and `PAGE_ID`: the portions after the PID's colon, as used in TTWR routes.

These placeholder names are for this guide; they are not additional application settings. Opening an API or viewer address reads existing records and does not ingest or change them.

### BDR Item API checks

```text
{BDR_BASE_URL}/api/items/{BOOK_PID}/
{BDR_BASE_URL}/api/items/{PAGE_PID}/
```

For the parent, confirm:

- `object_type` is `implicit-set`.
- `genre_aat` contains `books` or another value matching `book*`.
- `relations.isMemberOfCollection` includes the intended collection PID.
- `relations.hasPart` contains all intended image children in order.
- The title fields and repository link are present.
- The book can be retrieved publicly and is returned by the collection's public discovery query.

For each child, confirm:

- `object_type` is `image`.
- `relations.isPartOf` identifies the parent.
- Collection membership and the page number are correct.
- `image_accessibility_alt_text_ssi` contains the submitted visual description.
- The record can be retrieved publicly and has a working repository link.

### Image-service checks

```text
{BDR_BASE_URL}/viewers/image/thumbnail/{PAGE_PID}/
{BDR_BASE_URL}/viewers/image/zoom/{PAGE_PID}?first_child_only=1
```

Check every page. The thumbnail should show the intended image, and the zoom viewer should load the image and its description.

### TTWR checks

```text
{TTWR_BASE_URL}/books/
{TTWR_BASE_URL}/books/{BOOK_ID}/
{TTWR_BASE_URL}/books/{BOOK_ID}/{PAGE_ID}/
```

1. Select **All** in the book list and find the new book.
2. Open the book and compare the thumbnail count and order with the prepared image sequence.
3. Open each page and confirm the title, page label, and image viewer.
4. Check that previous/next navigation follows the intended order.
5. If annotation work is planned, sign in with an appropriate TTWR account and confirm that **Create New Annotation** is available.

## Optional Django-admin work

No Django-admin entry is required merely to display a BDR book and its images. For related editorial content:

- Add biographies for people who should have TTWR person pages or be selectable in annotation forms.
- Match BDR contributor names to `Biography.name` when books should appear automatically on those person pages.
- Add the book or page ID, without its PID prefix, to an essay's comma-separated `pids` field when the essay should be associated with it.
- Create page annotations after the pages and viewers are working.

The Document admin's file uploads and external links serve separate editorial purposes and do not ingest BDR books.

## Troubleshooting

| Symptom | What to check or correct |
| --- | --- |
| Book is absent from the list | Select **All**; confirm the configured collection, `implicit-set` object type, matching genre, public access, and completed indexing. |
| Book or page cannot be opened | Confirm the PID is publicly retrievable and the TTWR route uses the ID without its prefix. |
| Book has missing pages | Check the children's parent relationships, public display access, and indexing; then inspect the parent's `relations.hasPart`. |
| Page order is wrong | Correct child page numbers through the repository workflow and wait for reindexing before checking the parent response again. |
| Thumbnail or zoom image does not load | Check the image record's public access, completed image processing, and the direct image-service responses. |
| Accessibility description is missing | Check the child's own MODS description and its indexed `image_accessibility_alt_text_ssi` value, then reload the detailed viewer. |
| Book is missing from a person page | Compare the book's contributor metadata with the local biography name. |

If BDR is temporarily unavailable, retry after service is restored. See [BDR requests and temporary outages](bdr_requests.md) for TTWR's handling of temporary failures.

## Code references and scope

The TTWR behavior described here can be followed in:

- [Models and BDR wrappers](../rome_app/models.py): `BDRObject.search()`, `Book`, `Book.pages()`, `Biography.books()`, `BDRObject.thumbnail_src`, and `zoom_viewer_url()`.
- [Views](../rome_app/views.py): `book_list()`, `book_detail()`, `page_detail()`, and page navigation.
- [Application routes](../rome_app/urls_app.py): book-list, book-detail, and page-detail routes.
- [Book template](../rome_app/templates/rome_templates/book_detail.html): thumbnail display and page links.
- [Page template](../rome_app/templates/rome_templates/page_detail.html): page display and embedded image viewer.
- [Unit tests](../unit_tests/test_views.py): TTWR page behavior with simulated BDR responses.

The repository ingest and image-processing descriptions summarize the workflow assessed on the date above. The TTWR references were checked against this checkout; live ingest, public records, and image services were not rechecked when preparing this copy. Confirm current Workshop controls, metadata-profile requirements, collection selection, access permissions, and publication procedures with the repository team before ingesting a book.
