# Feature Specification: Netdata Multi-Instance Aggregator

**Feature Branch**: `001-netdata-aggregator`
**Created**: 2025-11-20
**Status**: Draft
**Input**: User description: "Создать простой агрегатор мониторинга Netdata для просмотра множества инстансов"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Single Host Dashboard (Priority: P1)

An operator needs to view the full Netdata dashboard for a specific monitored host without opening multiple browser tabs or remembering individual host URLs.

**Why this priority**: This is the core MVP - enables basic single-host monitoring through the aggregator, immediately solving the "multiple tabs" problem for at least one host at a time.

**Independent Test**: User can select a host from the sidebar, see its full Netdata dashboard loaded, and interact with all native Netdata features. Delivers immediate value by consolidating access.

**Acceptance Scenarios**:

1. **Given** the aggregator is configured with 3 hosts, **When** user clicks on "production-db-01" in the sidebar, **Then** the main area displays the full Netdata dashboard for that host
2. **Given** user is viewing a host dashboard, **When** the host is online, **Then** all Netdata charts, metrics, and interactions work exactly as if accessing the host directly
3. **Given** user is viewing a host dashboard, **When** the host becomes unavailable, **Then** an error message in Netdata visual style is displayed explaining the host is unreachable

---

### User Story 2 - Unified Alerts View (Priority: P2)

An operator needs to see all active alerts across all monitored hosts in a single view to quickly identify issues without checking each host individually.

**Why this priority**: Significantly improves incident response time by providing a centralized alert overview. Builds on P1 by adding cross-host monitoring capability.

**Independent Test**: User can switch to alerts mode and see a combined list of active alerts from all configured hosts. Can be tested independently by configuring hosts with known alert states.

**Acceptance Scenarios**:

1. **Given** multiple hosts have active alerts, **When** user switches to "Alerts" view mode, **Then** a unified list displays all active alerts sorted by severity (critical first) then by time
2. **Given** alerts view is open, **When** a new alert triggers on any host, **Then** the alert appears in the unified list within the polling interval at the appropriate position based on severity
3. **Given** alerts view shows alerts from multiple hosts, **When** user views the list, **Then** each alert clearly identifies which host it originated from
4. **Given** alerts view is open, **When** a host is unreachable, **Then** alerts from available hosts still display and the unreachable host is indicated

---

### User Story 3 - Simple Configuration (Priority: P3)

An administrator needs to add or remove monitored hosts by editing a simple configuration without complex metadata or restart procedures.

**Why this priority**: Reduces operational friction and makes the tool accessible to teams without deep technical expertise. Enhances usability but not critical for core monitoring function.

**Independent Test**: Administrator can modify the host list configuration file and see the updated host list appear in the sidebar automatically within 30 seconds without manual intervention.

**Acceptance Scenarios**:

1. **Given** the configuration file contains a comma-separated list of hosts, **When** administrator adds a new host and saves the file, **Then** the new host appears in the sidebar within 30 seconds automatically
2. **Given** the configuration contains invalid host entries, **When** the file is saved, **Then** clear error messages indicate which hosts failed validation without requiring restart
3. **Given** the host list is modified, **When** changes are automatically detected, **Then** previously selected host state does not cause errors if that host was removed

---

### Edge Cases

- What happens when all configured hosts are simultaneously unavailable?
- How does the system handle extremely long host lists (50+ hosts) in the sidebar?
- What happens when a host URL contains mixed HTTP/HTTPS or non-standard ports?
- How does the system behave when a host is slow to respond (exceeds 5s timeout) - display error immediately or retry?
- What happens when the alerts endpoint returns malformed data from a specific host?
- How does the sidebar indicate which host is currently selected across view mode switches?
- Should the system cache last known good state when a host times out?

## Clarifications

### Session 2025-11-20

