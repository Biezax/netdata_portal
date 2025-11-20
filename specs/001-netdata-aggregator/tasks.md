# Tasks: Netdata Multi-Instance Aggregator

**Input**: Design documents from `/specs/001-netdata-aggregator/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/backend-api.md, quickstart.md

**Tests**: Tests are NOT requested in this specification - focus on implementation only.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project directory structure (backend/, frontend/, docker/)
- [X] T002 Initialize backend Python 3.13 virtual environment in backend/
- [X] T003 [P] Create backend/requirements.txt with FastAPI 0.121.3, httpx 0.28.1, uvicorn 0.38.0, Pydantic 2.12.4, python-dotenv, watchdog
- [X] T004 [P] Initialize Next.js 16 project with TypeScript in frontend/
- [X] T005 [P] Configure ESLint, Prettier, and TypeScript strict mode in frontend/
- [X] T006 [P] Setup Tailwind CSS 3.4 in frontend/
- [X] T007 Create .env.example with NETDATA_HOSTS, ALERT_POLL_INTERVAL, REQUEST_TIMEOUT placeholders
- [X] T008 Create backend/tests/ directory structure (test_proxy.py, test_alerts.py, test_config.py)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T009 [P] Create Pydantic models in backend/models.py (HostConfig, HostStatus, Alert, AlertSeverity)
- [X] T010 [P] Implement config loader with validation in backend/config.py (parse NETDATA_HOSTS env var)
- [X] T011 [P] Create FastAPI app skeleton with CORS middleware in backend/main.py
- [X] T012 [P] Setup custom Tailwind dark theme in frontend/styles/netdata-theme.css (Grafana/Netdata colors)
- [X] T013 [P] Create base layout structure in frontend/app/layout.tsx (sidebar + main area)
- [X] T014 [P] Implement /health endpoint in backend/main.py
- [X] T015 [P] Create error handling utilities in backend/errors.py (standard error response format)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - View Single Host Dashboard (Priority: P1) 🎯 MVP

**Goal**: Enable viewing full Netdata dashboard for selected host through aggregator

**Independent Test**: User can select a host from sidebar, see its full Netdata dashboard loaded, interact with all native Netdata features

### Implementation for User Story 1

- [X] T016 [P] [US1] Implement proxy endpoint GET /api/proxy/{hostname}/{path} in backend/proxy.py
- [X] T017 [P] [US1] Add hostname whitelist validation in backend/proxy.py (reject non-configured hosts)
- [X] T018 [P] [US1] Implement 5-second timeout with httpx async client in backend/proxy.py
- [X] T019 [P] [US1] Add path traversal prevention (.., absolute paths) in backend/proxy.py
- [X] T020 [P] [US1] Implement header sanitization (forward Accept/User-Agent, strip Cookie/Host) in backend/proxy.py
- [X] T021 [P] [US1] Create GET /api/hosts endpoint in backend/main.py (return host list with status)
- [X] T022 [P] [US1] Create Sidebar component in frontend/app/components/Sidebar.tsx (host list with status indicators)
- [X] T023 [P] [US1] Create DashboardView component in frontend/app/components/DashboardView.tsx (iframe wrapper for /api/proxy/{host}/v3/)
- [X] T024 [P] [US1] Create ErrorPage component in frontend/app/components/ErrorPage.tsx (Netdata-styled error display)
- [X] T025 [US1] Wire up proxy routes in backend/main.py (register proxy endpoints)
- [X] T026 [US1] Implement home page in frontend/app/page.tsx (sidebar + dashboard view integration)
- [X] T027 [US1] Add URL state management in frontend/app/page.tsx (persist selected host in query params)
- [X] T028 [US1] Integration test: proxy with valid hostname returns Netdata content in backend/tests/test_proxy.py
- [X] T029 [US1] Integration test: proxy with invalid hostname returns 403 Forbidden in backend/tests/test_proxy.py
- [X] T030 [US1] Integration test: proxy with timeout simulation returns 504 Gateway Timeout in backend/tests/test_proxy.py
- [X] T031 [US1] Integration test: proxy rejects path traversal attempts in backend/tests/test_proxy.py
- [X] T032 [US1] Integration test: verify proxy forwards /v3/ path correctly to Netdata in backend/tests/test_proxy.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently - can select host, view dashboard, see errors on host down

---

## Phase 4: User Story 2 - Unified Alerts View (Priority: P2)

**Goal**: Display all active alerts across all monitored hosts in single view sorted by severity

**Independent Test**: User can switch to alerts mode and see combined list of active alerts from all configured hosts

### Implementation for User Story 2

- [X] T033 [P] [US2] Implement alert polling background task in backend/alerts.py (15-second interval, async polling all hosts)
- [X] T034 [P] [US2] Add Netdata API response parsing in backend/alerts.py (map /api/v1/alarms JSON to Alert models)
- [X] T035 [P] [US2] Implement severity mapping in backend/alerts.py (Netdata status → AlertSeverity enum)
- [X] T036 [P] [US2] Implement alert sorting logic in backend/alerts.py (severity first, then timestamp descending)
- [X] T037 [P] [US2] Add graceful failure handling in backend/alerts.py (partial host failures, track unreachable hosts)
- [X] T038 [P] [US2] Create GET /api/alerts endpoint in backend/main.py (return sorted aggregated alerts)
- [X] T039 [P] [US2] Start alert polling loop on FastAPI startup in backend/main.py (@app.on_event("startup"))
- [X] T040 [P] [US2] Create ViewModeSwitcher component in frontend/app/components/ViewModeSwitcher.tsx (Dashboard/Alerts toggle buttons)
- [X] T041 [P] [US2] Create AlertsView component in frontend/app/components/AlertsView.tsx (aggregated alerts table)
- [X] T042 [US2] Add alert auto-refresh polling in frontend/app/components/AlertsView.tsx (20-second interval)
- [X] T043 [US2] Integrate ViewModeSwitcher into page layout in frontend/app/page.tsx
- [X] T044 [US2] Add view mode state management in frontend/app/page.tsx (URL query param ?view=dashboard|alerts)
- [X] T045 [US2] Integration test: alert aggregation from multiple hosts in backend/tests/test_alerts.py
- [X] T046 [US2] Integration test: alert sorting by severity then timestamp in backend/tests/test_alerts.py
- [X] T047 [US2] Integration test: partial failure handling (some hosts down) in backend/tests/test_alerts.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - can switch to alerts view, see aggregated sorted alerts

---

## Phase 5: User Story 3 - Simple Configuration (Priority: P3)

**Goal**: Enable adding/removing hosts by editing configuration file with automatic reload within 30 seconds

**Independent Test**: Administrator can modify host list configuration file and see updated host list in sidebar automatically within 30 seconds

### Implementation for User Story 3

- [X] T048 [P] [US3] Implement file watcher in backend/config.py (watchdog monitoring .env file)
- [X] T049 [P] [US3] Add config reload logic in backend/config.py (re-parse NETDATA_HOSTS on file change)
- [X] T050 [P] [US3] Implement validation error logging in backend/config.py (log errors, keep last-known-good config)
- [X] T051 [P] [US3] Add in-memory host list update mechanism in backend/config.py (thread-safe update)
- [X] T052 [US3] Add auto-refresh sidebar data in frontend/app/components/Sidebar.tsx (30-second polling of /api/hosts)
- [X] T053 [US3] Start file watcher on FastAPI startup in backend/main.py
- [X] T054 [US3] Integration test: config reload on .env file change in backend/tests/test_config.py
- [X] T055 [US3] Integration test: invalid config handling (keep old config) in backend/tests/test_config.py

**Checkpoint**: All user stories should now be independently functional - edit .env, see sidebar update within 30s

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Docker deployment, documentation, and final validation

- [X] T056 [P] Create Dockerfile.backend in docker/ (Python 3.13-slim, FastAPI, uvicorn)
- [X] T057 [P] Create Dockerfile.frontend in docker/ (Node 22 build → static export)
- [X] T058 [P] Create docker-compose.yml in repository root (backend + frontend services)
- [X] T059 [P] Add structured JSON logging configuration in backend/main.py
- [X] T060 [P] Create README.md in repository root (link to quickstart.md)
- [X] T061 [P] Update .env.example with all configuration options
- [X] T062 Validate quickstart.md setup (docker-compose up → verify all features work)
- [X] T063 Performance validation: test with 20 hosts (verify <500ms dashboard load, <20% CPU during polling)
- [X] T064 Code cleanup: remove console.log, verify TypeScript strict mode compliance
- [X] T065 Final integration test: end-to-end user journey (all 3 user stories)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User Story 1 (P1): Can start after Foundational - No dependencies on other stories
  - User Story 2 (P2): Can start after Foundational - Independent of US1 (separate endpoints/components)
  - User Story 3 (P3): Can start after Foundational - Independent of US1/US2 (enhances config only)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Foundational → Proxy endpoint → Sidebar → Dashboard view → Tests
- **User Story 2 (P2)**: Foundational → Alert polling → GET /api/alerts → ViewModeSwitcher → AlertsView → Tests
- **User Story 3 (P3)**: Foundational → File watcher → Config reload → Sidebar auto-refresh → Tests

### Within Each User Story

1. Backend components before frontend (APIs ready first)
2. Core implementation before integration tests
3. Components marked [P] can run in parallel (different files)
4. Story complete before moving to next priority

### Parallel Opportunities

**Setup Phase**:
- T003, T004, T005, T006, T008 can all run in parallel

**Foundational Phase**:
- T009, T010, T011, T012, T013, T014, T015 can all run in parallel

**User Story 1** (max parallelization):
- Backend: T016, T017, T018, T019, T020, T021 can run in parallel (different concerns in same file or separate functions)
- Frontend: T022, T023, T024 can run in parallel (separate components)
- Integration: After T025-T027 complete, T028-T032 can run in parallel

**User Story 2**:
- Backend: T033-T037 can be parallelized initially
- Frontend: T040, T041 can run in parallel
- Integration: T045, T046, T047 can run in parallel

**User Story 3**:
- Backend: T048, T049, T050, T051 can be developed in parallel initially
- Integration: T054, T055 can run in parallel

**Polish Phase**:
- T056, T057, T058, T059, T060, T061 can all run in parallel

**Multiple developers**: After Foundational (Phase 2) completes, all 3 user stories can be developed in parallel by separate team members

---

## Parallel Example: User Story 1 Backend

```bash
# Launch all proxy-related backend tasks together:
Task: "Implement proxy endpoint GET /api/proxy/{hostname}/{path} in backend/proxy.py"
Task: "Add hostname whitelist validation in backend/proxy.py"
Task: "Implement 5-second timeout with httpx async client in backend/proxy.py"
Task: "Add path traversal prevention in backend/proxy.py"
Task: "Implement header sanitization in backend/proxy.py"
Task: "Create GET /api/hosts endpoint in backend/main.py"
```

---

## Parallel Example: User Story 1 Frontend

```bash
# Launch all frontend components together:
Task: "Create Sidebar component in frontend/app/components/Sidebar.tsx"
Task: "Create DashboardView component in frontend/app/components/DashboardView.tsx"
Task: "Create ErrorPage component in frontend/app/components/ErrorPage.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T008)
2. Complete Phase 2: Foundational (T009-T015) **CRITICAL - blocks all stories**
3. Complete Phase 3: User Story 1 (T016-T032)
4. **STOP and VALIDATE**: Test User Story 1 independently
   - Can select host from sidebar ✓
   - Dashboard loads and is interactive ✓
   - Error handling works (kill a host, verify error page) ✓
