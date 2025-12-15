# Twin-Turbo Workflow Rules

## Phase 1: Ingestion & Planning (The Huddle)
- Orchestrator embeds query and checks L3 Memory (Chroma).
- Orchestrator generates/updates Repo Map.
- Agents (Claude & Codex) coordinate in `HUDDLE.md` before coding.

## Phase 2: The Sprint (Parallel Execution)
- Thread A (Claude): Checks out `feature/backend`. Reads `SKILLS.md`.
- Thread B (Codex): Checks out `feature/frontend`. Reads `SKILLS.md`.
- Constraint: If an agent is stuck for > 60s, the Orchestrator interrupts it.

## Phase 3: The Merge & Cross-Review
- Orchestrator attempts to merge `feature/frontend` and `feature/backend` into `dev`.
- Cross-Review: Claude reviews Codex's code diff; Codex reviews Claude's code diff.
- Refinement: Issues trigger "Fix Tickets" in `activeContext.md`.

## Phase 4: Learning (The Skillbook Update)
- Build errors/resolutions update `SKILLS.md` to prevent recurrence.
