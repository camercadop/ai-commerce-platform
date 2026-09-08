# ADR-003: Security by Design

## Status

Accepted

## Context

The platform handles sensitive data across multiple domains: customer identity, payment
information, order history, and AI-mediated interactions. It is a distributed system with
multiple services, external integrations, event streams, storage systems, and AI components
— each representing a potential attack surface.

Security failures in software systems rarely stem from a single missing control. They
typically result from security being treated as a concern to be addressed after
functionality is built: a gateway added in front, a permission check bolted onto an
existing endpoint, secrets stored as an afterthought. This produces a system where
security is uneven, implicit, and fragile.

A production platform must treat security as a design constraint that shapes every
component from the beginning — not a layer applied on top. This means:

- **Access control**: every request is authenticated and authorized at the layer that
  processes it, with no implicit trust between components.
- **Data protection**: sensitive data is protected at rest and in transit, and only
  exposed to components that have a legitimate need for it.
- **Secrets management**: credentials, tokens, and keys are never hardcoded, logged, or
  stored in plaintext. Their lifecycle is managed explicitly.
- **Input validation**: all inputs are validated at the boundary where they enter the
  system, regardless of their origin.
- **Audit and non-repudiation**: security-relevant events are logged in a way that
  supports forensic investigation and compliance.
- **Dependency security**: third-party dependencies are tracked and evaluated as part of
  the system's attack surface.
- **Threat awareness**: security implications are considered during design, not discovered
  during incidents.

The platform must treat security as a structural property of the system, not as a
perimeter defense.

## Decision

Security is a design constraint, not a layer. Every component is designed with its
security responsibilities defined upfront, not retrofitted after functionality is built.

No component may defer its security responsibilities to another component, and no
capability may be built without its security implications being considered at design time.

## Rationale

**Benefits**

- No single point of failure: a compromised or misconfigured component does not expose
  the entire system.
- Security responsibilities are explicit and auditable at every component boundary.
- Sensitive data, secrets, and access control are consistently managed across all parts
  of the system, not just at the perimeter.
- Security issues are caught during design rather than discovered during incidents.

**Tradeoffs**

- Applying security constraints at every component adds design and implementation
  overhead compared to a single perimeter check.
- Consistent enforcement across many components requires shared standards and discipline.
- Secrets lifecycle management and dependency tracking require ongoing operational effort.

**Assumptions**

- The cost of a security breach — data exposure, unauthorized operations, regulatory
  consequences — exceeds the cost of building security in from the start.
- Security responsibilities can be defined clearly enough per component to be enforced
  consistently without becoming a bottleneck.

**Risks**

- Inconsistent enforcement across components can create gaps that are difficult to detect
  until exploited.
- Security overhead, if not designed carefully, can become a performance bottleneck in
  high-throughput paths.
- Dependency vulnerabilities may go undetected without automated tracking.

## Alternatives Considered

**Perimeter security only** — enforce security controls at the API gateway and trust all
internal traffic. Rejected because it creates implicit trust between internal components,
leaving data stores, event streams, and internal services unprotected if the perimeter
is bypassed or compromised.

**Security as a post-launch phase** — build functionality first and harden it later.
Rejected because retrofitting security into an existing distributed system is
disproportionately expensive and produces uneven coverage. Data exposure and access
control gaps discovered after launch are significantly harder to remediate.

**Service mesh with mutual TLS** — delegate internal security to a service mesh.
Rejected as a standalone solution because it addresses transport-level identity but does
not cover data protection, secrets management, input validation, or audit. It is a
complement to this principle, not a replacement.

## Consequences

### Positive

- The system remains secure even if a single component is misconfigured or compromised.
- Security responsibilities are explicit, reviewable, and testable at every component
  boundary.
- Sensitive data, secrets, and access decisions are consistently managed across the
  entire system.
- Security issues surface during design and development rather than in production.

### Negative

- Applying security constraints at every component requires more upfront design and
  implementation effort.
- Secrets lifecycle management, dependency tracking, and audit log coverage require
  ongoing operational discipline.
- Policy changes must be applied consistently across multiple components rather than
  in a single location.

### Risks

- Inconsistent application of security standards across components creates gaps that
  are difficult to detect without systematic review.
- Over-engineering security controls in low-risk internal paths adds complexity without
  proportional benefit.

## Mandatory Rules

- Every component must enforce its own access control independently, regardless of the
  request's origin or what upstream components may have already validated.
- Sensitive data must be protected at rest and in transit and must not be exposed beyond
  the component that owns it.
- All inputs must be validated at the boundary where they enter a component, regardless
  of their origin.
- Security-relevant events — failed authentication, denied authorization, invalid input,
  secrets access — must be logged at the component where they occur.

## Allowed Changes

- The specific mechanisms used to fulfill each security dimension (authentication
  protocols, secret storage backends, dependency scanning tools, audit log formats)
  may evolve without a new ADR, provided the principle of upfront security design
  is preserved.
- The scope and depth of security controls applied to a component may be calibrated
  to its risk profile, provided no component is exempt from the principle entirely.

## Forbidden Changes

- Security responsibilities may not be removed from a component on the grounds that
  another component already handles them.
- A capability may not be shipped without its security implications having been evaluated
  at design time.
- Secrets, credentials, or keys may never appear in source code, logs, or plaintext
  storage.
- This ADR may not be superseded by one that reduces security to a perimeter concern.

## Validation Criteria

- No secrets or credentials may appear in source code or version control history
  (automatable via secret scanning tools).
- Every component that handles requests must have at least one test that verifies access
  control enforcement independently of upstream components.
- Security-relevant events must produce log entries verifiable in isolation from each
  component, without relying on gateway or middleware logs.

## Related Documents

- [Vision](../VISION.md)

## Future Revisions

- If a service mesh is introduced, revisit whether transport-level mutual TLS can
  simplify service-to-service authentication without weakening the broader security
  principles defined here.
- If regulatory or compliance requirements are introduced, revisit audit logging and
  data protection rules to ensure they meet the required standard.
