# Netdata Multi-Instance Aggregator

Web-based aggregator for viewing multiple Netdata monitoring instances through a unified interface. Eliminates the need for dozens of browser tabs when monitoring multiple hosts.

## Quick Start

```bash
# 1. Clone repository
git clone <repo-url>
cd netdata_portal

# 2. Configure hosts
cp .env.example .env
# Edit config/hosts.txt and add your Netdata instances (one URL per line)

# 3. Start services
docker compose up -d

# 4. Access UI
open http://localhost:3000
```

## Features

- **Dashboard View (MVP)**: View full Netdata dashboard for any configured host
- **Unified Alerts**: See all active alerts across all hosts sorted by severity
- **Auto-reload Config**: Add/remove hosts by editing config/hosts.txt (updates within ~5s, no restart needed)
- **Dark Theme**: Netdata/Grafana-inspired visual style
- **Graceful Degradation**: Partial host failures don't block the UI

## Architecture

- **Backend**: FastAPI (Python 3.13) + httpx async proxy
- **Frontend**: Next.js 16 (React 19) + TypeScript + Tailwind CSS
- **Deployment**: Docker Compose (development) or Kubernetes (production)
- **Storage**: None - ephemeral in-memory state only

## Configuration

### Hosts Configuration (`config/hosts.txt`)

Add Netdata instance URLs, one per line:

```bash
# Production servers
http://prod-server-01:19999
http://prod-server-02:19999

# Dev servers
http://dev-server:19999
```

Lines starting with `#` are comments. Empty lines are ignored.
Changes are auto-detected within ~5 seconds (no restart needed).

### Environment Variables (`.env`)

```bash
ALERT_POLL_INTERVAL=15  # seconds
REQUEST_TIMEOUT=5       # seconds
```

Notification silence controls are disabled by default. For Docker Compose, keep
the backend-only Netdata Health Management API token in a mounted file:

```bash
NETDATA_MANAGEMENT_ENABLED=true
mkdir -p secrets
printf '%s' '<netdata-api-token>' > secrets/netdata_management_api_token
```

For non-container runs, `NETDATA_MANAGEMENT_API_TOKEN` or
`NETDATA_MANAGEMENT_API_TOKEN_FILE` can be used.

## Development

For local development with live code changes:

```bash
# Rebuild containers after code changes
docker compose up -d --build

# Or run services directly
uv sync --locked --dev
uv run uvicorn main:app --app-dir backend --reload
cd frontend && npm run dev
```

## Local Stand

Run a disposable stand with the portal and 10 Netdata agents:

```bash
docker compose -f docker-compose.stand.yml up -d --build
open http://localhost:3000
docker compose -f docker-compose.stand.yml down
```

## Documentation

- **Nginx Example**: [examples/nginx.conf](examples/nginx.conf) - Reverse proxy configuration with SSL

## Performance

- **Dashboard load**: <500ms
- **Alert aggregation**: <20s (includes 15s poll cycle)
- **Config reload**: ~5s (polling-based detection)
- **Supports**: 20+ concurrent Netdata hosts

## Security

- Hostname whitelist validation (SSRF protection)
- Path traversal prevention
- 5-second timeout per request (DoS protection)
- Optional LDAP authentication (see below)

## Authentication

LDAP authentication is enforced on the backend and covers every endpoint, including the
proxied Netdata dashboards. It is **disabled by default**; set `AUTH_ENABLED=true` and
configure the `LDAP_*` / `SESSION_*` variables (see `.env.example`) to turn it on.

Flow: the frontend shows a `/login` page that posts credentials to the backend, which
binds to LDAP and, on success, issues a signed `HttpOnly` session cookie. Subsequent
requests are gated by the backend; the frontend redirects to `/login` on any `401`.

Hardening built in:

- Empty passwords are rejected (avoids the anonymous-bind auth bypass).
- The username is escaped before it enters the search filter (LDAP injection).
- Access is restricted to members of `LDAP_REQUIRED_GROUP`.
- Encrypt the connection with `ldaps://` or `LDAP_START_TLS=true` and keep
  `LDAP_TLS_VALIDATE=true`. Set `SESSION_COOKIE_SECURE=true` behind HTTPS.
- Provide `SESSION_SECRET` (or `SESSION_SECRET_FILE`) — without it the backend refuses
  to start when auth is enabled. Generate one with `openssl rand -hex 32`.

Brute-force throttling is intentionally left to the reverse proxy / ingress
(e.g. nginx `limit_req`) — an in-app counter would not hold across replicas.

When auth is enabled, consider dropping the backend `8000:8000` port mapping in
`docker-compose.yml` so the API is only reachable through the frontend.

## License

MIT
