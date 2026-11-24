#!/usr/bin/env python3
"""Check a phased plan written as JSON and render its phase files.

Usage:
  plan-check.py PLAN_DIR [--repo DIR] [--spec FILE] [--design FILE] [--outline]

The planner writes PLAN_DIR/.plan/plan.json (plan.schema.json: outcomes,
cross-phase decisions, the contract registry, outcome tests, phases and
stages) and one PLAN_DIR/.plan/NN.json per phase (phase.schema.json: the
stage briefs). The field guides in skills/plan-in-phases say how to fill
them. This script checks what can be checked without judgment and renders
each phase whose JSON is clean to PLAN_DIR/NN-name.md in the phase file
layout. --outline checks plan.json only (before the phase JSON exists).

--spec and --design default to the paths a plan names in its sources and
must be given when quotes are to be checked; --repo defaults to the current
directory.

Output: one JSON line per problem, {"file", "where", "kind", "msg", "level"},
then a summary line. level "error" must be fixed; "warning" is reported for
the planner to judge. Exit codes: 0 no errors; 1 errors; 2 bad usage or a
missing or unreadable file.
"""

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
STAGE_ID = re.compile(r"^\d\d\.\d+$")
TESTY = re.compile(r"(^|/)tests?/|(^|/)test_|\.test\.|::test_")
CODEY = re.compile(r"```|`[^`\n]*(?:==|!=|\bis (?:not )?None\b|\breturn\b|\.get\(|\bfor \w+ in\b|\bif\b|\belse\b|\+=)[^`\n]*`")
WHERE = re.compile(r"(?:\./)?([\w./-]+):(\d+)(?:-(\d+))?")
PLAN_IDS = re.compile(r"\b[CD]\d{1,3}\b")
WARNINGS = {"code", "length", "other", "order-hint"}


# ---- a small JSON Schema subset (the plugin's scripts use the standard library only)

def validate(data, schema, root=None, path=""):
    root = root or schema
    if "$ref" in schema:
        schema = root["definitions"][schema["$ref"].split("/")[-1]]
    out = []
    t = schema.get("type")
    types = {"object": dict, "array": list, "string": str, "boolean": bool}
    if t == "integer":
        if not isinstance(data, int) or isinstance(data, bool):
            return [(path, f"must be an integer, got {type(data).__name__}")]
        if data < schema.get("minimum", data) or data > schema.get("maximum", data):
            out.append((path, f"{data} is outside {schema.get('minimum')}..{schema.get('maximum')}"))
    elif t and not isinstance(data, types[t]):
        return [(path, f"must be {t}, got {type(data).__name__}")]
    if "enum" in schema and data not in schema["enum"]:
        out.append((path, f"{data!r} is not one of {schema['enum']}"))
    if "pattern" in schema and isinstance(data, str) and not re.search(schema["pattern"], data):
        out.append((path, f"{data!r} does not match {schema['pattern']}"))
    if isinstance(data, dict):
        props = schema.get("properties", {})
        for k in schema.get("required", []):
            if k not in data:
                out.append((path, f"missing {k!r}"))
        for k, v in data.items():
            if k in props:
                out += validate(v, props[k], root, f"{path}/{k}")
            elif schema.get("additionalProperties") is False:
                out.append((path, f"unknown field {k!r}"))
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


def build_positions(plan):
    # global build position per stage; a parallel stage shares its partner's position
    pos, n = {}, 0
    for ph in plan["phases"]:
        for s in ph["stages"]:
            m = re.match(r"parallel with (\d\d\.\d+)", s["order"])
            if m and m.group(1) in pos:
                pos[s["id"]] = pos[m.group(1)]
            else:
                n += 1
                pos[s["id"]] = n
    return pos


class Report:
    def __init__(self):
        self.items = []

    def add(self, file, where, kind, msg):
        self.items.append({"file": file, "where": where, "kind": kind, "msg": msg,
                           "level": "warning" if kind in WARNINGS else "error"})

    def errors(self, file=None):
        return [x for x in self.items if x["level"] == "error" and (file is None or x["file"] == file)]


# ---- plan.json

