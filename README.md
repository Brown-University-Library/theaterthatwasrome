# The Theater That Was Rome

[![CI tests](https://github.com/Brown-University-Library/theaterthatwasrome/actions/workflows/tests.yml/badge.svg)](https://github.com/Brown-University-Library/theaterthatwasrome/actions/workflows/tests.yml)

- [Brief overview](#brief-overview)
- [More info](#more-info)
- [Local installation](#local-installation)
- [Optional BDR access through an SSH tunnel](#optional-bdr-access-through-an-ssh-tunnel)
- [Local testing](#local-testing)


## Brief overview

This repository contains the Django application for [The Theater That Was Rome](https://library.brown.edu/projects/rome/), a Brown University Library site for studying early modern books, prints, annotations, people, essays, shops, and related documents.

The application combines editorial content stored in a local Django database with records, images, and MODS annotations from the Brown Digital Repository (BDR). It currently uses Django 5.2, Python 3.10, `pyproject.toml`, and `uv` for dependency management and command execution.


## More info

The site brings together two complementary sources of information. Its local Django database stores editorial material such as biographies, essays, shop descriptions, documents, introductory pages, genres, and contributor roles. The Brown Digital Repository (BDR) supplies digitized books and prints, page images, descriptive metadata, relationships between records, and MODS annotations. Django views combine those sources when building pages, which means a local installation can run without a copy of the deployed database but may show empty pages or missing editorial content.

Public visitors can browse books, prints, and people; sort or filter book and print lists; filter people by role; examine zoomable page images; follow connections between works and contributors; and read scholarly essays and supporting documents. Authenticated editors can create or revise BDR annotations and add the local people, roles, and genres used by annotation forms. Annotation changes are remote writes, so development environments must be configured with correct BDR credentials.

The main application is in `rome_app/`, including routes, views, models, forms, templates, and static assets. Shared and environment-specific Django settings are in `config/settings/`. The isolated test suite is in `unit_tests/`; `integration_tests/` contains checks that depend on a configured live BDR service. Dependency versions are declared in `pyproject.toml` and locked in `uv.lock`.

- Browse the public site: [The Theater That Was Rome](https://library.brown.edu/projects/rome/)
- View the source repository: [Brown-University-Library/theaterthatwasrome](https://github.com/Brown-University-Library/theaterthatwasrome)


## Local installation

### Prerequisites

- Git
- [`uv`](https://docs.astral.sh/uv/)
- The correct local environment configuration, obtained from an application maintainer

The Python version is constrained by `pyproject.toml` to Python 3.10. `uv` will select or install a compatible interpreter.

### Install the application

Clone the repository and install the locked local dependency group:

```shell
cd /path/to/ttwr_stuff/
git clone https://github.com/Brown-University-Library/theaterthatwasrome.git ttwr
cd ttwr/
uv sync --locked --group local
```

Create a writable log directory:

```shell
mkdir -p ../logs
```

Both `manage.py` and the deployed WSGI entry point load an `.env` file from the directory immediately above the repository. For the above example, create `/path/to/ttwr_stuff/.env`.

At minimum, the local environment file must define:

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.local
LOG_DIR=/path/to/ttwr_stuff/logs
ROME_BDR_SERVER=<correct-bdr-host>
ROME_PID_PREFIX=<correct-pid-prefix>
ROME_BDR_IDENTITY=<correct-bdr-identity>
ROME_BDR_AUTH_CODE=<correct-bdr-authorization-code>
```

Obtain the BDR values through the application's maintainers. Do not commit the `.env` file or share its sensitive values.

### Set up the local database

The local development settings in `config/settings/local.py` use `rome.sqlite3` in the directory immediately above the repository, alongside `.env` and `logs/`. To work with existing editorial content, obtain the correct, sanitized development copy of that file from an application maintainer and place it at `/path/to/ttwr_stuff/rome.sqlite3`. Do not commit the database file.

If no database copy is available, the migration command below creates a new database and its tables, but it does not add editorial records.

Initialize the local SQLite database and start Django:

```shell
uv run ./manage.py migrate
uv run ./manage.py runserver
```

This completes the normal local installation; an SSH tunnel is not required. Django can load records from the local database, including biographies, essays, shops, documents, genres, roles, and database-backed informational pages. Without network access to the configured BDR host, BDR-dependent books, prints, page images, annotations, search data, and related-record features may be unavailable, incomplete, or displayed as broken images. See the next section if that access is needed.


## Optional BDR access through an SSH tunnel

The BDR development host may accept connections only through the correct development server. In that case, use SSH local port forwarding to send local BDR requests through an SSH-accessible gateway.

Choose an unused local port above 1024. Then edit `/etc/hosts` with administrator privileges and temporarily map the BDR hostname to your computer:

```text
127.0.0.1 <bdr-host>
```

The SSH gateway must use a different hostname or SSH alias that is not affected by this entry.

Update the BDR server setting in the repository-adjacent `.env` file. Keep the BDR hostname in the value so that HTTPS certificate validation continues to work:

```dotenv
ROME_BDR_SERVER=<bdr-host>:<local-port>
```

In a separate terminal tab, start the tunnel:

```shell
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:<local-port>:<bdr-host>:443 <ssh-user>@<ssh-gateway>
```

- `-N` tells SSH not to run a remote command because this connection is used only for port forwarding.
- `-L 127.0.0.1:<local-port>:<bdr-host>:443` forwards the chosen local port through the SSH gateway to the BDR host's HTTPS port.
- `-o ExitOnForwardFailure=yes` makes SSH report an error instead of remaining open when it cannot establish the forwarding listener.

The command normally produces no output. Keep its terminal tab open, then start or restart Django in another tab:

```shell
uv run ./manage.py runserver
```

The tunnel remains open while the SSH command is running. Press `Control-C` in that terminal to stop it. When tunneling is no longer needed, remove the temporary `/etc/hosts` entry and restore the usual `ROME_BDR_SERVER` value.


## Local testing

Assumes local dependencies have already been installed via the `uv sync...` command above.

Run the isolated Django unit suite with the same command used by continuous integration:

```shell
uv run ./run_tests.py
```

The unit runner selects `config.settings.unit_tests`, supplies non-production BDR placeholders, and creates a temporary log directory. The unit suite uses `responses` to mock expected HTTP calls. It does not require the normal local environment configuration.

The integration suite calls a live BDR service and loads the normal `.env` file. Run it only after confirming that the selected environment and service are appropriate:

```shell
uv run ./run_integration_tests.py
```
