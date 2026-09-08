# Guidelines

How-to references for common development tasks in this project.

## When to Write a Guideline

A guideline is warranted when:

- A recurring implementation pattern needs to be applied consistently across the codebase.
- The correct approach is not obvious from the code alone.
- Developers need step-by-step instructions to implement something correctly.

A guideline is NOT warranted for:

- Architectural decisions — those belong in `docs/adr/`.
- One-off or rarely repeated tasks.
- Anything already self-evident from the existing code.

## Structure

A guideline document must follow this structure:

1. Brief description of what the document covers.
2. Step-by-step instructions with code examples.

## Rules

- Filename: `kebab-case.md` (e.g., `writing-repositories.md`).
- Written in English, concise, task-oriented. No background theory — link to the relevant ADR instead.
- Code examples must be minimal and runnable.
- After adding a new guideline, add it to the index below.

## Index

- [api-design.md](api-design.md) — Response envelope, versioning, validation, pagination.
- [domain-module.md](domain-module.md) — How to create a new domain module.
- [error-handling.md](error-handling.md) — Domain exceptions, HTTP mapping, fallbacks, retry bounds.
- [event-design.md](event-design.md) — Event envelope, naming, versioning, idempotent consumers.
- [writing-logs.md](writing-logs.md) — Log levels, formatting, security events, sensitive data.
- [writing-models.md](writing-models.md) — UUID PKs, timestamps, field comments, indexes, relationships.
- [writing-tests.md](writing-tests.md) — Test layers, dependency injection, fixtures, fakes.
