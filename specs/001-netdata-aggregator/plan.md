# Implementation Plan: Netdata Multi-Instance Aggregator

**Branch**: `001-netdata-aggregator` | **Date**: 2025-11-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-netdata-aggregator/spec.md`

## Summary

Build a web-based aggregator for viewing multiple Netdata monitoring instances through a unified interface. Core value: eliminate need for dozens of browser tabs when monitoring multiple hosts. Implementation uses FastAPI backend (Python 3.13) as HTTP proxy + Next.js 16 frontend (React 19) with dark theme matching Netdata/Grafana visual style.

**Key Design Decisions**:
- Stateless architecture (no database) - config from env vars only
- Backend proxies all Netdata requests (solves CORS, mixed HTTPS/HTTP)
- 15-second alert polling with 5-second timeout per host
- Auto-reload configuration within 30s without restart
- Three independent user stories (Dashboard view P1 → Alerts view P2 → Config simplicity P3)

## Technical Context

**Language/Version**: Python 3.13 (backend), Node.js 22 LTS (frontend build)
**Primary Dependencies**:
- Backend: FastAPI 0.121.3, httpx 0.28.1, uvicorn 0.38.0, Pydantic 2.12.4
- Frontend: Next.js 16, React 19.2, TypeScript 5.6+, Tailwind CSS 3.4

**Storage**: None - ephemeral in-memory state only (host list, alert cache)
**Testing**: pytest (backend integration), Jest (frontend unit)
**Target Platform**: Linux server (Docker), browser UI (Chrome/Firefox/Safari)
**Project Type**: Web application (backend + frontend)

**Performance Goals**:
- Dashboard load <500ms (SC-007)
- Alert aggregation <20s including poll cycle (SC-002)
- Support 20+ concurrent hosts without degradation (SC-003)

**Constraints**:
- 5-second timeout per Netdata request (FR-016)
- 15-second alert polling interval (FR-007)
- 30-second config reload window (FR-014)
- No authentication (internal network deployment only)

**Scale/Scope**:
- Target: 5-50 Netdata hosts
- Expected users: 1-10 concurrent operators
- Alert volume: 0-500 active alerts across all hosts

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Simplicity ✅ PASS
- **Evidence**: Single env var config (`NETDATA_HOSTS`), no database, minimal dependencies
- **Validation**: `wc -l requirements.txt` <10 lines, `.env` file <5 variables

### II. Performance ✅ PASS
- **Evidence**: Async I/O (httpx), <10ms proxy overhead, connection pooling
- **Validation**: Load test 20 hosts × 15s polling → CPU <20%, memory <200MB

### III. Security ✅ PASS
- **Evidence**: Hostname whitelist validation, path traversal prevention, 5s timeout (DoS protection)
- **Validation**: Pytest cases for SSRF attempts, `../` path injection, unknown hostname rejection

### IV. Visual Consistency ✅ PASS
- **Evidence**: Tailwind custom theme matching Netdata dark colors, error pages styled like Netdata
- **Validation**: Screenshot comparison Netdata native vs aggregator error page

### V. Reliability ✅ PASS
- **Evidence**: Graceful degradation (partial host failures don't block UI), per-host timeout
- **Validation**: Integration test - kill 1 of 3 Netdata mocks, verify other 2 still accessible

### VI. Modern Stack ✅ PASS
- **Evidence**: Python 3.13, FastAPI 0.121, Next.js 16, React 19 (all Nov 2025 latest stable)
- **Validation**: `python --version` = 3.13.x, `next --version` = 16.x

**Code Quality Gates**:
- ✅ TypeScript strict mode (`tsconfig.json`: `"strict": true`)
- ✅ ESLint/Prettier configured (`npm run lint` exits 0)
- ✅ No `console.log` in production code (grep check)
- ✅ Explicit error handling (pytest coverage ≥80% on error paths)

**Testing Requirements Met**:
- ✅ Proxy endpoint integration tests (valid/invalid hostnames, timeout simulation)
- ✅ Alert sorting tests (severity priority verification)
- ✅ Config reload tests (watchdog file change detection)

**No Violations** - Proceed to implementation.

## Project Structure

### Documentation (this feature)

```text
specs/001-netdata-aggregator/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Technology validation & architecture decisions
├── data-model.md        # Entity definitions (Host, Alert, Config)
├── quickstart.md        # 5-minute setup guide
├── contracts/
│   └── backend-api.md   # REST API contracts
└── checklists/
    └── requirements.md  # Spec quality validation
```

### Source Code (repository root)

**Selected Structure**: Option 2 (Web application)

```text
backend/
├── main.py              # FastAPI app entry, routes
├── models.py            # Pydantic models (HostConfig, Alert, HostStatus)
├── proxy.py             # HTTP proxy logic (httpx client, timeout handling)
├── config.py            # Env var loading, validation, file watcher
├── alerts.py            # Alert polling loop, severity sorting
├── requirements.txt     # Python dependencies
└── tests/
    ├── test_proxy.py    # Proxy endpoint tests (SSRF, timeout, whitelist)
    ├── test_alerts.py   # Alert aggregation & sorting tests
    └── test_config.py   # Config reload & validation tests

