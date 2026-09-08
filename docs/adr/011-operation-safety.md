# ADR-011: Operation Safety

## Status

Accepted

## Context

The platform handles operations with real-world consequences: payments are charged,
orders are placed, inventory is reserved, and AI tool calls trigger external actions.
These operations execute in an environment where retries are not exceptional — they are
structural. HTTP clients retry on timeout, message queues guarantee at-least-once
delivery, users resubmit when the UI is slow, and infrastructure failures trigger
automatic reconnection and retry.

When a write operation is not safe to retry, every one of these scenarios becomes a
source of data corruption: a payment charged twice, a duplicate order, an inventory
reservation applied twice, an AI tool call executed multiple times for the same intent.

The platform cannot rely on infrastructure to guarantee exactly-once delivery. That
guarantee does not exist in distributed systems. The application layer must be the
authority on what has already been processed.

Constraints:

- Distributed system — retries occur at every layer: HTTP, message queues, service
  orchestration, and client-side UI.
- High-consequence operations — duplicate payments, orders, and inventory mutations
  have direct financial and operational impact.
- AI tool calls — an AI agent retrying a failed tool call must not produce duplicate
  side effects in external systems.
- Multiple consumer types — external clients, internal services, and AI agents all
  submit write operations and may all retry independently.

Architectural goals affected: correctness, data integrity, operational resilience,
consumer trust.

## Decision

Write operations are designed to be safe to execute more than once with the same
logical intent. Submitting the same operation multiple times produces the same outcome
as submitting it exactly once. The system is the authority on what has already been
processed — consumers do not need to implement their own deduplication to achieve
correct behavior.

This applies across all write surfaces: HTTP endpoints, message queue consumers, AI
tool call handlers, and internal service-to-service calls.

## Rationale

**Benefits**

- Retries at any layer — network, client, queue, AI agent — are safe by design, not
  by luck.
- Consumers implement simple retry logic without needing to solve deduplication
  themselves.
- Background processing is resilient: at-least-once delivery is sufficient without
  requiring exactly-once infrastructure.
- Payment and order operations can be retried aggressively without risk of duplication.

**Tradeoffs**

- Every write operation must consider its idempotency strategy at design time, not
  as an afterthought.
- Deduplication mechanisms — idempotency keys, unique constraints, state guards —
  require storage and add implementation complexity.
- Not all operations are naturally idempotent; some require explicit mechanisms.

**Assumptions**

- At-least-once delivery is the baseline guarantee from all infrastructure layers.
- The cost of duplicate payments, orders, or AI actions exceeds the cost of
  implementing idempotency mechanisms.
- Most write operations can be made safe through design choices — state guards, unique
  constraints, upsert semantics — without dedicated deduplication infrastructure.

**Risks**

- False deduplication: incorrectly identifying a legitimate new operation as a retry
  of a previous one, causing valid requests to be silently rejected.
- Idempotency key storage growing without retention policies.
- Side effect deduplication failing silently at async boundaries, leaving the system
  in a state where the primary operation succeeded but its side effects did not.

## Alternatives Considered

**Exactly-once delivery infrastructure** — invest in infrastructure that guarantees
each message is processed exactly once. Rejected because exactly-once delivery is
a theoretical impossibility in distributed systems; all practical implementations
are at-least-once with application-level deduplication. Client-side retries (user
resubmissions, HTTP retries) still produce duplicates at the application boundary
regardless of queue guarantees.

**Client-side deduplication only** — require consumers to implement their own
deduplication; the server processes every request as unique. Rejected because it
shifts the same problem to every consumer independently, including AI agents and
third-party integrations that are not under the platform's control. The server is
the only reliable authority on what has already been processed.

**Idempotency only for payment operations** — apply operation safety selectively to
high-risk operations. Rejected because the boundary between "high-risk" and
"low-risk" shifts as the system evolves. An operation that seems low-risk today
may acquire financial or compliance significance later. Uniform application is
cheaper than case-by-case risk assessment.

