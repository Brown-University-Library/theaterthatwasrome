# Improved BDR data-source handling in TTWRome

(2026-September-21)

TTWRome now handles temporary failures from the Brown Digital Repository (BDR) with explicit timeouts, a clear notice for visitors, and fewer administrator emails. Where possible, it continues to display content stored in its own database. The existing site-checker remains responsible for notifying staff when the repository becomes unavailable and when it recovers.

This document describes the implementation completed and checked locally. It does not report a deployment or a test against the live repository. File references below are relative to the `ttwr/` code directory.

## Contents

- [Why the change was needed](#why-the-change-was-needed)
- [How a BDR failure is handled](#how-a-bdr-failure-is-handled)
- [Why middleware handles the outage page](#why-middleware-handles-the-outage-page)
- [Timeout settings](#timeout-settings)
- [What visitors see](#what-visitors-see)
- [How repeated error emails are prevented](#how-repeated-error-emails-are-prevented)
- [Search and annotation editing](#search-and-annotation-editing)
- [Files and supporting changes](#files-and-supporting-changes)
- [Checks performed](#checks-performed)
- [Limits of this implementation](#limits-of-this-implementation)
- [Original prompt](#original-prompt)

## Why the change was needed

TTWRome combines its own editorial content with book, print, image, and annotation information retrieved from BDR. Previously, several BDR requests had no explicit timeout. If BDR stopped responding, a visitor's page request could wait a long time before failing.

The essay list illustrated the problem. TTWRome retrieved essays from its own database, then contacted BDR separately for each essay's related works. A failed BDR connection could prevent the entire page from appearing, even though the essay titles and text were available locally. The resulting Django error also generated an administrator email for each failed page request.

Because a separate site-checker already sends outage and recovery notifications, these repeated application emails did not provide useful additional notice.

## How a BDR failure is handled

The application now uses one shared function for its Python BDR requests. That function uses `httpx2` and applies the timeout settings described below.

The sequence is:

1. A page or annotation form requests information from BDR, or submits an annotation to it.
2. The shared function makes the request with explicit limits on how long it can wait for a connection or for data to move.
3. If the connection fails, the request times out, the connection ends with an invalid or incomplete HTTP response, or BDR returns one of the recognized service-error responses, the function records a short warning and raises `BdrUnavailable`. This is a specific Python exception meaning that BDR could not provide the requested service.
4. The page either keeps its local content and shows an outage notice, or returns a page explaining that the required content is temporarily unavailable.
5. The email handling recognizes the deliberately handled outage response and does not send an administrator email for it.

The recognized BDR service-error responses are HTTP 500, 502, 503, and 504. Other failures remain separate. For example, an authorization error or unexpected data format is not automatically treated as an ordinary outage. A missing BDR item still follows the existing 404, or “not found,” behavior where that item lookup supports it.

## Why middleware handles the outage page

In Django, *middleware* is shared code that can take part in handling requests across the application. This implementation uses its exception-handling step: if the function building a page cannot finish because BDR is unavailable, Django gives the middleware an opportunity to supply a response.

I chose this approach because several different pages and annotation forms depend on BDR. Repeating the same full-page outage handling in every page function would create several copies to maintain. It would also make it easier to miss a BDR lookup and accidentally leave that page returning a general error and sending repeated emails. A shared handler gives those pages one place to produce the same notice, response status, suggested retry time, and instructions against saving the outage response for later reuse.

The responsibilities remain separate:

1. The shared BDR request function identifies the external-service failure. It does not decide which HTML page to show.
2. A page that can still display useful local content handles that specific failure itself and continues rendering its content with a notice.
3. If the page cannot continue, the `BdrUnavailable` exception reaches the middleware, which returns the dedicated outage page.

This lets essay, shop, and biography pages keep their local content while other pages use the same outage page. It also keeps the BDR request function usable from code that is not building a web page.

The middleware catches only `BdrUnavailable`. It does not turn every Python exception or every error response into a repository-outage message. Existing code that broadly catches exceptions around BDR operations was adjusted to let this particular exception reach the shared handler. Other errors retain their existing handling.

Middleware alone does not solve the email problem. Django still records a deliberately returned 503 as an error. The outage-response helper therefore adds an internal marker, and the separate email filter uses that marker to recognize the response. Keeping that distinction allows the application to suppress the expected outage emails while continuing to report unexpected failures.

This middleware does not check BDR before each visitor's page loads, block the whole site, or remember whether BDR is down. It produces an outage response only when a page raises the specific exception. That keeps the change focused on failed BDR operations and avoids adding another monitoring system alongside the existing site-checker.

## Timeout settings

These optional environment variables can be set in the application's existing `.env` file:

```dotenv
ROME_BDR_CONNECT_TIMEOUT=5
ROME_BDR_READ_TIMEOUT=10
```

Both values were added to the local `.env` file. The application also uses 5 and 10 as its defaults when the variables are absent.

| Setting | Default | What it controls |
| --- | --- | --- |
| `ROME_BDR_CONNECT_TIMEOUT` | 5 seconds | How long the HTTP client waits to establish a connection. It also sets the limit for waiting for an available client connection. |
| `ROME_BDR_READ_TIMEOUT` | 10 seconds | How long the HTTP client waits for the next portion of response data. The same value limits waiting while sending request data. |

Values must be numbers of seconds greater than zero. Fractions such as `2.5` are allowed. Empty values, words, zero, negative numbers, and special values such as infinity produce a configuration error. Restart the application after changing the settings so that it reads the new values.

These settings do **not** guarantee that a whole page will finish within 15 seconds. The read limit measures inactivity while receiving data, and some pages make more than one BDR request. A response that keeps delivering data can take longer than ten seconds overall.

The shared function does not retry a failed request automatically. This avoids adding another wait to the same operation.

## What visitors see

The common notice says:

> Some content from the Brown Digital Repository is temporarily unavailable. Our monitoring service alerts staff to outages. Please try again in a few minutes.

The wording explains that staff receive monitoring alerts without claiming that a notification has already been delivered for the current failure. TTWRome does not consult the site-checker's notification history.

The result depends on what the visitor is trying to see:

| Page or content | Behavior during a recognized BDR failure |
| --- | --- |
| Essay list | Essay titles and previews remain available. The page shows the notice and skips further BDR lookups after the first failure. |
| Individual essay | Local essay text remains available. Unavailable related BDR works are omitted, and the notice explains the missing content. |
| Shop details | Local shop text and other locally available information remain available with the notice. |
| Biography details | Local biography content remains available with the notice. Further related BDR lookups stop when a failure occurs. |
| Pages that require BDR data | The application shows a dedicated “Content temporarily unavailable” page instead of the former general error response. |

Pages that still provide their local content return a normal successful response. The dedicated outage page returns HTTP 503, the standard response for a temporarily unavailable service. It includes `Retry-After: 60`, which suggests trying again after a minute; this does not automatically reload the visitor's page.

Both the dedicated outage response and local-content pages affected by an outage include instructions telling browsers and intermediary services not to save those incomplete responses for later reuse. This helps prevent an outage notice from lingering after BDR recovers.

The dedicated outage page does not contact BDR to render itself. The notice also identifies itself to assistive technology as a status message and uses readable colors within the site's existing design.

## How repeated error emails are prevented

Returning a friendly page is only part of the solution. Django records HTTP 503 responses as errors even when the application deliberately returns them. Without an email change, the friendly outage page could still generate an administrator email on every visit.

The new email filter excludes a message only when all of these conditions are met:

- It is a Django request-error message.
- Its response status is 503.
- The request carries an internal marker showing that TTWRome's BDR outage handler produced the response.
- The message does not contain a separate exception traceback, which records where an unexpected error occurred.

The application adds the marker only after the outage page has rendered successfully. An error while rendering that page therefore does not get mistaken for a successfully handled BDR failure.

Unexpected application errors, unrelated 503 responses, and security-related error messages retain their existing email behavior. The separate emails for invalid annotation data also remain separate from this outage handling.

For recognized BDR failures, the application writes a short warning to its existing log. The new warning includes the kind of request and either the failure type or the BDR response code. It does not copy authorization values or full request contents into that warning.

## Search and annotation editing

### Search in the visitor's browser

The search page already contacted BDR directly from JavaScript in the visitor's browser. Those requests do not pass through the new Python function, so search received its own timeout and failure handling.

Each browser search request now has a timeout equal to the sum of the two settings: 15 seconds with the defaults. This is one browser-request timeout; it does not separately measure connecting and reading. Very small positive settings are rounded up to at least one millisecond so they cannot accidentally disable the timeout.

If the initial search or a later request for result details fails, the page displays the same outage notice, explains that some results could not be loaded, and cancels its outstanding requests. Starting another search clears the previous failure notice and tries again. A successful search restores the normal results display.

### Creating or updating annotations

Annotation submissions also use `httpx2` and the shared timeouts. The application does not automatically repeat these submissions or follow a response that would redirect and resend them.

This matters because a lost response does not necessarily mean a failed save. BDR may have saved an annotation before the connection failed. Repeating the submission automatically could create a duplicate.

When an annotation submission produces the outage page, it includes this additional message:

> We could not confirm whether your annotation was saved. Before submitting it again, check the record when the repository is available.

## Files and supporting changes

| File or group of files | Purpose |
| --- | --- |
| `rome_app/lib/bdr_client.py` | Makes BDR requests with `httpx2`, applies the timeouts, and identifies recognized service failures. |
| `config/settings/base.py` | Reads and validates the environment settings, enables the BDR exception handler, and installs the email filter. |
| `config/middleware/bdr_failure_middleware.py` | Catches an unhandled `BdrUnavailable` exception from a page and supplies the dedicated outage response. |
| `rome_app/lib/bdr_failure.py` | Builds the outage response, prevents affected pages from being saved for reuse, and filters the matching administrator emails. |
| `rome_app/lib/bdr_display.py` | Supports displaying local essay, shop, and biography content when related BDR information is unavailable. |
| `rome_app/models.py` and `rome_app/lib/annotation_helpers.py` | Route their existing BDR requests through the shared function. |
| `rome_app/views.py` and `rome_app/lib/annotation_forms.py` | Apply the new page and annotation behavior. Annotation-editing helper functions were moved out of `views.py` into `lib/` to follow the repository's existing organization rules. |
| Templates under `rome_app/templates/rome_templates/` and `rome_app/static/rome/css/common.css` | Provide the shared notice, dedicated outage page, and browser-search changes. |
| `pyproject.toml` and `uv.lock` | Declare and record the new `httpx2` dependency and its supporting packages. |
| `unit_tests/http_mock.py` and the BDR-related tests | Supply simulated HTTP responses and check the new behavior without contacting a live BDR service. |
| `typings/bdrxml/` | Describe the XML fields the existing annotation code uses so that Python type checking understands fields the XML library adds while running. |

**About `.pyi` files:** Type annotations could be added directly to `bdrxml`'s own source code, even though it is an imported package. Because we are not modifying that dependency, our `.pyi` files provide those descriptions separately for tools such as Pylance and Pyright. `__init__.pyi` describes the package's available imports; `mods.pyi` describes the XML classes, fields, and functions TTWR uses. These files help check the code; the application still runs the installed package's Python code.

The change also adds a small number of type annotations and explicit checks for missing values in the existing code. It does not add database fields or require a database migration. The separate Turnstile integration continues using its existing HTTP library.

A shorter reference is available in `docs/bdr_requests.md`.

## Checks performed

The full Django unit suite passed: **114 tests**, including the existing page, form, and accessibility checks. Run that suite from the code directory with:

```sh
uv run ./run_tests.py
```

The added checks cover:

- Default and overridden timeout values, including fractional seconds and rejected invalid settings.
- Connection timeouts, read timeouts, connection failures, interrupted responses, and recognized BDR service errors.
- Repeated failed page requests producing no administrator email, followed by successful recovery on a later request.
- Unexpected data still producing an application error email.
- Missing items remaining distinguishable from unavailable services.
- Essay lists retaining every local essay and stopping BDR requests after the first outage failure.
- Essay, shop, and biography detail pages retaining local text.
- Annotation creates and updates stopping after a failed submission, without an automatic retry or outage email.
- The narrow email-filter conditions and the configured browser-search timeout.

Separate browser checks used simulated BDR responses to verify an initial search failure, successful recovery, a failure while retrieving result details, and the dedicated outage page. Desktop and mobile versions of the outage page were visually inspected.

Pyright checked the changed Python files and new type definitions using the project's interpreter and the matching editor type-checking settings, including the editor's Django definitions. It reported **zero errors and zero warnings**. The new modules and type definitions also passed the code-style checks, and the final changes passed the whitespace check.

The package-version file, `uv.lock`, was updated, and installing its recorded package versions succeeded. These checks did not submit annotations to a live repository or send outage notifications to staff.

## Limits of this implementation

This implements the first proposed approach: consistent timeout handling and useful responses to recognized BDR failures.

It does not remember an outage across separate visitors or pause BDR requests for a shared interval. Each new page request can still attempt to contact BDR and experience its configured wait. Within an essay-list request, however, the first recognized failure stops the remaining BDR lookups for that page.

The application does not start a background recovery checker. Later page requests and searches try BDR again normally, so successful responses restore ordinary behavior without staff needing to clear a saved outage state. The existing site-checker remains responsible for its own checks and notifications.

The change does not save older BDR results for use during an outage, copy repository images into TTWRome, or make unavailable image viewers work offline. Images and viewers loaded directly by the browser are not governed by the Python request timeouts.

Finally, this change deliberately distinguishes a recognized repository outage from an unexpected application problem. A successful HTTP response containing unusable data can still produce an error that needs investigation. Those errors retain the existing notification behavior.


## Original prompt

Goal: Determine a way to handle "bdr is down" timeouts better in the TTWRome webapp.

Context:

- The TTWRome project accesses the brown digital repository (BDR) for much content.

- Sometimes the BDR is down, resulting in the TTWRome django app hanging, and generating an error-email for every problematic BDR access.

- We already have a site-checker webapp that:
	- checks websites at pre-determined frequencies
	- notifies appropriate staff _once_ if a site is down
	- rechecks frequently to see if it's back up
	- notifies staff when the site is back up
	- (therefore, we definitely don't need dozens or hundreds of error emails in this timeout situation)

- Roughly, I'm thinking of a solution that:
	- uses timeouts for the bdr-api/solr web-requests
	- has some indicator to the TTWRome webapp user that a data-source is temporarily unavailable, that staff have been notified, and to check back in a few minutes.

- If you implement a new solution, use httpx2.

Tasks:

- Review the uploaded example error-email to understand the code underlying the issue.

- Propose one or two ways to improve the current situation in which we get hundreds of emails -- incorporating the reality that we already are notified of underlying data-source errors other ways.

- Ask me a clarifying question before proceeding. Thanks.

---
