# Digital Meal – Project Overview

## What Is Digital Meal?

Digital Meal is an overarching project combining the following subprojects:

1. **Digital Meal Education:** a web-based learning and teaching tool designed to be used by teachers/educators to foster media literacy among students; `digital_meal` in this repository
2. **My Digital Meal:** a web-based media use exploration tool designed to be used by the general public to gain insights into their TikTok use; `mydigitalmeal` in this repository
3. **Digital Meal Panel Study:** a panel study focusing on digital media use; currently not part of this repository

This repository covers the implementation of the Digital Meal Education and My Digital Meal Apps, which share a single 
Django project (`config/`), database, and user model. However, they are their own isolated applications and are 
logically separated through URL namespacing and, optionally, subdomain-level isolation. See the `shared/routing` module for
the mechanics.

---

## Repository Structure

```
DigitalMeal/
├── config/                  # Django project configuration
├── digital_meal/            # Digital Meal Education application
│   ├── core/                # App bootstrap and logging utilities
│   ├── dashboard/           # Admin Dashboard
│   ├── reports/             # Media usage report generation
│   ├── tool/                # Teacher registration and class management
│   └── website/             # Public website and Wagtail CMS
├── mydigitalmeal/           # My Digital Meal application
│   ├── core/                # App bootstrap and static file entry point
│   ├── userflow/            # App navigation flow
│   ├── profiles/            # App authentication
│   ├── questionnaire/       # Survey collection
│   ├── datadonation/        # Platform data download and portability
│   ├── reports/             # Usage reports
│   ├── statistics/          # Aggregated statistics (Celery tasks)
│   ├── infopages/           # Static informational pages
│   └── assets/scss/         # SASS source files (compiled to CSS)
├── shared/                  # Reusable modules used by both applications
│   ├── routing/             # Multi-context URL and auth routing
│   └── portability/         # TikTok OAuth and data takeout handling
├── docs/                    # Project documentation (this directory)
├── locale/                  # Internationalisation (German)
├── logs/                    # Application log files (auto-created)
├── media/                   # User-uploaded files
├── requirements/            # Python dependency files
├── templates/               # Base template overrides (allauth, Django defaults)
└── .sass/                   # Node project for SASS compilation
```

---


## Base Application (`config/`)

`config/` is not an application itself but the Django project root that ties together both
applications and all shared modules. It owns the settings hierarchy, the root URL dispatcher,
and the WSGI/ASGI entry points.

### Settings

Settings are split into a base module and environment-specific overrides that import from it:

- `settings/base.py` – All settings shared across every environment: installed apps, middleware
  stack, authentication (allauth), routing configuration, Celery, logging, TikTok / portability,
  and DDM integration.
- `settings/local.py` – Development overrides: `DEBUG=True`, SQLite database, console email
  backend, `CELERY_TASK_ALWAYS_EAGER=True` (tasks run synchronously — no worker needed), and
  relaxed DDM email domain check (`.ch` instead of `.uzh.ch`).
- `settings/production.py` – Production overrides: `DEBUG=False`, MySQL database, full HTTPS
  enforcement (HSTS, `SECURE_SSL_REDIRECT`, secure cookies), and `X-Real-IP` header trust for
  reverse-proxy deployments.
- `settings/ci.py` – CI/CD environment settings.

### URL Dispatcher

`urls.py` is the root URL configuration. It composes URL patterns from all sub-applications:

- Core Digital Meal Education routes (`/tool/`, `/reports/`, `/dashboard/`, `/`).
- My Digital Meal routes, dynamically mounted by `shared.routing.urls.get_mdm_urlpatterns()`
  either under a path prefix (e.g. `/my/`) or at the root of a subdomain, depending on
  `MDM_ROUTING_MODE`.
- DDM participation, projects, questionnaire, and API routes.
- Wagtail CMS and documents (registered last, as a catch-all).
- In debug mode: static/media file serving, Django Debug Toolbar, and browser auto-reload.

### Other Files

- `logging_utils.py` – Custom log filters; notably `ThrottledAdminEmailFilter`, which limits
  error notification emails to admins to at most one per 3 minutes per error.
- `wsgi.py` / `asgi.py` – Standard Django application entry points for deployment.

---


## Digital Meal Education (`digital_meal/`)

