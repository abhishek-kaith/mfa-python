# Multi-Factor Authentication System

A Django-based application that demonstrates four authentication methods working together:
email and password, magic link, OAuth 2.0 social login (Google and GitHub),
and TOTP two-factor authentication.

## Team

| Field         | Value                                                            |
| ------------- | ---------------------------------------------------------------- |
| Project title | Multi-Factor Authentication System Using Python and Django       |
| Team          | Abhishek, Akhil, Himanshu                                        |
| Program       | Master of Computer Applications (MCA), 2nd Semester              |
| Institution   | Department of Computer Science, Himachal Pradesh University, Shimla |
| Guide         | Mr. Anshul Kalia, Assistant Professor                            |
| Session       | Academic Session 2025-26                                         |

## Features

- **Email + Password** with PBKDF2-SHA256 hashing and a strong password policy.
- **Magic Link Login** with one-time, hash-stored, time-bound tokens.
- **OAuth 2.0** with Google and GitHub providers.
- **TOTP 2FA** (RFC 6238) with QR enrolment and 8 single-use backup codes.
- Account lockout after 5 failed attempts in 15 minutes.
- Audit log of every login attempt.
- TOTP secrets encrypted at rest with Fernet.
- `/healthz/` liveness + db-readiness probe for production.

## Architecture

```
Browser ──► Django (gunicorn / runserver)
              │
              ├── apps/accounts   email + password, registration, lockout
              ├── apps/magic      magic-link issue and consume
              ├── apps/oauth      Google and GitHub providers
              ├── apps/mfa        TOTP enrolment, challenge, backup codes
              ├── apps/dashboard  authenticated landing and security pages
              └── apps/common     audit log, encryption, lockout helpers
              │
              ▼
            PostgreSQL 15
```

The development stack also runs **MailHog** to catch outbound email and serve a UI.

## Tech Stack

- Python 3.11, Django 5.x
- PostgreSQL 15, psycopg 3
- uv for dependency management, mise for tool versions
- ruff for lint and format, pytest with pytest-django for tests
- pyotp + qrcode for TOTP, cryptography for Fernet encryption
- gunicorn + WhiteNoise for production

## Quickstart (development)

```bash
git clone <repo> && cd mfa-python
cp .env.example .env
make keys                     # paste the printed values into .env
docker compose up --build
# Application:    http://localhost:8001
# Email catcher:  http://localhost:8026
```

The dev compose binds only the web port and the MailHog UI on the host.
Postgres and the MailHog SMTP port stay inside the compose network so they
do not collide with anything else you already run.

If 8001 or 8026 are already taken on your machine, set `WEB_PORT` and
`MAILHOG_UI_PORT` in `.env` before bringing up the stack.

To create three demo users for graders to try the system quickly:

```bash
make demo-users
```

This seeds:
- `alice@demo.local` (plain account)
- `bob@demo.local` (TOTP enabled — the printed secret can be added to your authenticator app)
- `carol@demo.local` (Google account linked at the database level)

All three use password `Demo-Pass-2026!`.

## Production deployment

The project is built so you only have to fill in `.env`. Steps:

```bash
cp .env.example .env
make keys
# Edit .env: set DJANGO_DEBUG=False, DJANGO_ALLOWED_HOSTS, a strong
# POSTGRES_PASSWORD, a real SMTP host/user/password, and the OAuth
# redirect URIs at your real domain (https://your-domain/oauth/.../callback/).

docker compose -f docker-compose.prod.yml up -d --build
```

The prod compose:

- runs migrations and `collectstatic` automatically on start
- serves with gunicorn (`GUNICORN_WORKERS` defaults to 3)
- enables HSTS, secure cookies, `X-Frame-Options: DENY`, and other headers from spec section 9
- exposes `/healthz/` for the container's own healthcheck (and any external monitor)
- restarts on failure (`restart: unless-stopped`)

Front the `web` container with your own TLS-terminating reverse proxy (nginx, Caddy,
Traefik, a load balancer). Django reads `X-Forwarded-Proto` to know it is behind HTTPS.

## Enabling Google OAuth

1. Go to the Google Cloud Console, create a project, enable the OAuth consent screen.
2. Create an OAuth 2.0 Client ID of type "Web application".
3. Add the authorised redirect URI to match `GOOGLE_OAUTH_REDIRECT_URI` in `.env`.
4. Copy the client ID and client secret into `.env`.
5. Scopes requested: `openid email profile`.

## Enabling GitHub OAuth

1. On GitHub: Settings → Developer settings → OAuth Apps → New OAuth App.
2. Set the Authorization callback URL to match `GITHUB_OAUTH_REDIRECT_URI` in `.env`.
3. Copy the client ID and client secret into `.env`.
4. Scope requested: `user:email`.

## Running tests

```bash
make test       # runs pytest inside the web container
```

The suite has 37 tests; coverage on `apps/` is 85%.

## Lint and format

```bash
make lint
make fmt
```

`pre-commit install` once will run the same checks on every commit.

## Project structure

```
mfa-project/
├── config/               settings, urls, wsgi
├── apps/
│   ├── accounts/         User model, registration, login, password reset
│   ├── magic/            magic-link login
│   ├── oauth/            Google and GitHub providers
│   ├── mfa/              TOTP devices, backup codes
│   ├── dashboard/        post-login pages, healthz
│   └── common/           audit log, lockout, crypto helpers
├── templates/            HTML templates (one base.html plus per-app)
├── static/css/style.css  one stylesheet for the entire UI
├── tests/                pytest suite
└── scripts/              dev utilities (key generation)
```

## Acknowledgments

- **Django** — the web framework.
- **IETF RFC 6238** — TOTP: Time-Based One-Time Password Algorithm.
- **IETF RFC 6749** — The OAuth 2.0 Authorization Framework.
- **pyotp** — TOTP implementation in Python.
