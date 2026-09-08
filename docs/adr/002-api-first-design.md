# ADR-002: API-First Design

## Status

Accepted

## Context

The platform exposes multiple business capabilities across independent services. External
clients, internal services, and AI agents all need to interact with these capabilities.

Without a clear contract-first discipline, APIs tend to be designed as implementation
artifacts — shaped by internal data models, database schemas, or framework conventions
rather than by the needs of their consumers. This produces brittle integrations, undocumented
behavior, and APIs that are difficult to version or evolve without breaking consumers.

The platform must support multiple consumer types (external clients, service-to-service
calls, AI tool calls) and must be able to evolve its internal implementation without
breaking those consumers.

## Decision

Every business capability must be accessible through a well-defined, versioned API contract.

The contract is defined first, independently of implementation. The implementation must
conform to the contract, not the other way around. A capability that has no published
contract does not exist from the perspective of any consumer.

API contracts are the authoritative interface between a service and its consumers.
Internal implementation details — data models, storage, business logic — are never
exposed directly.

## Rationale

**Benefits**

- Consumers depend on a stable contract, not on implementation internals. Internal changes
  do not break consumers as long as the contract is honored.
- Contracts can be reviewed, versioned, and validated independently of the code that
  implements them.
- AI agents and external integrations can interact with the platform through the same
  contracts as any other consumer, with no special access paths.

**Tradeoffs**

- Defining the contract before implementation requires upfront design effort.
- Contract versioning adds overhead when breaking changes are necessary.
- Keeping contracts and implementations in sync requires discipline and tooling.

**Assumptions**

- Consumer needs can be understood well enough upfront to design a useful contract.
- The cost of upfront contract design is lower than the cost of fixing broken integrations
  after the fact.

**Risks**

- A poorly designed contract that does not meet consumer needs will require a breaking
  version change, which is expensive once consumers exist.
- Contract drift — where the implementation diverges from the published contract — can
  go undetected without automated validation.

## Alternatives Considered

**Implementation-first APIs** — design the API by exposing what the implementation
produces. Rejected because it couples consumers to internal data models and makes
refactoring the implementation a breaking change.

**Internal direct access for trusted consumers** — allow service-to-service calls to
bypass the API and access internal data directly. Rejected because it violates ADR-001
(domain ownership) and creates hidden coupling that is invisible to contract consumers.

## Consequences

### Positive

- Service internals can be refactored freely without affecting consumers, as long as the
  contract is preserved.
- API contracts serve as living documentation that is always accurate by definition.
- Versioning is explicit and deliberate rather than accidental.

### Negative

- Breaking changes require a new contract version and a migration path for existing
  consumers.
- Contract-first design requires more upfront investment than writing an endpoint and
  seeing what it returns.

### Risks

- If contract validation is not automated, implementation drift will go undetected until
  a consumer breaks.
- Over-versioning — creating new versions for non-breaking changes — adds unnecessary
  complexity.

## Mandatory Rules

- Every capability exposed to any consumer must have a published API contract before
  implementation begins.
- No consumer may access a service's internals directly — all access goes through the
  published contract.
- Breaking changes to an existing contract require a new versioned contract. The old
  version must remain available until all consumers have migrated.

## Allowed Changes

- Non-breaking additions to an existing contract (new optional fields, new endpoints)
  do not require a new version.
- Internal implementation may change freely as long as the published contract continues
  to be honored.
- Contract format and tooling may evolve without a new ADR, provided the contract-first
  principle is preserved.

## Forbidden Changes

- No capability may be made available to consumers through any path other than a
  published API contract.
- No internal data model, database schema, or implementation detail may be exposed
  directly as part of a contract.
- A contract version may not be modified in a breaking way once consumers depend on it.

## Validation Criteria

- Every service endpoint must have a corresponding contract definition that predates or
  accompanies its implementation.
- Contract definitions must be versioned and stored alongside the service code.
- Automated contract validation must be in place to detect drift between the contract
  and the implementation.

## Related Documents

- [Vision](../VISION.md)
- [ADR-001: Service Boundaries and Domain Ownership](001-service-boundaries-and-domain-ownership.md)

## Future Revisions

- If internal service-to-service communication proves too costly to route through full
  API contracts, revisit whether a lighter-weight internal contract format is appropriate
  for private service interfaces.
- If contract tooling evolves significantly, revisit the validation criteria to take
  advantage of improved automation.
