# ADR-006: Explicit over Implicit

## Status

Accepted

## Context

The platform is a distributed system built across multiple services, contracts,
integrations, and AI components. At this scale, implicit behavior — hidden defaults,
magic conventions, silent fallbacks, inferred dependencies — becomes a liability. When
behavior is implicit, it is invisible to the people who depend on it. It cannot be
reviewed, tested, or reasoned about independently of the implementation that produces it.

Implicit behavior compounds across a distributed system. A hidden default in one service
becomes an undocumented assumption in its consumers. A silent fallback in one component
becomes an invisible dependency in another. Over time, the system accumulates behavior
that nobody designed and nobody owns.

This applies across every layer of the platform: API contracts must be explicit,
dependencies must be declared, failure modes must be surfaced, security responsibilities
must be assigned, and runtime behavior must be traceable to a deliberate decision.

## Decision

Every behavioral decision in the system must be explicit and traceable. No component may
rely on hidden defaults, magic conventions, or implicit assumptions to define how it
behaves. Dependencies, contracts, failure modes, and security responsibilities are
declared, not inferred.

## Rationale

**Benefits**

- Behavior is reviewable and testable independently of the implementation that produces
  it — there is no hidden layer to discover.
- Dependencies and contracts are visible at component boundaries, making the system
  easier to reason about, debug, and evolve.
- Implicit assumptions cannot accumulate silently across service boundaries.

**Tradeoffs**

- Explicit declarations require more upfront design effort than relying on conventions
  or defaults.
- Codebases that favor explicitness tend to be more verbose than those that rely on
  framework magic or convention-over-configuration.

**Assumptions**

- The cost of debugging implicit behavior in a distributed system — invisible defaults,
  undocumented fallbacks, inferred dependencies — exceeds the cost of declaring
  behavior explicitly upfront.
- Explicit declarations can be made without becoming so verbose that they obscure the
  intent of the code.

**Risks**

- Explicitness applied without judgment can produce boilerplate that obscures intent
  rather than clarifying it.
- Teams under time pressure may introduce implicit behavior incrementally, each instance
  appearing harmless in isolation.

## Alternatives Considered

**Convention over configuration** — rely on shared conventions to reduce the need for
explicit declarations. Rejected because conventions are invisible to new contributors,
difficult to enforce across service boundaries, and tend to accumulate undocumented
exceptions over time.

**Framework-driven defaults** — allow frameworks to define default behavior and override
only when necessary. Rejected as a general principle because framework defaults are
implicit by definition: they define behavior that is not declared in the component that
depends on it, making that behavior invisible to reviewers and consumers.

## Consequences

### Positive

- Every behavioral decision is traceable to a deliberate declaration, making the system
  auditable and reviewable.
- New contributors can understand component behavior without reverse-engineering
  conventions or framework internals.
- Implicit assumptions cannot propagate silently across service boundaries.

### Negative

- Explicit declarations add verbosity. Components require more upfront design effort
  than convention-based alternatives.
- Existing implicit behavior must be made explicit when discovered, which requires
  deliberate refactoring effort.

### Risks

- Explicitness applied mechanically — declaring everything regardless of value — produces
  noise that obscures genuine design decisions.
- The principle is easy to erode incrementally: each implicit shortcut appears harmless
  in isolation.

## Mandatory Rules

- Every dependency a component relies on must be declared explicitly — never resolved
  through ambient context, global state, or convention.
- Every contract exposed to a consumer must be explicit and versioned — no undocumented
  behavior may be relied upon.
- Every failure mode must be surfaced explicitly — no silent defaults, swallowed
  exceptions, or implicit fallbacks.
- Runtime behavior must be traceable to a deliberate design decision — no magic
  conventions that alter behavior invisibly.

## Allowed Changes

- The form of explicit declaration — interface definitions, schema files, type
  annotations, configuration — may evolve without a new ADR, provided the principle
  of explicit over implicit is preserved.
- Conventions may be used within a single component's internal implementation, provided
  they do not cross component boundaries or affect consumer-visible behavior.

## Forbidden Changes

- No component may rely on implicit conventions to define its consumer-visible behavior
  where an explicit declaration is possible.
- No dependency may be resolved through global state or ambient context without an
  explicit declaration at the component boundary.
- This ADR may not be superseded by one that permits implicit behavior on the grounds
  of convenience or reduced boilerplate.

## Validation Criteria

- Every cross-service dependency must be traceable to an explicit contract definition —
  no undocumented behavior may be relied upon by a consumer.
- Code review must reject components that resolve dependencies through global state,
  ambient context, or undeclared conventions.
- Every failure path in a component must have an explicit handling declaration,
  verifiable through code review and testing.

## Related Documents

- [Vision](../VISION.md)

## Future Revisions

- If a framework or tooling convention proves sufficiently universal and well-documented
  that treating it as implicit does not create the risks described here, revisit whether
  a narrow exception is warranted for that convention.
- If the verbosity cost of full explicitness proves prohibitive in a specific layer,
  revisit whether a lighter-weight declaration form can preserve the principle without
  the overhead.