def check_plan(plan, repo, docs, r):
    F = "plan.json"
    stages = {s["id"]: (ph, s) for ph in plan["phases"] for s in ph["stages"]}
    contracts = {c["id"]: c for c in plan["contracts"]}
    pos = build_positions(plan)
    for group, prefix in (("outcomes", "O"), ("decisions", "D")):
        ids = [x["id"] for x in plan[group]]
        if ids != [f"{prefix}{i}" for i in range(1, len(ids) + 1)]:
            r.add(F, group, "id", f"ids must run {prefix}1..{prefix}{len(ids)} in order")
    nums = [ph["phase"] for ph in plan["phases"]]
    if nums != [f"{i:02d}" for i in range(1, len(nums) + 1)]:
        r.add(F, "phases", "id", f"phases must be numbered 01..{len(nums):02d} in build order, got {nums}")
    for ph in plan["phases"]:
        if not ph["file"].startswith(ph["phase"] + "-"):
            r.add(F, ph["phase"], "id", f"file {ph['file']} does not start with {ph['phase']}-")
        for s in ph["stages"]:
            if not s["id"].startswith(ph["phase"] + "."):
                r.add(F, s["id"], "id", f"stage {s['id']} is listed in phase {ph['phase']}")
    if len(stages) != sum(len(ph["stages"]) for ph in plan["phases"]):
        r.add(F, "stages", "id", "duplicate stage ids")
    if len(contracts) != len(plan["contracts"]):
        r.add(F, "contracts", "id", "duplicate contract ids")
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
    for ph in plan["phases"]:
        for s in ph["stages"]:
            for f in s["files"]:
                if f["action"] == "create":
                    created.setdefault(f["path"], s["id"])
    for c in plan["contracts"]:
        w, prov = c["id"], c["provided_by"]
        if prov.startswith("existing:"):
            path = prov[len("existing:"):].split("::")[0]
            m = WHERE.fullmatch(path)
            path = m.group(1) if m else path
            if not os.path.exists(os.path.join(repo, path)):
                r.add(F, w, "ref", f"{c['name']}: existing path {path} not found")
        elif prov not in stages:
            r.add(F, w, "ref", f"{c['name']}: provided_by {prov} is not a stage or existing:<path>")
        elif w not in stages[prov][1]["provides"]:
            r.add(F, w, "registry", f"{c['name']}: stage {prov} does not list {w} in provides")
        if not [u for u in c["used_by"] if c["kind"] == "test-helper" or not TESTY.search(u)]:
            r.add(F, w, "internal", f"{c['name']}: used only by tests; that is internal: leave it out and state "
                  "what tests observe as behaviour")
        for u in c["used_by"]:
            if not STAGE_ID.match(u):
                continue
            if u not in stages:
                r.add(F, w, "ref", f"{c['name']}: used_by {u} is not a stage")
                continue
            if w not in stages[u][1]["uses"]:
                r.add(F, w, "registry", f"{c['name']}: used_by {u}, but {u} does not list {w} in uses")
            if prov in pos and pos[prov] >= pos[u]:
                r.add(F, w, "order", f"{c['name']}: provided by {prov}, used by {u}, which is not built after it")
        if len(c["shape"]) > SHAPE_MAX[c["kind"]]:
            r.add(F, w, "shape", f"{c['name']}: shape is {len(c['shape'])} chars > {SHAPE_MAX[c['kind']]} for {c['kind']}")
        if c["kind"] == "other":
            r.add(F, w, "other", f"{c['name']}: kind other" + ("" if c.get("other_reason") else " without other_reason"))
    for sid, (ph, s) in stages.items():
        for cid in s["provides"] + s["uses"]:
            if cid not in contracts:
                r.add(F, sid, "ref", f"lists unknown contract {cid}")
        for cid in s["provides"]:
            if cid in contracts and contracts[cid]["provided_by"] != sid:
                r.add(F, sid, "registry", f"provides {cid}, but the registry says {contracts[cid]['provided_by']}")
        for cid in s["uses"]:
            if cid in contracts and sid not in contracts[cid]["used_by"]:
                r.add(F, sid, "registry", f"uses {cid}, but {sid} is not in its used_by")
        for f in s["files"]:
            exists = os.path.exists(os.path.join(repo, f["path"]))
            if f["action"] == "create" and exists:
                r.add(F, sid, "files", f"creates {f['path']}, which already exists")
            if f["action"] != "create" and not exists and not (
                    f["path"] in created and pos[created[f["path"]]] < pos[sid]):
                r.add(F, sid, "files", f"{f['action']}s {f['path']}, which does not exist and no earlier stage creates")
        m = re.match(r"(?:after|parallel with) (\d\d\.\d+)", s["order"])
        listed = list(stages)
        if m and m.group(1) not in stages:
            r.add(F, sid, "order", f"order names {m.group(1)}, which is not a stage")
        elif m and listed.index(m.group(1)) > listed.index(sid):
            r.add(F, sid, "order", f"order names {m.group(1)}, which is listed after {sid}; list stages in build order")
        elif m and s["order"].startswith("after"):
            dep = stages[m.group(1)][1]
            if not set(dep["provides"]) & set(s["uses"]) and not (
                    {f["path"] for f in dep["files"]} & {f["path"] for f in s["files"]}):
                r.add(F, sid, "order-hint", f"ordered after {m.group(1)} but uses none of its contracts and shares "
                      "no file; if nothing else needs it first, order it after the stage it does depend on or in parallel")
        if m and m.group(1) in stages and s["order"].startswith("parallel"):
            shared = {f["path"] for f in s["files"]} & {f["path"] for f in stages[m.group(1)][1]["files"]}
            if shared:
                r.add(F, sid, "parallel", f"shares {sorted(shared)} with parallel stage {m.group(1)}")
    have = {t["outcome"] for t in plan["outcome_tests"]}
    for x in plan["outcomes"]:
        if x["id"] not in have:
            r.add(F, x["id"], "coverage", f"outcome {x['id']} has no outcome test")
    known = {x["id"] for x in plan["outcomes"]}
    for t in plan["outcome_tests"]:
        if t["outcome"] not in known:
            r.add(F, t["test"], "ref", f"outcome {t['outcome']} is not in outcomes")
        for k in ("written_in", "passes_from"):
            if t[k] not in stages:
                r.add(F, t["test"], "ref", f"{k} {t[k]} is not a stage")
        if t["written_in"] in pos and t["passes_from"] in pos and pos[t["written_in"]] > pos[t["passes_from"]]:
            r.add(F, t["test"], "order", f"written in {t['written_in']}, after it must pass ({t['passes_from']})")
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


