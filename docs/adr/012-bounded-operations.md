# ADR-012: Bounded Operations

## Status

Accepted

## Context

The platform is a distributed system serving multiple consumers: external clients,
internal services, and AI agents. Operations that have no declared upper bound on
time, size, or resource consumption are a structural risk in this environment. A
catalog query that returns every product, an AI agent that issues unbounded search
requests, an order history export with no size limit, or an external API call with
no timeout — each of these can exhaust resources, block downstream services, and
degrade the platform for all consumers simultaneously.

Unbounded operations are a category of silent failure. The system does not crash
visibly; it becomes slow, unresponsive, or unavailable. This violates ADR-008:
a degradation that produces no explicit signal is an implicit failure.

AI agents introduce a distinct concern not present in traditional systems. An agent
may issue queries programmatically, at high frequency, with no human judgment
applied to result set size or request rate. Without enforced bounds, an agent
operating on the catalog or order history can produce workloads that no human
consumer would generate.

Constraints:

- Distributed system — resource exhaustion in one service propagates to its
  consumers through latency and timeout cascades.
- AI consumers — agents issue operations programmatically without inherent
  size or rate awareness.
- Multiple consumer types — external clients, internal services, and AI agents
  share the same infrastructure and must not starve each other.
- External dependencies — third-party APIs, payment providers, and AI model
  endpoints have their own latency profiles and failure modes.

Architectural goals affected: reliability, predictability, fairness, operational
stability.

## Decision

Every operation in the platform has explicit, declared limits on result size, input
size, and time. Unbounded operations are not permitted. When a limit is reached,
the operation fails explicitly rather than degrading silently or truncating results
without signaling it.

This applies across all operation types: API endpoints, internal service calls,
AI tool calls, message queue consumers, and calls to external dependencies.

## Rationale

**Benefits**

- Resource consumption per operation is predictable — capacity planning is possible
  because operations have known upper bounds.
- No single consumer — including an AI agent — can monopolize shared infrastructure.
- Failures from exceeding limits are immediate and informative, not slow degradations
  discovered minutes later.
- External dependency timeouts are explicit, making failure modes visible and
  testable rather than dependent on infrastructure defaults.

**Tradeoffs**

- Legitimate large operations — full catalog exports, bulk order processing — require
  explicit chunked or paginated design rather than naive unbounded loops.
- Limit values must be chosen, documented, and maintained as the system evolves.
- AI agents must be designed to handle paginated responses and explicit rejections
  rather than assuming they can retrieve everything in one call.

**Assumptions**

- Reasonable upper bounds exist for every operation — no operation legitimately
  requires unbounded resources.
- Consumers, including AI agents, can handle paginated results and explicit size
  rejections.
- Static limits per operation category are sufficient; per-request negotiation is
  not needed.

**Risks**

- Limits set too conservatively reject valid operations and erode consumer trust.
- Limits set too generously fail to protect shared resources when it matters most.
- AI agents that are not designed to handle pagination or size rejections will fail
  in ways that are hard to diagnose without adequate observability (ADR-005).

## Alternatives Considered

**Soft limits with warnings** — operations that exceed thresholds log warnings and
continue, only hard-failing at extreme values. Rejected because a warning that is
ignored is a silent failure (ADR-008). Soft limits become the effective limits in
practice, and the hard limit is never reached because the system has already
degraded.

**Per-consumer resource quotas** — each consumer gets a resource budget and can
use it however they want within that budget. Rejected because quotas do not prevent
a single operation from consuming the entire budget in one request. Per-operation
bounds are still required regardless of whether quotas also exist.

**Infrastructure-level throttling only** — rely on API gateways, load balancers,
and database connection pools to enforce limits. Rejected because infrastructure
throttling operates on connections and request rates, not on result set sizes or
semantic operation bounds. An unbounded query that returns within the connection
limit is still an unbounded query.

## Consequences

### Positive

- The platform's worst-case resource consumption per operation is known and bounded.
- AI agents receive explicit, actionable rejections rather than silent degradation
  or timeouts.
- Capacity planning is tractable — bounded operations have predictable resource
  profiles.
- External dependency failures surface at a declared timeout, not as indefinite
  hangs.

### Negative

- Large legitimate operations require chunked or paginated design — no convenience
  path for retrieving everything at once.
- Limit values must be chosen and maintained — an ongoing configuration concern.
- AI agent integrations must be designed to handle pagination and size rejections
  from the start.

### Risks

- Poorly chosen limits causing false rejections that push consumers toward
  workarounds that bypass the bounds entirely.
- Limit configuration becoming scattered across services without a single
  discoverable location per service (ADR-006).
- AI agents that retry rejected operations without reducing request size, producing
  retry storms that amplify the original problem.

## Mandatory Rules

- Every operation must declare explicit limits on result size, input size, and time
  before it is considered complete.
- No operation may return results to a consumer without signaling when those results
  have been bounded. A consumer must always be able to determine whether they
  received the full result or a bounded subset.
- Every interaction with an external dependency must have a declared time limit.
  No operation may wait indefinitely for an external system to respond.
- Exceeding any declared limit must produce an explicit failure signal (per ADR-008)
  that identifies which limit was exceeded. Silent truncation is not permitted.

## Allowed Changes

- Adjusting limit values as operational experience reveals appropriate thresholds,
  without a new ADR.
- Defining tiered limits for different operation contexts, provided all tiers have
  explicit declared ceilings.
- Adding new limit categories as new operation types are introduced.

## Forbidden Changes

- Operations with no declared limit on result size, input size, or time.
- Returning a bounded result to any consumer — including AI agents — without
  signaling that the result was bounded.
- Allowing any interaction with an external dependency to execute without a
  declared time limit.
- Silent truncation of results that exceed a limit.
- This ADR may not be superseded by one that permits unbounded operations for
  specific consumer types on the grounds of convenience.

## Validation Criteria

- Every operation that returns a collection signals explicitly when the result has
  been bounded — verifiable by requesting a result set that exceeds the declared
  limit and asserting an explicit signal in the response.
- Every operation that exceeds its input size limit produces an explicit failure
  response — verifiable by submitting inputs that exceed the declared limit and
  asserting the failure signal.
- Every interaction with an external dependency fails explicitly when the declared
  time limit is exceeded — verifiable by simulating an unresponsive dependency and
  asserting an explicit failure within the declared time budget.
- No operation in the system has an undeclared limit — verifiable by requiring
  each operation's limits to be documented alongside its definition.

## Related Documents

- [ADR-005: Observability by Design](005-observability-by-design.md)
- [ADR-006: Explicit over Implicit](006-explicit-over-implicit.md)
- [ADR-008: Explicit Failure Handling](008-explicit-failure-handling.md)

## Future Revisions

- If AI agents evolve to negotiate result set sizes dynamically, define how
  agent-declared bounds interact with server-enforced maximums — the server
  maximum always wins, but agents may request smaller bounds.
- If streaming responses become common for large exports, define how streaming
  interacts with bounded operations as a follow-up ADR.
- If per-consumer resource quotas become necessary beyond per-operation limits,
  define a supplementary ADR for quota management that builds on this one.