## Consequences

### Positive

- Retries at any layer are safe — no duplicate records, charges, or side effects.
- AI agents can retry failed tool calls without producing duplicate external actions.
- Background task processing is resilient without exactly-once infrastructure.
- Consumers trust that submitting the same request twice is always safe.

### Negative

- Every write operation requires an explicit idempotency strategy during design.
- Deduplication records require storage and retention management.
- State transition guards add code to every operation that moves a resource between
  states.

### Risks

- Idempotency key scoping errors causing false deduplication — legitimate operations
  rejected as duplicates.
- Deduplication record retention becoming unbounded if not governed (see ADR-008:
  failures must be explicit, not silently truncated).
- Side effect deduplication at async boundaries being incomplete — a retried operation
  that skips already-executed side effects may leave the system inconsistent if the
  original side effect also failed.

## Mandatory Rules

- Write operations must be safe to execute more than once with the same logical intent.
  Duplicate submissions must not produce duplicate state changes, charges, or side
  effects.
- State transitions must validate current state before applying. A transition that has
  already been applied must be recognized and handled explicitly — not blindly
  reapplied.
- Operations that are not naturally idempotent must implement an explicit idempotency
  mechanism: idempotency keys, unique constraints, or conditional writes.
- AI tool call handlers must deduplicate at the handler boundary. A retried tool call
  with the same logical intent must not re-execute external actions already performed.
- Duplicate detection must produce an explicit, informative response. Silent success
  that hides the fact that the operation was already processed is not permitted
  (per ADR-006 and ADR-008).

## Allowed Changes

- Choosing different idempotency strategies per operation type — natural idempotency,
  idempotency keys, unique constraints, conditional writes — based on the operation's
  characteristics.
- Defining retention policies for deduplication records, provided the retention window
  exceeds the maximum expected retry window for that operation type.
- Exempting purely additive, append-only operations (audit records, event log entries)
  from deduplication requirements where duplication has no correctness consequence.
- Implementing side effect deduplication at the side effect boundary rather than at
  the primary operation level, when the side effect executor has its own deduplication
  capability.

## Forbidden Changes

- Write operations that produce duplicate records, charges, state transitions, or side
  effects when retried.
- State transitions applied without checking current state.
- Silent success responses on duplicate detection — the caller must be able to
  distinguish a first-time success from a deduplicated one.
- Relying solely on consumer-side deduplication for correctness. The server must be
  the authority on what has been processed.
- This ADR may not be superseded by one that limits operation safety to a subset of
  operation types on the grounds of perceived risk.

## Validation Criteria

- Every write endpoint, when called twice with the same logical request, produces the
  same final state and does not create duplicate records — verifiable by integration
  tests that submit each write operation twice.
- Payment and order operations reject or return the existing result on duplicate
  submission — verifiable by asserting response equality between first and duplicate
  submissions.
- State transition operations reject or gracefully handle attempts to apply an
  already-completed transition — verifiable by testing transition replay.
- AI tool call handlers produce no duplicate external actions when the same tool call
  is submitted more than once — verifiable by testing retry scenarios with side effect
  observation.
- Background tasks produce correct results when delivered more than once — verifiable
  by executing each task type twice with the same payload.

## Related Documents

- [ADR-006: Explicit over Implicit](006-explicit-over-implicit.md)
- [ADR-008: Explicit Failure Handling](008-explicit-failure-handling.md)

## Future Revisions

- If the platform introduces event sourcing, revisit how idempotency interacts with
  event replay — event streams have their own deduplication semantics.
- If AI agents evolve to manage multi-step tool call sequences, define how operation
  safety applies to partial completion of a sequence where individual steps may be
  retried independently.
- If idempotency key storage becomes a scaling concern, evaluate time-windowed key
  stores or distributed deduplication strategies without weakening the server-side
  authority requirement.
