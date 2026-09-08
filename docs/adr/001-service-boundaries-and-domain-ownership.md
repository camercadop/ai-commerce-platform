# ADR-001: Service Boundaries and Domain Ownership

## Status

Accepted

## Context

The platform covers multiple distinct business capabilities: identity, catalog, commerce,
inventory, payments, search, media, notifications, AI, and integrations. These capabilities
have different data models, consistency requirements, scaling profiles, and rates of change.

Without explicit boundaries, these capabilities tend to collapse into a shared codebase and
a shared database. That coupling makes it impossible to evolve, scale, or replace one
capability without affecting others. It also makes ownership ambiguous — any part of the
system can read or write any data, so no part of the system is fully responsible for its
correctness.

The platform must support independent evolution of capabilities, clear data ownership, and
the ability to extract a capability into a separate deployment when complexity warrants it.

## Decision

The platform is structured as a set of services, each owning a single business domain.

A service is the sole authority over its domain data. No other service may read from or
write to another service's data store directly. Cross-service data access must go through
the owning service's API or through events it publishes.

Domain boundaries are established first. Physical deployment boundaries — whether a
capability runs as a separate process — are a separate concern and may be deferred until
complexity or scaling requirements justify the operational cost.

## Rationale

**Benefits**

- Each service can evolve its data model, storage technology, and internal logic
  independently without coordinating with other services.
- Ownership is unambiguous: one service is responsible for the correctness and consistency
  of its domain data.
- Services can be scaled, replaced, or extracted independently.

**Tradeoffs**

- Queries that span multiple domains require either API composition or event-driven
  denormalization. There is no cross-service join.
- Eventual consistency is the norm for data that crosses service boundaries.
- More coordination is required when a business operation touches multiple domains.

**Assumptions**

- Domain boundaries can be identified clearly enough upfront to avoid frequent boundary
  changes. Boundary changes are expensive once data and APIs are established.
- The team accepts the operational overhead of multiple services in exchange for
  independent evolvability.

**Risks**

- If domain boundaries are drawn incorrectly, refactoring them later requires data
  migration, API versioning, and consumer coordination.
- Distributed operations across service boundaries are harder to reason about and test
  than local transactions.

## Alternatives Considered

**Modular monolith with shared database** — a single deployable with internal module
boundaries but a shared data store. Rejected because it does not enforce data ownership:
any module can bypass another module's logic and access its data directly, which defeats
the purpose of the boundary.

**Shared database with schema-per-service** — separate schemas within one database instance.
Rejected because schema-level isolation is a convention, not an enforced boundary. It
provides no protection against cross-schema queries and couples all services to the same
database lifecycle.

## Consequences

### Positive

- Service boundaries create a natural forcing function for good API design.
- Data ownership makes it straightforward to reason about consistency within a domain.
- Independent deployability becomes possible without architectural rework.

### Negative

- Cross-domain reads require API calls or event-driven projections, adding latency and
  complexity compared to a local join.
- Distributed transactions across services require explicit patterns (outbox, saga) rather
  than database-level atomicity.

### Risks

- Incorrect initial boundaries may require expensive restructuring once consumers depend
  on the existing API contracts.
- Teams may be tempted to bypass service boundaries for convenience, especially under
  time pressure.

## Mandatory Rules

- A service must never directly access another service's database or internal data store.
- Every cross-service data dependency must be satisfied through the owning service's
  published API or published events.
- Domain boundaries must be established before any shared infrastructure or data model
  is introduced.

## Allowed Changes

- A service may be split into two services if its domain grows complex enough to warrant
  it, provided the new boundary is clean and existing consumers are migrated.
- Multiple services may share the same physical deployment (process) as a temporary
  measure, as long as their data stores and APIs remain separate.
- Internal implementation details of a service — its storage technology, internal models,
  business logic — may change freely without requiring a new ADR.

## Forbidden Changes

- No service may read from or write to another service's data store, regardless of
  convenience or performance justification.
- No shared domain model or shared database schema may be introduced across service
  boundaries.
- Two services may not be merged into one unless a new ADR is written that supersedes
  this one and justifies the consolidation.

## Validation Criteria

- Code review must reject any import or database query that crosses a service boundary.
- Each service must have its own isolated data store configuration with no shared
  connection strings or ORM models across services.
- Integration between services must be traceable to either an API call or a consumed event.

## Related Documents

- [Vision](../VISION.md)

## Future Revisions

- If the operational cost of running multiple services proves prohibitive at early stages,
  revisit whether a modular monolith with strict module boundaries is a better fit for
  the current team size and deployment context.
- If a domain boundary proves consistently wrong — requiring frequent cross-boundary
  transactions — revisit the boundary definition before adding more workarounds.
