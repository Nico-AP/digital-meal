# Development Guide

## Prerequisites

| Tool          | Version         | Notes                                               |
|---------------|-----------------|-----------------------------------------------------|
| Python        | 3.12            | Required; use pyenv or a system package             |
| Node.js + npm | any current LTS | Required only for My Digital Meal CSS compilation   |
| Redis         | 7+              | Required for Celery; `redis-server` must be running |
| MySQL         | 8+              | Production only; SQLite is used locally             |
| Git           | any             | Pre-commit hooks are used                           |

---

## Initial Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd DigitalMeal
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

### 3. Install Python dependencies

```bash
pip install -r requirements/base.txt
pip install -r requirements/development.txt
```

### 4. Download spaCy language models

Required for word cloud generation in reports:

```bash
python -m spacy download en_core_web_sm
python -m spacy download de_core_news_sm
```

### 5. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in the required values. See [Environment Variables](#environment-variables) below
for a full reference.

At minimum, for local development set:

```
DJANGO_SECRET=<any-random-string>
DJANGO_SETTINGS_MODULE=config.settings.local
SALT_KEY=<any-random-string>
TIKTOK_CLIENT_KEY=<your-key>
TIKTOK_CLIENT_SECRET=<your-secret>
TIKTOK_REDIRECT_URL=<your-callback-url>
```

Email and database settings can be left empty in `local.py` — the local settings use SQLite and
print emails to the console.

### 6. Install pre-commit hooks

```bash
pre-commit install
```

### 7. Apply database migrations

```bash
python manage.py migrate
```

### 8. Create a superuser

```bash
python manage.py createsuperuser
```

### 9. Install SASS dependencies (My Digital Meal only)

```bash
cd .sass
npm install
cd ..
```

### 10. Local Domain Setup for Development

To test subdomain routing locally, you need to map custom domains to your
local machine by editing your hosts file.

#### Unix (macOS / Linux)

Open `/etc/hosts` with sudo:
```bash
sudo nano /etc/hosts
```

Add the following lines:
```
127.0.0.1 domain.test
127.0.0.1 sub.domain.test
```

Save with `Ctrl+O`, exit with `Ctrl+X`, then flush the DNS cache:
```bash
# macOS
sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder

# Linux
sudo systemd-resolve --flush-caches
```

#### Windows 11

