# Retrospective

## Milestone: v1.0 — MVP

**Shipped:** 2026-11-27
**Phases:** 5 | **Plans:** 15

### What Was Built
The whole of `planning/PLAN.md`: live prices, trading, charts, AI copilot and one-command Docker run.

### What Worked
- Vertical slices, each with its own unit tests
- Browser checks on temporary databases

### What Was Inefficient
- Phase 1 used 11 plans; later phases used one each and were built outside GSD, so no verification reports exist
- An old Docker volume and shared Docker names caused fixes after release

### Key Lessons
- Give each branch its own Docker image, container and volume names
- Handle data saved by earlier versions

## Cross-Milestone Trends

| Milestone | Phases | Plans |
|-----------|--------|-------|
| v1.0 | 5 | 15 |