# ---- NN.json

def check_phase(num, d, plan, repo, docs, r):
    F = f"{num}.json"
    ph = next(p for p in plan["phases"] if p["phase"] == num)
    want = {s["id"]: s for s in ph["stages"]}
    got = {s["id"]: s for s in d["stages"]}
    if list(want) != [s["id"] for s in d["stages"]]:
        r.add(F, "stages", "plan", f"stages are {list(got)}, plan.json gives {list(want)} in that order")
    contracts = {c["id"]: c for c in plan["contracts"]}
    ids = set(contracts) | {x["id"] for x in plan["decisions"]}
    table = {(t["test"].strip("`"), s) for t in plan["outcome_tests"] for s in (t["written_in"], t["passes_from"])}
    for sid, s in got.items():
        where = lambda field: f"{sid}{field}"
        if sid in want:
            wf = {f["path"]: f["action"] for f in want[sid]["files"]}
            gf = {f["path"]: f["action"] for f in s["files"]}
            if wf != gf:
                r.add(F, sid, "plan", f"files differ from plan.json: missing {sorted(set(wf) - set(gf))}, "
                      f"extra {sorted(set(gf) - set(wf))}, or a different action")
            provided = " ".join(c["name"] + " " + c["shape"] for c in s["contracts"] if c["direction"] == "provides").lower()
            for cid in want[sid]["provides"]:
                if cid in contracts and norm(contracts[cid]["name"]) not in norm(provided):
                    r.add(F, sid, "plan", f"does not provide `{contracts[cid]['name']}`, which plan.json gives it")
        if len(s["goal"]) > GOAL_MAX:
            r.add(F, sid, "length", f"goal is {len(s['goal'])} chars > {GOAL_MAX}")
        for f, n in LIMITS.items():
            if len(s[f]) > n:
                r.add(F, sid, "length", f"{f} has {len(s[f])} items > {n}")
        if len(s["context"]["code_read"]) > CODE_READ_MAX:
            r.add(F, sid, "length", f"code_read has {len(s['context']['code_read'])} items > {CODE_READ_MAX}")
        if len(s["context"]["design"]) > DESIGN_MAX:
            r.add(F, sid, "length", f"design has {len(s['context']['design'])} items > {DESIGN_MAX}")
        for c in s["contracts"]:
            others = [x for x in c["counterparts"] if x != sid]
            if c["kind"] != "test-helper":
                others = [x for x in others if not TESTY.search(x)]
            if not others:
                r.add(F, sid, "internal", f"contract {c['name']}: no counterpart outside {sid} other than tests; "
                      "internal: leave it out and state what tests observe as behaviour")
            if len(c["shape"]) > SHAPE_MAX[c["kind"]]:
                r.add(F, sid, "shape", f"contract {c['name']}: shape is {len(c['shape'])} chars > {SHAPE_MAX[c['kind']]} for {c['kind']}")
            if c["kind"] == "other":
                r.add(F, sid, "other", f"contract {c['name']} is kind other" + ("" if c.get("other_reason") else " without other_reason"))
        for t in s["tests"]:
            if t["kind"] == "unit" and not t.get("why_unit"):
                r.add(F, sid, "tests", f"unit test {t['test']} needs why_unit")
            if (t["test"].strip("`"), sid) in table:
                r.add(F, sid, "tests", f"{t['test']} is an outcome test of this stage in plan.json; the rendered brief lists it")
        for x in s["context"]["design"]:
            check_quote(F, where("/context/design"), x, docs, r)
        for x in s["context"]["code_read"]:
            check_cite(F, where("/context/code_read"), x["where"], x["shows"], repo, r)
        for path, text in strings(s):
            if not path.startswith("/contracts") or not path.endswith("/shape"):
                if CODEY.search(text):
                    r.add(F, where(path), "code", CODEY.search(text).group(0)[:80])
    for path, text in strings(d):
        m = next((m for m in PLAN_IDS.finditer(text) if m.group(0) in ids), None)
        if m:
            r.add(F, path, "standalone", f"uses the plan.json id {m.group(0)}, which the phase file does not define; "
                  "name the contract or decision instead")
        if ".plan/" in text:
            r.add(F, path, "standalone", "cites the .plan folder; the phase file must stand alone")
    for k in ("before", "after"):
        n = len(re.findall(r"[.!?](?:\s|$)", d[k]))
        if n > SENTENCES_MAX:
            r.add(F, k, "length", f"{k} has {n} sentences > {SENTENCES_MAX}")


