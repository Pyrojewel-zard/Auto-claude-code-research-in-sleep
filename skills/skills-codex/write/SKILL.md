---
name: write
description: Use when a legacy caller invokes the old ARIS writing entry.
argument-hint: "[research-workspace] — mode: proposal|paper"
---

# `/write` compatibility router

`/write` is retained only for compatibility. Route the request to the
canonical `/research-write` entry and do not draft from this file. The
canonical entry owns promoted-only evidence, `OBLIGATIONS.md`, proposal/paper
language boundaries, `WRITING_CLAIMS.md`, freeze, and the final
`/research-audit` handoff.

```text
/write <research-workspace> — mode: proposal|paper
  -> /research-write <research-workspace> — mode: proposal|paper
```

If the workspace has no promoted branch, return to
`/autoresearch-topic` or `/autoresearch-proposal`; never create a second
promotion rule here.
