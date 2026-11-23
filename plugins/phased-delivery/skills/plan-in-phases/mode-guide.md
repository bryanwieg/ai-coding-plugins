# Planning mode: the quick estimate

Before planning, estimate how much planning the change needs. This is an
estimate with hard limits, not the start of a plan: you do no searching of
your own, open at most 5 files, and stop. `scripts/plan-mode.py` does the
searches, checks the form and picks the mode; follow it. Examples use an
unrelated web app to show form, not content.

| Mode | What happens |
| --- | --- |
| direct | No plan file. Make the change in context: read the code first, run the tests after. |
| quick | One phase file, checked by `plan-check.py`; no review subagent. Re-score when it is written (below). |
| full | The full process in SKILL.md. |

## The steps

1. **Terms, without tools.** Write `TERMS.json` (mode.schema.json `terms`):
   the request and up to 5 terms from it, the names of things it
   mentions or needs: commands, options, settings, routes, functions,
   pages, file names. Use the words the code would use (`read_only`,
   `--auth-file`, `/login`), not descriptions ("the login feature").
2. **Locate.** Run `plan-mode.py locate TERMS.json --repo .`. It prints,
   for each term, the files that mention it or are named after it (at most
   10 per term).
3. **Read at most 5 files** from that list, only far enough to tell what
   each part of the change is: what the file holds and where the change
   lands. Do not read the logic, follow calls or search further.
4. **Form.** Write `FORM.json` (mode.schema.json `form`, fields below).
   What you could not find in those 5 files goes in `unresolved`; do not
   read more to find it.
5. **Score.** Run `plan-mode.py score FORM.json --repo .`. Fix any error it
   reports (a wrong path, too many files opened) without reading more,
   and follow the mode it prints.

How the script scores each part: `kind` weight × `lines` size × reach,
summed, plus one per open question. Reach counts the files outside the
part that contain the part's `changes` names; the script finds them. Direct
up to 4, quick up to 15, full above. A data part that changes existing
data is always full; anything unresolved makes it at least quick.

| kind | weight | | lines | size | | files in reach | reach |
| --- | --- | --- | --- | --- | --- | --- | --- |
| new | 0.5 | | under 30 | 1 | | none | 1 |
| internal | 1 | | 30-150 | 2 | | 1–3 | 1.5 |
| interface | 2 | | over 150 | 5 | | 4–9 | 2 |
| architecture, data | 3 | | | | | 10 or more | 3 |

## The form

### request
The request in one sentence, as the user gave it.

### opened
The files you read in step 3, at most 5.

### parts
Split the change into pieces that differ in kind: usually one to five.
Code that existing code will call is two parts: the new code (`new`) and
the edit that calls it (`internal` or `interface`). Tests go in the part
they test. Text or code moved without changing what it says or does is one
`internal` part, however many lines and new files it takes; a section
heading is not a name others use unless something links to it.
- `title`: a few words.
- `kind`, by what the part changes, not by its size:
  - `new`: code nothing existing calls or reads (a script, a page, a
    module), with its tests and docs.
  - `internal`: bodies change; every signature, route, key, format and
    output others see stays the same.
  - `interface`: something others see changes: a signature, route,
    config key, file or wire format, CLI option, event, or a page others
    link to.
  - `architecture`: responsibilities move between components, or a layer,
    component, service or dependency is added or removed, or data takes a
    different path.
  - `data`: stored data or its format changes, or a migration runs.
- `files`: the paths the part creates, edits or deletes, as far as the
  located and opened files show. The script checks edited and deleted
  paths exist and created ones do not.
- `lines`: your guess of lines added plus removed in the part's non-test
  files, as a bucket: `under 30`, `30-150` or `over 150`.
- `changes`: for interface, architecture and data parts, the names others
  see that this part adds, changes or changes the meaning of:
  the whole identifier, key, option or route as written in the code
  (`check_rate`, `auth_file`, `/api/login`). The script searches for them;
  a short or common word matches everywhere, so give the exact name. When
  the part adds something to an existing thing (an option to a command, a
  section to a file format, a field to a response), list both the new name
  and the existing thing's name (`--min-small` and `select-models.py`):
  whoever uses the existing thing now meets the addition. Empty for new and
  internal parts.
- `existing_data`: data parts only: true when data written before this
  change must still be read or converted.

Good, for "add a per-address login rate limit":
`{"title": "limiter module", "kind": "new", "files": [{"path":
"app/ratelimit.py", "action": "create"}], "lines": "30-150", "changes": []}`
and `{"title": "login answers 429 when limited", "kind": "interface",
"files": [{"path": "app/views.py", "action": "edit"}], "lines": "under 30",
"changes": ["/login"]}`.

Bad: one part for the whole request; `architecture` because the change is
large; `changes: ["login"]`, a word that matches every file about logging
in.

### unresolved
A part of the change you could not place: you do not know which component
or file it lands in, so you cannot tell its kind or reach. One line each
("which component checks permissions", "which module renders the
header"). Details the builder reads while working are not unresolved:
which test file to extend, which API or fixture a script uses, how a state
is detected. Empty when every part has its files. Anything here makes the
mode at least quick; the quick plan reads further.

### open_questions
Questions the code cannot answer and only the user, or code not yet
written, can: one line each. None is the usual case. Changing something
people outside the repository use (a config key in their own files, a CLI
option in their scripts, a public API) raises one: keep the old form, or
break it?

## Re-scoring

The mode holds only while the estimate is true.
- **Quick plan:** when its `plan.json` passes `plan-check.py --outline`,
  update the form from it (the stages' files, the contracts' kinds and
  names, anything unresolved now found) and score again. If it says full,
  continue as a full plan. If it says direct, stop planning and make the
  change directly.
- **Direct work:** when the work finds a user of something it changes that
  the estimate missed, or a part of another kind, stop, update the form and
  score again. Move up when it says so.
