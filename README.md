# The Theater That Was Rome

[![CI tests](https://github.com/Brown-University-Library/ttwr/actions/workflows/tests.yml/badge.svg)](https://github.com/Brown-University-Library/ttwr/actions/workflows/tests.yml)

- [Brief overview](#brief-overview)
- [More info](#more-info)
- [Local installation](#local-installation)
- [Local testing](#local-testing)


## Brief overview

This repository contains the Django application for [The Theater That Was Rome](https://library.brown.edu/projects/rome/), a Brown University Library site for studying early modern books, prints, annotations, people, essays, shops, and related documents.

The application combines editorial content stored in a local Django database with records, images, and MODS annotations from the Brown Digital Repository (BDR). It currently uses Django 5.2, Python 3.10, `pyproject.toml`, and `uv` for dependency management and command execution.


## More info

- Browse the public site: [The Theater That Was Rome](https://library.brown.edu/projects/rome/)
- View the source repository: [Brown-University-Library/ttwr](https://github.com/Brown-University-Library/ttwr)
- Read the repository's [accessibility assessment](ACCESSIBILITY_REPORT.md)

The main Django application is in `rome_app/`. Environment-specific settings are in `config/settings/`, isolated tests are in `unit_tests/`, and live-service tests are in `integration_tests/`.


## Local installation

### Prerequisites

- Git
- [`uv`](https://docs.astral.sh/uv/)
- Access to the approved local BDR configuration values

The Python version is constrained by `pyproject.toml` to Python 3.10. `uv` will select or install a compatible interpreter when possible.

### Install the application

Clone the repository and install the locked local dependency group:

```shell
git clone https://github.com/Brown-University-Library/ttwr.git
cd ttwr
uv sync --locked --group local
```

Create a writable log directory:

```shell
mkdir -p logs
```

Both `manage.py` and the deployed WSGI entry point load an `.env` file from the directory immediately above the repository. For example, if the checkout is `/path/to/rome/ttwr`, create `/path/to/rome/.env`.

At minimum, the local environment file must define:

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.local
LOG_DIR=/absolute/path/to/rome/ttwr/logs
ROME_BDR_SERVER=<approved-bdr-host>
ROME_PID_PREFIX=<approved-pid-prefix>
ROME_BDR_IDENTITY=<approved-bdr-identity>
ROME_BDR_AUTH_CODE=<approved-bdr-authorization-code>
```

Obtain the BDR values through the application's maintainers. Do not commit the `.env` file or share its sensitive values.

Initialize the local SQLite database and start Django:

```shell
uv run ./manage.py migrate
uv run ./manage.py runserver
```

The local database begins without the editorial content used by the deployed site. Pages backed by local models may therefore be empty or return a not-found response until suitable local data is added.


## Local testing

Install the locked local dependencies if they are not already present:

```shell
uv sync --locked --group local
```

Run the isolated Django unit suite with the same command used by continuous integration:

```shell
uv run ./run_tests.py
```

The unit runner selects `config.settings.unit_tests`, supplies non-production BDR placeholders, creates a temporary log directory, and mocks expected HTTP calls. It does not require the normal local environment configuration.

The integration suite calls a live BDR service and loads the normal `.env` file. Run it only after confirming that the selected environment and service are appropriate:

```shell
uv run ./run_integration_tests.py
```
