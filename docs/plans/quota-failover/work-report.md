# Work report: quota-failover

Generated with `scripts/stage-stats.sh` in each repository: ai-coding-plugins
`6a000a1..HEAD` (phases 01–02) and ai-coding-sandbox `ffb401a..HEAD`
(phase 03, branch `ai-codex-statusline`).

# ai-coding-plugins

### Work by model

Range `6a000a1..HEAD`: 8 accepted stages, 4 later fixes.

| Model | Effort | Tool | Stages | First try | Clean | Failed tries | Fixes needed | Tokens spent | Wasted | Per stage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| opus | medium | claude-code | 1 | 0/1 | 0/1 | 0 | 0 | 43710 | 0 | 43710 |
| gpt-6.2-astra | high | codex | 1 | 0/1 | 0/1 | 1 | 0 | 313799 | 99410 | 214389 |
| gpt-6.2-sol | medium | codex | 1 | 0/1 | 0/1 | 2 | 1 | 522108 (+1 unknown) | 70869 | 451239 |
| opus | high | claude-code | 3 | 3/3 | 0/3 | 0 | 3 | 148027 | 0 | 49342 |
| orchestrator | default | claude-code | 2 | 2/2 | 2/2 | 0 | 0 | 0 (+6 unknown) | 0 | n/a |
| **All** | | | 8 | 5/8 | 2/8 | 3 | 4 | 1027644 (+7 unknown) | 170279 | |

#### Reruns

- 02.1 accepted from opus medium on attempt 2; earlier gpt-6.2-sol medium (unknown tokens): Codex token expired (401 token_expired); turn failed, model unsupported for the account; no edits
- 01.3 accepted from gpt-6.2-astra high on attempt 2; earlier gpt-6.2-astra high (99410 tokens): Codex sandbox could not start in the container (fixed by 01.4)
- 01.1 accepted from gpt-6.2-sol medium on attempt 2; earlier gpt-6.2-sol medium (70869 tokens): Codex sandbox could not start in the container (fixed by 01.4)

#### Fixes after acceptance

- 02.2 (built by opus high): Fix 02.2: codex exec reads no stdin, so it cannot hang; by orchestrator default, unknown tokens [e7f1ceb]
- 02.4 (built by opus high): Fix 02.4: plan-time Codex files follow the availability check; by orchestrator default, unknown tokens [08bc879]
- 02.3 (built by opus high): Fix 02.3: Codex dispatches run alone and snapshot first; re-sign-in is the user's word; by orchestrator default, unknown tokens [ba014c9]
- 01.1 (built by gpt-6.2-sol medium): Fix 01.1: keep usage above 100% as nearly out, not no data; by orchestrator default, unknown tokens [059d8d4]

# ai-coding-sandbox

### Work by model

Range `ffb401a..HEAD`: 3 accepted stages, 0 later fixes.

| Model | Effort | Tool | Stages | First try | Clean | Failed tries | Fixes needed | Tokens spent | Wasted | Per stage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| opus | medium | claude-code | 2 | 2/2 | 2/2 | 0 | 0 | 66100 | 0 | 33050 |
| opus | high | claude-code | 1 | 1/1 | 1/1 | 0 | 0 | 40395 | 0 | 40395 |
| **All** | | | 3 | 3/3 | 3/3 | 0 | 0 | 106495 | 0 | |

#### Reruns

None.

#### Fixes after acceptance

None.

## Reading

- **11 accepted stages in total, too few to change any tier's candidate.**
  Every failed try had an environmental cause, not a model cause. Codex's
  sandbox could not start in the container (01.1 and 01.3, 170,279 tokens
  wasted; fixed by 01.4), and Codex's sign-in token expired (02.1). None of
  the reruns points to an under-scored measure.
- **opus high (`middle+` and `top`):** 4 stages, all accepted first try.
  Clean is 1/4: the phase 02 review found 3 small gaps in its stages
  (02.2's missing `< /dev/null`, 02.3's "dispatches run alone" pointer,
  02.4's stale plan-time bullet). All were gaps in the briefs rather than
  in the reasoning, and each was fixed in one line. About 47,000 tokens
  per stage.
- **opus medium (`middle`):** 3 stages, all first try. 02.1 was attempt 2
  only because Codex failed first. About 36,600 tokens per stage, the
  cheapest Claude candidate here.
- **Codex (gpt-6.2-sol medium, gpt-6.2-astra high):** 2 stages accepted
  (phase 01), with 214,000–451,000 tokens per stage, several times opus's
  count. The counting differs, though: Codex's figure is input plus output
  over the whole run. 01.1 later needed a fix (usage above 100% read as no
  data).
- **What the reruns and fixes had in common:** Codex's availability, which
  is what this plan builds. Expect fewer wasted Codex tokens once the
  availability check (02.1) and exits 3, 5 and 6 (02.2, 02.5) are in use.

## Unknown token counts

- The orchestrator's own stages and fixes (01.2, 01.4, 02.5 and 4 fixes)
  have no subagent usage report.
- The failed Codex try of 02.1 ended before any `turn.completed` event, so
  Codex reported no usage.