5. Deploy/demo MVP

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP: single host dashboard view)
3. Add User Story 2 → Test independently → Deploy/Demo (MVP + unified alerts)
4. Add User Story 3 → Test independently → Deploy/Demo (MVP + alerts + auto-reload config)
5. Add Polish → Final production-ready release

### Parallel Team Strategy

With 2-3 developers:

1. Team completes Setup + Foundational together (1-2 days)
2. Once Foundational is done:
   - **Developer A**: User Story 1 (P1) - Dashboard view
   - **Developer B**: User Story 2 (P2) - Alerts view
   - **Developer C**: User Story 3 (P3) - Config reload
3. Stories complete independently and integrate cleanly (no shared file conflicts)

---

## Notes

- **[P] tasks**: Different files or independent functions, no sequential dependencies
- **[Story] label**: Maps task to specific user story for traceability
- **No tests by default**: Tests included but optional (can be deferred if needed)
- **Each user story is independently completable and testable**: Can deploy US1 alone, or US1+US2, etc.
- **Commit strategy**: Commit after each task or logical group
- **Stop at any checkpoint**: Validate story independently before proceeding
- **File paths**: All paths are relative to repository root
- **Avoid**: Vague tasks, same file conflicts, cross-story dependencies that break independence

---

## Task Count Summary

- **Phase 1 (Setup)**: 8 tasks
- **Phase 2 (Foundational)**: 7 tasks
- **Phase 3 (User Story 1)**: 17 tasks
- **Phase 4 (User Story 2)**: 15 tasks
- **Phase 5 (User Story 3)**: 8 tasks
- **Phase 6 (Polish)**: 10 tasks

**Total**: 65 tasks

**Parallel opportunities**: ~36 tasks can be parallelized (55%)

**MVP scope** (User Story 1 only): 32 tasks (Setup + Foundational + US1)

**Suggested first milestone**: Complete T001-T032 for working dashboard view MVP
