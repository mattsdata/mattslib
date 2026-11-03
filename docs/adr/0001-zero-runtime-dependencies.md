# ADR-0001: Zero runtime dependencies

- **Status:** Accepted
- **Date:** 2026-11-03

## Context

`mattslib` is meant to be dropped into any project — scripts, services, data jobs, legacy
codebases — without friction. Every third-party dependency it pulled in would become a
dependency of every project that uses it, with version conflicts, security patching and
supply-chain risk attached.

Mature libraries exist for several of these concerns (`tenacity` for retries, `structlog` for
logging, `pydantic-settings` for config, `cachetools` for caching).

## Decision

The library uses the **Python standard library only** at runtime. Development tools
(pytest, ruff, mypy) are optional `dev` extras and never installed by users.

## Consequences

**Positive**
- Installs anywhere Python 3.10+ runs, including locked-down corporate environments.
- No transitive version conflicts; tiny attack surface.
- Each utility is small enough to read in a few minutes.

**Negative / trade-offs**
- Fewer features than the specialised libraries above. When a project needs, for example,
  full validation of nested models, it should use `pydantic-settings` instead of
  `mattslib.config`.
- We own the maintenance of this code.

**Revisit when** a utility would need to reimplement a large, security-sensitive component
(for example HTTP or cryptography). Such modules go behind an optional extra
(`pip install mattslib[http]`) with their own ADR.
