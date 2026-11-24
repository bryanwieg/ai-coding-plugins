#!/usr/bin/env python3
"""Check a phased plan written as JSON and render its plan.md and phase.md files.

Usage:
  plan-check.py PLAN_DIR [--repo DIR] [--spec FILE] [--design FILE] [--outline] [--phase NN]
  plan-check.py PLAN_DIR --packet NN.n

The plan is PLAN_DIR/plan.json (plan.schema.json: outcomes, cross-phase
decisions, existing interfaces, phases) and, per phase, a folder NN-name
holding phase.json (phase.schema.json) and one NN.n.json per stage
(stage.schema.json). Each of those has a `brief`, written by planning and
revising, and a `record`, written by the build scripts. The field guides in
skills/plan-in-phases say how to fill them. This script checks what can be
checked without judgment and renders PLAN_DIR/plan.md and, for each phase
whose JSON is clean, NN-name/phase.md. --outline checks plan.json and the
outline fields of the stage files only, and renders nothing.

The checks that compare a brief with the repository apply to stages still to
build: file actions to stages with no commit, code citations also to reopened
ones; --phase NN limits them to that phase. A brief that changed since an
attempt built it needs a higher `revision`.

--packet prints the stage packet, the only plan text a builder is given: the
phase's role, why, how, before, after and test budget, then the stage's
brief as phase.md shows it. It checks and renders nothing; exit 2 for an unknown stage.

--spec and --design default to the paths plan.json names in `docs`, relative
to --repo, which defaults to the current directory.

Output: one JSON line per problem, {"file", "where", "kind", "msg", "level"},
then a summary line. level "error" must be fixed; "warning" is reported for
the planner to judge. Exit codes: 0 no errors; 1 errors; 2 bad usage or a
missing or unreadable file.
"""

import hashlib
import json
import os
import re
import sys

SKILL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "plan-in-phases")
MEASURES = "JFRCKPVS"
SHAPE_MAX = {"function": 200, "class": 200, "error": 200, "test-helper": 200, "config": 300,
             "event": 300, "cli": 300, "format": 400, "route": 500, "other": 200}
LIMITS = {"behaviour": 8, "done_when": 6, "out_of_scope": 5}
CODE_READ_MAX, DESIGN_MAX, GOAL_MAX, SENTENCES_MAX = 8, 4, 250, 6
STAGE_FILE = re.compile(r"^\d\d\.\d+\.json$")
OUTLINE = ["revision", "title", "order", "lines", "files", "provides", "uses"]
TESTY = re.compile(r"(^|/)tests?/|(^|/)test_|\.test\.|::test_")
CODEY = re.compile(r"```|`[^`\n]*(?:==|!=|\bis (?:not )?None\b|\breturn\b|\.get\(|\bfor \w+ in\b|\bif\b|\belse\b|\+=)[^`\n]*`")
WHERE = re.compile(r"(?:\./)?([\w./-]+):(\d+)(?:-(\d+))?")
PLAN_IDS = re.compile(r"\b[CD]\d{1,3}\b")
WARNINGS = {"code", "length", "other", "order-hint"}


# ---- a small JSON Schema subset (the plugin's scripts use the standard library only)

TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None),
         "integer": int, "number": (int, float)}


def is_type(data, name):
    # a bool is an int in Python, not in JSON
    return isinstance(data, TYPES[name]) and (name == "boolean" or not isinstance(data, bool))


