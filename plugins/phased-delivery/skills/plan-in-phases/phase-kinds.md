# Planning each kind of phase

Each kind of phase settles different decisions, reads different code and
rests on different assumptions. Name that phase's assumptions in its file,
check them against the code, and record what could not be checked yet (see
Assumptions and Notes in [phase-file-template.md](phase-file-template.md)).

**Skeleton.**
- Settle: where every new file lives, how it is named, how it is registered
  or wired (entry points, routes, configuration, build and package files), and
  how it stays inactive until cutover (flag, unregistered, unreachable).
- Read: the project's layout and conventions, the registration and build
  files the new pieces join, and neighbors of the same kind to copy their
  pattern.
- Assumptions to check: where things belong, that the wiring point exists
  and works as believed, that inactive code really has no effect.
- Done when: the files exist and are wired, the project builds and its
  existing tests pass, behavior is unchanged, and the test harness can drive
  the real entry point the outcome tests will use.

**Roles and interfaces.**
- Settle every contract here: signatures, inputs and outputs, data formats,
  error cases at trust boundaries, and which component owns what. Later phases
  consume these contracts; they do not invent new ones.
- Read: every existing interface the new code calls or is called by, the real
  data formats it reads or writes, and existing types it should reuse.
- Assumptions to check: what existing callers and callees actually accept and
  return, how data really looks (sample it where possible), that the
  responsibility split covers every requirement once.
- Done when: the whole flow traces end to end through mock bodies returning
  fixed or pass-through data, the contracts are written in the code
  itself, not only in the plan, and every outcome test is written and runs
  through the mocks, marked expected-fail where the mocks cannot produce the
  outcome yet.

**Internals.**
- Settle, per stage, one behavior behind a fixed contract: the algorithm or
  approach, the existing code it reuses, edge cases it handles, which
  outcome tests it makes pass, and any other test it needs under
  [test-planning.md](test-planning.md).
- Read: the contract and mock it replaces, the code it calls, existing
  helpers that already do part of the job, and the tests nearby.
- Assumptions to check: that the contract is sufficient for the real logic,
  that existing helpers behave as their names suggest, performance or data
  size limits that matter.
- Done when: the mock is replaced, the outcome tests it names have their
  expected-fail marks removed and pass, its other tests pass, and the
  contract is unchanged. If the real logic needs a different contract, that
  is a revision of the interfaces phase, not a local change.

**Integration and cutover.**
- Settle: how the new work is switched on, what old code, configuration and
  data it replaces and how those are retired or migrated, the order of
  switching so nothing is left half-working, how to undo it if required, and
  which documentation changes.
- Read: every caller of what is being replaced, configuration and deployment
  files, existing migrations, and the documentation that describes the old
  behavior.
- Assumptions to check: that every user of the old path is found, that data
  written by older versions is handled, that nothing outside the repository
  depends on what is removed.
- Done when: the new path is the only path, the old one is gone or
  deliberately kept with a reason, every outcome test passes with no
  expected-fail mark left, the full test suite passes within its time
  budget, and the documentation matches.
