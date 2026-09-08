# ADR-005: Observability by Design

## Status

Accepted

## Context

The platform is a distributed system composed of multiple services, event streams,
external integrations, and AI components. In a distributed system, failures are not
exceptional — they are expected. Services degrade, dependencies become slow, AI
components produce unexpected outputs, and user-facing errors occur without a clear
single point of origin.

Without deliberate observability, diagnosing failures in a distributed system requires
guesswork. A request that fails may have touched five services; without correlated
traces, structured logs, and metrics at each boundary, the cause is invisible. Debugging
becomes a manual, time-consuming process that depends on tribal knowledge rather than
instrumented evidence.

Observability is not a monitoring dashboard added after the system is built. It is the
property of a system that makes its internal state inferable from its external outputs.
A system that is not observable cannot be reliably operated, debugged, or improved.

The platform must be designed so that any failure, degradation, or unexpected behavior
can be diagnosed from the system's own outputs — without requiring access to internal
state or manual intervention.

## Decision

Observability is a design requirement, not an operational add-on. Every component is
designed to emit the signals — logs, metrics, and traces — needed to understand its
behavior and diagnose failures from the outside.

No component may be considered complete if its behavior cannot be inferred from its
observable outputs.

## Rationale

**Benefits**

- Failures can be diagnosed from system outputs without requiring access to internal
  state or live debugging sessions.
- Correlated signals across service boundaries make it possible to trace a request
  end-to-end through the distributed system.
- Degradation and anomalies can be detected proactively rather than discovered through
  user reports.
- Observability signals serve as a feedback mechanism for understanding how the system
  behaves under real conditions.

**Tradeoffs**

- Instrumenting every component adds implementation effort and requires consistent
  standards across services.
- Emitting high-cardinality signals at scale has storage and cost implications that
  must be managed.
- Defining what to observe requires design judgment; over-instrumentation produces
  noise, under-instrumentation produces blind spots.

**Assumptions**

- The cost of operating an unobservable distributed system — in debugging time, incident
  duration, and undetected degradation — exceeds the cost of building observability in
  from the start.
- Useful observability signals can be defined per component without requiring a
  centralized observability team to instrument each one.

**Risks**

- Inconsistent instrumentation across components produces gaps that are only discovered
  during incidents.
- Sensitive data may be inadvertently included in logs or traces if observability
  instrumentation is not reviewed against security constraints.
- Observability signals that are never acted on create operational overhead without
  benefit.

## Alternatives Considered

**Observability as an operational concern** — instrument the system after it is built,
using infrastructure-level monitoring (host metrics, load balancer logs). Rejected
because infrastructure-level signals do not provide the application-level context needed
to diagnose failures in a distributed system. They can detect that something is wrong
but not why.

**Centralized instrumentation via a service mesh or sidecar** — delegate observability
to infrastructure rather than requiring each component to emit signals. Rejected as a
standalone solution because infrastructure-level tracing does not capture
application-level semantics: business events, AI model behavior, domain errors, and
decision points that are invisible to a network-level observer.

## Consequences

### Positive

- Any failure or degradation in the system can be diagnosed from its observable outputs
  without requiring live access or manual investigation.
- Correlated traces across service boundaries make end-to-end request diagnosis
  tractable.
- Observability signals provide a continuous feedback loop for understanding real system
  behavior.

### Negative

- Every component must be instrumented as part of its implementation, not as a
  follow-up task.
- Consistent signal formats and correlation identifiers must be maintained across all
  services.

### Risks

- Observability instrumentation that includes sensitive data violates ADR-003. Every
  signal must be reviewed against data protection constraints.
- Gaps in instrumentation are invisible until a failure occurs in an uninstrumented path.

## Mandatory Rules

- Every component must emit structured logs, metrics, and trace spans sufficient to
  diagnose its own failures from the outside.
- Trace context must be propagated across all service boundaries so that a request can
  be correlated end-to-end.
- Observability signals must never include secrets, credentials, or sensitive personal
  data.
- A component is not considered complete until its observable outputs are sufficient to
  diagnose its failure modes.

## Allowed Changes

- The specific tooling, formats, and backends used to collect and store observability
  signals may evolve without a new ADR, provided the principle of design-time
  instrumentation is preserved.
- The granularity and cardinality of signals emitted by a component may be calibrated
  to its operational risk profile, provided no component is exempt from the principle
  entirely.

## Forbidden Changes

- Observability instrumentation may not be deferred to a post-launch phase on the
  grounds that the component is not yet in production.
- A component may not omit trace propagation on the grounds that it is internal or
  low-risk.
- Observability signals may not include secrets, credentials, or sensitive personal
  data, regardless of the diagnostic value.
- This ADR may not be superseded by one that treats observability as an operational
  concern separate from component design.

## Validation Criteria

- Every service must emit structured logs with a consistent format and a correlation
  identifier that links to the originating request.
- Every cross-service call must propagate trace context, verifiable by tracing a
  synthetic request end-to-end through the system.
- No observability signal may contain secrets or sensitive personal data (automatable
  via log scanning and secret detection tools).

## Related Documents

- [Vision](../VISION.md)
- [ADR-003: Security by Design](003-security-by-design.md)

## Future Revisions

- If AI components produce outputs that are not captured by standard log/metric/trace
  signals, revisit whether additional signal types are needed to make AI behavior
  observable.
- If the cost of high-cardinality signals at scale becomes prohibitive, revisit the
  granularity rules to define a tiered approach based on component risk profile.
