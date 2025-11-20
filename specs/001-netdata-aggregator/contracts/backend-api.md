# Backend API Contracts

**Feature**: 001-netdata-aggregator
**Date**: 2025-11-20
**Base URL**: `http://localhost:8000` (development)

## Overview

RESTful API for Netdata aggregator backend. All endpoints return JSON unless specified otherwise (proxy endpoint returns raw HTML/binary).

## Authentication

**None** - System designed for internal networks (per FR spec clarification).

## Error Responses

Standard error format for all endpoints:

```json
{
  "error": "string",        // Error type (e.g., "ValidationError", "HostNotFound")
  "detail": "string",       // Human-readable message
  "host": "string" | null   // Affected hostname if applicable
}
```

HTTP Status Codes:
- `400 Bad Request` - Invalid input (malformed hostname, missing params)
- `403 Forbidden` - Hostname not in whitelist
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Unexpected backend error
- `504 Gateway Timeout` - Netdata host exceeded 5s timeout

---

## Endpoints

### 1. Get Configured Hosts

**Purpose**: Retrieve list of all configured Netdata instances (for sidebar rendering)

```http
GET /api/hosts
```

**Request**: None

**Response** (200 OK):
```json
{
  "hosts": [
    {
      "name": "prod-db-01",
      "url": "http://prod-db-01:19999",
      "status": {
        "reachable": true,
        "last_check": "2025-11-20T10:30:00Z",
        "alert_count": 3,
        "error_message": null
      }
    },
    {
      "name": "prod-web-01",
      "url": "https://prod-web-01:19999",
      "status": {
        "reachable": false,
        "last_check": "2025-11-20T10:29:45Z",
        "alert_count": 0,
        "error_message": "Connection timeout after 5s"
      }
    }
  ],
  "total": 2,
  "healthy": 1
}
```

**Fields**:
- `name`: Display name (hostname extracted from URL)
- `url`: Full base URL for Netdata instance
- `status.reachable`: `true` if last health check succeeded within 5s timeout
- `status.last_check`: ISO 8601 timestamp of most recent check
- `status.alert_count`: Number of active alerts (0 if unreachable)
- `status.error_message`: Human-readable error (null if reachable)

**Notes**:
- Cached data, updated every 15s during alert polling
- Frontend should poll this endpoint every 30s to refresh sidebar status

---

### 2. Get Aggregated Alerts

**Purpose**: Retrieve all active alerts across all hosts, sorted by severity (FR-015)

```http
GET /api/alerts
```

**Request**: None

**Response** (200 OK):
```json
{
  "alerts": [
    {
      "source_host": "prod-db-01",
      "alert_id": "cpu.cpu0",
      "name": "CPU Usage",
      "severity": "critical",
      "status": "CRITICAL",
      "timestamp": "2025-11-20T10:25:00Z",
      "value": 95.2,
      "message": "CPU usage above 90% for 5 minutes"
    },
    {
      "source_host": "prod-web-01",
      "alert_id": "disk.root",
      "name": "Root Disk Space",
      "severity": "warning",
      "status": "WARNING",
      "timestamp": "2025-11-20T10:28:00Z",
      "value": 85.0,
      "message": "Disk usage above 80%"
    }
  ],
  "total": 2,
  "by_severity": {
    "critical": 1,
    "warning": 1,
    "info": 0
  },
  "unreachable_hosts": ["prod-cache-01"]
}
```

**Fields**:
- `alerts[]`: Sorted array (critical → warning → info, then by timestamp descending)
- `source_host`: Which Netdata instance triggered this alert (FR-012)
- `severity`: Normalized severity (`"critical"`, `"warning"`, `"info"`)
- `timestamp`: When alert triggered (ISO 8601)
- `value`: Current metric value (null if not numeric)
- `unreachable_hosts`: Hosts that failed to respond (timeout/error)

**Sorting** (FR-015):
1. Primary: `severity` (critical=1, warning=2, info=3)
2. Secondary: `timestamp` (newest first)

**Notes**:
- Data refreshed every 15s via background polling (FR-007)
- Frontend should poll this endpoint every 20s in alerts view
- Empty `alerts` array if all hosts unreachable

---

### 3. Proxy Netdata Requests

**Purpose**: Forward requests to Netdata instances, avoiding CORS/mixed-content issues (FR-006)

