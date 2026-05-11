# MFA Project

A Django application that demonstrates four authentication methods working together:
email + password, magic link, OAuth 2.0 (Google + GitHub), and TOTP two-factor authentication.

Built by **Abhishek**, **Akhil**, and **Himanshu** — MCA 2nd Semester,
Department of Computer Science, Himachal Pradesh University, Shimla.
Guide: Mr. Anshul Kalia. Session 2025-26.

---

## Features

- **Email + password** with PBKDF2-SHA256 hashing and a strong password policy
- **Magic link** login with one-time, hash-stored, time-bound tokens
- **OAuth 2.0** with Google and GitHub
- **TOTP 2FA** (RFC 6238) with QR enrolment and 8 single-use backup codes
- Account lockout after 5 failed attempts in 15 minutes
- Audit log of every login attempt
- TOTP secrets encrypted at rest with Fernet
- `/healthz/` liveness + database-readiness probe

## Tech stack

| Layer | Choice |
|---|---|
| Language / framework | Python 3.11, Django 5.x |
| Database | PostgreSQL 15 (driver: `psycopg` 3) |
| Dependencies | `uv` + `pyproject.toml` + `uv.lock` |
| Tool versions | `mise` |
| Lint / format | `ruff` |
| Tests | `pytest` + `pytest-django` (+ `responses` for HTTP mocks) |
| TOTP / QR | `pyotp`, `qrcode` |
| Encryption | `cryptography` (Fernet) |
| OAuth client | `requests`, `requests-oauthlib` |
| Static files (prod) | `whitenoise` |
| WSGI (prod) | `gunicorn` |
| Email (dev) | `mailhog` |

---

## Run with Docker (recommended)

```bash
cp .env.example .env
make keys                # paste both printed values into .env
docker compose up --build
```

Then open:

- App → http://localhost:8001
- Inbox (MailHog) → http://localhost:8026

Seed three demo users for a quick tour:

```bash
make demo-users
```

This creates:

| Email | Password | Notes |
|---|---|---|
| `alice@demo.local` | `Demo-Pass-2026!` | plain account |
| `bob@demo.local` | `Demo-Pass-2026!` | TOTP enabled (secret printed by the command) |
| `carol@demo.local` | `Demo-Pass-2026!` | Google account linked |

## Run from scratch (no Docker)

Requires Python 3.11 and a PostgreSQL 15 running locally.

```bash
mise install                    # installs Python 3.11
uv sync                         # installs dependencies into .venv
cp .env.example .env
make keys                       # paste both values into .env

# Edit .env: replace DATABASE_URL with your local Postgres:
#   DATABASE_URL=postgres://USER:PASS@localhost:5432/DBNAME

uv run python manage.py migrate
uv run python manage.py runserver
```

App at http://localhost:8000.

---

## Tests and lint

```bash
make test     # full pytest suite (43 tests, ~85% coverage on apps/)
make lint     # ruff check
make fmt      # ruff format
```

## Production

The same image runs in production via `docker-compose.prod.yml`. Edit `.env`
(set `DJANGO_DEBUG=False`, real `DJANGO_ALLOWED_HOSTS`, a strong
`POSTGRES_PASSWORD`, real SMTP credentials, OAuth redirect URIs at your
domain), then:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Front the `web` container with your own TLS-terminating reverse proxy.
The app reads `X-Forwarded-Proto` and serves with HSTS, secure cookies,
`X-Frame-Options: DENY`, and the other headers from `config/settings/prod.py`.

## Enabling OAuth providers

| Provider | Console | Required env vars |
|---|---|---|
| Google | https://console.cloud.google.com/apis/credentials | `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_REDIRECT_URI` |
| GitHub | Settings → Developer settings → OAuth Apps | `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET`, `GITHUB_OAUTH_REDIRECT_URI` |

The authorised redirect URI in the provider's console must match the value in `.env` exactly.
Leave the client id and secret blank to disable that provider's button.
