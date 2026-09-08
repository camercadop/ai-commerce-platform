# ADR-009: Least Privilege by Default

## Status

Accepted

## Context

The platform is composed of multiple services, AI components, external integrations,
and infrastructure dependencies. Each component requires access to resources — databases,
message queues, secrets, external APIs, other services — to fulfill its responsibilities.
The natural tendency under time pressure is to grant broad access: a service that needs
read access to one table gets access to the entire database; a component that needs one
secret gets access to the entire secrets store.

Broad permissions are not just a security risk — they are an architectural one. A
component with more access than it needs can affect parts of the system it was never
designed to interact with. When something goes wrong — a bug, a compromised dependency,
a misconfiguration — the blast radius is determined by the access that was granted, not
the access that was intended.

Least privilege is not a hardening step applied after the system is built. It is a
design constraint that shapes how components are structured, what interfaces they expose,
and what resources they are permitted to reach.

## Decision

Every component is granted only the access required to fulfill its declared
responsibilities. Broad permissions are not permitted as a convenience or a default.
Access scope is defined at design time alongside the component's responsibilities, not
granted incrementally as needs arise.

## Rationale

**Benefits**

- The blast radius of a compromised or misbehaving component is bounded by its declared
  access scope, not by the broadest permission that was convenient to grant.
- Access grants are auditable: every component's permissions are traceable to a declared
  responsibility.
- Components cannot accidentally affect parts of the system outside their intended scope.

**Tradeoffs**

- Defining precise access scopes requires more upfront design effort than granting broad
  permissions and narrowing later.
- Access grants must be maintained as component responsibilities evolve, adding ongoing
  operational overhead.

**Assumptions**

- The cost of a security or operational incident caused by over-permissioned components
  exceeds the cost of defining precise access scopes upfront.
- Component responsibilities can be declared clearly enough to derive a precise access
  scope without requiring exhaustive enumeration of every resource.

**Risks**

- Access scopes defined too narrowly may block legitimate operations, leading to
  pressure to broaden them without proper review.
- Access grants that are not reviewed when responsibilities change may drift out of
  alignment with the principle over time.

## Alternatives Considered

**Broad permissions with runtime enforcement** — grant wide access and rely on
application-level checks to prevent misuse. Rejected because application-level checks
are bypassable by bugs, compromised dependencies, or misconfiguration. The permission
boundary must exist at the infrastructure level, not only in application code.

**Incremental permission grants** — start with minimal access and add permissions as
needs arise. Rejected as a process because it produces undeclared, undocumented access
growth that is difficult to audit and tends to accumulate without review.

## Consequences

### Positive

- Security incidents and operational failures are contained to the access scope of the
  affected component, limiting their impact on the rest of the system.
- Access grants are explicit, auditable, and tied to declared responsibilities.
- Components cannot reach resources outside their intended scope, even under failure
  conditions.

### Negative

- Defining and maintaining precise access scopes adds design and operational overhead
  compared to broad permission grants.
- Access scope reviews must be integrated into the change process for component
  responsibilities, adding a step that is easy to skip under time pressure.

### Risks

- If access scope reviews are not enforced as part of the change process, permissions
  will drift over time and the principle will erode silently.
- Overly narrow access scopes in critical paths may create operational bottlenecks that
  generate pressure to grant broad permissions as a workaround.

## Mandatory Rules

- Every component must declare the resources it requires access to as part of its
  design.
- No component may be granted access beyond what its declared responsibilities require.
- Broad or wildcard permissions are not permitted regardless of convenience or time
  pressure.
- Access grants must be reviewed whenever a component's responsibilities change.

## Allowed Changes

- The mechanism used to define and enforce access scopes — IAM policies, database
  roles, secret store policies — may evolve without a new ADR, provided the principle
  of least privilege is preserved.
- Access scopes may be refined to be more precise without a new ADR, provided they are
  not broadened beyond what the component's responsibilities require.

## Forbidden Changes

- No component may be granted broad permissions on the grounds that specific permissions
  are inconvenient to define.
- Access scope may not be expanded without a corresponding expansion of the component's
  declared responsibilities.
- This ADR may not be superseded by one that permits broad permissions as a default or
  convenience.

## Validation Criteria

- Every component must have a documented access scope that is reviewable independently
  of its implementation.
- Code and infrastructure review must reject permission grants that exceed the
  component's declared responsibilities.
- Access scope changes must be traceable to a corresponding change in the component's
  declared responsibilities.

## Related Documents

- [Vision](../VISION.md)
- [ADR-003: Security by Design](003-security-by-design.md)

## Future Revisions

- If the operational overhead of maintaining precise access scopes proves prohibitive
  at early stages, revisit whether a tiered approach — stricter scopes for
  high-sensitivity resources, broader scopes for low-sensitivity ones — is a justified
  calibration.
- If a service mesh or zero-trust network architecture is introduced, revisit whether
  transport-level identity can simplify access scope definitions without weakening the
  principle.
