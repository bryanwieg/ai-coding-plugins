# Plan the tests

Tests prove the change does what it was for, not that its pieces run. Small
targeted tests can each pass while the whole fails; a run-through of the
real program catches that. Derive the tests from the outcomes settled in the
grill (see [grill.md](grill.md)), and plan fewer, larger tests.

- **Outcome tests come first.** Each outcome gets at least one test that
  drives the real entry point (command, API, hook, UI) through the real
  components and checks what a user would observe: output, files written,
  exit status, state left behind. Cover the outcome's main failure paths
  too. Every outcome has a test; the plan is done when they all pass.
- **Integration tests** only for a contract or trust boundary the outcome
  tests do not exercise. Use real components; substitute only what lies
  outside the repository (network, paid or remote services), with a local
  stand-in.
- **Unit tests are the exception.** Plan one only where a run-through
  cannot reach the cases cheaply: a parser with many input shapes, money,
  a security check, a state machine, a tricky algorithm. Each states why in
  one line. No unit tests for wiring, pass-throughs, accessors, mocks, or
  anything an outcome test already covers.
- **Make failures easy to place.** A failing run-through should show where
  it broke: assert on the intermediate results a user could observe (files,
  logged steps, exit codes) rather than adding unit tests to locate faults.
- **Deterministic.** No real clocks, randomness, sleeps or outside services
  in a test's result; poll with a timeout instead of sleeping. A flaky
  run-through is worse than none.
- **Runtime is a design constraint.** Unless the project sets its own, the
  budget is about a minute for the tests one stage runs and a few minutes
  for the whole suite. Design tests to fit: small realistic data, temporary
  directories, expensive setup done once and shared, tests independent so
  they can run in parallel. A test that is slow by nature (real network,
  large data) is marked as such and runs at phase end and cutover only.
- **Write outcome tests early.** The interfaces phase writes them against
  the contracts, marked expected-fail with the framework's strict marker
  (one that fails when the test unexpectedly passes, such as pytest's
  `xfail(strict=True)`). Each internals stage removes the marks of the
  tests it makes pass. Without such a marker, write each outcome test in
  the stage that makes it pass.

Each phase file's Outcome tests section lists the outcomes it writes tests
for or makes pass; across the plan, every outcome is written once and made
to pass once. Each stage brief's Tests line names the exact tests that stage
writes or turns on. The project's own testing rules take precedence.
