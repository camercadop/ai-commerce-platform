# ADR-014: Uniform Interface Contract

## Status

Accepted

## Context

The platform exposes multiple independent services, each built and evolved at
different times by different contributors. Without a governing principle, interfaces
diverge: one service structures its responses differently from another, error signals
are inconsistent across service boundaries, and conventions for communicating partial
results, failures, or bounded responses vary per service.

Interface inconsistency has compounding costs in a distributed system. A consumer —
whether an external client, an internal service, or an AI agent — must learn each
service's idiosyncrasies independently. Knowledge gained from integrating with one
service does not transfer to another. Shared client logic cannot be written because
there is no shared contract shape to write it against. Every new service integration
is a net-new learning cost.

ADR-002 establishes that every capability must have a published contract before
implementation. This ADR governs what all those contracts have in common. ADR-002
answers "does a contract exist?" — this ADR answers "do all contracts speak the
same structural language?"

Constraints:

- Multiple independent services — each service is built independently, creating
  natural pressure toward divergence.
- Multiple consumer types — external clients, internal services, and AI agents all
  depend on predictable interface structure to build reliable integrations.
- Evolvability — the platform adds new services over time; each must be immediately
  predictable to existing consumers without a new learning curve.

Architectural goals affected: consistency, developer experience, evolvability,
consumer trust.

## Decision

All interfaces the platform exposes follow the same structural rules. A consumer
who learns the structure of one service's interface can predict the structure of
any other. Structural rules are defined once at the platform level — no service
defines its own structural conventions.

Where a service cannot conform to the platform's structural rules, the deviation
is explicit, documented, and justified. Silent divergence is not permitted.

## Rationale

**Benefits**

- A consumer integrates once with the platform's structural conventions and applies
  that knowledge to every service — integration cost does not scale with the number
  of services.
- Shared client logic is possible because the structural contract is stable and
  consistent across all services.
- New services are immediately usable by existing consumers without a new learning
  curve — the structure is already known.
- Structural deviations are enumerable and visible — consumers know exactly where
  the uniform contract does not apply.

**Tradeoffs**

- Platform-level structural rules must be designed before the second service exists.
  This requires anticipating what all services will have in common.
- Some services may carry structural overhead that their specific use case does not
  require — uniformity takes precedence over per-service optimization.
- Changing the platform's structural rules is a breaking change for all consumers
  simultaneously.

**Assumptions**

- The set of structural rules is small and stable — it does not need to change
  frequently once established.
- Most services share enough in common that a uniform structure is achievable
  without forcing awkward conformance.
- Consumers benefit more from predictability than from per-service structural
  optimization.

**Risks**

- Structural rules designed too early, before enough services exist to validate
  them, may prove too rigid for legitimate future requirements.
- Exceptions accumulating over time until the uniform contract is uniform in name
  only.
- A structural rule that works for synchronous request-response interfaces may not
  apply cleanly to other interface types as the platform evolves.

## Alternatives Considered

**Per-service structural conventions** — each service defines its own response
structure, error format, and conventions based on its specific needs. Rejected
because it violates ADR-002's contract-first discipline — if every service defines
its own structure, there is no platform-level contract, only per-service ones.
Consumer integration cost scales linearly with the number of services.

**Structural conventions enforced by documentation only** — define the conventions
in a style guide and rely on code review to enforce them. Rejected because
documentation-only enforcement degrades over time, especially under deadline
pressure. Silent divergence is indistinguishable from intentional deviation without
a structural backstop.

## Consequences

### Positive

- Consumers learn the platform's structural contract once and apply it everywhere.
- Shared client utilities are possible and remain valid as new services are added.
- New services are immediately predictable to existing consumers.
- Structural deviations are explicit and enumerable — consumers are never surprised
  by undocumented divergence.

### Negative

- Platform-level structural rules add design overhead before the first service is
  complete.
- Services that would benefit from a different structure must conform or formally
  document a deviation.
- Breaking changes to the structural rules affect all consumers simultaneously,
  making evolution of the rules expensive once consumers exist.

### Risks

- Structural rules ossifying before enough real-world usage validates them, forcing
  awkward workarounds for legitimate cases.
- Exception creep — too many documented deviations eroding the uniformity until it
  is meaningless in practice.
- Structural rules that apply cleanly to synchronous interfaces proving insufficient
  as the platform introduces other interface types.

## Mandatory Rules

- Every interface the platform exposes must conform to the platform's structural
  rules. No service may define its own structural conventions.
- A consumer who knows the platform's structural rules must be able to interact with
  any service without learning service-specific structural behavior.
- Deviations from the platform's structural rules must be explicitly documented and
  justified. Silent divergence is not permitted.
- Structural rules are defined at the platform level and apply uniformly — no
  service is exempt on the grounds of its specific use case.

## Allowed Changes

- Evolving the platform's structural rules in a backward-compatible way — adding
  optional structure that existing consumers can ignore.
- Documenting explicit, justified exceptions for interface types that structurally
  cannot conform — provided exceptions are enumerable and visible to consumers.
- Versioning the structural rules if breaking changes become necessary, provided
  all services within a version are uniform.

## Forbidden Changes

- Services defining their own structural conventions independently of the platform
  rules.
- Silent deviations from the platform's structural rules — any exception must be
  documented and justified.
- Removing or weakening the platform's structural rules on the grounds that a
  specific service has unique requirements.
- This ADR may not be superseded by one that permits per-service structural
  conventions on the grounds of flexibility or optimization.

## Validation Criteria

- Every service interface conforms to the platform's structural rules — verifiable
  by a consumer using the same structural parsing logic against any service and
  asserting consistent behavior.
- Every documented deviation from the structural rules is explicitly justified and
  discoverable from a single location — verifiable by asserting no undocumented
  structural divergence exists across services.
- A new service added to the platform is immediately usable by a consumer familiar
  only with the platform's structural rules — verifiable by integrating a new
  service using only the platform-level structural contract.

## Related Documents

- [ADR-002: API-First Design](002-api-first-design.md)
- [ADR-006: Explicit over Implicit](006-explicit-over-implicit.md)

## Future Revisions

- If the number of documented exceptions grows beyond a threshold, revisit the
  structural rules to determine whether they are too rigid for the platform's
  actual interface diversity.
- If the platform introduces interface types beyond synchronous request-response
  — event streams, async callbacks — define how the uniformity principle applies
  to those interfaces, either as an extension of this ADR or as a supplementary one.
- If API versioning becomes necessary, define how multiple structural rule versions
  coexist without fragmenting the uniformity guarantee within each version.