- Q: How does the aggregator authenticate to individual Netdata instances? → A: Netdata instances do not require authentication (protected at network level - VPN, firewall rules)
- Q: What is the exact polling interval for retrieving alerts from Netdata instances? → A: 15 seconds
- Q: How are configuration changes applied? → A: Automatic reload - system monitors configuration file and applies changes automatically
- Q: How should alerts be sorted in the unified alerts view? → A: By severity (critical → warning → info), then by time
- Q: What timeout should be used for slow-responding hosts? → A: 5 seconds timeout before treating host as unavailable

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display a sidebar containing a list of all configured Netdata hosts
- **FR-002**: System MUST allow users to select a host from the sidebar to view its dashboard
- **FR-003**: System MUST provide two view modes accessible via top navigation: "Dashboard" and "Alerts"
- **FR-004**: Dashboard mode MUST display the full Netdata interface for the selected host
- **FR-005**: Alerts mode MUST aggregate and display active alerts from all configured hosts
- **FR-006**: System MUST proxy all requests to Netdata hosts through the backend to avoid mixed content issues
- **FR-007**: System MUST poll the `/api/v1/alarms` endpoint on each host every 15 seconds to retrieve alert data
- **FR-008**: System MUST display error messages matching Netdata visual style when hosts are unreachable
- **FR-009**: Configuration MUST accept a simple comma-separated list of host URLs
  - **Format Example**: `NETDATA_HOSTS="http://prod-db-01:19999,https://prod-web-01:19999,http://192.168.1.100:19999"`
  - Each host MUST include scheme (http:// or https://)
  - Port specification is required (typically 19999)
  - Hosts separated by commas without spaces
- **FR-010**: System MUST validate host names/URLs before attempting to proxy requests
- **FR-011**: Dashboard view MUST load the `/v3/` path of the selected Netdata host
- **FR-012**: Alerts view MUST clearly identify which host each alert originated from
- **FR-013**: System MUST handle partial failures gracefully (some hosts down, others operational)
- **FR-014**: System MUST automatically detect configuration file changes and apply them within 30 seconds without requiring restart
- **FR-015**: Alerts view MUST sort alerts by severity (critical first, then warning, then info) with secondary sorting by timestamp (newest first within each severity level)
- **FR-016**: System MUST apply a 5-second timeout to all requests to Netdata hosts, treating hosts as unavailable if they exceed this timeout
- **FR-017**: System MUST display a clear "All hosts unreachable" message in alerts view when no configured hosts respond to health checks

### Key Entities

- **Host**: Represents a monitored Netdata instance; attributes include URL/hostname, reachability status, current alert count
- **Alert**: Represents an active alarm from a Netdata instance; attributes include source host, alert name, severity, status, timestamp
- **View Mode**: Represents the current display mode (Dashboard or Alerts); determines what content is shown in the main area

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can access any configured host's dashboard in under 3 clicks (select host, view loads)
- **SC-002**: Alert view displays consolidated alerts from all configured hosts within 20 seconds of opening (accounts for 15s polling interval)
- **SC-003**: System remains usable when monitoring 20+ hosts simultaneously
- **SC-004**: Configuration changes are automatically detected and applied within 30 seconds of file modification
- **SC-005**: 95% reduction in number of browser tabs needed for multi-host monitoring (from N tabs to 1)
- **SC-006**: Error messages are clear enough that 90% of users can diagnose host connectivity issues without documentation
- **SC-007**: Dashboard interaction (chart zooming, filtering) responds within 500ms for responsive monitoring

### Assumptions

- Netdata instances are accessible via HTTP/HTTPS URLs from the aggregator backend
- All Netdata instances run compatible versions supporting `/v3/` dashboard path and `/api/v1/alarms` endpoint
- Host URLs are provided with protocol (http:// or https://)
- Users have network access to the aggregator web interface
- Alert polling interval of 15 seconds provides sufficient freshness for incident response
- Mixed HTTP/HTTPS hosts are supported through backend proxying
- Netdata instances do not require authentication from the aggregator (protected at network level via VPN/firewall)
