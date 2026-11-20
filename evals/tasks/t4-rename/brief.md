# Phase 01: Rename the phase reviewer directions

Implement with the implement-in-phases skill; do not build from this file
without it. Model tiers map to models in [models.md](models.md).
Status: planned
Before: the phase review directions are in
`plugins/phased-delivery/skills/implement-in-phases/phase-reviewer.md`.
After: they are in `phase-review.md` in the same directory, with identical
content, and every reference to the old name points to the new one.

## Assumptions
- Verified: the only reference to `phase-reviewer` in the repository
  outside `plan/` is the markdown link on line 66 of
  `plugins/phased-delivery/skills/implement-in-phases/SKILL.md`:
  `[phase-reviewer.md](phase-reviewer.md)` (checked with a recursive search
  for `phase-reviewer` over the whole repository).
- Verified: `phase-reviewer.md` itself links only to
  `../plan-in-phases/model-selection.md`, which still resolves from the same
  directory after the rename (checked in `phase-reviewer.md`).
- Verified: `plugins/phased-delivery/skills/plan-in-phases/plan-reviewer.md`
  is a different file (the plan reviewer) and is not renamed (checked in
  `plan-in-phases/SKILL.md`, which links to it).

## Stages

| Stage | Goal | Tier | Order | Status |
| --- | --- | --- | --- | --- |
| 01.1 | Rename phase-reviewer.md to phase-review.md | small | first | planned |

## 01.1 Rename phase-reviewer.md to phase-review.md

Goal:            `phase-reviewer.md` is renamed to `phase-review.md` with
                 unchanged content, and no file outside `plan/` mentions
                 `phase-reviewer` any more.
Context:         Read while planning:
                 - `plugins/phased-delivery/skills/implement-in-phases/phase-reviewer.md`
                   (the file to rename; its heading "Phase reviewer
                   directions" is prose, not the file name, and stays).
                 - `plugins/phased-delivery/skills/implement-in-phases/SKILL.md`,
                   section "3. Review the phase", line 66:
                   `[phase-reviewer.md](phase-reviewer.md) unchanged and its inputs filled in, on`
Contracts:       The new path
                 `plugins/phased-delivery/skills/implement-in-phases/phase-review.md`.
Files:           plugins/phased-delivery/skills/implement-in-phases/phase-reviewer.md (removed)
                 plugins/phased-delivery/skills/implement-in-phases/phase-review.md (new)
                 plugins/phased-delivery/skills/implement-in-phases/SKILL.md
Work:            1. Rename the file with `mv` (not git); its content does
                    not change.
                 2. In `SKILL.md` line 66, change both the link text and the
                    link target to `phase-review.md`:
                    `[phase-review.md](phase-review.md)`. Leave the rest of
                    the line and paragraph as they are, without rewrapping.
                 3. Search the whole repository, excluding `plan/`, for
                    `phase-reviewer`; there must be no matches.
External inputs: none
Done when:       - `phase-review.md` exists with exactly the old content and
                   `phase-reviewer.md` does not exist.
                 - A recursive search for `phase-reviewer` outside `plan/`
                   finds nothing.
                 - Every relative markdown link in `plugins/phased-delivery`
                   and `README.md` points to an existing file.
Out of scope:    `plan-reviewer.md` and every mention of it; the words
                 "phase reviewer" or "reviewer" in prose; any other wording,
                 wrapping or formatting.
Model basis:     J0 F1 R0 C0 K0 P0 V0 = 1 -> small

## Notes
- 2026-11-19: Renamed so the file names the activity, like
  `stage-builder.md` names the builder's directions.
