# ADR-010: Testability by Design

## Status

Accepted

## Context

The platform is a distributed system with multiple services, external integrations,
cloud dependencies, and AI components. Without deliberate design for testability,
verifying component behavior requires live infrastructure: a running database, a real
cloud service, a live AI provider. This makes tests slow, expensive, and
environment-dependent. It also means that behavior can only be verified end-to-end,
not at the component boundary where the responsibility is defined.

Testability is not a property that can be added after a component is built. A component
that resolves its dependencies implicitly, couples its logic to infrastructure, or
produces side effects without declaration cannot be tested in isolation without
significant rework. Testability must be a design constraint from the start — it is a
direct consequence of ADR-004 (Cloud Agnosticism) and ADR-006 (Explicit over Implicit).

Every component must be designed so that its behavior can be verified in isolation,
using controlled inputs and observable outputs, without requiring live infrastructure.

## Decision

Every component is designed to be testable in isolation. Dependencies are injected, not
resolved implicitly. Behavior is verifiable through controlled inputs and observable
outputs without requiring live infrastructure or external services.

## Rationale

**Benefits**

- Component behavior can be verified at the boundary where the responsibility is
  defined, not only end-to-end.
- Tests run without live infrastructure, making them fast, deterministic, and
  executable in any environment including local development and CI.
- Design for testability enforces the same structural properties as ADR-004 and
  ADR-006: explicit dependencies, declared side effects, injectable abstractions.

**Tradeoffs**

- Designing for testability requires more upfront structural discipline than writing
  components that resolve dependencies directly.
- Test implementations of dependencies must be maintained alongside production ones.

**Assumptions**

- The cost of slow, environment-dependent, or untestable components — in debugging
  time, CI reliability, and confidence in changes — exceeds the cost of designing
  for testability upfront.
- Useful test implementations can be written for every infrastructure dependency the
  platform introduces.

**Risks**

- Test implementations that do not faithfully represent production behavior reduce the
  value of isolation tests and can mask real failures.
- Designing for testability in isolation does not eliminate the need for integration
  tests; gaps between isolated and integrated behavior must still be covered.

## Alternatives Considered

**Integration-first testing** — test components against live infrastructure rather than
designing for isolation. Rejected because it makes tests environment-dependent, slow,
and impossible to run without provisioned infrastructure. It also defers the discovery
of design problems that testability constraints would surface earlier.

**Test doubles at the framework level** — rely on framework-provided mocking to
substitute dependencies without designing for injection. Rejected because framework
mocking bypasses the component's declared interface and tests implementation details
rather than behavior, producing tests that are brittle and tightly coupled to the
implementation.

## Consequences

### Positive

- Every component's core behavior is verifiable in isolation, without live
  infrastructure, in any environment.
- Testability constraints enforce the same structural properties as ADR-004 and
  ADR-006, reinforcing those principles at the implementation level.
- Failures are diagnosable at the component boundary, not only through end-to-end
  symptoms.

### Negative

- Every infrastructure dependency requires a test implementation that must be
  maintained alongside the production one.
- Isolation tests do not cover integration behavior; a separate layer of integration
  testing is still required.

### Risks

- Test implementations that diverge from production behavior over time produce false
  confidence in isolation tests.
- The discipline required to maintain injectable dependencies erodes under time
  pressure, especially for components perceived as simple or low-risk.

## Mandatory Rules

- Every component must be testable without live infrastructure dependencies.
- Dependencies must be injectable so that test implementations can be substituted for
  production ones.
- Side effects must be declared and observable so that tests can verify them without
  relying on live systems.
- No component may be considered complete if its core behavior cannot be verified in
  isolation.

## Allowed Changes

- The specific testing patterns, frameworks, and test implementation strategies may
  evolve without a new ADR, provided the principle of isolation testability is
  preserved.
- The granularity of isolation — which dependencies are substituted and which are
  allowed in isolation tests — may be calibrated per component, provided no component
  is exempt from the principle entirely.

## Forbidden Changes

- No component may resolve infrastructure dependencies implicitly in a way that
  prevents substitution in tests.
- A component may not be considered complete without at least one test that verifies
  its core behavior in isolation.
- This ADR may not be superseded by one that permits infrastructure-dependent tests
  as the primary verification mechanism.

## Validation Criteria

- Every component must have at least one isolation test that runs without live
  infrastructure, verifiable in a CI environment with no external service access.
- Code review must reject components that resolve infrastructure dependencies
  implicitly without an injectable abstraction.
- Every declared side effect must be covered by at least one test that verifies it
  through an observable output, not through live system state.

## Related Documents

- [Vision](../VISION.md)
- [ADR-004: Cloud Agnosticism](004-cloud-agnosticism.md)
- [ADR-006: Explicit over Implicit](006-explicit-over-implicit.md)

## Future Revisions

- If AI components produce non-deterministic outputs that cannot be verified through
  controlled inputs, revisit whether a different verification model is needed for
  AI-specific behavior.
- If the cost of maintaining test implementations for all infrastructure dependencies
  proves prohibitive, revisit whether a shared test implementation library is
  warranted as a platform-level concern.
