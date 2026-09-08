# ADR-015: Behavior Driven by Configuration

## Status

Accepted

## Context

The platform has multiple points where behavior must vary across environments and
change over time without a code deployment: provider selection among registered
implementations, feature availability, operational limits, and routing rules. In a
distributed system with AI components, payment providers, and multiple consumer
types, the set of these variation points grows as the platform evolves.

Without a governing principle, configuration accumulates informally. Values are
hardcoded in source, read from undeclared environment variables, defaulted silently
when absent, or scattered across service internals with no consistent declaration
point. The result is behavior that cannot be audited, limits that cannot be changed
without a deployment, and missing configuration that produces silent misbehavior
rather than an explicit failure.

This is a direct violation of ADR-006: behavior shaped by undeclared configuration
is implicit behavior. It is also a violation of ADR-008: a service that starts
successfully with missing configuration and then fails at the point of use has
swallowed a startup failure and surfaced it as a runtime one.

Constraints:

- Distributed system — each service has its own configuration surface; there is no
  single configuration authority across services.
- Multiple environments — development, CI, staging, and production require different
  values for the same configuration keys.
- AI components and pluggable providers — behavioral variation points are structural,
  not exceptional. Provider selection and feature availability change independently
  of the code that uses them.
- Operational limits — values defined by ADR-012 (page sizes, timeouts, input bounds)
  must be adjustable without a code change.

Architectural goals affected: explicitness, operability, evolvability, correctness.

## Decision

Every value that governs system behavior and may vary across environments or change
independently of a code deployment is declared as configuration. Configuration is
explicit: every key a component depends on is declared at the component boundary,
with its type, valid range, and the behavior it controls. No component may read
configuration from ambient context without a declared dependency.

Configuration is validated at startup. A component that cannot resolve or validate
its declared configuration does not start. Missing or invalid configuration is never
silently defaulted into a running system.

## Rationale

**Benefits**

- Behavioral variation points are visible and auditable — every configurable value
  is declared, not discovered by reading source code.
- Operational changes — adjusting a limit, switching a provider, toggling a feature —
  do not require a code change or deployment.
- Startup validation surfaces misconfiguration immediately, before the component
  serves any traffic, rather than as a runtime failure under load.
- Declared configuration dependencies make components easier to test: configuration
  is injected like any other dependency, and test environments supply controlled values.

**Tradeoffs**

- Every configurable value requires an explicit declaration, adding upfront design
  effort compared to reading an environment variable inline.
- Startup validation means a misconfigured deployment fails visibly and immediately,
  which is the correct behavior but requires operational readiness to handle.

**Assumptions**

- Every configurable value has a finite, declarable set of valid values or a
  validatable range. No configuration value is inherently unvalidatable.
- The cost of silent misconfiguration — a service running with wrong limits, a
  provider silently falling back to a default, a feature unexpectedly disabled —
  exceeds the cost of explicit declaration and startup validation.

**Risks**

- Configuration declarations becoming stale if not updated when the behavior they
  govern changes, producing declarations that no longer reflect reality.
- Startup validation that is too strict rejecting valid configurations due to
  overly narrow range definitions, creating operational friction.

## Alternatives Considered

**Inline environment variable reads** — components read environment variables
directly at the point of use, with silent defaults when absent. Rejected because
it produces undeclared configuration dependencies that are invisible at the
component boundary, violating ADR-006, and silent defaults that mask
misconfiguration, violating ADR-008.

**Hardcoded values with deployment-time substitution** — values are hardcoded in
source and replaced at build or deployment time. Rejected because it couples
behavioral variation to the deployment pipeline, making operational changes
impossible without a deployment, and makes the variation points invisible in the
running system.

**Lazy validation at point of use** — configuration is read and validated when
first accessed rather than at startup. Rejected because it defers misconfiguration
failures to runtime, potentially under production load, rather than surfacing them
at the earliest possible point. This is a silent startup success that becomes an
explicit runtime failure — the pattern ADR-008 prohibits.

## Consequences

### Positive

- Every behavioral variation point in the platform is discoverable from configuration
  declarations, not from source code archaeology.
- Misconfigured deployments fail at startup with an explicit, actionable error
  identifying the missing or invalid key — not as a runtime failure under load.
- Operational changes to limits, provider selection, and feature availability do not
  require code changes or deployments.
- Configuration is injectable, making components testable with controlled values
  without live environment setup.

### Negative

- Every configurable value requires an explicit declaration and validation rule,
  adding design overhead per component.
- Startup validation makes deployment failures more visible and immediate, requiring
  operational processes that handle failed starts gracefully.

### Risks

- Configuration declarations drifting from the behavior they govern as the system
  evolves, producing declarations that are present but misleading.
- Overly strict validation ranges causing operational friction when legitimate
  values fall outside the originally declared bounds.

## Mandatory Rules

- Every value that governs system behavior and may vary across environments must be
  declared as configuration at the component boundary. No component may read
  configuration from ambient context without a declared dependency.
- All declared configuration must be validated at startup. A component with missing
  or invalid configuration must not start.
- Missing configuration must never be silently defaulted into a running system.
  If a default is appropriate, it must be declared explicitly alongside the
  configuration key, not applied silently at the point of use.
- Configuration declarations must specify the type, valid range or set of values,
  and the behavior the key controls.

## Allowed Changes

- The mechanism used to supply configuration values — environment variables,
  configuration files, remote configuration stores — may evolve without a new ADR,
  provided the principles of explicit declaration and startup validation are preserved.
- Default values may be declared for configuration keys where a safe, universal
  default exists, provided the default is explicit in the declaration and not
  silently applied at the point of use.
- Configuration keys may be added, removed, or renamed without a new ADR, provided
  the declaration and validation rules are updated in the same change.

## Forbidden Changes

- Components reading configuration from ambient context — environment variables,
  global state, implicit defaults — without a declared dependency at the component
  boundary.
- Deferring configuration validation to the point of use rather than performing it
  at startup.
- Silently defaulting missing configuration into a running system without an
  explicit declared default.
- This ADR may not be superseded by one that permits undeclared configuration
  dependencies or deferred validation on the grounds of convenience or simplicity.

## Validation Criteria

- Every configuration key a component depends on is discoverable from the
  component's declared configuration boundary without reading its implementation —
  verifiable by code review of the component's entry point.
- A component started with a missing required configuration key fails at startup
  with an explicit error identifying the missing key — verifiable by starting each
  component with required keys absent and asserting a startup failure with an
  actionable message.
- A component started with an out-of-range configuration value fails at startup —
  verifiable by supplying invalid values and asserting rejection before the component
  serves any traffic.
- No component reads a configuration value for the first time after startup has
  completed — verifiable by asserting all configuration reads occur within the
  startup validation path.

## Related Documents

- [ADR-006: Explicit over Implicit](006-explicit-over-implicit.md)
- [ADR-008: Explicit Failure Handling](008-explicit-failure-handling.md)
- [ADR-012: Bounded Operations](012-bounded-operations.md)

## Future Revisions

- If the platform introduces a remote configuration store that supports runtime
  updates without restart, revisit the startup validation model to define how
  post-startup configuration changes are validated and how invalid updates are
  rejected without taking the service down.
- If the number of configurable values per service grows to the point where
  declaration overhead becomes a bottleneck, revisit whether a schema-based
  declaration format can reduce the per-key overhead without weakening the
  explicitness requirement.