# ---- rendering

def bullets(items, fmt):
    return [f"- {fmt(x)}" for x in items] or ["none"]


def render(num, d, plan):
    ph = next(p for p in plan["phases"] if p["phase"] == num)
    order = {s["id"]: s["order"] for s in ph["stages"]}
    titles = {s["id"]: s["title"] for s in ph["stages"]}
    sids = set(order)
    outcomes = {x["id"]: x for x in plan["outcomes"]}
    rows = [t for t in plan["outcome_tests"] if t["written_in"] in sids or t["passes_from"] in sids]
    L = [f"# Phase {num}: {ph['name']}", "",
         "Implement with the implement-in-phases skill; do not build from this file",
         "without it. Model tiers map to models in [models.md](models.md).",
         "Status: planned", f"Before: {d['before']}", f"After: {d['after']}", "", "## Assumptions"]
    L += bullets(d["assumptions"], lambda a: f"{a['status'].capitalize()}: {a['text']} ({a['evidence']})")
    if plan["size"]["verdict"] == "quick":
        L += ["", "## Size", "", "Quick plan:"] + bullets(plan["size"]["evidence"], str)
    L += ["", "## Outcome tests", f"Budget: {d['test_budget']}", "",
          "| Outcome | Test | Written in | Passes from |", "| --- | --- | --- | --- |"]
    L += [f"| {outcomes[t['outcome']]['observable'] if t['outcome'] in outcomes else t['outcome']} | "
          f"`{t['test'].strip('`')}` | {t['written_in']} | {t['passes_from']} |" for t in rows]
    L += ["", "## Stages", "", "| Stage | Goal | Tier | Order | Status |", "| --- | --- | --- | --- | --- |"]
    L += [f"| {s['id']} | {s['goal']} | {tier(s['model_basis'])[1]} | {order.get(s['id'], '?')} | planned |"
          for s in d["stages"]]
    for s in d["stages"]:
        c = s["context"]
        L += ["", f"## {s['id']} {titles.get(s['id'], '')}".rstrip(), "", f"Goal: {s['goal']}", "", "Context:"]
        ctx = [f"- Builds on {x['source']}: {x['what']}" for x in c["builds_on"]]
        ctx += [f"- `{x['where']}`: {x['fact']}" for x in c["code_read"]]
        ctx += [f"- {x['doc'].capitalize()}, {x['section']}: \"{x['quote']}\"" for x in c["design"]]
        L += ctx or ["none"]
        L += ["", "Contracts:"] + bullets(s["contracts"], lambda x:
              f"{x['kind']} `{x['name']}` ({x['direction']}; {', '.join(x['counterparts'])}): {x['shape']}")
        L += ["", "Files:"] + bullets(s["files"], lambda x: f"`{x['path']}` ({x['action']}): {x['role']}")
        L += ["", "Behaviour:"] + bullets(s["behaviour"], lambda x:
              f"Given {x['given']}, when {x['when']}, then {x['then'].rstrip('.')}.")
        L += ["", "External inputs:"] + bullets(s["external_inputs"], lambda x:
              f"{x['source']}: {x['check']}; on failure, {x['on_failure']}")
        tests = [f"- writes `{t['test'].strip('`')}` (outcome): {outcomes.get(t['outcome'], {}).get('observable', t['outcome'])}"
                 for t in rows if t["written_in"] == s["id"]]
        tests += [f"- turns on `{t['test'].strip('`')}` (outcome): {outcomes.get(t['outcome'], {}).get('observable', t['outcome'])}"
                  for t in rows if t["passes_from"] == s["id"] and t["written_in"] != s["id"]]
        tests += [f"- {x['action']} `{x['test'].strip('`')}` ({x['kind']}): {x['proves']}"
                  + (f" (unit because: {x['why_unit']})" if x.get("why_unit") else "") for x in s["tests"]]
        L += ["", "Tests:"] + (tests or ["none"])
        L += ["", "Done when:"] + bullets(s["done_when"], str)
        L += ["", "Out of scope:"] + bullets(s["out_of_scope"], str)
        total, t, why = tier(s["model_basis"])
        L += ["", "Model basis: " + " ".join(f"{m}{s['model_basis'][m]}" for m in MEASURES)
              + f" = {total} -> {t}" + (f" (override: {why})" if why else "")]
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