```http
GET /api/proxy/{hostname}/{path:path}
```

**Path Parameters**:
- `hostname`: Netdata instance name (MUST match configured host)
- `path`: Relative path to proxy (e.g., `v3/`, `api/v1/data`, `static/css/main.css`)

**Request Headers** (forwarded):
- `Accept`
- `Accept-Language`
- `User-Agent`

**Headers NOT forwarded** (security):
- `Cookie` (prevent credential leakage)
- `Authorization` (no auth required)
- `Host` (replaced with target Netdata host)

**Response** (200 OK):
- Content-Type: Mirrors Netdata response (`text/html`, `application/json`, etc.)
- Body: Streamed directly from Netdata (no buffering for large responses)

**Example Requests**:

Dashboard iframe:
```http
GET /api/proxy/prod-db-01/v3/
→ Proxies to http://prod-db-01:19999/v3/
```

Chart data:
```http
GET /api/proxy/prod-db-01/api/v1/data?chart=cpu.cpu0
→ Proxies to http://prod-db-01:19999/api/v1/data?chart=cpu.cpu0
```

**Error Responses**:

Hostname not in whitelist (403):
```json
{
  "error": "HostNotAllowed",
  "detail": "Hostname 'malicious.com' not in configured hosts",
  "host": "malicious.com"
}
```

Host timeout (504):
```json
{
  "error": "GatewayTimeout",
  "detail": "prod-db-01 did not respond within 5 seconds",
  "host": "prod-db-01"
}
```

Connection refused (502):
```json
{
  "error": "BadGateway",
  "detail": "Could not connect to prod-db-01 (connection refused)",
  "host": "prod-db-01"
}
```

**Security** (FR-010, Constitution III):
- MUST validate `hostname` against whitelist before proxying
- MUST reject paths containing `..` (path traversal prevention)
- MUST NOT proxy to `localhost`, `127.0.0.1`, private IPs (SSRF protection)
- MUST apply 5s timeout per request (FR-016)

---

### 4. Health Check

**Purpose**: Kubernetes/Docker health probe endpoint

```http
GET /health
```

**Response** (200 OK):
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "configured_hosts": 3,
  "reachable_hosts": 2
}
```

**Response** (503 Service Unavailable) - if critical failure:
```json
{
  "status": "unhealthy",
  "error": "Failed to parse NETDATA_HOSTS configuration"
}
```

**Notes**:
- Always returns 200 if backend process running (even if all Netdata hosts down)
- 503 only if configuration invalid or critical internal error

---

## WebSocket (Future Enhancement - Not MVP)

**Not implemented in initial version** to maintain simplicity. If real-time updates needed later:

```
WS /ws/alerts
→ Streams alert updates as they occur (instead of polling)
```

Deferred per Constitution Principle I (Simplicity).

---

## Rate Limiting

**None** - Designed for internal use with trusted operators. Add `slowapi` if exposed to untrusted networks.

---

## CORS Configuration

**Development**: Allow `http://localhost:3000` (Next.js dev server)
**Production**: Same-origin only (frontend served by FastAPI)

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"] if DEV else [],
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"]
)
```

---

## Example Client Usage (TypeScript)

```typescript
// Fetch host list
const { hosts } = await fetch('/api/hosts').then(r => r.json());

// Fetch aggregated alerts
const { alerts } = await fetch('/api/alerts').then(r => r.json());

// Proxy Netdata dashboard (iframe)
<iframe src={`/api/proxy/${selectedHost}/v3/`} />
```

---

## Testing Requirements

Integration tests MUST cover:

1. **GET /api/hosts**:
   - Returns configured hosts from NETDATA_HOSTS
   - Status reflects unreachable hosts (timeout simulation)

2. **GET /api/alerts**:
   - Aggregates alerts from multiple hosts
   - Correct severity-based sorting (FR-015)
   - Handles partial failures (some hosts down)

3. **GET /api/proxy/{hostname}/{path}**:
   - Rejects unknown hostnames (403)
   - Rejects path traversal attempts (`../etc/passwd` → 400)
   - Respects 5s timeout (504 for slow mock server)
   - Streams large responses without buffering

4. **GET /health**:
   - Returns 200 with valid config
   - Returns 503 with malformed NETDATA_HOSTS

**Mock Netdata responses** using `pytest` + `httpx.AsyncClient`.
