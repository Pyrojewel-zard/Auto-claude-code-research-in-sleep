---
name: audit
description: Use when a legacy caller invokes the old ARIS audit entry.
argument-hint: "[branch-or-frozen-package] — mode: branch-evidence|frozen-artifact"
---

# `/audit` compatibility router

`/audit` is retained only for compatibility. Route the request to the
canonical `/research-audit` entry and do not implement a second Anti or
reviewer path here.

```text
/audit <branch-or-frozen-package> — mode: branch-evidence|frozen-artifact
  -> /research-audit <branch-or-frozen-package> — mode: branch-evidence|frozen-artifact
```

The canonical entry owns the Zotero evidence audit, ARIS promotion gate,
vendored Anti-Autoresearch provenance, frozen-input hashes, isolated Codex
review, and `REVIEW_UNAVAILABLE` fail-closed behavior.
