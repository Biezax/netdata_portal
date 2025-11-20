# Data Model: Netdata Multi-Instance Aggregator

**Date**: 2025-11-20
**Feature**: 001-netdata-aggregator

## Overview

Stateless design - no persistent database. All entities exist in-memory on backend, derived from configuration and live Netdata API responses.

## Entity Definitions

### 1. Host Configuration

**Source**: Environment variable `NETDATA_HOSTS`
**Lifecycle**: Loaded on startup, reloaded on .env file change (FR-014)
**Storage**: In-memory Python list

```python
@dataclass
class HostConfig:
    """Validated Netdata instance configuration"""
    url: HttpUrl              # Pydantic validated URL (http:// or https://)
    display_name: str         # Extracted from hostname (e.g., "host1" from "http://host1:19999")

    # Validation rules (Pydantic)
    @validator('url')
    def validate_url(cls, v):
        # Must have scheme (http/https)
        # Must not contain path/query (base URL only)
        # Must be in NETDATA_HOSTS whitelist
        return v
```

**Validation (FR-010)**:
- URL scheme MUST be `http://` or `https://`
- Port MUST be specified or defaults to 19999
- Hostname MUST match pattern `^[a-zA-Z0-9.-]+$` (no special chars)
- Rejects: `javascript:`, `file:`, relative URLs, localhost (security)

**Example**:
```python
hosts = [
    HostConfig(url="http://prod-db-01:19999", display_name="prod-db-01"),
    HostConfig(url="https://prod-web-01:19999", display_name="prod-web-01")
]
```

---

### 2. Host Status

**Source**: Runtime state from health checks
**Lifecycle**: Updated every 15s during alert polling
**Storage**: In-memory dict keyed by hostname

```python
@dataclass
class HostStatus:
    """Runtime health status of Netdata instance"""
    hostname: str
    reachable: bool           # True if last request succeeded within 5s timeout
    last_check: datetime      # Timestamp of most recent health check
    error_message: str | None # Human-readable error if unreachable (FR-008)
    alert_count: int          # Number of active alerts (all severities)

    def is_healthy(self) -> bool:
        """Host is healthy if reachable within last 30s"""
        return self.reachable and (datetime.now() - self.last_check) < timedelta(seconds=30)
```

**State Transitions**:
1. **Initial**: `reachable=False`, `last_check=None` (never checked)
2. **Healthy**: Request succeeds in <5s → `reachable=True`
3. **Timeout**: Request exceeds 5s (FR-016) → `reachable=False`, `error_message="Connection timeout"`
4. **Unreachable**: Connection refused/DNS failure → `reachable=False`, `error_message="Host unreachable"`

**Error Messages (FR-008)** - Netdata visual style:
```
"❌ prod-db-01 is unreachable (connection timeout after 5s)"
"❌ prod-web-01 is unreachable (connection refused)"
"⚠️ prod-cache-01 responded slowly (>3s)"
```

---

### 3. Alert

**Source**: Netdata `/api/v1/alarms` endpoint response
**Lifecycle**: Fetched every 15s, discarded after processing (no persistence)
**Storage**: Temporary list during alert view rendering

```python
@dataclass
class Alert:
    """Active alarm from Netdata instance"""
    source_host: str          # Which Netdata instance (FR-012)
    alert_id: str             # Unique ID from Netdata (e.g., "cpu.cpu0")
    name: str                 # Human-readable name (e.g., "CPU Usage")
    severity: AlertSeverity   # Enum: CRITICAL, WARNING, INFO
    status: str               # Netdata status string (e.g., "WARNING")
    timestamp: datetime       # When alert triggered (for sorting FR-015)
    value: float | None       # Current metric value
    message: str              # Alert description from Netdata

class AlertSeverity(Enum):
    CRITICAL = 1  # Highest priority
    WARNING = 2
    INFO = 3

    def __lt__(self, other):
        return self.value < other.value  # For sorting
```

**Sorting Rules (FR-015)**:
```python
def sort_alerts(alerts: list[Alert]) -> list[Alert]:
    """Primary: severity (critical first), Secondary: timestamp (newest first)"""
    return sorted(alerts, key=lambda a: (a.severity, -a.timestamp.timestamp()))
```

**Mapping from Netdata API**:
```json
// Netdata /api/v1/alarms response
{
  "alarms": {
    "cpu.cpu0": {
      "name": "CPU Usage",
      "status": "WARNING",
      "value": 85.5,
      "updated": 1732118400,
      "info": "CPU usage above 80%"
    }
  }
}

// Maps to:
Alert(
    source_host="prod-db-01",
    alert_id="cpu.cpu0",
    name="CPU Usage",
    severity=AlertSeverity.WARNING,  # Derived from status
    status="WARNING",
    timestamp=datetime.fromtimestamp(1732118400),
    value=85.5,
    message="CPU usage above 80%"
)
```

**Severity Mapping**:
- Netdata `"CRITICAL"` → `AlertSeverity.CRITICAL`
- Netdata `"WARNING"` → `AlertSeverity.WARNING`
- Netdata `"CLEAR"` → Filtered out (not active)
- Unknown status → `AlertSeverity.INFO` (safe default)

---

### 4. View Mode

**Source**: Frontend UI state
**Lifecycle**: Managed by React state, persisted in URL query param
**Storage**: Client-side only (not sent to backend)

