# AGENTS.md — Repository Agent Instructions (Source of Truth)

This file defines the canonical coding directives for this repository.

If other instruction files exist (Copilot, IDE rules, contributor docs) and conflict with this file, follow this file and treat the others as stale.


## Table of contents

- [Project basics](#project-basics)
- [How to run code](#how-to-run-code)
- [Coding directives (Python)](#coding-directives-python)
- [Django architecture conventions](#django-architecture-conventions)
- [Front-end change guidance](#front-end-change-guidance)
- [Tests](#tests)
- [Change workflow expectations](#change-workflow-expectations)
- [If instructions are missing or ambiguous](#if-instructions-are-missing-or-ambiguous)
- [Agent project index](#agent-project-index)


## Project basics

- Primary language: Python
- Framework: Django 5.2
- Target runtime: Python 3.10, as constrained by `pyproject.toml`
- Dependency / execution tool: `uv`
- Project root: the directory containing this file, `.git/`, `manage.py`, and `pyproject.toml`
- This is a public repository. Never copy credentials, tokens, private host details, or other sensitive values from environment files, logs, backups, or material in the enclosing directory into repository files, tests, messages, or documentation.


## How to run code

- Assume the user is in the project-root directory.
- Do not use `python` to run scripts.
- Install the locked local dependencies via: `uv sync --locked --group local`
- Run a script via: `uv run ./path_to_script.py --help`
- Run the unit tests via: `uv run ./run_tests.py`
- Run Django management commands via: `uv run ./manage.py THE-COMMAND`
- `manage.py` loads the environment file from the enclosing directory. Before running a management command, make sure its selected `DJANGO_SETTINGS_MODULE`, database, and BDR service are appropriate for the task.
- Do not run `run_integration_tests.py` by default. It loads the normal environment and calls a live BDR service; use it only when the task requires live integration coverage and the environment has been checked.


## Coding directives (Python)

### Type hints and imports

- Use Python 3.10-compatible type hints for functions and important variables.
- Prefer builtin generics (for example, `list[str]` and `dict[str, int]`) over `typing.List` and `typing.Dict` in new or substantially changed code.
- Prefer PEP 604 unions (for example, `str | None`) over `Optional[str]` in new or substantially changed code.
- Avoid `typing` and `annotations` imports unless strictly necessary.

### Script structure

- Structure runnable modules as:
  - `def main() -> None: ...`
  - `if __name__ == '__main__': main()`
- Keep `main()` simple: parse arguments and coordinate calls only.
- Put real logic into top-level helper functions and modules; do not define functions inside other functions.
- Rarely use more than three levels of function calls. Keep control flow easy to follow.

### Functions and control flow

- Prefer single-return functions: use local variables and a final return when that remains clear.
- Do not define functions inside other functions.
- Favor clarity and explicitness over cleverness.
- Match the surrounding legacy style only where doing so is required for a small, safe change. Apply these directives to new code without turning a focused task into a broad rewrite.

### Logging

- When adding a log statement, when possible, format variable values as a label, followed by a comma and a space, with the value enclosed in double backticks.
- Prefer a label that matches the variable name. For example: `log.debug(f'branch_and_commit, ``{branch_and_commit}``')`.
- Never log BDR authorization values, database credentials, Turnstile secrets or tokens, session data, or complete request payloads that may contain those values.

### HTTP and networking

- Prefer `httpx` for a new, isolated HTTP integration.
- Existing BDR and Turnstile code uses `requests`, and the unit suite mocks it with `responses`. Do not partially migrate an existing request path as an incidental change.
- If a task intentionally migrates an existing request path, update its dependency declaration, lockfile, mocks, timeout handling, and error handling together.
- Add an explicit timeout to new network calls.

### Docstrings

- Use triple-quoted docstrings.
- Write docstrings in present tense, with triple quotes on their own lines.
  - Good:
    ```python
    """
    Parses ...
    """
    ```
  - Avoid: `"""Parse ..."""`
- The last line of non-test function docstrings should be `Called by: the_caller_function()` or, for a caller in another class or module, `Called by: module.Class.the_caller_function()`.
- Start test-function docstring text with `Checks...`.
- For header comments inside functions, start the comment with two hashes, for example `## does this`.

### Additional coding directives

- Inspect `/ruff.toml` for additional coding directives, including the 125-character maximum line length and single-quote style.

### Markdown formatting

- Do not use hard line breaks in Markdown files; let paragraphs wrap naturally.
- When creating a Markdown file with more than three top-level `##` headings, add a table of contents near the top with links to those `##` headings.


## Django architecture conventions

### View-layer responsibilities

- `rome_app/views.py` should contain only view functions that directly handle URL endpoints and small helpers that are tightly coupled to response construction.
- Every endpoint view in `rome_app/views.py` should correspond to an entry in `rome_app/urls_app.py`; the Turnstile verification endpoint is the exception and is wired in `config/urls.py`.
- Views should coordinate request and response work:
  - Parse query parameters, POST bodies, and files.
  - Perform minimal validation and shaping of inputs.
  - Delegate substantive work to modules under `rome_app/lib/` or to narrowly focused model behavior.
  - Convert returned results into the appropriate response: HTML, JSON, redirect, or error response.

### Business logic placement

- Put new domain logic, integrations, and reusable operations in `rome_app/lib/`, not in `views.py`.
- If multiple endpoints share logic, move that shared logic into `rome_app/lib/` and keep each view thin.
- Prefer testable functions in `rome_app/lib/` that accept plain Python values rather than Django request objects, unless passing the request is necessary for a narrow, documented reason.
- `rome_app/models.py` currently contains both Django models and legacy BDR API wrapper classes. Do not add unrelated request coordination there; preserve existing behavior while moving newly extracted reusable logic toward `rome_app/lib/`.

### Imports and dependencies

- `views.py` should primarily import Django response/request primitives and the minimal set of functions and classes needed by each endpoint.
- Avoid creating another group of general-purpose view helpers inside `views.py`; place those helpers in `rome_app/lib/`.
- Avoid import-time network or database work. `rome_app/app_settings.py` already reads required environment values at import time, so tests and scripts must establish those values before Django setup.


## Front-end change guidance

- Use JavaScript only where it is truly required.
- Prefer updates in CSS, Python code, or Django template code when those can satisfy the behavior or presentation need.
- Preserve the existing visual design unless the task requests a redesign.
- Maintain accessible names for images, frames, form controls, and interactive elements.
- Keep text and interactive-control contrast at WCAG AA levels. The unit tests enforce specific shared colors and reject known low-contrast inline colors.
- Before editing one of the similarly named or legacy templates, search for the template path used by `render()`, `{% extends %}`, or `{% include %}`. Some files under `rome_app/templates/rome_templates/essays/` are old and are not used by current views.


## Tests

- Use Django's test framework.
- The canonical unit suite is `uv run ./run_tests.py`; this is also the command run by CI.
- Unit tests belong in `unit_tests/`. HTTP behavior is normally isolated with `responses`, using data from `unit_tests/responses_data.py`.
- Live-service tests belong in `integration_tests/` and run through `uv run ./run_integration_tests.py` only when live integration coverage is intentional.
- New behavior should usually have a focused test covering:
  - The expected path.
  - At least one failure or edge case.
- Front-end changes should preserve the accessibility checks in `unit_tests/test_views.py`, including shared color contrast, disallowed inline colors, image alternative text, frame titles, and representative rendered pages.
- BDR query tests may match an encoded URL and its query string exactly. If a query changes intentionally, update both the behavior and its mocked URL or matcher.


## Change workflow expectations

When implementing a change, especially from an issue or task:

1. Read the relevant surrounding code and match established behavior.
2. Make the smallest correct change that satisfies the request.
3. Update tests and run `uv run ./run_tests.py`.
4. If dependencies change, update both `pyproject.toml` and `uv.lock`, then verify with the appropriate locked dependency group.
5. If tests cannot run in the environment, still write or adjust the tests and state exactly what should be run.

### Commit messages

- Group related files into logical, focused commits; do not require a separate commit for every file.
- Keep each commit message brief, with no more than ten words.
- Write messages in the present tense so they complete the phrase "This commit..." Begin with a fitting verb such as "Adds," "Implements," or "Updates."


## If instructions are missing or ambiguous

- Do not ask questions unless absolutely necessary to proceed.
- Make reasonable assumptions, state them explicitly, then implement.
- If blocked, provide:
  - What you tried.
  - What you found in the repository.
  - A concrete next step: a command, file to edit, or minimal decision needed.


## Agent project index

### Purpose and major areas

This Django application serves The Theater That Was Rome, a scholarly site for early modern books, prints, annotations, people, essays, shops, and related documents. It combines locally managed editorial content with records and images fetched from the Brown Digital Repository (BDR).

- `config/`: shared, local, test, staging, and production Django settings; root URLs; Passenger WSGI startup; and Cloudflare Turnstile middleware.
- `rome_app/urls_app.py`: application route map. Start here to connect a public URL to its view.
- `rome_app/views.py`: page assembly, BDR lookups, annotation forms, and response handling. This is a large legacy module; search for the route's named view before reading it broadly.
- `rome_app/models.py`: local Django models plus non-database wrappers for BDR objects and MODS annotations.
- `rome_app/forms.py`, `rome_app/widgets.py`, and `rome_app/admin.py`: editorial forms, add-another popup behavior, and admin registration.
- `rome_app/templates/rome_templates/`: site templates. Most pages extend `base.html`; list pages commonly extend `result_base.html`.
- `rome_app/static/rome/`: shared CSS, page-specific CSS, legacy JavaScript, and images.
- `unit_tests/`: the isolated CI suite.
- `integration_tests/`: tests that expect a configured live service.

### Routing and page construction

- `config/urls.py` exposes the Turnstile verification endpoint and then includes `rome_app/urls_app.py` at the root.
- `rome_app/urls_app.py` groups routes for static pages, books/pages, prints, essays, people, shops, documents, authenticated record creation, search, version information, and a temporary role checker.
- `std_context()` in `rome_app/views.py` supplies common styles, image paths, title data, and breadcrumbs. Most rendered views depend on it.
- Book and print detail pages share `rome_templates/page_detail.html`, distinguished by `book_mode` and `print_mode` context flags.
- Static production hosting uses a `/projects/rome/` prefix outside the Django route definitions. Do not add that prefix to `rome_app/urls_app.py`; settings and the hosting layer handle it.

### Local database content versus BDR content

- Django ORM models are `Biography`, `Document`, `Essay`, `Static`, `Shop`, `Genre`, and `Role`.
- `Book`, `Page`, `Print`, `BDRObject`, and `Annotation` are plain Python wrappers around remote BDR JSON or MODS XML; they are not Django ORM models.
- About, Links, Shops introduction text, biographies, essays, shops, documents, genres, and roles come from the local database. An empty or wrong database can therefore produce valid routes with missing content or 404 responses.
- Book, page, print, thumbnail, viewer, and annotation metadata largely come from BDR APIs. Many view responses combine local ORM rows with remote records.
- BDR identifiers are built from an environment-selected PID prefix plus the numeric-looking route ID. The collection PID also varies by settings module. Use `PID_PREFIX` and `settings.TTWR_COLLECTION_PID`; do not hardcode an environment's values into application logic.
- BDR response dictionaries contain optional and sometimes differently named fields. Preserve the established fallback behavior for titles, authors, dates, parent relations, and pagination when changing parsing code.

### Annotation creation and editing

- Create/edit routes require login. The views combine `AnnotationForm` with person and inscription formsets.
- `Annotation` in `rome_app/models.py` translates cleaned form data to and from MODS XML using `bdrxml` and `eulxml`.
- New annotations are sent to BDR with POST; edits are sent with PUT. These paths require BDR identity and authorization environment values. Never exercise a live write while running ordinary tests or exploratory commands.
- A MODS name links to a local biography through the biography's zero-padded `trp_id` in an `xlink:href`; its role text must match a local `Role`. Invalid existing metadata can raise `InvalidNameError` and send an administrator email.
- The small `new_genre`, `new_role`, and `new_biography` endpoints support the custom add-another popup used by annotation forms. Preserve the popup response contract when changing these forms.

### Settings and environment behavior

- `config/settings/base.py` requires `LOG_DIR` while settings are imported.
- `rome_app/app_settings.py` requires the BDR server, PID prefix, identity, and authorization values while the module is imported.
- `manage.py` and `config/passenger_wsgi.py` load the environment file from the directory above the repository. That external file selects the settings module and supplies deployment values.
- `config/settings/local.py` uses SQLite. Staging and production use MySQL and append the Turnstile middleware. Unit tests use `config/settings/unit_tests.py` and normally use SQLite.
- `run_tests.py` establishes harmless BDR placeholders and a temporary log directory before Django setup. Use it instead of relying on an interactive shell's current environment.
- Treat all external environment files and enclosing-directory notes or backups as private operational material. They are context only, not source files to copy, normalize, or commit.

### Turnstile request gate

- Turnstile is enabled only by the staging and production settings modules.
- `config/middleware/turnstile_middleware.py` allows an already verified session, the verification endpoint, or an allowed IP; otherwise it renders `turnstile_challenge.html`.
- `config/middleware/turnstile_view.py` verifies the submitted token with Cloudflare and records success in the session for the configured duration.
- Pure validation behavior is covered in `unit_tests/test_middleware.py`. Keep network verification separately mockable and never expose the secret or submitted token in logs.

### Templates, styles, and accessibility

- `base.html` loads `common.css` plus the page stylesheet chosen by `std_context()`. `result_base.html` adds Bootstrap and list filtering/sorting support.
- The site intentionally retains legacy assets, including Bootstrap CSS, jQuery 1.11.1, and `list.js`. Do not replace or modernize them unless the task calls for it and all dependent templates are checked.
- Several templates contain large inline style blocks. Search both CSS files and templates when tracing a displayed rule.
- The accessibility tests inspect source text and rendered HTML. Known low-contrast colors are rejected in inline styles and JavaScript assignments, and representative thumbnails and image viewers require useful alternative text or titles.
- Markdown-backed database content is rendered with `markdown_deux`; admin editing uses Pagedown. Preserve escaping and safe-rendering behavior when changing these paths.

### Test boundaries and common gotchas

- `unit_tests/test_views.py` contains most page behavior tests and extensive exact BDR mocks. `unit_tests/test_models.py` covers selected model behavior; `unit_tests/test_middleware.py` covers Turnstile helpers.
- `run_tests.py` is the reliable, CI-matching entry point. The README explicitly labels its old installation commands as outdated.
- Integration tests use the normal external environment and live records. Their expected identifiers and available records can become stale independently of the code.
- Search for usages before editing duplicate or historical templates and image assets; a matching filename does not prove that a current view renders it.
- The legacy code mixes formatting styles and places substantial work in `views.py` and `models.py`. Prefer focused improvements around the requested behavior instead of unrelated cleanup.
- The `/version/` endpoint reads Git branch and commit data at request time. Changes to deployment layout or Git availability can affect it even when ordinary page rendering works.

---
