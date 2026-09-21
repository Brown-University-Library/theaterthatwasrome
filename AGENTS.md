# AGENTS.md — Repository Agent Instructions (Source of Truth)

This file defines the canonical coding directives for this repository.

Keep this `AGENTS.md` file at no more than 300 lines, counting blank lines and the final `---`. When adding guidance, shorten or remove repeated material first; keep repository-specific instructions and the project index useful.

If other instruction files exist (Copilot, IDE rules, contributor docs) and conflict with this file, follow this file and treat the others as stale.


## Table of contents

- [Project basics](#project-basics)
- [How to run code](#how-to-run-code)
- [Coding directives (Python)](#coding-directives-python)
- [Django architecture conventions](#django-architecture-conventions)
- [Front-end change guidance](#front-end-change-guidance)
- [Tests](#tests)
- [Change workflow expectations](#change-workflow-expectations)
- [Privacy and publication](#privacy-and-publication)
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
- Favor clarity and explicitness over cleverness.
- Match the surrounding legacy style only where doing so is required for a small, safe change. Apply these directives to new code without turning a focused task into a broad rewrite.

### Logging

- When adding a log statement, when possible, format variable values as a label, followed by a comma and a space, with the value enclosed in double backticks.
- Prefer a label that matches the variable name. For example: `log.debug(f'branch_and_commit, ``{branch_and_commit}``')`.
- Never log BDR authorization values, database credentials, Turnstile secrets or tokens, session data, or complete request payloads that may contain those values.

### HTTP and networking

- Prefer `httpx` for a new, isolated HTTP integration.
- BDR calls use `httpx2` through `rome_app/lib/bdr_client.py`; reuse that client for new BDR calls. Turnstile verification still uses `requests`. Do not partially migrate an existing request path as an incidental change.
- If a task intentionally migrates an existing request path, update its dependency declaration, lockfile, mocks, timeout handling, and error handling together.
- Add an explicit timeout to new network calls.
- Preserve the BDR client's explicit connection and read timeouts, its handling of temporary failures through `BdrUnavailable`, and its rule against automatically retrying or following redirects for annotation writes.

### Docstrings

- Write triple-quoted docstrings in present tense (for example, "Parses ..."), with the opening and closing triple quotes on their own lines.
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

- Always use function-based views for Django projects. Do not use class-based views.
- Every application endpoint in `rome_app/urls_app.py` must refer directly to a manager function in `rome_app/views.py` as `views.function_name`. Do not split these endpoint functions into separate view modules. Django's admin URL include remains managed by Django.
- `rome_app/views.py` should contain only view functions that directly handle URL endpoints.
- Existing helpers in `views.py`, such as `std_context()`, are legacy code. Put new helpers under `rome_app/lib/`; move existing helpers when the task requires changing them, without broad unrelated cleanup.
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
- Check changed Python files with VS Code's Pylance, using the project's interpreter and type-checking settings. If Pylance is unavailable, use Pyright with matching settings and Django type definitions. Different type-definition versions can produce different results; a standalone check with newer definitions does not establish that the editor is clear. Do not suppress diagnostics to work around missing definitions.
- Unit tests belong in `unit_tests/`. BDR HTTP calls are isolated with `BdrMock` in `unit_tests/http_mock.py`, using data from `unit_tests/responses_data.py` or small synthetic examples. The mock rejects unexpected network requests.
- Live-service tests belong in `integration_tests/` and run through `uv run ./run_integration_tests.py` only when live integration coverage is intentional.
- New behavior should usually have a focused test covering the expected path and at least one failure or edge case.
- Front-end changes should preserve the accessibility checks in `unit_tests/test_views.py`, including shared color contrast, disallowed inline colors, image alternative text, frame titles, and representative rendered pages.
- BDR query tests may match an encoded URL and its query string exactly. If a query changes intentionally, update both the behavior and its mocked URL or matcher.


## Change workflow expectations

1. Read the relevant surrounding code and match established behavior.
2. Make the smallest correct change that satisfies the request.
3. Update tests and run `uv run ./run_tests.py`.
4. If dependencies change, update both `pyproject.toml` and `uv.lock`, then verify with the appropriate locked dependency group.
5. If tests cannot run in the environment, still write or adjust the tests and state exactly what should be run.

### Issue-based work and review

- Work directly from the current user request. Issues, formal templates, labels, preliminary discussions, and decision comments are not prerequisites for authorized local work.
- When issue-based work is authorized, organize each issue around one clear outcome and create a branch for its file changes. Include the issue number and a short description in the branch name, and record it in work reports. Reuse the current issue branch when it already matches the task. A request to change local files does not by itself authorize creating an issue or posting comments.
- Save requested plans, documentation, and code changes locally, leaving them uncommitted for the user's review unless the user explicitly requests a commit. Preserve the user's manual edits during revisions.
- Report the files changed, checks actually performed, and anything needing review. Distinguish work ready for review from work accepted by the user, and distinguish local, committed, and pushed changes. Link existing issues, commits, and pull requests when relevant.
- Ask questions only when necessary to proceed. Otherwise, state reasonable assumptions and implement. If blocked, report what you tried, what you found, and a concrete next step.

### GitHub attribution

- Every GitHub post or text update must visibly identify Codex as the agent that created or edited it. This includes issue descriptions, pull-request descriptions, comments, reviews, and discussions; do not rely on the displayed account name to convey authorship.
- Begin new issue descriptions with `Created by Codex at the user's request.` Keep this attribution separate from the user's prompt. For other posts or edits, use an accurate visible attribution such as `Posted by Codex` or `Edited by Codex`; begin issue comments with `Codex response` as described below.
- Distinguish who posted the material from who wrote it: identify quoted prompts as the user's words, and identify Codex's summaries, proposals, and reports as Codex's work.

### Issue bodies and user prompts

- When the user provides a prompt and asks to post it as an issue, put the complete, exact prompt in the issue description after the separate Codex attribution line. Preserve wording, spelling, punctuation, Markdown, links, paragraph breaks, and order. Do not summarize, reorganize, correct, omit parts, or add completion criteria. A prompt comment does not substitute for the issue body.
- Apply [Privacy and publication](#privacy-and-publication) before reproducing a prompt. When privacy requires redaction, mark each omission explicitly and explain outside the prompt that redactions were necessary. If the user requests a sanitized summary instead of a quotation, write a fresh summary and label it as Codex's summary of the request. Put any authorized Codex interpretation or work report in a separately attributed comment.
- When asked to draft an issue instead, use **Goal** for the intended outcome, **Context** for relevant background and constraints, and **Tasks** for the requested actions. Make clear whether the user wants advice, a plan, documentation, or implementation. Add **Completion criteria** only when observable checks would clarify what counts as done. Keep the structure proportional to the work.
- Use a structured body argument when available, or a temporary file with `--body-file` when using `gh`. After posting or editing, fetch the issue and verify the body and visible attribution. For a supplied prompt, compare its text against the original, allowing only explicitly marked privacy redactions. Return the issue link.

### GitHub issue comments

- Post a comment only when the user asks or has already authorized it. Authorization to maintain prompt and work records for an issue can cover later updates within that scope. A request to implement a change does not by itself authorize a comment, and a request to comment does not by itself authorize implementation or commits.
- Before posting, read the target issue, all its comments, and applicable `AGENTS.md` files. Address the current request within its stated scope; use newer maintainer guidance to resolve older conflicting comments.
- Begin comments with `Codex response` and identify the response type, such as **answer**, **advice**, **proposal**, **prompt record**, or **implementation report**. Clearly distinguish an agent proposal from an accepted maintainer decision.
- When asked to record a prompt as a comment, preserve the user's wording in a Markdown blockquote under `Codex response — **prompt record**`. Identify it as the user's prompt from the local work session and keep explanations outside the quotation. Apply [Privacy and publication](#privacy-and-publication), marking any required omissions explicitly. Label a requested sanitized summary as Codex's summary rather than presenting it as the user's exact words.
- Use authorized comments to record substantive prompts and work at useful milestones; every local exchange does not need a GitHub update. Implementation reports should describe what changed, what was verified, any remaining work or review, and whether changes are local, committed, or pushed. Posting a report does not authorize a commit or issue closure.
- Use a structured comment-body argument when available. If using `gh`, put multiline Markdown in a temporary file and pass it with `--body-file`. Verify the posted text and return its direct link. If a posting attempt has an uncertain result, check existing comments before retrying to avoid duplicates.

### Commit authorization

- Create or amend a commit only when the user explicitly asks Codex to commit the changes in question. This applies to Git commands and equivalent tools or APIs. A request to develop a plan, implement a change, save files, create a branch, post a summary, or finish the work does not authorize a commit.
- Review approval, a suggested commit message, or the user saying they might commit the work is not an instruction for Codex to commit. Commit-message conventions describe how to write an authorized commit; they do not grant permission to make one.
- Apply an explicit commit instruction only to its stated changes and scope. Permission for an earlier task or commit does not automatically cover later revisions. Do not ask again when the current changes are already covered by clear authorization.
- If commit authorization is absent or unclear, finish the authorized local work and report that it is ready for review and uncommitted. Do not delay that work to ask whether to commit.
- Permission to commit does not by itself authorize pushing, creating or merging a pull request, or closing an issue. Follow the user's instructions for each action separately.

### Issue closure

- Only the user closes issues unless the user specifically asks Codex to close an identified issue. Keep issues open by default, even after requested work, tests, review, commits, pushes, or merges are complete. A request to finish the task or approval of a plan is not permission to close the issue.
- Without that specific request, do not close issues through the UI, CLI, API, tools, or a comment-and-close action. Do not arrange automatic closure through commit messages, pull-request descriptions, links, or automation.
- Use ordinary references such as `Refs #123` or an issue URL unless closure is authorized. Do not use closing keywords such as `Closes`, `Fixes`, or `Resolves` with an issue reference or add links that close the issue when merged. Before an authorized merge, check for existing automatic closure instructions and links; remove them if authorized or leave the merge pending if it would close an issue without permission.

### Commit messages

- After [commit authorization](#commit-authorization), group related files into logical, focused commits; do not require a separate commit for every file.
- Use no more than ten words per commit message. Write in the present tense to complete "This commit...", beginning with a verb such as "Adds," "Implements," or "Updates."


## Privacy and publication

- Apply these rules to public and private repositories, including tracked files, agent notes, issue titles and bodies, comments, pull requests, commit messages, and attachments. Permission to investigate using conversation, local files, or tool output is not permission to publish that information.
- Do not publish explicit server names, hostnames, server IP addresses, credentials, tokens, private endpoints, personal information, cookies, session data, or unreviewed browser artifacts. Use generic descriptions and relative paths or variable names instead of full local or server filesystem paths.
- Keep sensitive working notes out of tracked files. Do not publish known or suspected vulnerabilities, affected live systems, exploit steps, or details that could help someone exploit a weakness. Discuss findings privately with the user; describe repository updates in terms of the general improvement and safe validation results.
- Write fresh, minimal summaries for repository reports. Do not paste private conversation excerpts, raw logs, tracebacks, configuration, commands, or tool output. Explicitly requested prompt records follow the prompt rules above only after the same privacy review; they never authorize publishing sensitive content.
- Before every repository post or edit, review the exact outgoing text, examples, links, screenshots, and attachments for sensitive information. Check combinations of details as well as individual values. Information already present in source code or an earlier post is not automatic permission to repeat it.
- When posting is authorized and the complete content is clearly safe to publish, proceed without another approval request. If sensitivity is uncertain, prepare sanitized wording, show it in the private conversation, explain the uncertainty without repeating sensitive values, and wait for confirmation of that exact text before posting. Never use an issue or comment to ask whether sensitive information is safe to disclose.
- Keep full server filesystem paths out of documentation, examples, and agent notes. Keep all server-deployment documentation, including any mention of deployment caller scripts, outside READMEs. When dependency migration includes a deployment caller, create it outside the Git repository.


## Agent project index

### Purpose and major areas

This Django application serves The Theater That Was Rome, a scholarly site for early modern books, prints, annotations, people, essays, shops, and related documents. It combines locally managed editorial content with records and images fetched from the Brown Digital Repository (BDR).

- `config/`: shared, local, test, staging, and production Django settings; root URLs; Passenger WSGI startup; and Cloudflare Turnstile middleware.
- `rome_app/urls_app.py`: application route map. Start here to connect a public URL to its view.
- `rome_app/views.py`: page assembly, BDR lookups, annotation forms, and response handling. This is a large legacy module; search for the route's named view before reading it broadly.
- `rome_app/models.py`: local Django models plus non-database wrappers for BDR objects and MODS annotations.
- `rome_app/lib/annotation_forms.py`: the shared helper for editing book and print annotations. `rome_app/lib/bdr_client.py` handles BDR HTTP calls; `rome_app/lib/bdr_failure.py` and `config/middleware/bdr_failure_middleware.py` handle temporary service failures.
- `rome_app/forms.py`, `rome_app/widgets.py`, and `rome_app/admin.py`: editorial forms, add-another popup behavior, and admin registration.
- `rome_app/templates/rome_templates/`: site templates. Most pages extend `base.html`; list pages commonly extend `result_base.html`.
- `rome_app/static/rome/`: shared CSS, page-specific CSS, legacy JavaScript, and images.
- `unit_tests/`: the isolated CI suite.
- `integration_tests/`: tests that expect a configured live service.

### Routing and page construction

- `config/urls.py` exposes the Turnstile verification endpoint and then includes `rome_app/urls_app.py` at the root.
- `rome_app/urls_app.py` groups routes for static pages, books/pages, prints, essays, people, shops, documents, authenticated record creation, search, version information, and a temporary role checker.
- `std_context()` in `rome_app/views.py` supplies common styles, image paths, title data, and breadcrumbs. Most rendered views depend on it.
- The `rome_login` route calls `views.login_page()`, which uses Django's `AuthenticationForm` and renders `rome_templates/login.html` with `home.css` and `login.css`. Successful login stays on this route even when a `next` destination was supplied. The page greets an authenticated user by first name, falling back to username. Login behavior is covered in `unit_tests/test_login.py`.
- The welcome page includes annotation guidance, book and print links, an admin link for active staff, and a CSRF-protected sign-out form. `rome_app/lib/login_helpers.py` validates `next` against the website's editing routes; a valid destination is retained in the session for the optional Continue editing link. `views.logout_page()` accepts only POST and returns to the login form.
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
- An existing annotation's genre text must match a local `Genre`. `MissingGenreError` produces a correction page through the shared editing helper, with HTTP 409 and no caching. Opening the page does not add genre records or change the annotation. The editor responsible for genre data must resolve the mismatch before the edit form can load. `unit_tests/test_annotation_genres.py` covers both edit routes and recovery after correction.
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
- `run_tests.py` is the reliable, CI-matching entry point. The current README documents installation with `uv sync --locked --group local`.
- `unit_tests/test_bdr_failures.py` checks timeouts, temporary service failures, recovery, and annotation write failures. Keep those failures distinct from missing local editorial data, and preserve the rule against automatically retrying annotation writes.
- Integration tests use the normal external environment and live records. Their expected identifiers and available records can become stale independently of the code.
- Search for usages before editing duplicate or historical templates and image assets; a matching filename does not prove that a current view renders it.
- The legacy code mixes formatting styles and places substantial work in `views.py` and `models.py`. Prefer focused improvements around the requested behavior instead of unrelated cleanup.
- The `/version/` endpoint reads Git branch and commit data at request time. Changes to deployment layout or Git availability can affect it even when ordinary page rendering works.

---