def validate(data, schema, root=None, path=""):
    root = root or schema
    if "$ref" in schema:
        schema = root["definitions"][schema["$ref"].split("/")[-1]]
    out = []
    t = schema.get("type")
    if t and not any(is_type(data, name) for name in ([t] if isinstance(t, str) else t)):
        wanted = "an integer" if t == "integer" else t if isinstance(t, str) else " or ".join(t)
        return [(path, f"must be {wanted}, got {type(data).__name__}")]
    if is_type(data, "number") and (data < schema.get("minimum", data) or data > schema.get("maximum", data)):
        out.append((path, f"{data} is outside {schema.get('minimum')}..{schema.get('maximum')}"))
    if "enum" in schema and data not in schema["enum"]:
        out.append((path, f"{data!r} is not one of {schema['enum']}"))
    if "pattern" in schema and isinstance(data, str) and not re.search(schema["pattern"], data):
        out.append((path, f"{data!r} does not match {schema['pattern']}"))
    if isinstance(data, dict):
        props = schema.get("properties", {})
        for k in schema.get("required", []):
            if k not in data:
                out.append((path, f"missing {k!r}"))
        extra = schema.get("additionalProperties")
        for k, v in data.items():
            if k in props:
                out += validate(v, props[k], root, f"{path}/{k}")
            elif extra is False:
                out.append((path, f"unknown field {k!r}"))
            elif isinstance(extra, dict):
                out += validate(v, extra, root, f"{path}/{k}")
    if isinstance(data, list):
        if len(data) < schema.get("minItems", 0):
            out.append((path, f"needs at least {schema['minItems']} items"))
        for i, v in enumerate(data):
            out += validate(v, schema.get("items", {}), root, f"{path}/{i}")
    return out


# ---- helpers

def norm(t):
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("—", "-"), ("–", "-")):
        t = t.replace(a, b)
    return re.sub(r"\s+", " ", re.sub(r"[`*_]", "", t)).strip().lower()


def quote_found(q, text):
    parts = [norm(x) for x in re.split(r"\.\.\.|…", q)]
    return any(parts) and all(x in text for x in parts if x)


def tier(mb):
    total = sum(mb[m] for m in MEASURES)
    t, why = ("small" if total <= 3 else "middle" if total <= 8 else "top"), ""
    if t == "small" and not (all(mb[m] == 0 for m in "JCKS") and mb["P"] == 0 and mb["V"] == 0):
        t, why = "middle", "small only for mechanical stages"
    if t == "middle" and 2 in mb.values():
        t, why = "middle+", "middle with a measure at 2"
    return total, t, why


