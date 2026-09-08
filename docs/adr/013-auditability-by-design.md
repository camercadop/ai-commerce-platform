# ADR-013: Auditability by Design

## Status

Accepted

## Context

The platform handles operations with legal, financial, and compliance consequences:
payments are processed, orders are placed, and customer data is accessed. When
something goes wrong — a payment disputed, an order incorrectly modified, a customer
record accessed without authorization — the first question is always: who did this,
when, and through what path?

Without a governing principle, auditability is added reactively. A log line here
when a bug is hard to reproduce, a record there when a compliance question arises.
The result is coverage that reflects the failures that have already happened, not
the ones that are about to happen. Gaps are invisible until they become incidents
or regulatory findings.

The platform is also a distributed system where a single user-facing operation may
touch multiple services. Without a correlation identity that crosses service
boundaries, the audit trail is fragmented — each service has a partial record, but
no coherent picture of what happened exists.

Constraints:

- Financial operations — payment disputes and order corrections require a complete,
  trustworthy record of what happened and who authorized it.
- Distributed system — a single user-facing operation may touch multiple services;
  the audit trail must be coherent across service boundaries, not fragmented per
  service.
- Regulatory exposure — depending on jurisdiction, the platform may be required to
  demonstrate who accessed or modified specific data.

Architectural goals affected: accountability, debuggability, compliance, consumer
trust.

## Decision

Every operation that changes state is traceable after the fact. The system is
explainable — not just correct. Every operation has a declared actor and carries
a correlation identity that links it across service boundaries. This traceability
is part of the operation's correctness guarantee, not an optional logging concern.

## Rationale

**Benefits**

- Payment disputes and order corrections are resolvable from recorded facts, not
  from reproduction attempts or customer recollection.
- Compliance questions are answerable from system data without log archaeology.
- Accountability is structural — not dependent on developers remembering to add
  logging to sensitive paths.
- Cross-service operations are diagnosable end-to-end from a coherent trail, not
  from fragmented per-service records.

**Tradeoffs**

- Every state-changing operation carries the overhead of audit recording.
- Audit data accumulates and requires retention and access control governance.
- Correlation identity must be propagated across all service boundaries.

**Assumptions**

- The cost of not having an audit trail during a payment dispute or compliance audit
  exceeds the cost of recording it.
- Correlation identity can be reliably propagated across service boundaries.
- Audit records are immutable — once written, they are never modified or removed.

**Risks**

- Context propagation failing silently at service boundaries, producing audit records
  that cannot be attributed to the originating actor.
- Audit records themselves becoming a data exposure vector if not governed with
  the same access control as the data they describe.
- Over-auditing — recording so much that the signal is lost in noise, making the
  audit trail useless in practice.

## Alternatives Considered

**Application-level logging as audit trail** — rely on structured log lines with
context rather than a dedicated audit mechanism. Rejected because logs are
ephemeral, optimized for debugging rather than compliance, not queryable as
structured data, and do not participate in the operation's transaction — a log
line can be written for an operation that was subsequently rolled back.

**Selective auditing of high-risk operations** — audit only operations deemed
sensitive, decided per-operation by the developer. Rejected because "high-risk"
is subjective and changes as the system evolves. An operation that seems routine
today may acquire financial or compliance significance later. Gaps in the audit
trail are invisible until the missing record is needed.

**Per-service audit implementations** — each service owns its own audit mechanism
independently. Rejected because it produces inconsistent coverage, inconsistent
record formats, and fragmented trails for operations that cross service boundaries.
A payment dispute that touches three services requires a coherent trail, not three
independent ones.

## Consequences

### Positive

- Payment disputes, order corrections, and compliance questions are answerable
  from system data.
- Cross-service operations produce a coherent audit trail linked by correlation
  identity, not fragmented per-service records.
- Incident investigation starts from recorded facts, not from reproduction attempts.

### Negative

- Write amplification — every state change produces at least one additional write.
- Audit data requires retention policies, access control, and storage governance.
- Correlation identity must be propagated across every service boundary, adding a
  concern to every cross-service interaction.

### Risks

- Audit records containing sensitive data becoming a leak vector if not governed
  with the same access control as the data they describe.
- Context propagation failing silently at service boundaries, producing audit records
  that cannot be attributed to the originating actor.
- Audit storage becoming a performance bottleneck without appropriate retention and
  archival strategies.

## Mandatory Rules

- Every operation that changes state must produce a traceable record identifying
  who performed it, what was performed, and when.
- No operation may execute without a declared actor. System-initiated operations
  must use a declared system identity — anonymous or unattributed operations are
  not permitted.
- Correlation identity must be propagated across all service boundaries so that
  operations spanning multiple services produce a coherent, linked audit trail.
- Audit records are immutable. Once written, they may not be altered or removed.
- Audit data must be governed with the same access control as the data it describes.
  Access to an audit record must not exceed access to the operation it records.

## Allowed Changes

- Varying the detail level of audit records by operation category — more detail for
  destructive or financial operations, less for routine reads — provided every
  operation remains traceable to an actor, an action, and a time.
- Defining retention and archival policies that purge audit records after a declared
  period, provided the purge operation is itself audited.
- Extending audit records with additional context fields as operational or compliance
  needs evolve.

## Forbidden Changes

- State-changing operations that execute without producing a traceable record.
- Operations that execute without a declared actor.
- Altering or removing existing audit records.
- Dropping correlation identity at any service boundary.
- Audit records with weaker access control than the data they describe.
- This ADR may not be superseded by one that makes auditability optional or
  limited to a declared subset of operation types.

## Validation Criteria

- Every state-changing operation produces a traceable record attributable to a
  declared actor — verifiable by performing a state change and asserting a
  corresponding record exists with a non-anonymous actor.
- An operation attempted without a declared actor is rejected — verifiable by
  attempting an operation with no actor context and asserting it does not succeed.
- A single operation that spans multiple services produces audit records linked
  by a shared correlation identity — verifiable by tracing a cross-service
  operation and asserting correlation identity is consistent across all resulting
  records.
- Audit records cannot be altered or removed after creation — verifiable by
  asserting no interface exists through which an audit record can be modified
  or deleted.

## Related Documents

- [ADR-003: Security by Design](003-security-by-design.md)
- [ADR-005: Observability by Design](005-observability-by-design.md)
- [ADR-006: Explicit over Implicit](006-explicit-over-implicit.md)
- [ADR-008: Explicit Failure Handling](008-explicit-failure-handling.md)

## Future Revisions

- If the platform introduces read-auditing requirements — compliance scenarios where
  data access must be traced, not just state changes — extend this ADR or create a
  supplementary one. The current scope covers state changes only.
- If audit storage volume becomes a cost or performance concern, define a tiered
  retention strategy as a follow-up ADR without weakening the immutability and
  access control requirements.