### Overview

Digital Meal Education is a web-based learning and teaching tool designed to foster media literacy among students.
The core idea is to enable educators to guide students through critically reflecting on their personal
media consumption by analysing and discussing the data that platforms collect about them.

The application:

- Guides students on how to request and download their personal data from platforms such as YouTube and TikTok.
- Generates personalized usage reports based on that data.
- Integrates with [django-ddm](https://github.com/uzh/ddm) for data donation and questionnaire collection.
- Offers teachers a management interface to create and administer class groups.

Entry points:
- `site.com/`
- `site.com/tool/`

### App Components

#### `digital_meal/core/`

App bootstrap and shared utilities. Provides a custom `JsonFormatter` for structured logging.

#### `digital_meal/tool/`

Teacher registration and class management.

- Defines the project-wide **custom user model** (`tool.User`), required by `AUTH_USER_MODEL`.
- Models: `User`, `Account`, `Class`.
- Views and forms for teacher signup and class administration.
- The teacher-facing admin interface lives under `/tool/`.

#### `digital_meal/dashboard/`

Admin dashboard: providing Django admins/superusers with an overview of participation statistics
Entry point: `/dashboard/`

#### `digital_meal/reports/`

Generates personalised media usage reports for classes and students. Supports TikTok and YouTube data. Entry point: `/reports/`.

- Report logic is split by platform: `views/tiktok.py`, `views/youtube.py`.
- Utilities in `utils/` handle data parsing and visualisation (uses `pandas`, `bokeh`, `wordcloud`, `spacy`).

#### `digital_meal/website/`

Public-facing website with Wagtail CMS integration.

- Wagtail pages for homepage, info pages, and other editorial content.
- Middleware (`RestrictDDMMiddleware`) blocks DDM admin access from the public site.
- Sitemap and redirect support via Wagtail.

---


## My Digital Meal (`mydigitalmeal/`)

### Overview

My Digital Meal is a web-based data usage exploration tool directed at the broader public. TikTok users can connect their
TikTok usage histories to My Digital Meal to receive a personalized usage report. By connecting their data to My Digital Meal,
users also support academic research into TikTok usage patterns.

The application:

- Guides users on how to request and download their personal data from TikTok.
- Generates personalized usage reports based on that data.
- Integrates with [django-ddm](https://github.com/uzh/ddm) for data donation and questionnaire collection.

### App Components

#### `mydigitalmeal/core/`

App bootstrap and static file entry point. The compiled CSS for My Digital Meal is served from
`mydigitalmeal/core/static/mydigitalmeal/css/mydigitalmeal.css`.

#### `mydigitalmeal/userflow/`

Orchestrates the user journey through the application: landing page, overview, navigation between
steps, and shortcut URL constants (`constants.py`).

#### `mydigitalmeal/profiles/`

User authentication via django-allauth.

- Code-based login (no password required for My Digital Meal users; code sent to email).
- Custom views for login, logout, and login-code confirmation.
- My Digital Meal uses different allauth settings than Digital Meal Education (no email verification,
  code-based signup); see `ALLAUTH_MDM` in `config/settings/base.py`.

#### `mydigitalmeal/questionnaire/`

Displays and handles submission of DDM questionnaires embedded in the user flow.

#### `mydigitalmeal/datadonation/`

Manages the data portability workflow.

- Guides users through authorising TikTok data access or uploading a data takeout file.
- Displays status messages while awaiting a data download (`portability/await_partials/`).
- Interacts with `shared.portability` for the OAuth and download logic.

#### `mydigitalmeal/reports/`

User-facing view of their personalised usage report. Distinct from `digital_meal/reports/`,
which is the teacher/admin-facing report generator.

#### `mydigitalmeal/statistics/`

Computes and stores aggregated, anonymised statistics.
Computation is handled asynchronously via Celery tasks.

#### `mydigitalmeal/infopages/`

Static informational pages shown to users (e.g., privacy notice, about pages).

#### `mydigitalmeal/assets/scss/`

SASS source files for all My Digital Meal styles, organised using the
[7-1 pattern](https://sass-guidelin.es/#the-7-1-pattern):
`abstracts/`, `base/`, `components/`, `layout/`, `pages/`, `themes/`, `utilities/`.

The compiled output is `mydigitalmeal/core/static/mydigitalmeal/css/mydigitalmeal.css`.
See [CSS / SASS](#css--sass) in the development guide for build instructions.

---


### Shared Modules (`shared/`)

#### `shared/routing/`

Handles the multi-context serving of Digital Meal and My Digital Meal from a single Django project.

Supports two deployment modes (controlled by `MDM_ROUTING_MODE`):

- **`URL_PREFIX`** (default) – My Digital Meal is served under a URL path prefix, e.g. `site.com/my/`.
- **`SUBDOMAIN`** – My Digital Meal is served on a separate subdomain, e.g. `my.site.com`.
  `SubdomainRoutingMiddleware` enforces that MDM URLs are only reachable on the MDM subdomain and vice versa.

Key components:

- `middleware.py` – `SubdomainRoutingMiddleware`: blocks cross-domain access in subdomain mode.
- `urls.py` – `get_mdm_urlpatterns()` dynamically builds MDM URL patterns based on `MDM_ROUTING_MODE`.
  Also provides `absolute_reverse()` and `absolute_reverse_lazy()` helpers that prepend the correct
  domain in subdomain mode.
- `constants.py` – `MDMRoutingTypes` enum.
- `templatetags/routing_tags.py` – Template tag for generating absolute URLs in templates.
- `allauth_integration/` – Context-aware authentication:
  - `adapters.py` – `SubdomainAccountAdapter`: overrides allauth settings per routing context.
  - `middleware.py` – `SubdomainAuthMiddleware`: applies MDM-specific allauth overrides for MDM requests.
  - `sessions.py` – Cross-context session handling.
  - `settings.py` – Per-context allauth setting overrides (see `ALLAUTH_MDM` in `base.py`).

#### `shared/portability/`

TikTok Portability API integration and data takeout handling.

- Models for storing OAuth access tokens and session state.
- REST views for the OAuth callback.
- Service layer for communicating with the TikTok API.
- Management command for cleaning up stale portability data.

---

### `templates/`

Top-level template directory. Contains overrides of base templates from third-party dependencies
(primarily django-allauth and Django's own defaults). App-specific templates live inside each app's
own `templates/` subdirectory.

---


## URL Routing

```
/admin/                                 Django admin
/accounts/                              django-allauth authentication
/ckeditor5/                             CKEditor 5 file upload API
/reports/                               digital_meal.reports (usage reports)
/tool/                                  digital_meal.tool (teacher management)
/dashboard/                             digital_meal.dashboard (teacher dashboard)
/portability/                           shared.portability (TikTok OAuth callbacks)
/teilnahme/<slug>/                      ddm.participation (DDM study participation)
/ddm/projects/                          ddm.projects (DDM project management)
/ddm/projects/<slug>/questionnaire/     ddm.questionnaire
/ddm/projects/<slug>/data-donation/     ddm.datadonation
/logs/                                  ddm.logging
/ddm/                                   ddm.auth
/ddm-api/                               ddm REST API
/cms/                                   Wagtail admin
/documents/                             Wagtail documents
/my/                                    mydigitalmeal (URL_PREFIX mode) or root of my.site.com (SUBDOMAIN mode)
/                                       digital_meal.website / Wagtail pages (catch-all)
```

---


## Key Dependencies

| Package                        | Purpose                                   |
|--------------------------------|-------------------------------------------|
| Django 5.2                     | Web framework                             |
| django-allauth 65              | Authentication (email + code-based login) |
| django-ddm 2.1                 | Data donation and questionnaire module    |
| Wagtail 7.3                    | CMS for editorial content                 |
| Celery 5.6 + Redis             | Async task queue (statistics computation) |
| pandas, numpy                  | Data processing for reports               |
| spaCy                          | NLP for word cloud pre-processing         |
| bokeh                          | Interactive visualisations in reports     |
| wordcloud                      | Word cloud generation                     |
| django-htmx                    | HTMX integration                          |
| django-fernet-encrypted-fields | Field-level encryption for sensitive data |
| environs                       | `.env`-based configuration                |

---


## Internationalisation

The default language is German (`de`), timezone is `Europe/Zurich`. Translation files live in `locale/`.
Wagtail's simple translation module is enabled.