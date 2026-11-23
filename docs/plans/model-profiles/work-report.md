## Work by model

Range `b0c58e2..HEAD`: 10 accepted stages, 8 later fixes.

| Model | Effort | Tool | Stages | First try | Clean | Failed tries | Fixes needed | Tokens spent | Wasted | Per stage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| opus | medium | claude-code | 3 | 3/3 | 1/3 | 0 | 2 | 110525 | 0 | 36841 |
| opus | high | claude-code | 7 | 7/7 | 1/7 | 0 | 6 | 440280 | 0 | 62897 |
| orchestrator | default | claude-code | 0 | 0/0 | 0/0 | 0 | 0 | 0 (+8 unknown) | 0 | n/a |
| **All** | | | 10 | 10/10 | 2/10 | 0 | 8 | 550805 (+8 unknown) | 0 | |

### Reruns

None.

### Fixes after acceptance

- 04.3 (built by opus high): 04.3 fix: a timed-out check before a phase starts it without Codex; by orchestrator default, unknown tokens [1432de0]
- 04.1 (built by opus high): 04.1 fix: an unwritable cache never crashes; timeout tested; by orchestrator default, unknown tokens [1c13abe]
- 03.2 (built by opus high): 03.2 fix: retries never repeat a tried pair; exit 4 stops; Codex outside the budget; by orchestrator default, unknown tokens [63de83b]
- 03.1 (built by opus high): 03.1 fix: an error result is never built; tests cover permissions and flags; by orchestrator default, unknown tokens [9fc005a]
- 02.2 (built by opus medium): 02.2 fix: preferences never undo the risk step; route reads straight through; by orchestrator default, unknown tokens [b9de1bd]
- 01.3 (built by opus medium): 01.3 fix: report header names what reads the JSON now; by orchestrator default, unknown tokens [2f08ab4]
- 01.2 (built by opus high): 01.2 fix: selector test uses frozen fixtures; by orchestrator default, unknown tokens [fe210a1]
- 01.1 (built by opus high): 01.1 fix: profiles failures exit 2, never 1; tests use a frozen report; by orchestrator default, unknown tokens [3e19fa1]

## Reading

- **Effectiveness:** all 10 stages were accepted on the first dispatch;
  none was rerun. Only 2 of 10 are clean, because the phase reviews asked
  for fixes on 8. Most fixes were gaps the briefs left open rather than
  reasoning errors: an exit code a crash could share (01.1, 04.1), a test
  tied to live data (01.2, a brief gap), stale wording (01.3), a rule
  interaction the brief did not bound (02.2), and retry and error paths
  the docs or script did not cover (03.1, 03.2, 04.3). The one real logic
  slip was 02.2, where the J2/C2 preference could undo the risk step.
- **Cost:** Opus high spent about 63k tokens per stage, Opus medium about
  37k. Fixes were made by the orchestrator, so their tokens are unknown
  and not counted against either.
- **Candidates:** too few stages, all on Opus, to judge a tier change. No
  stage ran on the small tier (none was mechanical), so Haiku was not
  exercised. The briefs, more than the models, decided the fix rate:
  plans should name failure exits and retry paths explicitly.

## Unknown token counts

The 8 fixes were made directly by the orchestrator, whose own tokens are
not reported per change.