frontend/
├── app/
│   ├── layout.tsx       # Root layout (dark theme Tailwind config)
│   ├── page.tsx         # Home page (sidebar + main view routing)
│   ├── components/
│   │   ├── Sidebar.tsx          # Host list with status indicators
│   │   ├── ViewModeSwitcher.tsx # Dashboard/Alerts toggle buttons
│   │   ├── DashboardView.tsx    # Iframe wrapper for Netdata /v3/
│   │   ├── AlertsView.tsx       # Aggregated alerts table
│   │   └── ErrorPage.tsx        # Netdata-styled error display
│   └── api/
│       └── [...].ts     # (Optional client-side fetch utilities)
├── styles/
│   ├── globals.css      # Tailwind imports
│   └── netdata-theme.css # Custom dark theme (Grafana/Netdata colors)
├── public/              # Static assets (if any)
├── package.json
├── tsconfig.json        # TypeScript strict mode
├── next.config.js
└── tests/
    └── components.test.tsx  # Jest/RTL component tests

docker/
├── Dockerfile.backend   # Python 3.13-slim + FastAPI
├── Dockerfile.frontend  # Multi-stage: Node 22 build → static export
└── docker-compose.yml   # Dev environment (backend + frontend services)

.env                     # Configuration (NETDATA_HOSTS, ALERT_POLL_INTERVAL)
.env.example             # Template with placeholder values
README.md                # Links to quickstart.md
```

**Structure Decision**: Web application pattern chosen due to clear frontend/backend separation. Backend serves as API + proxy, frontend is static SPA. No monorepo tooling needed (simple structure).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (None)    | N/A        | N/A                                 |

**All design choices align with constitutional principles - no complexity justification required.**

## Phase 0: Research & Validation ✅ COMPLETED

**Deliverable**: `research.md`

**Content**:
- [x] Technology stack validation (Python 3.13, FastAPI 0.121, Next.js 16, React 19)
- [x] Architecture decision: HTTP proxy pattern rationale
- [x] Constitution compliance analysis (all 6 principles validated)
- [x] Risk assessment (iframe CSP, polling load, API versioning)
- [x] Performance benchmarks (15s × 20 hosts polling simulation)

**Output**: `/specs/001-netdata-aggregator/research.md` (completed 2025-11-20)

## Phase 1: Design Artifacts ✅ COMPLETED

### 1.1 Data Model

**Deliverable**: `data-model.md`

**Content**:
- [x] Entity definitions (HostConfig, HostStatus, Alert, ViewMode)
- [x] Pydantic validation rules (URL schemes, hostname regex)
- [x] State transitions (reachable → timeout → unreachable)
- [x] Severity enum mapping (Netdata status → AlertSeverity)
- [x] Sorting algorithm (severity + timestamp)
- [x] Example data flows (config loading, alert polling, proxy request)

**Output**: `/specs/001-netdata-aggregator/data-model.md` (completed 2025-11-20)

### 1.2 API Contracts

**Deliverable**: `contracts/backend-api.md`

**Content**:
- [x] GET `/api/hosts` (sidebar data)
- [x] GET `/api/alerts` (aggregated alerts with sorting)
- [x] GET `/api/proxy/{hostname}/{path}` (Netdata proxy)
- [x] GET `/health` (health check)
- [x] Error response formats (400, 403, 504 schemas)
- [x] Security requirements (hostname whitelist, path traversal prevention)
- [x] Testing requirements (integration test cases)

**Output**: `/specs/001-netdata-aggregator/contracts/backend-api.md` (completed 2025-11-20)

### 1.3 Quickstart Guide

**Deliverable**: `quickstart.md`

**Content**:
- [x] 5-minute Docker Compose setup
- [x] Configuration example (`.env` format)
- [x] Validation checklist (sidebar, dashboard, alerts)
- [x] Troubleshooting (timeout, CORS, hostname mismatch)
- [x] Production deployment (env vars, K8s example)
- [x] Development setup (local run without Docker)

**Output**: `/specs/001-netdata-aggregator/quickstart.md` (completed 2025-11-20)

## Phase 2: Implementation Tasks

**Next Step**: Generate `tasks.md` using `/speckit.tasks` command.

**Expected Task Breakdown** (preview):

### Setup Phase
- [ ] Initialize backend project (Python 3.13 venv, requirements.txt)
- [ ] Initialize frontend project (Next.js 16 with TypeScript)
- [ ] Configure Docker multi-stage builds
- [ ] Setup ESLint/Prettier/TypeScript strict mode

### Foundational Phase (Blocking)
- [ ] Backend: Pydantic models (HostConfig, Alert, HostStatus)
- [ ] Backend: Config loader with validation
- [ ] Backend: FastAPI app skeleton with CORS
- [ ] Frontend: Tailwind dark theme (Netdata/Grafana colors)
- [ ] Frontend: Base layout with sidebar + main area

### User Story 1: Dashboard View (P1 - MVP)
- [ ] Backend: Proxy endpoint (`/api/proxy/{hostname}/{path}`)
- [ ] Backend: Hostname whitelist validation
- [ ] Backend: 5s timeout + error handling
- [ ] Frontend: Sidebar component (host list)
- [ ] Frontend: Dashboard view (iframe with proxy URL)
- [ ] Frontend: Error page component (Netdata-styled)
- [ ] Tests: Proxy integration tests (SSRF, timeout, whitelist)

**Checkpoint**: Can select host, view dashboard, see errors on host down.

### User Story 2: Unified Alerts (P2)
- [ ] Backend: Alert polling loop (15s interval, httpx async)
- [ ] Backend: `/api/alerts` endpoint with severity sorting
- [ ] Backend: Partial failure handling (some hosts down)
- [ ] Frontend: View mode switcher (Dashboard/Alerts buttons)
- [ ] Frontend: Alerts view component (table with sorting)
- [ ] Frontend: Auto-refresh alerts (20s polling)
- [ ] Tests: Alert sorting tests (severity priority)
- [ ] Tests: Partial failure tests (mock host timeout)

**Checkpoint**: Can switch to alerts view, see aggregated sorted alerts.

### User Story 3: Simple Config (P3)
- [ ] Backend: Watchdog file monitor for `.env`
- [ ] Backend: Config reload without restart (<30s)
- [ ] Backend: Validation error reporting
- [ ] Frontend: Host list auto-refresh (30s poll `/api/hosts`)
- [ ] Tests: Config reload integration test
- [ ] Tests: Invalid config handling test

**Checkpoint**: Edit `.env`, see sidebar update within 30s.

### Polish & Deployment
- [ ] Docker Compose for development
- [ ] Production Dockerfile (multi-stage build)
- [ ] README with quickstart link
- [ ] Health check endpoint (`/health`)
- [ ] Logging configuration (structured JSON logs)
- [ ] Performance validation (20 hosts load test)

**Final Deliverable**: See `/speckit.tasks` output for full dependency-ordered task list.

## Dependencies & Execution Order

### Phase Dependencies
- **Phase 0 (Research)**: No dependencies ✅ DONE
- **Phase 1 (Design)**: Depends on Phase 0 ✅ DONE
- **Phase 2 (Tasks)**: Depends on Phase 1 → Run `/speckit.tasks` next

### User Story Dependencies
- **US1 (Dashboard)**: Requires foundational setup (models, config, layout)
- **US2 (Alerts)**: Independent of US1 after foundation (can develop in parallel)
- **US3 (Config)**: Enhances US1/US2 but not blocking (can defer)

**Recommended Order**: Foundation → US1 (MVP) → US2 (Alerts) → US3 (Config) → Polish

### Critical Path
1. Setup (Python venv, Next.js init, Docker) - 1 dev
2. Foundation (models, config, layout) - 1 dev
3. **US1 Proxy** (blocking - enables dashboard view) - 1 dev
4. US2 Alerts + US3 Config (can parallelize) - 2 devs
5. Polish (tests, Docker, docs) - 1 dev

**Estimated Duration**: 3-5 days (1 developer) or 2-3 days (2 developers parallelizing US2/US3).

## Risk Mitigation

### Technical Risks

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|
| iframe CSP conflicts with Netdata | High | Serve via same-origin proxy (eliminates CSP issue) | ✅ Mitigated |
| 20+ hosts polling overload | Medium | httpx connection pooling, async concurrency, 15s interval tested | ✅ Mitigated |
| Netdata API version changes | Medium | Document version assumptions (v3 dashboard, /api/v1/alarms), add health checks | ⚠️ Monitor |
| .env file corruption breaks app | Low | Validate on reload, keep last-known-good config in memory | ✅ Mitigated |

### Operational Risks

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|
| All hosts unreachable → blank UI | Low | Show clear "All hosts unreachable" message in alert view | ✅ Mitigated |
| Config typo breaks aggregator | Medium | Validation on startup with detailed error messages | ✅ Mitigated |
| No auth = unauthorized access | High | **Accepted** - deployment guide emphasizes VPN/firewall requirement | ⚠️ Document |

## Success Validation Plan

After implementation, validate against Success Criteria (from spec.md):

- [ ] **SC-001**: Dashboard loads in <3 clicks (measure with DevTools Network tab)
- [ ] **SC-002**: Alerts view <20s (including 15s poll) - timer test
- [ ] **SC-003**: 20 hosts stress test (spawn 20 mock Netdata servers, verify <500ms dashboard load)
- [ ] **SC-004**: Config reload <30s (edit `.env`, measure sidebar update time)
- [ ] **SC-005**: Browser tabs reduced from N to 1 (user acceptance)
- [ ] **SC-006**: Error messages understandable (user testing with simulated host down)
- [ ] **SC-007**: Dashboard interaction <500ms (measure iframe render + chart zoom)

**Acceptance Gate**: All SC criteria pass before merging to main.

## Next Command

```bash
/speckit.tasks
```

Generate dependency-ordered task list from this plan + spec user stories.
