# ADR-004: Cloud Agnosticism

## Status

Accepted

## Context

The platform is built on cloud infrastructure. Cloud providers offer managed services
that reduce operational burden: compute, storage, messaging, databases, AI APIs, and
more. These services are convenient and often well-integrated, but they come with
proprietary interfaces, data formats, and behavioral contracts that are specific to a
single provider.

A platform that couples its core logic directly to provider-specific interfaces becomes
difficult to migrate, test, and reason about independently of the cloud environment.
Provider lock-in is not just a commercial risk — it is an architectural one. When
business logic, data access, and integration code are written against provider APIs
directly, the cost of changing providers or running the system outside a cloud
environment becomes prohibitive.

The platform must be able to evolve its infrastructure choices — including cloud
provider — without rewriting its core logic. It must also be testable and runnable
in local and CI environments without requiring live cloud access.

## Decision

The platform's core logic is independent of any specific cloud provider's interfaces.

Cloud provider services are accessed through abstractions that the platform defines.
The implementation of those abstractions may use any provider, but the core logic
depends only on the abstraction. No provider-specific SDK, API, or data format may
appear in application or domain code.

## Rationale

**Benefits**

- Core logic can be tested without live cloud access, using local or in-process
  implementations of the abstractions.
- The platform can migrate infrastructure components — storage, messaging, compute —
  without modifying business logic.
- Provider-specific behavior is isolated to adapter implementations, making it
  auditable and replaceable.

**Tradeoffs**

- Defining abstractions over cloud services requires upfront design effort and
  introduces an indirection layer.
- Some provider-specific capabilities may not map cleanly to a general abstraction,
  requiring deliberate decisions about what to expose.
- Abstraction boundaries must be maintained with discipline; they erode easily under
  time pressure.

**Assumptions**

- The cost of provider lock-in — migration difficulty, testing friction, commercial
  dependency — exceeds the cost of maintaining abstraction boundaries.
- Useful abstractions can be defined over the cloud services the platform depends on
  without losing the capabilities the platform requires.

**Risks**

- Abstractions that are too thin may leak provider-specific behavior into core logic
  indirectly.
- Abstractions that are too thick may fail to expose capabilities that the platform
  legitimately needs, leading to workarounds that bypass the boundary.

## Alternatives Considered

**Direct provider SDK usage throughout** — use provider SDKs wherever convenient and
accept the lock-in. Rejected because it makes the platform untestable without live
cloud access and couples business logic to infrastructure choices that should be
independently replaceable.

**Multi-cloud compatibility layer** — build a compatibility layer that supports multiple
providers simultaneously. Rejected as a goal in itself: the principle is not to support
multiple providers at once, but to ensure that switching providers does not require
rewriting core logic.

## Consequences

### Positive

- The platform can be developed and tested locally without cloud credentials or live
  services.
- Infrastructure decisions — which provider, which managed service — can be revisited
  without architectural rework.
- Provider-specific behavior is contained and visible, making it easier to evaluate
  the cost of a migration.

### Negative

- Every cloud dependency requires a defined abstraction before it can be used in
  application code.
- Maintaining abstraction boundaries requires ongoing discipline, especially as
  provider SDKs evolve.

### Risks

- Abstraction boundaries may erode incrementally — one direct SDK call at a time —
  without a visible threshold being crossed.
- A poorly designed abstraction may be worse than no abstraction: it adds indirection
  without providing portability.

## Mandatory Rules

- No provider-specific SDK, client library, or API interface may appear in application
  or domain code.
- Every cloud service dependency must be accessed through an abstraction defined by
  the platform.
- Abstraction implementations must be replaceable without modifying the code that
  depends on them.

## Allowed Changes

- The specific cloud provider or managed service used to implement an abstraction may
  change without a new ADR, provided the abstraction contract is preserved.
- New cloud service dependencies may be introduced, provided they are accessed through
  a platform-defined abstraction from the start.
- The form of the abstraction — interface style, granularity — may evolve without a
  new ADR, provided provider-specific details remain isolated to implementations.

## Forbidden Changes

- No provider-specific interface may be used directly in application or domain code,
  regardless of convenience or performance justification.
- An abstraction may not be removed in favor of direct provider access without a new
  ADR that supersedes this one.
- This ADR may not be superseded by one that permits provider-specific interfaces in
  core logic.

## Validation Criteria

- Code review must reject any import of a provider-specific SDK or client in
  application or domain code.
- Every cloud service dependency must have a corresponding platform-defined abstraction
  that can be implemented without live cloud access.
- Local and CI environments must be able to run the full application without cloud
  credentials.

## Related Documents

- [Vision](../VISION.md)

## Future Revisions

- If a cloud provider offers a capability with no reasonable abstraction — where the
  abstraction would be so thin it provides no portability — revisit whether the
  capability should be used at all or whether the abstraction boundary should be
  redefined.
- If the platform commits to a single provider for a sustained period, revisit whether
  the abstraction overhead remains justified or whether a lighter-weight boundary
  convention is sufficient.