# ---- main

def load(path, schema_name, r, file):
    try:
        data = json.load(open(path))
    except OSError:
        return None
    except ValueError as e:
        r.add(file, "-", "json", f"not valid JSON: {e}")
        return None
    errs = validate(data, json.load(open(os.path.join(SKILL, schema_name))))
    for where, msg in errs:
        r.add(file, where or "/", "schema", msg)
    return None if errs else data


def main(argv):
    args, opts = [], {"--repo": ".", "--spec": None, "--design": None}
    outline_only, i = False, 0
    while i < len(argv):
        if argv[i] in opts and i + 1 < len(argv):
            opts[argv[i]] = argv[i + 1]
            i += 2
        elif argv[i] == "--outline":
            outline_only, i = True, i + 1
        else:
            args.append(argv[i])
            i += 1
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    plan_dir, repo = args[0], opts["--repo"]
    docs = {}
    for k in ("spec", "design"):
        if opts[f"--{k}"]:
            try:
                docs[k] = norm(open(opts[f"--{k}"]).read())
            except OSError as e:
                print(f"cannot read --{k}: {e}", file=sys.stderr)
                return 2
    r = Report()
    plan_path = os.path.join(plan_dir, ".plan", "plan.json")
    if not os.path.exists(plan_path):
        print(f"missing {plan_path}", file=sys.stderr)
        return 2
    plan = load(plan_path, "plan.schema.json", r, "plan.json")
    rendered, missing = [], []
    if plan:
        check_plan(plan, repo, docs, r)
        if not outline_only:
            for ph in plan["phases"]:
                num, f = ph["phase"], f"{ph['phase']}.json"
                path = os.path.join(plan_dir, ".plan", f)
                if not os.path.exists(path):
                    missing.append(f)
                    r.add(f, "-", "missing", "phase JSON not written yet")
                    continue
                d = load(path, "phase.schema.json", r, f)
                if d is None:
                    continue
                check_phase(num, d, plan, repo, docs, r)
                if not r.errors(f) and not r.errors("plan.json"):
                    open(os.path.join(plan_dir, ph["file"]), "w").write(render(num, d, plan))
                    rendered.append(ph["file"])
    for x in r.items:
        print(json.dumps(x))
    print(json.dumps({"summary": {"errors": len(r.errors()), "warnings": len(r.items) - len(r.errors()),
                                  "rendered": rendered, "quotes_checked": sorted(docs)}}))
    return 1 if r.errors() else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
