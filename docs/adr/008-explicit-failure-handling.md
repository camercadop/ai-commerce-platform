# ADR-008: Explicit Failure Handling

## Status

Accepted

## Context

The platform is a distributed system where failures are expected — network timeouts,
dependency unavailability, invalid inputs, AI model errors, and partial failures across
service boundaries. In distributed systems, the most dangerous failures are not the ones
that crash loudly but the ones that fail silently: a retry that produces a duplicate, a
fallback that returns stale data without signaling it, a timeout that is swallowed and
treated as success.

Without explicit failure handling, components accumulate implicit behavior: undocumented
retries, silent catches, fallbacks that are invisible to callers. This makes the system
unpredictable and difficult to operate — failures are discovered through symptoms rather
than through the component that caused them. It also violates ADR-006: a silent fallback
is implicit behavior that alters the system's response without any declaration at the
component boundary.

Every component must define its failure modes at design time and handle them explicitly.
Callers must be able to reason about what a component does when it fails.

## Decision

Every component defines its failure modes and recovery behavior explicitly at design
time. Failures are surfaced to callers in a form they can reason about. Silent failures,
implicit fallbacks, and swallowed exceptions are not permitted.

## Rationale

**Benefits**

- Callers can reason about what a component does when it fails — there is no hidden
  behavior to discover at runtime.
- Failures surface at the component that causes them, not as symptoms in an unrelated
  part of the system.
- Explicit retry and fallback declarations make the system's resilience behavior
  auditable and testable.

**Tradeoffs**

- Defining failure modes upfront requires more design effort than catching exceptions
  broadly and handling them generically.
- Explicit failure contracts add surface area to component interfaces.

**Assumptions**

- The cost of debugging silent failures in a distributed system — invisible fallbacks,
  swallowed exceptions, undocumented retries — exceeds the cost of declaring failure
  behavior explicitly upfront.
- Failure modes can be identified clearly enough at design time to be declared without
  requiring exhaustive enumeration of every possible error condition.

**Risks**

- Overly broad failure declarations may obscure meaningful distinctions between failure
  modes, reducing the value of the explicit contract.
- Teams under time pressure may swallow exceptions or add silent fallbacks
  incrementally, each instance appearing harmless in isolation.

## Alternatives Considered

**Generic exception handling** — catch all exceptions at a top-level handler and return
a generic error response. Rejected because it makes all failure modes indistinguishable
to callers and hides the component that caused the failure.

**Resilience-first fallbacks** — apply silent fallbacks broadly to maximize availability.
Rejected because silent fallbacks produce responses that callers cannot distinguish from
successful ones, making the system's actual state invisible and violating ADR-006.

## Consequences

### Positive

- Failure behavior is auditable and testable at every component boundary.
- Callers can make informed decisions based on the failure mode surfaced, rather than
  guessing at the cause of a degraded response.
- Silent failures cannot propagate undetected across service boundaries.

### Negative

- Every component must define and maintain its failure contract, adding ongoing design
  and documentation overhead.
- Explicit failure surfaces require consumers to handle more distinct error cases than
  a generic error response would.

### Risks

- If failure contracts are defined too broadly, they provide no more information than
  a generic error, defeating the purpose.
- Explicit failure handling in high-throughput paths must be designed carefully to avoid
  performance overhead from exception construction and propagation.

## Mandatory Rules

- Every component must document its failure modes and the behavior it guarantees under
  each.
- Failures must be surfaced explicitly to callers — never swallowed, hidden behind a
  default, or converted to a success response.
- Fallback behavior, if any, must be explicit and visible to the caller, not applied
  silently.
- Retry logic must be intentional, bounded, and declared at the component that applies
  it.

## Allowed Changes

- The form of failure declaration — typed exceptions, result types, error envelopes —
  may evolve without a new ADR, provided the principle of explicit failure surfacing
  is preserved.
- The granularity of failure modes declared by a component may be calibrated to its
  risk profile, provided no component is permitted to swallow failures entirely.

## Forbidden Changes

- A component may not silently swallow exceptions or convert failures to success
  responses.
- Implicit fallbacks — where a component returns a degraded result without signaling
  it to the caller — are not permitted.
- Retry logic may not be added to a component without an explicit declaration of its
  bounds and conditions.
- This ADR may not be superseded by one that permits silent failure handling on the
  grounds of resilience or availability.

## Validation Criteria

- Code review must reject any catch block that swallows an exception without surfacing
  it to the caller in an explicit form.
- Every component that applies retry logic must have a documented and tested bound on
  the number of retries and the conditions under which they apply.
- Every fallback path must be covered by a test that verifies the caller receives an
  explicit signal that a fallback occurred.

## Related Documents

- [Vision](../VISION.md)
- [ADR-006: Explicit over Implicit](006-explicit-over-implicit.md)

## Future Revisions

- If AI components introduce failure modes that do not map cleanly to the explicit
  failure contract model — probabilistic degradation, partial outputs — revisit whether
  a different failure declaration form is needed for AI-specific components.
- If a high-throughput path proves that explicit failure propagation has unacceptable
  performance cost, revisit whether a narrow exception is warranted for that path,
  with explicit justification.
