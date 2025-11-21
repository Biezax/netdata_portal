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

## Development

For local development with live code changes:

```bash
# Use dev compose file with build context
docker compose -f docker-compose.dev.yml up --build

# Or rebuild after code changes
docker compose -f docker-compose.dev.yml up -d --build
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
- No authentication (internal network deployment only)

## License

MIT
