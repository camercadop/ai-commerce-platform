# ADR-007: Open for Extension

## Status

Accepted

## Context

The platform is designed to evolve. New business capabilities, AI integrations, payment
providers, and consumer types will be added over time. In a system that grows by
modification — where adding a new variant requires editing existing dispatch logic,
existing registries, or existing conditionals — every addition is a risk. Existing
behavior can be broken by a change that was only intended to add something new.

The alternative is a system designed so that new behavior can be added by introducing
new code, not by modifying existing code. This requires that extension points are
explicit and that the system discovers implementations rather than enumerating them.
When this principle holds, existing behavior is protected by default — it cannot be
broken by an addition.

This applies across the platform: new payment providers, new AI model adapters, new
notification channels, new event handlers, and new API consumers should all be addable
without modifying the components that orchestrate them.

## Decision

The platform is designed so that new behavior is added by introducing new
implementations, not by modifying existing orchestration logic. Extension points are
explicit. Implementations register themselves or are discovered at runtime. No existing
component needs to be modified to accommodate a new variant of an existing capability.

## Rationale

**Benefits**

- Existing behavior is protected by default — adding a new implementation cannot break
  existing ones because no existing code is modified.
- The set of implementations is open-ended; the platform can grow without accumulating
  conditional logic that enumerates every known variant.
- Extension points are explicit and auditable, making it clear where the system is
  designed to be extended.

**Tradeoffs**

- Registry-based dispatch requires more upfront design than a simple conditional. The
  extension point must be defined before the first implementation is added.
- Discovery mechanisms add indirection that can make the flow of control less obvious
  to a reader unfamiliar with the pattern.

**Assumptions**

- The set of implementations for any given capability will grow over time. If a
  capability will only ever have one implementation, the extension point adds overhead
  without benefit.
- The cost of modifying existing dispatch logic — regression risk, coordination overhead,
  review burden — exceeds the cost of defining explicit extension points upfront.

**Risks**

- Poorly defined extension points may be too narrow to accommodate legitimate new
  implementations without modification, defeating the purpose.
- Registry-based dispatch can obscure which implementations are active at runtime,
  making debugging harder without adequate observability.

## Alternatives Considered

**Hardcoded conditional dispatch** — use if/elif or match statements to select behavior
based on a named type or variant. Rejected because every new variant requires modifying
existing dispatch logic, creating regression risk and coupling the orchestrator to the
full set of known implementations.

**Inheritance-based extension** — extend behavior by subclassing existing components.
Rejected as a general dispatch mechanism because it couples the extension to the
internal structure of the base class and does not support runtime discovery of new
implementations without modifying the base.

## Consequences

### Positive

- New implementations can be added without touching existing orchestration logic,
  eliminating a class of regression risk.
- The platform's extension points are explicit and documented, making the intended
  growth paths visible.
- Dispatch logic does not accumulate over time as new variants are added.

### Negative

- Extension points must be designed upfront, before the second implementation exists.
  This requires anticipating where the system will grow.
- Registry-based dispatch adds indirection. Tracing the flow of control requires
  understanding the registry mechanism, not just reading the call site.

### Risks

- An extension point defined too narrowly will require modification when a new
  implementation does not fit the existing contract, undermining the principle.
- If registry discovery is not covered by observability signals, it becomes difficult
  to determine which implementations are active at runtime.

## Mandatory Rules

- Dispatch logic — selecting which implementation to use based on a type, mode, or
  variant — must use a registry or discovery mechanism, not a hardcoded conditional.
- Adding a new implementation of an existing capability must not require modifying the
  component that uses it.
- Extension points must be explicit and documented — implicit extension through
  monkey-patching or runtime mutation is not permitted.

## Allowed Changes

- The specific mechanism used to implement a registry or discovery pattern may evolve
  without a new ADR, provided the principle of extension without modification is
  preserved.
- An extension point may be redesigned if its contract proves too narrow to accommodate
  legitimate implementations, provided existing implementations are migrated and the
  new contract is explicit.

## Forbidden Changes

- No component may use if/elif chains or match statements to dispatch behavior based
  on a named type or variant where a registry-based mechanism is possible.
- An extension point may not be removed or made non-extensible without a new ADR that
  supersedes this one.
- This ADR may not be superseded by one that permits hardcoded dispatch logic on the
  grounds of simplicity.

## Validation Criteria

- Code review must reject any if/elif or match statement that dispatches behavior based
  on a named type, mode, or variant in a context where a registry-based mechanism
  applies.
- Every declared extension point must have at least two implementations or a documented
  justification for why a single implementation is expected to remain stable.
- Adding a new implementation of any registered capability must be verifiable without
  modifying any existing file outside the new implementation itself.

## Related Documents

- [Vision](../VISION.md)
- [ADR-006: Explicit over Implicit](006-explicit-over-implicit.md)

## Future Revisions

- If a capability proves to have a genuinely fixed set of implementations that will
  never grow, revisit whether the extension point overhead is justified or whether a
  simpler dispatch mechanism is appropriate for that specific case.
- If registry-based dispatch proves difficult to observe at runtime, revisit the
  observability requirements for extension points in conjunction with ADR-005.