```typescript
enum ViewMode {
  DASHBOARD = "dashboard",  // FR-004: Show single host iframe
  ALERTS = "alerts"         // FR-005: Show aggregated alerts
}

interface AppState {
  viewMode: ViewMode;
  selectedHost: string | null;  // Current host in dashboard mode
}
```

**URL Structure**:
```
/?view=dashboard&host=prod-db-01   // Dashboard mode
/?view=alerts                       // Alerts mode
```

**State Persistence**: URL query params enable browser back/forward, bookmarking specific views.

---

## Data Flow Diagrams

### Configuration Loading (Startup + Auto-reload)

```
[.env file]
    ↓ (watchdog monitors)
[File Change Detected]
    ↓
[Parse NETDATA_HOSTS]
    ↓
[Validate Each URL] → (Invalid) → [Log Error, Keep Old Config]
    ↓ (All Valid)
[Update In-Memory hosts: list[HostConfig]]
    ↓
[Broadcast to Frontend via WebSocket/Polling] (optional future enhancement)
```

### Alert Polling Loop (Every 15s)

```
[Timer: 15s Interval]
    ↓
[For Each Host in hosts]
    ↓
[Async GET {host}/api/v1/alarms] (5s timeout FR-016)
    ↓─────┬─────────┐
   (Success)    (Timeout/Error)
    ↓               ↓
[Parse Response] [Mark Host Unreachable]
    ↓               ↓
[Map to Alert[]]  [HostStatus.reachable=False]
    ↓
[Aggregate All Alerts]
    ↓
[Sort by Severity + Timestamp (FR-015)]
    ↓
[Cache in Memory: latest_alerts]
    ↓
[Return to Frontend on Next Request]
```

### Proxy Request Flow (Dashboard Mode)

```
[Frontend iframe]
    ↓
[GET /api/proxy/prod-db-01/v3/]
    ↓
[Validate "prod-db-01" in hosts whitelist] → (Invalid) → [403 Forbidden]
    ↓ (Valid)
[httpx.get("http://prod-db-01:19999/v3/", timeout=5)]
    ↓─────┬─────────┐
   (Success)    (Timeout/Error)
    ↓               ↓
[Stream Response] [Return Netdata-style Error HTML]
    ↓
[Frontend Displays]
```

---

## Constraints & Invariants

### Configuration Constraints

1. **Host List Non-Empty**: `NETDATA_HOSTS` MUST contain ≥1 valid URL (startup fails otherwise)
2. **Unique Hostnames**: Display names MUST be unique (derived from URL hostname)
3. **URL Immutability**: Once validated, URL string is immutable (creates new HostConfig on reload)

### Runtime Constraints

1. **5s Timeout** (FR-016): All HTTP requests to Netdata hosts bounded by 5s
2. **15s Poll Interval** (FR-007): Alert polling MUST NOT drift (use `asyncio.sleep` not timestamp calculation)
3. **Memory Limit**: Alert cache capped at 1000 alerts total (oldest discarded if exceeded)

### Security Constraints

1. **Hostname Whitelist**: Proxy MUST reject any hostname not in `hosts` list (prevents SSRF)
2. **Path Traversal Prevention**: Proxy paths MUST NOT contain `..` or absolute paths
3. **Header Sanitization**: Forward only safe headers (`Accept`, `User-Agent`), strip `Host`, `Cookie`

---

## Example Scenarios

### Scenario 1: Startup with 3 Hosts

**Input**: `NETDATA_HOSTS="http://h1:19999,http://h2:19999,http://h3:19999"`

**Result**:
```python
hosts = [
    HostConfig(url="http://h1:19999", display_name="h1"),
    HostConfig(url="http://h2:19999", display_name="h2"),
    HostConfig(url="http://h3:19999", display_name="h3")
]
host_status = {
    "h1": HostStatus(reachable=False, last_check=None, ...),
    "h2": HostStatus(reachable=False, last_check=None, ...),
    "h3": HostStatus(reachable=False, last_check=None, ...)
}
```

After first poll (15s):
```python
host_status = {
    "h1": HostStatus(reachable=True, alert_count=2, ...),
    "h2": HostStatus(reachable=False, error_message="timeout", ...),
    "h3": HostStatus(reachable=True, alert_count=0, ...)
}
```

### Scenario 2: Alert Aggregation (2 Hosts)

**Netdata Responses**:
- h1: 1 CRITICAL, 2 WARNING
- h2: 1 WARNING, 3 INFO

**Aggregated & Sorted**:
```python
[
    Alert(source_host="h1", severity=CRITICAL, timestamp=...),  # 1
    Alert(source_host="h1", severity=WARNING, timestamp=T1),    # 2
    Alert(source_host="h1", severity=WARNING, timestamp=T2),    # 3
    Alert(source_host="h2", severity=WARNING, timestamp=T3),    # 4
    Alert(source_host="h2", severity=INFO, timestamp=...),      # 5-7
    ...
]
```

Order: CRITICAL first, then WARNING (sorted by time), then INFO.

---

## Technology Mapping

| Entity | Backend (Python) | Frontend (TypeScript) |
|--------|------------------|----------------------|
| HostConfig | `@dataclass` with Pydantic | `interface Host { url: string; name: string }` |
| HostStatus | In-memory dict | Fetched via `/api/hosts` endpoint |
| Alert | Pydantic model | `interface Alert { ... }` |
| ViewMode | N/A (frontend-only) | `enum ViewMode` |

**API Contract**: See `contracts/backend-api.md` for full endpoint schemas.
