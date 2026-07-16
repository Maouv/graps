# Handoff — Graps Next Session

## Current State (2026-07-15)
- Project status: `done`. All 4 tasks complete, 181 tests pass, ruff+mypy clean.
- Branch: `experimental`, pushed to origin.
- pos.py: 0 errors.

## User's Pending Request
User wants to restructure project — "banyak bug dan ga sesuai dengan kemauan saya layout dan struktur project nya."
User will pass a reference file next session showing desired layout/structure.
Approach: compare current → desired, identify gaps, plan changes, confirm scope before executing.

## Backlog (7 items)
- BUG-0002: Symlink bypass in credential check (open)
- REF-0001: SSH key files not in credential set (open)
- REF-0002: FEAT-0018 multi-language module resolution (open)
- REF-0003: Browser E2E tests for click contract (open)
- REF-0004: Minify frontend assets (open)
- REF-0005: CSRF token mechanism (open)
- FEAT-BL-001: FEAT-0019 enrichment rejection pipeline (open)

## Key Files
- Plan: `plan/experimental-graps/`
- Source: `graps/` (scanner, server, ai, storage, cli)
- Tests: `tests/` (10 test files, 181 tests)
- Frontend: `graps/public/` (index.html, app.js, app.css, icon/)
- Work dir: `/workspace/graps/`
- Venv: `.venv/`

## Context for Next Session
1. Load plan-os + ponytail skills
2. `cd /workspace/graps && git pull`
3. Read SYSTEM_PROMPT.md
4. Wait for user to pass reference file
5. Compare current structure vs desired, present gap analysis
6. Confirm scope before executing changes
