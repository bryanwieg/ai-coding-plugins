# Planning mode: field guide

Before planning, decide how much planning the change needs. Read the code
the request touches, fill a form in [mode.schema.json](mode.schema.json),
and run `scripts/plan-mode.py FORM.json --repo .`. The script checks the
evidence and picks the mode; follow it. Examples use an unrelated web app
to show form, not content.

| Mode | What happens |
| --- | --- |
| direct | No plan file. Make the change in context: read the code first, run the tests after. |
| quick | One phase file, checked by `plan-check.py`; no review subagent. |
| full | The full process in SKILL.md. |

How the script scores each part: `kind` weight × `lines` size × `reach`,
summed, plus one per open question. Direct up to 4, quick up to 15, full
above. A data part that changes existing data is always full.

| kind | weight | | lines | size | | files in reach | reach |
| --- | --- | --- | --- | --- | --- | --- | --- |
| new | 0.5 | | under 30 | 1 | | none | 1 |
| internal | 1 | | 30–150 | 2 | | 1–3 | 1.5 |
| interface | 2 | | over 150 | 5 | | 4–9 | 2 |
| architecture, data | 3 | | | | | 10 or more | 3 |

## request
The request in one sentence, as the user gave it.

## parts
Split the change into the pieces that differ in kind: usually one to five.
Code that existing code will call is two parts: the new code (`new`) and
the edit that calls it (`internal` or `interface`). Tests go in the part
they test.
- `title`: a few words.
- `kind`, by what the part changes, not by its size:
  - `new`: code nothing existing calls or reads (a script, a page, a
    module), and its tests and docs.
  - `internal`: bodies change; every signature, route, key, format and
    output others see stays the same.
  - `interface`: something others see changes: a signature, route,
    config key, file or wire format, CLI option, event, or a page others
    link to.
  - `architecture`: responsibilities move between components, or a layer,
    component, service or dependency is added or removed, or data takes a
    different path.
  - `data`: stored data or its format changes, or a migration runs.
- `files`: every path the part creates, edits or deletes. The script
  checks edited and deleted paths exist and created ones do not.
- `lines`: your estimate of lines added plus removed in the part's
  non-test files.
- `reach`: for interface, architecture and data parts, the files outside
  the part that must change or be checked because of it: callers, readers,
  configs, docs. Find them by searching, never by guessing; `path` or
  `path:line`. Each distinct file counts once. Empty when nothing else
  uses it.
- `search`: the searches that found the reach (for example `grep -rn
  "rate_limit" src tests docs`). Required for interface, architecture and
  data parts, also when the reach is empty.
- `existing_data`: data parts only: true when data written before this
  change must still be read or converted.

Good, for "add a per-address login rate limit":
`{"title": "limiter module", "kind": "new", "files": [{"path":
"app/ratelimit.py", "action": "create"}, {"path": "tests/test_ratelimit.py",
"action": "create"}], "lines": 60, "reach": [], "search": ""}` and `{"title": "login view calls the limiter",
"kind": "interface", "files": [{"path": "app/views.py", "action": "edit"}],
"lines": 15, "reach": ["docs/api.md:40", "frontend/login.ts:22"], "search":
"grep -rn \"/login\" docs frontend"}` (the route
gains a 429 answer that the docs and the frontend see).

Bad: one part for the whole request; `architecture` because the change is
large; a reach of "probably the views".

## open_questions
Questions the code cannot answer now and only the user, or code not yet
written, can: one line each. A question the code answers is not open: read
the code. None is the usual case. Changing something people outside the
repository use (a config key in their own files, a CLI option in their
scripts, a public API) raises one: keep the old form, or break it?

## When the work turns out bigger

The mode holds only while the form is true. When direct work finds a user
of something it changes that the reach missed, or a part of another kind,
stop, update the form and run the script again. Move up when it says so;
never move down in the middle of the work.
