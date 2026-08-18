# Entry-point discovery for component registration

- **Date:** 2026-08-19 (moved here from ADR 005, which carried this as a non-template "Deferred
  extension" section since it was frozen; captured originally during the ADR 005 session)
- **Trigger:** ADR 005 (component loading and plugin registration model) explicitly deferred
  entry-point discovery out of its implementation freeze
- **Status:** open
- **Affected:** ADR 005

Entry-point discovery is explicitly deferred and is not part of the ADR 005 implementation freeze.

Before implementing entry points, a separate ADR must define:

- registration conflict policy for same-name components from different modules/packages;
- whether registries stay name-only or move to module-qualified identifiers;
- deterministic precedence and override rules;
- operator visibility/auditability of auto-discovered components.