Open Notepad as Administrator (search for Notepad, right-click → "Run as
administrator"), then open the file:
```
C:\Windows\System32\drivers\etc\hosts
```

Add the following lines:
```
127.0.0.1 domain.test
127.0.0.1 sub.domain.test
```

Save the file. It may be that you then have to flush the DNS cache by running in Command Prompt:
```
ipconfig /flushdns
```

### 11. Running the Dev Server

Start Django binding to all interfaces:
```bash
python manage.py runserver 0.0.0.0:8000
```

Then access the app at:
- `http://domain.test:8000`
- `http://sub.domain.test:8000`

Make sure both domains are in `ALLOWED_HOSTS` in your local settings:
```python
ALLOWED_HOSTS = ['domain.test', 'sub.domain.test']
```

---

## Environment Variables

All variables are read from `.env` via `environs`. The `.env.example` file lists every variable.

### Django core

| Variable                 | Description                                                                                          |
|--------------------------|------------------------------------------------------------------------------------------------------|
| `DJANGO_SECRET`          | Django `SECRET_KEY`. Use a long random string.                                                       |
| `DJANGO_SETTINGS_MODULE` | Settings module to load. Use `config.settings.local` for development.                                |
| `ALLOWED_HOSTS`          | Space-separated list of allowed host/domain names.                                                   |
| `ADMINS`                 | JSON array of `[name, email]` pairs for error email recipients.                                      |
| `SALT_KEY`               | Salt for `django-fernet-encrypted-fields`. Keep stable — changing it breaks existing encrypted data. |

### Database (production only)

| Variable         | Description          |
|------------------|----------------------|
| `DJANGO_DB_NAME` | MySQL database name. |
| `DJANGO_DB_USER` | MySQL user.          |
| `DJANGO_DB_PW`   | MySQL password.      |
| `DJANGO_DB_HOST` | MySQL host.          |

Local development uses SQLite (`dm.sqlite`) automatically via `config/settings/local.py`.

### Email

| Variable                 | Description                                               |
|--------------------------|-----------------------------------------------------------|
| `EMAIL_HOST`             | SMTP server hostname.                                     |
| `EMAIL_PORT`             | SMTP port (typically 587).                                |
| `EMAIL_HOST_USER`        | SMTP username.                                            |
| `EMAIL_HOST_PASSWORD`    | SMTP password.                                            |
| `DEFAULT_FROM_EMAIL`     | Default sender address for outgoing mail.                 |
| `SERVER_EMAIL`           | Address used for error/admin emails.                      |
| `ALLOWED_REPORT_DOMAINS` | Space-separated domains allowed as report link base URLs. |

Local development uses the console email backend — no SMTP configuration needed.

### Routing

| Variable             | Description                                                                                                       |
|----------------------|-------------------------------------------------------------------------------------------------------------------|
| `MDM_ROUTING_MODE`   | `URL_PREFIX` (default) or `SUBDOMAIN`. See [Routing Modes](#routing-modes).                                       |
| `MDM_ROUTING_SCHEME` | Whether to use `http` (for testing and local development) or `https` (for stage/production);                      |
| `MDM_MAIN_DOMAIN`    | Primary domain of the Digital Meal site (e.g. `digital-meal.ch`).                                                 |
| `MDM_SUBDOMAIN`      | Subdomain for My Digital Meal (e.g. `my.digital-meal.ch`). Used when `MDM_ROUTING_MODE=SUBDOMAIN`.                |
| `MDM_URL_PREFIX`     | URL prefix for My Digital Meal (e.g. `my/`). Used when `MDM_ROUTING_MODE=URL_PREFIX`. Include the trailing slash. |

### TikTok / Portability

| Variable               | Description                                   |
|------------------------|-----------------------------------------------|
| `TIKTOK_CLIENT_KEY`    | TikTok app client key.                        |
| `TIKTOK_CLIENT_SECRET` | TikTok app client secret.                     |
| `TIKTOK_REDIRECT_URL`  | OAuth redirect URL registered with TikTok.    |
| `TIKTOK_AUTH_URL`      | (optional) Override TikTok authorisation URL. |
| `TIKTOK_TOKEN_URL`     | (optional) Override TikTok token URL.         |
| `TIKTOK_USER_INFO_URL` | (optional) Override TikTok user info URL.     |

### Redis / Celery

| Variable    | Description                                                |
|-------------|------------------------------------------------------------|
| `REDIS_URL` | Redis connection string (e.g. `redis://127.0.0.1:6379/0`). |

In `local.py`, `CELERY_TASK_ALWAYS_EAGER=True` means Celery tasks run synchronously inline — no Redis
or Celery worker is needed for local development unless you specifically need to test async behaviour.

### Wagtail

| Varia-ble               | Description                                 |
|-------------------------|---------------------------------------------|
| `WAGTAILADMIN_BASE_URL` | Base URL for Wagtail admin links in emails. |

---

## Routing Modes

The `MDM_ROUTING_MODE` setting controls how Digital Meal and My Digital Meal are served:

### `URL_PREFIX` (default, recommended for development)

My Digital Meal is mounted under a URL path prefix on the same domain:

```
site.com/tool/          → Digital Meal (teachers)
site.com/my/            → My Digital Meal (students)
```

Set in `.env`:

```
MDM_ROUTING_MODE=URL_PREFIX
MDM_URL_PREFIX=my/
```

No additional configuration is required for local development.

### `SUBDOMAIN`

My Digital Meal is served on a separate subdomain:

```
digital-meal.ch/tool/   → Digital Meal (teachers)
my.digital-meal.ch/     → My Digital Meal (students)
```

Set in `.env`:

```
MDM_ROUTING_MODE=SUBDOMAIN
MDM_MAIN_DOMAIN=digital-meal.ch
MDM_SUBDOMAIN=my.digital-meal.ch
```

Both domains must be in `ALLOWED_HOSTS`. `SubdomainRoutingMiddleware` blocks cross-domain access
(e.g., reaching MDM routes on the main domain). Testing subdomain routing locally requires a reverse
proxy or editing `/etc/hosts`.

---

## CSS / SASS

**`digital_meal/`** uses plain CSS files. No build step is required.

**`mydigitalmeal/`** uses SASS. The SASS source lives in `mydigitalmeal/assets/scss/` (organised using
the [7-1 pattern](https://sass-guidelin.es/#the-7-1-pattern)). The compiled output is committed to the
repository at `mydigitalmeal/core/static/mydigitalmeal/css/mydigitalmeal.css`.

### During development

```bash
cd .sass
npm run sass:watch
```

This watches for changes in the SCSS source and recompiles automatically.

### Before committing

Compile a production-optimised (compressed, no source map) build:

```bash
cd .sass
npm run sass:build
```

Always commit the compiled CSS alongside SCSS changes.

---

## Running Celery

In production, Celery handles asynchronous tasks such as computing aggregated statistics. Locally,
tasks run synchronously (`CELERY_TASK_ALWAYS_EAGER=True`) so no worker is needed.

To test true async behaviour locally, start Redis and a worker:

```bash
redis-server
celery -A config.celery_app worker --loglevel=info
```

---

## Testing

### Run the test suite

```bash
python manage.py test
```

Or with coverage:

```bash
coverage run manage.py test
coverage report
```

Coverage is configured in `pyproject.toml`:
- Includes `digital_meal/**` and `shared/**`.
- Excludes migrations and test files.
- Fails if coverage drops below 80%.

### Test settings

Tests use `config.settings.local` unless a different module is specified via `DJANGO_SETTINGS_MODULE`.
Each app has tests in a `tests.py` file or a `tests/` package.

---

## Code Quality Tools

All tools are configured in `pyproject.toml` and run automatically via pre-commit hooks.

### ruff — linting and formatting

```bash
ruff check .          # lint
ruff format .         # format
```

Target: Python 3.12. A broad set of rule categories is enabled (style, security, Django-specific, etc.).
Some rules are selectively ignored for `digital_meal/` and `shared/portability/`.

### mypy — type checking

```bash
mypy .
```

`check_untyped_defs = true` is set. Migrations are excluded. Django and DRF stubs are active.

### djlint — template linting

```bash
djlint . --lint
djlint . --check      # format check
```

Max line length: 119. Blank lines enforced after `load`, `extends`, and `include` tags.

### Pre-commit hooks

```bash
pre-commit run --all-files    # run all hooks manually
```

Installed hooks:
- **pre-commit-hooks**: trailing whitespace, EOF newline, JSON/YAML/TOML/XML validation,
  debug statement detection, private key detection.
- **django-upgrade**: auto-upgrades code to Django 5.2 patterns.
- **ruff**: linting and formatting (runs on commit).
- **djlint**: template linting (runs on commit).
- **pip-audit**: dependency vulnerability scan (runs on push).

---

## Logging

Log files are written to the `logs/` directory (created automatically on startup):

| File                | Content                                  | Format       |
|---------------------|------------------------------------------|--------------|
| `django.log`        | General application logs (WARNING+)      | verbose text |
| `mydigitalmeal.log` | My Digital Meal events (INFO+)           | JSON         |
| `portability.log`   | TikTok / data portability events (INFO+) | JSON         |
| `errors.log`        | All ERROR-level logs                     | verbose text |
| `security.log`      | Security warnings                        | verbose text |

In development (`DEBUG=True`), logs are also printed to the console. In production, ERROR-level events
trigger an email to `ADMINS` (throttled to one email per 3 minutes per error).

---

## TikTok Integration Testing

The TikTok OAuth callback URL is registered with TikTok pointing to the production environment,
so the full OAuth flow cannot be completed locally.

To test locally:

1. Complete authentication in the production environment.
2. Open `/admin` in the production environment and copy the resulting `TikTokAccessToken` record.
3. Replicate it in the local database via `python manage.py shell`.
4. Get your local session ID from the browser's developer tools (cookie named `sessionid`).
5. Inject the `tiktok_open_id` into the session:

```bash
python manage.py edit_session
```

---

## Production Deployment

### Settings

Use `config.settings.production` (`DJANGO_SETTINGS_MODULE=config.settings.production`).

Key differences from local:
- `DEBUG = False`
- MySQL database (configure `DJANGO_DB_*` env vars).
- HTTPS enforced: `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, secure cookies.
- `ALLAUTH_TRUSTED_CLIENT_IP_HEADER = "X-Real-IP"` for reverse proxy IP trust.
- `X_FRAME_OPTIONS = "DENY"`.
- DDM `EMAIL_PERMISSION_CHECK` restricts DDM access to `.uzh.ch` email domains.

### Checklist

1. Set all required environment variables (see [Environment Variables](#environment-variables)).
2. Run migrations: `python manage.py migrate`.
3. Collect static files: `python manage.py collectstatic`.
4. Ensure the `logs/` directory is writable by the application process.

### Static files

In production, `python manage.py collectstatic` writes all static assets to `staticfiles/`.
Serve this directory via your web server (nginx, etc.), not through Django.

### DDM webpack bundles

DDM's JavaScript bundles are distributed with the `django-ddm` package and referenced via
`django-webpack-loader`. After `collectstatic`, the webpack stats JSON files must be present in
`staticfiles/ddm_core/frontend/*/webpack-stats.json`. These are included in the DDM package itself
and do not require a separate build step.

### Data retention

The setting `DAYS_TO_DONATION_DELETION` (default: 180) controls how many days after submission a
data donation is deleted if no consent was given. This is enforced via a management command or
Celery task in `shared.portability`.