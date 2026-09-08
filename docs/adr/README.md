# Architecture Decision Records (ADRs)

This directory contains the Architecture Decision Records for this project.

## Rules

1. Numbering is sequential, zero-padded to 3 digits (`001`, `002`, ...).
2. Filename format: `{NNN}-{kebab-case-title}.md` (e.g., `001-modular-monolith-architecture.md`).
3. All ADRs live in `docs/adr/`.
4. Sections that don't apply may be omitted — but `Context`, `Decision`, `Rationale`, and `Consequences` are always required.
5. ADRs are immutable once accepted. To change a decision, create a new ADR that supersedes the old one (update the old one's status to `Superseded by ADR-XXX`).
6. Language: English, concise, no filler. Written for a developer joining the project 6 months from now.
7. An ADR should document one decision — not bundle multiple unrelated choices.
8. An ADR can only reference ADRs with a lower number (previous decisions). Never reference future ADRs.
9. ADRs document architectural principles and decisions — not implementation details. Technology-specific choices (frameworks, file layouts, code patterns) belong in separate implementation ADRs or documentation.
10. Every section must operate at the level of the decision being documented. Content that belongs to a lower level of abstraction — implementation details, operational processes, specific technologies — does not belong in any section of an ADR.
11. Foundational ADRs must explicitly protect themselves from being eroded by future superseding ADRs that narrow the principle to a specific concern. This must be stated in the Forbidden Changes section.

## When to Write an ADR

An ADR is warranted when:

- The decision affects how the system is structured or how components interact.
- Reversing it would require significant effort.
- There are meaningful alternatives that were deliberately rejected.

An ADR is NOT warranted for:

- Tooling choices or configuration.
- Decisions contained within a single file or module with no external impact.
- Anything reversible with trivial effort.

## Writing Guidelines

### Status

One of: `Proposed`, `Accepted`, `Deprecated`, `Superseded by ADR-XXX`.

### Context

Describe the current situation and the problem being solved. Answer these questions:

- What problem exists?
- Why does it matter?
- What constraints exist?
- What architectural goals are affected?

Do not propose solutions here — only describe the problem space.

### Decision

Clear, concise statement of what was decided. One, two or three paragraphs maximum. A reader should understand the decision without reading any other section.

### Rationale

Explain why this decision was selected. Include:

- **Benefits** — what we gain.
- **Tradeoffs** — what we accept as a cost.
- **Assumptions** — what must remain true for this decision to hold.
- **Risks** — what could go wrong with our assumptions.

### Alternatives Considered

Each alternative as a named option with a brief explanation of why it was rejected. Focus on the disqualifying reason, not a full analysis.

### Consequences

Structure as three subsections:

- **Positive** — what improves as a result.
- **Negative** — what gets worse or becomes harder.
- **Risks** — what could go wrong while living with this decision.

### Mandatory Rules

Non-negotiable constraints that must be followed while this ADR is active. These are enforceable — if someone violates them, it's a bug.

### Allowed Changes

What modifications or extensions are permitted without writing a new ADR.

### Forbidden Changes

What is explicitly prohibited while this ADR is active. Violating these requires a new ADR that supersedes this one.

### Validation Criteria

How to verify compliance. Prefer automated checks (linting rules, CI checks, grep commands) over subjective review criteria. Each criterion should be verifiable by someone unfamiliar with the decision's history.

### Related Documents

Links to previous ADRs and other documentation. Only reference ADRs with a lower number. Only include ADRs that are actually cited in the document's reasoning — do not list all previous ADRs.

### Future Revisions

Known triggers that would cause this decision to be revisited. Written as conditions: "If X happens, revisit this ADR."

## Template

See [ADR_BASE_TEMPLATE.md](ADR_BASE_TEMPLATE.md) for the copy-paste skeleton.
