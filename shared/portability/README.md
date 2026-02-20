# Digital Meal Portability

A shared Django application that connects Digital Meal with the portability APIs of external platforms (currently TikTok). It handles OAuth authentication, access token management, data export requests, and session state — in a way that is reusable across the two consumer apps: **Digital Meal Education** (DM EDU) and **My Digital Meal** (My DM).


## Architecture

The app is organised into the following layers:

| Module        | Responsibility                                                                                                                                    |
|---------------|---------------------------------------------------------------------------------------------------------------------------------------------------|
| `models.py`   | Database models for OAuth tokens, access tokens, and data requests. Defines `PortabilityContexts`.                                                |
| `sessions.py` | Session dataclass and manager. Provides `PortabilitySessionMixin` for views.                                                                      |
| `views.py`    | View mixins for auth enforcement, access token management, and state token handling. Concrete views for the TikTok OAuth and data download flows. |
| `services.py` | API clients for communicating with TikTok (token exchange, portability API).                                                                      |
| `utils.py`    | Utility helpers (e.g. resolving the portability context from a request).                                                                          |


## Portability Contexts

`PortabilityContexts` (a `TextChoices` enum on `models.py`) identifies which consumer app a given portability session belongs to:

- `DM_EDU` — Digital Meal Education
- `MY_DM` — My Digital Meal

The context is resolved from the request path at auth time and stored in the session. It is used to route users back to the correct consumer app after authentication.


## Session Layer

Portability state for a user's request is stored in Django's session under a single key (`"portability"`). The state is represented by three components:

- **`PortabilitySession`** — a dataclass with three fields: `context`, `state_token`, and `tiktok_open_id`. Handles type coercion of the context string to a `PortabilityContexts` enum member on deserialisation.
- **`PortabilitySessionManager`** — wraps the Django session and provides typed read/write access to the `PortabilitySession` fields (`get`, `update`, `reset`, `delete`, `get_token`, `get_context`, `get_tiktok_open_id`).
- **`PortabilitySessionMixin`** — a view mixin that initialises a `PortabilitySessionManager` instance as `self.port_session` at the start of each request. Must be listed after any mixin that accesses `self.port_session` in a view's inheritance chain.


## TikTok Integration

### Authentication Flow

1. **Auth initiation** (`TikTokAuthView`): A state token is generated and stored in the portability session. The user is redirected to TikTok's authorisation page with the state token embedded in the URL.

2. **OAuth callback** (`TikTokCallbackView`): TikTok redirects the user back with an authorisation code. The state token is validated and consumed (CSRF protection). The authorisation code is exchanged for an access token via the TikTok API, and the resulting `TikTokAccessToken` is written to the database. The user's TikTok `open_id` is stored in the portability session.

3. **Data request** (`TikTokAwaitDataDownloadView` / `TikTokCheckDownloadAvailabilityView`): A data export request is issued to TikTok's Portability API. The status of the request is polled and surfaced to the user.

4. **Data download** (`TikTokDataDownloadView`): Once TikTok has prepared the export, the ZIP file is streamed directly to the user.

5. **Disconnect** (`TikTokDisconnectView`): The user's `open_id` is cleared from the portability session and the Django session is rotated.

### State Token

Each authentication attempt generates an `OAuthStateToken` database record. It is single-use, expires after 10 minutes, and is tied to a portability context. It protects the callback endpoint against CSRF without exposing Django's CSRF token to an external redirect.

### View Mixins

| Mixin                            | Purpose                                                                                           |
|----------------------------------|---------------------------------------------------------------------------------------------------|
| `PortabilitySessionMixin`        | Initialises `self.port_session` on every request.                                                 |
| `AuthenticationRequiredMixin`    | Requires `tiktok_open_id` to be present in the portability session.                               |
| `ActiveAccessTokenRequiredMixin` | Requires a valid, non-expired `TikTokAccessToken` in the database. Refreshes it if needed.        |


## Settings & Environment Variables

| Variable               | Required | Default                                       | Description                                                                  |
|------------------------|----------|-----------------------------------------------|------------------------------------------------------------------------------|
| `TIKTOK_CLIENT_KEY`    | Yes      | —                                             | Client key issued by TikTok.                                                 |
| `TIKTOK_CLIENT_SECRET` | Yes      | —                                             | Client secret issued by TikTok.                                              |
| `TIKTOK_REDIRECT_URL`  | Yes      | —                                             | Callback URL; must point to `https://<domain>/portability/tiktok/callback/`. |
| `TIKTOK_AUTH_URL`      | No       | `https://www.tiktok.com/v2/auth/authorize/`   | TikTok authorisation page URL.                                               |
| `TIKTOK_TOKEN_URL`     | No       | `https://open.tiktokapis.com/v2/oauth/token/` | TikTok token exchange URL.                                                   |
| `TIKTOK_USER_INFO_URL` | No       | `https://open.tiktokapis.com/v2/user/info/`   | TikTok User Info API URL.                                                    |


## Development

### Prerequisites

TODO

[//]: # (TODO)