def strings(x, path=""):
    if isinstance(x, str):
        yield path, x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield from strings(v, f"{path}/{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from strings(v, f"{path}/{i}")


def brief_hash(brief):
    return hashlib.sha256(json.dumps(brief, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def stage_files(pdir):
    return sorted((n for n in os.listdir(pdir) if STAGE_FILE.match(n)),
                  key=lambda n: [int(x) for x in n[:-5].split(".")])


def flatten(phases):
    # every stage of the plan in build order: id -> its file's content, phase number and file name
    return {sid: {**s, "phase": ph["phase"], "file": f"{ph['dir']}/{sid}.json"}
            for ph, _, found in phases for sid, s in found.items()}


def build_positions(stages):
    # global build position per stage; a parallel stage shares its partner's position
    pos, n = {}, 0
    for sid, s in stages.items():
        m = re.match(r"parallel with (\d\d\.\d+)", s["brief"]["order"])
        if m and m.group(1) in pos:
            pos[sid] = pos[m.group(1)]
        else:
            n += 1
            pos[sid] = n
    return pos


def registry(stages):
    # the contracts the stages provide, each with its provider and the stages whose `uses` name it
    return [{**c, "provided_by": sid, "users": [u for u, x in stages.items() if c["name"] in x["brief"]["uses"]]}
            for sid, s in stages.items() for c in s["brief"]["provides"]]


def outcome_rows(stages):
    tests = [(sid, t) for sid, s in stages.items() for t in s["brief"].get("tests", []) if t["kind"] == "outcome"]
    turned_on = {t["test"].strip("`"): sid for sid, t in tests if t["action"] == "turns on"}
    return [{"outcome": t["outcome"], "test": t["test"].strip("`"), "written_in": sid,
             "passes_from": turned_on.get(t["test"].strip("`"), sid)}
            for sid, t in tests if t["action"] == "writes" and "outcome" in t]


def stage_status(s):
    rec = s["record"]
    attempts = rec.get("attempts", [])
    if not rec.get("commit"):
        return "in progress" if attempts else "planned"
    built = max((a["revision"] for a in attempts if a["commit"] == rec["commit"]), default=s["brief"]["revision"])
    return "reopened" if s["brief"]["revision"] > built else "done"


def phase_status(record, stages):
    if record.get("built"):
        return f"built {record['built']}"
    halt = record.get("halt")
    if halt:
        return f"halted: {halt['reason']}"
    states = {sid: stage_status(s) for sid, s in stages.items()}
    if all(x == "planned" for x in states.values()):
        return "planned"
    return f"in progress (stages done: {', '.join(k for k, x in states.items() if x == 'done') or 'none'})"


class Report:
    def __init__(self):
        self.items = []

    def add(self, file, where, kind, msg):
        self.items.append({"file": file, "where": where, "kind": kind, "msg": msg,
                           "level": "warning" if kind in WARNINGS else "error"})

    def errors(self, prefix=""):
        return [x for x in self.items if x["level"] == "error" and x["file"].startswith(prefix)]


# ---- the whole plan: plan.json and what the stage files say to each other

def check_plan(plan, stages, repo, docs, scope, outline, r):
    F = "plan.json"
    pos = build_positions(stages)
    for group, prefix in (("outcomes", "O"), ("decisions", "D")):
        ids = [x["id"] for x in plan[group]]
        if ids != [f"{prefix}{i}" for i in range(1, len(ids) + 1)]:
            r.add(F, group, "id", f"ids must run {prefix}1..{prefix}{len(ids)} in order")
    nums = [ph["phase"] for ph in plan["phases"]]
    if nums != [f"{i:02d}" for i in range(1, len(nums) + 1)]:
        r.add(F, "phases", "id", f"phases must be numbered 01..{len(nums):02d} in build order, got {nums}")
    for ph in plan["phases"]:
        if not ph["dir"].startswith(ph["phase"] + "-"):
            r.add(F, ph["phase"], "id", f"dir {ph['dir']} does not start with {ph['phase']}-")
    for x in plan["outcomes"]:
        for s in x["sources"]:
            check_quote(F, x["id"], s, docs, r)
    for x in plan["decisions"]:
        if x.get("departs_from"):
            check_quote(F, x["id"], x["departs_from"], docs, r)
            if x.get("user_answer") is None:
                r.add(F, x["id"], "departure", "departs from the spec or design: set user_answer to given or assumed")
        for p in x["phases"]:
            if p != "all" and p not in nums:
                r.add(F, x["id"], "ref", f"names phase {p}, which does not exist")
    created = {}
    for sid, s in stages.items():
        for f in s["brief"]["files"]:
            if f["action"] == "create":
                created.setdefault(f["path"], sid)
    contracts = registry(stages)
    names = [c["name"] for c in contracts] + [e["name"] for e in plan["existing"]]
    for name in sorted({n for n in names if names.count(n) > 1}):
        r.add(F, name, "registry", f"{name}: more than one provider; a name in uses must resolve to exactly one "
              "stage's provides or one existing entry")
    for e in plan["existing"]:
        m = WHERE.fullmatch(e["path"])
        path = m.group(1) if m else e["path"]
        if not os.path.exists(os.path.join(repo, path)):
            r.add(F, e["name"], "ref", f"{e['name']}: existing path {path} not found")
    for c in contracts:
        w, G = c["provided_by"], stages[c["provided_by"]]["file"]
        if not c["users"] and not [u for u in c["used_by"] if c["kind"] == "test-helper" or not TESTY.search(u)]:
            r.add(G, w, "internal", f"{c['name']}: no stage uses it and no user outside the plan other than tests; "
                  "that is internal: leave it out and state what tests observe as behaviour")
        for u in c["users"]:
            if pos[w] >= pos[u]:
                r.add(G, w, "order", f"{c['name']}: provided by {w}, used by {u}, which is not built after it")
        if len(c["shape"]) > SHAPE_MAX[c["kind"]]:
            r.add(G, w, "shape", f"{c['name']}: shape is {len(c['shape'])} chars > {SHAPE_MAX[c['kind']]} for {c['kind']}")
        if c["kind"] == "other":
            r.add(G, w, "other", f"{c['name']}: kind other" + ("" if c.get("other_reason") else " without other_reason"))
    listed = list(stages)
    written = {t["test"].strip("`") for s in stages.values() for t in s["brief"].get("tests", [])
               if t["kind"] == "outcome" and t["action"] == "writes"}
    for sid, s in stages.items():
        b, G = s["brief"], s["file"]
        paths = {f["path"] for f in b["files"]}
        for name in b["uses"]:
            if name not in names:
                r.add(G, sid, "ref", f"uses {name!r}, which no stage provides and existing does not list")
        if not s["record"].get("commit") and scope in (None, s["phase"]):
            for f in b["files"]:
                exists = os.path.exists(os.path.join(repo, f["path"]))
                if f["action"] == "create" and exists:
                    r.add(G, sid, "files", f"creates {f['path']}, which already exists")
                if f["action"] != "create" and not exists and not (
                        f["path"] in created and pos[created[f["path"]]] < pos[sid]):
                    r.add(G, sid, "files", f"{f['action']}s {f['path']}, which does not exist and no earlier stage creates")
        m = re.match(r"(?:after|parallel with) (\d\d\.\d+)", b["order"])
        if m and m.group(1) not in stages:
            r.add(G, sid, "order", f"order names {m.group(1)}, which is not a stage")
        elif m and listed.index(m.group(1)) > listed.index(sid):
            r.add(G, sid, "order", f"order names {m.group(1)}, which is built after {sid}")
        elif m:
            dep = stages[m.group(1)]["brief"]
            shared = paths & {f["path"] for f in dep["files"]}
            if b["order"].startswith("parallel") and shared:
                r.add(G, sid, "parallel", f"shares {sorted(shared)} with parallel stage {m.group(1)}")
            if b["order"].startswith("after") and not shared and not {c["name"] for c in dep["provides"]} & set(b["uses"]):
                r.add(G, sid, "order-hint", f"ordered after {m.group(1)} but uses none of its contracts and shares "
                      "no file; if nothing else needs it first, order it after the stage it does depend on or in parallel")
        for t in b.get("tests", []):
            if t["kind"] == "outcome" and t["action"] == "writes" and "outcome" not in t:
                r.add(G, sid, "tests", f"outcome test {t['test']} needs the id of its outcome in `outcome`")
            if t["kind"] == "outcome" and t["action"] == "turns on" and t["test"].strip("`") not in written:
                r.add(G, sid, "ref", f"turns on {t['test']}, which no stage writes")
    rows = outcome_rows(stages)
    known = {x["id"] for x in plan["outcomes"]}
    if not outline:  # tests are not an outline field
        for x in sorted(known - {t["outcome"] for t in rows}):
            r.add(F, x, "coverage", f"outcome {x} has no outcome test")
    for t in rows:
        G = stages[t["written_in"]]["file"]
        if t["outcome"] not in known:
            r.add(G, t["test"], "ref", f"outcome {t['outcome']} is not in outcomes")
        if pos[t["written_in"]] > pos[t["passes_from"]]:
            r.add(G, t["test"], "order", f"written in {t['written_in']}, after it must pass ({t['passes_from']})")
    for path, text in strings({k: plan[k] for k in ("size", "decisions", "outcomes")}):
        if CODEY.search(text):
            r.add(F, path, "code", CODEY.search(text).group(0)[:80])


def check_quote(file, where, src, docs, r):
    if src["doc"] not in docs:
        return
    if len(norm(src["quote"])) < 8:
        r.add(file, where, "quote", f"quote {src['quote']!r} is too short to locate; copy the words that matter")
    elif not quote_found(src["quote"], docs[src["doc"]]):
        r.add(file, where, "quote", f"not found in the {src['doc']}: {src['quote'][:100]!r}; copy it exactly, or "
              "mark the words as a paraphrase without quoting them")


def check_cite(file, where, cite, shows, repo, r):
    m = WHERE.fullmatch(cite.strip().strip("`"))
    if not m:
        r.add(file, where, "cite", f"{cite!r} is not path:line or path:start-end")
        return
    try:
        lines = open(os.path.join(repo, m.group(1)), errors="replace").read().splitlines()
    except OSError:
        r.add(file, where, "cite", f"{m.group(1)}: no such file")
        return
    lo, hi = int(m.group(2)), int(m.group(3) or m.group(2))
    if lo < 1 or hi < lo or hi > len(lines):
        r.add(file, where, "cite", f"{cite}: the file has {len(lines)} lines")
    elif shows is not None and norm(shows) not in norm(" ".join(lines[max(0, lo - 3):hi + 2])):
        r.add(file, where, "cite", f"{cite} does not show {shows!r}; cite the lines that do")


# ---- phase.json and the stage files

def check_revision(sid, s, r):
    revs, rev = s["record"].get("revisions", {}), s["brief"]["revision"]
    bad = [n for n in revs if not n.isdecimal()]
    if bad:
        r.add(s["file"], sid, "revision", f"stage {sid}: revisions keys {bad} are not revision numbers")
    if str(rev) in revs and revs[str(rev)] != brief_hash(s["brief"]):
        r.add(s["file"], sid, "revision", f"stage {sid}: the brief changed since revision {rev} was built; raise revision")
    elif any(int(n) > rev for n in revs if n.isdecimal()):
        r.add(s["file"], sid, "revision", f"stage {sid}: revision {rev} is lower than a revision already built")


def check_standalone(F, where, data, ids, r):
    for path, text in strings(data):
        m = next((m for m in PLAN_IDS.finditer(text) if m.group(0) in ids), None)
        if m:
            r.add(F, where + path, "standalone", f"uses the plan.json id {m.group(0)}, which the phase file does not "
                  "define; name the decision instead")
        if ".plan/" in text:
            r.add(F, where + path, "standalone", "cites the .plan folder; the phase file must stand alone")


def check_phase(F, brief, ids, r):
    check_standalone(F, "", brief, ids, r)
    for k in ("before", "after"):
        n = len(re.findall(r"[.!?](?:\s|$)", brief[k]))
        if n > SENTENCES_MAX:
            r.add(F, k, "length", f"{k} has {n} sentences > {SENTENCES_MAX}")


def check_stage(sid, s, ids, repo, docs, scope, r):
    b, F = s["brief"], s["file"]
    if len(b["goal"]) > GOAL_MAX:
        r.add(F, sid, "length", f"goal is {len(b['goal'])} chars > {GOAL_MAX}")
    for f, n in LIMITS.items():
        if len(b[f]) > n:
            r.add(F, sid, "length", f"{f} has {len(b[f])} items > {n}")
    if len(b["context"]["code_read"]) > CODE_READ_MAX:
        r.add(F, sid, "length", f"code_read has {len(b['context']['code_read'])} items > {CODE_READ_MAX}")
    if len(b["context"]["design"]) > DESIGN_MAX:
        r.add(F, sid, "length", f"design has {len(b['context']['design'])} items > {DESIGN_MAX}")
    for t in b["tests"]:
        if t["kind"] == "unit" and not t.get("why_unit"):
            r.add(F, sid, "tests", f"unit test {t['test']} needs why_unit")
    for x in b["context"]["design"]:
        check_quote(F, f"{sid}/context/design", x, docs, r)
    if stage_status(s) != "done" and scope in (None, s["phase"]):
        for x in b["context"]["code_read"]:
            check_cite(F, f"{sid}/context/code_read", x["where"], x["shows"], repo, r)
    for path, text in strings({k: v for k, v in b.items() if k != "checks"}):
        if not (path.startswith("/provides") and path.endswith("/shape")) and CODEY.search(text):
            r.add(F, sid + path, "code", CODEY.search(text).group(0)[:80])
    check_standalone(F, sid, b, ids, r)


# ---- rendering

def bullets(items, fmt):
    return [f"- {fmt(x)}" for x in items] or ["none"]


def contract_lines(sid, brief, contracts, existing):
    mine = [f"- {c['kind']} `{c['name']}` (provides; {', '.join(c['users'] + c['used_by'])}): {c['shape']}"
            for c in contracts if c["provided_by"] == sid]
    sources = {**{e["name"]: {**e, "provided_by": f"existing, `{e['path']}`"} for e in existing},
               **{c["name"]: c for c in contracts}}
    used = [f"- {c['kind']} `{c['name']}` (uses; {c['provided_by']}): {c['shape']}"
            for c in (sources[n] for n in brief["uses"] if n in sources)]
    return mine + used or ["none"]


def phase_rows(found, stages):
    return [t for t in outcome_rows(stages) if t["written_in"] in found or t["passes_from"] in found]


def render_stage(sid, s, plan, stages, proves):
    # the stage's section of phase.md, also the body of its packet
    b = s["brief"]
    c = b["context"]
    L = ["", f"## {sid} {b['title']}".rstrip(), "", f"Goal: {b['goal']}", "", "Context:"]
    ctx = [f"- Builds on {x['source']}: {x['what']}" for x in c["builds_on"]]
    ctx += [f"- `{x['where']}`: {x['fact']}" for x in c["code_read"]]
    ctx += [f"- {x['doc'].capitalize()}, {x['section']}: \"{x['quote']}\"" for x in c["design"]]
    L += ctx or ["none"]
    L += ["", "Contracts:"] + contract_lines(sid, b, registry(stages), plan["existing"])
    L += ["", "Files:"] + bullets(b["files"], lambda x: f"`{x['path']}` ({x['action']}): {x['role']}")
    L += ["", "Behaviour:"] + bullets(b["behaviour"], lambda x:
          f"Given {x['given']}, when {x['when']}, then {x['then'].rstrip('.')}.")
    L += ["", "External inputs:"] + bullets(b["external_inputs"], lambda x:
          f"{x['source']}: {x['check']}; on failure, {x['on_failure']}")
    L += ["", "Tests:"] + bullets(b["tests"], lambda x:
          f"{x['action']} `{x['test'].strip('`')}` ({x['kind']}): "
          + (proves.get(x["test"].strip("`"), x["proves"]) if x["kind"] == "outcome" else x["proves"])
          + (f" (unit because: {x['why_unit']})" if x.get("why_unit") else ""))
    L += ["", "Done when:"] + bullets(b["done_when"], str)
    L += ["", "Checks:"] + bullets(b["checks"], lambda x: f"`{x}`")
    L += ["", "Out of scope:"] + bullets(b["out_of_scope"], str)
    total, t, why = tier(b["model_basis"])
    L += ["", "Model basis: " + " ".join(f"{m}{b['model_basis'][m]}" for m in MEASURES)
          + f" = {total} -> {t}" + (f" (override: {why})" if why else "")]
    return L


def render_phase(ph, pj, found, plan, stages):
    num, d = ph["phase"], pj["brief"]
    outcomes = {x["id"]: x["observable"] for x in plan["outcomes"]}
    rows = phase_rows(found, stages)
    proves = {t["test"]: outcomes.get(t["outcome"], t["outcome"]) for t in rows}
    L = [f"# Phase {num}: {ph['name']}", "",
         "Implement with the implement-in-phases skill; do not build from this file",
         "without it. Model tiers map to models in [models.md](../models.md).",
         f"Status: {phase_status(pj['record'], found)}", f"Before: {d['before']}", f"After: {d['after']}", "",
         f"Role: {d['role']}", f"Why: {d['why']}", f"How: {d['how']}", "", "## Assumptions"]
    L += bullets(d["assumptions"], lambda a: f"{a['status'].capitalize()}: {a['text']} ({a['evidence']})")
    if plan["size"]["verdict"] == "quick":
        L += ["", "## Size", "", "Quick plan:"] + bullets(plan["size"]["evidence"], str)
    L += ["", "## Outcome tests", f"Budget: {d['test_budget']}", "",
          "| Outcome | Test | Written in | Passes from |", "| --- | --- | --- | --- |"]
    L += [f"| {proves[t['test']]} | `{t['test']}` | {t['written_in']} | {t['passes_from']} |" for t in rows]
    L += ["", "## Stages", "", "| Stage | Goal | Tier | Order | Status |", "| --- | --- | --- | --- | --- |"]
    L += [f"| {sid} | {s['brief']['goal']} | {tier(s['brief']['model_basis'])[1]} | {s['brief']['order']} | "
          f"{stage_status(s)} |" for sid, s in found.items()]
    for sid, s in found.items():
        L += render_stage(sid, s, plan, stages, proves)
    notes = list(d["notes"])
    for x in plan["decisions"]:
        if "all" in x["phases"] or num in x["phases"]:
            line = f"{x['text']} Reason: {x['reason']}"
            if x.get("departs_from"):
                src = x["departs_from"]
                tag = "Assumed (user unavailable)" if x.get("user_answer") == "assumed" else "User's answer"
                line = f"{tag}, departs from the {src['doc']} ({src['section']}: \"{src['quote']}\"): {line}"
            notes.append(line)
    L += ["", "## Notes"] + bullets(notes, str)
    return "\n".join(L) + "\n"


def render_overview(plan, phases, stages):
    L = [f"# Plan: {plan['description']}", "",
         "Rendered by plan-check.py from plan.json and the stage files; never edited by hand.", "",
         f"Goal: {plan['goal']}", f"Why: {plan['why']}", "", "## Outcomes"]
    L += bullets(plan["outcomes"], lambda x: f"{x['id']} {x['title']}: {x['observable']} Check: {x['how_to_check']}")
    L += ["", "## Decisions"] + bullets(plan["decisions"], lambda x:
          f"{x['id']} (phases {', '.join(x['phases'])}): {x['text']} Reason: {x['reason']}")
    L += ["", "## Contracts"] + bullets(registry(stages), lambda c:
          f"{c['kind']} `{c['name']}` (provided by {c['provided_by']}; used by "
          f"{', '.join(c['users'] + c['used_by']) or 'none'}): {c['shape']}")
    L += ["", "## Existing interfaces"] + bullets(plan["existing"], lambda e:
          f"{e['kind']} `{e['name']}` (`{e['path']}`; used by "
          f"{', '.join(u for u, s in stages.items() if e['name'] in s['brief']['uses']) or 'none'}): {e['shape']}")
    L += ["", "## Phases", "", "| Phase | Kind | Status |", "| --- | --- | --- |"]
    L += [f"| [{ph['phase']} {ph['name']}]({ph['dir']}/phase.md) | {ph['kind']} | "
          f"{phase_status((pj or {}).get('record', {}), found)} |" for ph, pj, found in phases]
    return "\n".join(L) + "\n"


def write(plan_dir, plan, phases, nums):
    # writes phase.md for the phases in nums, then plan.md; returns the names written, relative to plan_dir
    stages = flatten(phases)
    texts = {f"{ph['dir']}/phase.md": render_phase(ph, pj, found, plan, stages)
             for ph, pj, found in phases if ph["phase"] in nums}
    texts["plan.md"] = render_overview(plan, phases, stages)
    for name, text in texts.items():
        with open(os.path.join(plan_dir, name), "w") as f:
            f.write(text)
    return list(texts)


def read_plan(plan_dir):
    # (plan.json, [(its phase entry, phase.json, {stage id: stage file})]) as they are, without checks
    plan = read_json(os.path.join(plan_dir, "plan.json"))
    return plan, [(ph, read_json(os.path.join(plan_dir, ph["dir"], "phase.json")),
                   {n[:-5]: read_json(os.path.join(plan_dir, ph["dir"], n))
                    for n in stage_files(os.path.join(plan_dir, ph["dir"]))}) for ph in plan["phases"]]


def packet(plan_dir, sid):
    """The stage packet, the only plan text a builder is given, or None for an unknown stage."""
    plan, phases = read_plan(plan_dir)
    stages = flatten(phases)
    for _, pj, found in phases:
        if sid in found:
            d = pj["brief"]
            outcomes = {x["id"]: x["observable"] for x in plan["outcomes"]}
            proves = {t["test"]: outcomes.get(t["outcome"], t["outcome"]) for t in phase_rows(found, stages)}
            head = [f"Role: {d['role']}", f"Why: {d['why']}", f"How: {d['how']}",
                    f"Before: {d['before']}", f"After: {d['after']}", f"Test budget: {d['test_budget']}"]
            return "\n".join(head + render_stage(sid, found[sid], plan, stages, proves)) + "\n"
    return None


def render_plan(plan_dir):
    """Re-render plan.md and every phase.md from the JSON as it is, without checks; returns the paths written."""
    plan, phases = read_plan(plan_dir)
    return [os.path.join(plan_dir, n) for n in write(plan_dir, plan, phases, [ph["phase"] for ph in plan["phases"]])]


# ---- main

def read_json(path):
    with open(path) as f:
        return json.load(f)


def schema_for(name, outline=False):
    schema = read_json(os.path.join(SKILL, name))
    if not outline:
        return schema
    brief = {**schema["properties"]["brief"], "required": OUTLINE}
    return {**schema, "properties": {**schema["properties"], "brief": brief}}


def load(path, schema, r, file):
    try:
        data = read_json(path)
    except OSError:
        r.add(file, "-", "missing", "not written yet")
        return None
    except ValueError as e:
        r.add(file, "-", "json", f"not valid JSON: {e}")
        return None
    errs = validate(data, schema)
    for where, msg in errs:
        r.add(file, where or "/", "schema", msg)
    return None if errs else data


def load_phase(plan_dir, ph, outline, stage_schema, r):
    # (phase.json or None, {stage id: stage file}); outline mode reads the stage files only
    pdir, num = os.path.join(plan_dir, ph["dir"]), ph["phase"]
    if not os.path.isdir(pdir):
        r.add(f"{ph['dir']}/phase.json", "-", "missing", f"phase folder {ph['dir']} not written yet")
        return None, {}
    pj = None if outline else load(os.path.join(pdir, "phase.json"), schema_for("phase.schema.json"), r,
                                   f"{ph['dir']}/phase.json")
    names = stage_files(pdir)
    if not names:
        r.add(f"{ph['dir']}/phase.json", "-", "missing", f"no stage files in {ph['dir']}")
    for n in names:
        if not n.startswith(num + "."):
            r.add(f"{ph['dir']}/{n}", n[:-5], "id", f"stage {n[:-5]} is in the folder of phase {num}")
    loaded = {n[:-5]: load(os.path.join(pdir, n), stage_schema, r, f"{ph['dir']}/{n}")
              for n in names if n.startswith(num + ".")}
    return pj, {sid: s for sid, s in loaded.items() if s is not None}


def main(argv):
    args, opts = [], {"--repo": ".", "--spec": None, "--design": None, "--phase": None, "--packet": None}
    outline, i = False, 0
    while i < len(argv):
        if argv[i] in opts and i + 1 < len(argv):
            opts[argv[i]] = argv[i + 1]
            i += 2
        elif argv[i] == "--outline":
            outline, i = True, i + 1
        else:
            args.append(argv[i])
            i += 1
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    plan_dir, repo, scope = args[0], opts["--repo"], opts["--phase"]
    if opts["--packet"] is not None:
        try:
            text = packet(plan_dir, opts["--packet"])
        except (OSError, ValueError) as e:
            print(e, file=sys.stderr)
            return 2
        if text is None:
            print(f"--packet {opts['--packet']} is not a stage of the plan", file=sys.stderr)
            return 2
        print(text, end="")
        return 0
    r = Report()
    plan_path = os.path.join(plan_dir, "plan.json")
    if not os.path.exists(plan_path):
        print(f"missing {plan_path}", file=sys.stderr)
        return 2
    plan = load(plan_path, schema_for("plan.schema.json"), r, "plan.json")
    if plan and scope is not None and scope not in [ph["phase"] for ph in plan["phases"]]:
        print(f"--phase {scope} is not a phase of the plan", file=sys.stderr)
        return 2
    named = {k: os.path.join(repo, v) for k, v in (plan or {}).get("docs", {}).items()}
    paths = {k: opts[f"--{k}"] or named.get(k) for k in ("spec", "design")}
    docs = {}
    for k, path in paths.items():
        if path:
            try:
                docs[k] = norm(open(path).read())
            except OSError as e:
                print(f"cannot read the {k}: {e}", file=sys.stderr)
                return 2
    rendered = []
    if plan:
        stage_schema = schema_for("stage.schema.json", outline)
        phases = [(ph, *load_phase(plan_dir, ph, outline, stage_schema, r)) for ph in plan["phases"]]
        stages = flatten(phases)
        check_plan(plan, stages, repo, docs, scope, outline, r)
        ids = {x["id"] for x in plan["decisions"]}
        for sid, s in stages.items():
            check_revision(sid, s, r)
            if not outline:
                check_stage(sid, s, ids, repo, docs, scope, r)
        for ph, pj, _ in phases:
            if pj:
                check_phase(f"{ph['dir']}/phase.json", pj["brief"], ids, r)
        clean = [ph["phase"] for ph, pj, _ in phases if pj and not r.errors(ph["dir"] + "/")]
        if clean and not r.errors("plan.json"):
            rendered = write(plan_dir, plan, phases, clean)
    for x in r.items:
        print(json.dumps(x))
    print(json.dumps({"summary": {"errors": len(r.errors()), "warnings": len(r.items) - len(r.errors()),
                                  "rendered": rendered, "quotes_checked": sorted(docs)}}))
    return 1 if r.errors() else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
