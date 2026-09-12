---
name: audit
description: Use when a frozen ARIS artifact package needs an independent Anti-Autoresearch audit before delivery.
argument-hint: "[frozen-artifact-directory]"
---

# Audit

This Claude-compatible entry delegates to the Codex canonical contract at
`skills/skills-codex/audit/SKILL.md`. Use it for a frozen proposal, paper,
research branch, code, or results package. It resolves the Anti engine from
ARIS's vendored snapshot, uses a fresh isolated reviewer, preserves
`REVIEW_UNAVAILABLE` as blocked, and records the ARIS gate plus append-only
obligations.
