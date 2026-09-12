---
name: research
description: Use when a legacy caller invokes the old combined ARIS research entry.
argument-hint: "[topic-or-application-draft]"
---

# `/research` compatibility router

`/research` is retained for callers of the old combined entry. It is not a
second workflow and is not part of the reduced `pyrojewel-research` profile.

Route the input without performing retrieval here:

- a topic, question, or method goes to `/autoresearch-topic`;
- a readable grant/project application draft goes to `/autoresearch-proposal`.

The four canonical entries own all behavior:

```text
/autoresearch-topic or /autoresearch-proposal
  -> Zotero semantic search -> complete branch autoresearch
  -> /research-audit -> promoted synthesis -> /research-write
```

Do not add a source selector, call a second scholarly search backend, or copy
the branch, coverage, promotion, or audit rules into this compatibility file.
