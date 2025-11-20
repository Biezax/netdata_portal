<!--
Sync Impact Report:
- Version: NEW → 1.0.0
- Initial ratification of Netdata Portal constitution
- Principles established: Simplicity, Performance, Security, Visual Consistency, Reliability, Modern Stack
- Templates requiring updates:
  ✅ plan-template.md (no changes needed - constitution gates section present)
  ✅ spec-template.md (no changes needed - requirements section compatible)
  ✅ tasks-template.md (no changes needed - task structure compatible)
- Follow-up TODOs: None
-->

# Netdata Portal Constitution

## Core Principles

### I. Simplicity

Configuration MUST remain minimal, consisting only of a host list. The system MUST NOT require complex metadata, service discovery configurations, or elaborate setup procedures. Any feature that introduces configuration complexity MUST be rejected unless absolutely necessary for core functionality.

**Rationale**: Reduces operational overhead, deployment time, and potential misconfiguration errors.

### II. Performance

HTTP proxy implementation MUST be efficient with minimal overhead. Memory consumption MUST be optimized for handling multiple concurrent host connections. The system MUST NOT introduce performance bottlenecks between clients and Netdata instances.

**Rationale**: Portal acts as intermediary - any inefficiency multiplies across all monitored hosts.

### III. Security

Host name validation MUST be enforced at all input boundaries. Proxy patterns MUST follow secure forwarding practices (no arbitrary URL redirection, proper header sanitization). The system MUST protect against injection attacks (path traversal, header injection, SSRF).

**Rationale**: Portal aggregates access to multiple infrastructure hosts - compromise has cascading impact.

### IV. Visual Consistency

Error pages and UI elements MUST match native Netdata visual style. Dark theme implementation MUST follow Grafana design patterns where applicable. User experience MUST feel seamless - portal should be transparent wrapper, not separate application.

**Rationale**: Maintains professional appearance and reduces cognitive load during incident response.

### V. Reliability

The system MUST degrade gracefully when individual hosts are unavailable. Error messages MUST be clear, actionable, and user-friendly. Partial failures MUST NOT prevent access to healthy hosts.

**Rationale**: Monitoring system must remain operational during incidents - that's when it's most needed.

### VI. Modern Stack

The system MUST use latest stable versions of chosen technologies. Legacy patterns (callbacks, var, outdated APIs) MUST be avoided in favor of modern equivalents (async/await, const/let, current standards).

**Rationale**: Reduces technical debt, improves maintainability, leverages ecosystem improvements.

## Development Standards

### Code Quality

- TypeScript strict mode MUST be enabled
- ESLint/Prettier rules MUST pass before commit
- No console.log in production code
- Error handling MUST be explicit (no silent failures)

### Testing Requirements

- Critical paths (proxy, authentication, host validation) MUST have integration tests
- Security validations MUST have dedicated test coverage
- Error scenarios MUST be tested (host down, timeout, invalid input)

### Documentation Standards

- README MUST include quick start with minimal example
- Configuration options MUST be documented with types and validation rules
- Architecture decisions MUST be captured in ADR format when non-obvious

## Governance

### Amendment Process

Constitutional changes require:
1. Documented rationale for the change
2. Analysis of impact on existing principles
3. Migration plan for affected code
4. Update of dependent templates and documentation

### Versioning Policy

Constitution follows semantic versioning:
- MAJOR: Principle removal or incompatible changes to governance
- MINOR: New principle added or existing principle significantly expanded
- PATCH: Clarifications, wording improvements, non-semantic fixes

### Compliance

- All PRs MUST verify alignment with constitutional principles
- Complexity that violates principles MUST be justified in plan.md Complexity Tracking table
- Regular reviews MUST ensure codebase remains compliant as it evolves

**Version**: 1.0.0 | **Ratified**: 2025-11-20 | **Last Amended**: 2025-11-20
