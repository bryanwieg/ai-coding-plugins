#!/bin/sh
# stage-stats.sh [REV-RANGE]: write a Markdown report of the work each model
# did, from implement-in-phases commit trailers (Stage, Fixes-Stage, Tool,
# Model, Effort, Attempt, Tokens, Earlier-Attempt). Run inside the
# repository; REV-RANGE defaults to HEAD (use <start>..HEAD for one plan).
#
# Per model and effort:
#   Stages        accepted stages it built
#   First try     of those, accepted on the stage's first dispatch (Attempt 1)
#   Clean         first try and never fixed afterwards: right first time
#   Failed tries  its attempts that failed and were rerun (Earlier-Attempt)
#   Fixes needed  later commits fixing a stage it built (Fixes-Stage)
#   Tokens spent  its builds, failed tries and the fixes it made
#   Wasted        tokens of its failed tries
#   Per stage     build tokens per accepted stage
set -eu
range=${1:-HEAD}

# One line per commit, fields separated by 0x1F; Earlier-Attempt entries by 0x1E.
git log --format='%(trailers:key=Stage,valueonly,separator=%x2C)%x1F%(trailers:key=Fixes-Stage,valueonly,separator=%x2C)%x1F%(trailers:key=Model,valueonly,separator=%x2C)%x1F%(trailers:key=Effort,valueonly,separator=%x2C)%x1F%(trailers:key=Attempt,valueonly,separator=%x2C)%x1F%(trailers:key=Tokens,valueonly,separator=%x2C)%x1F%(trailers:key=Earlier-Attempt,valueonly,separator=%x1E)%x1F%(trailers:key=Tool,valueonly,separator=%x2C)%x1F%s%x1F%h' "$range" |
awk -v range="$range" '
  BEGIN { FS = "\037" }
  function key(m, e) { return (m == "" ? "?" : m) " " (e == "" ? "default" : e) }
  function add_tokens(k, t) {
    if (t ~ /^[0-9]+$/) spent[k] += t; else unknown[k]++
  }
  function tok(n, u) { return n (u ? " (+" u " unknown)" : "") }
  $1 != "" {
    k = key($3, $4); seen[k] = 1; nstages++
    if ($8 != "") tool[k] = $8
    stages[k]++; builder[$1] = k
    attempt = ($5 == "" ? 1 : $5)
    if (attempt == 1) { first[k]++; firsttry[$1] = 1 }
    add_tokens(k, $6)
    if ($6 ~ /^[0-9]+$/) { built[k] += $6; counted[k]++ }
    if ($7 != "") {
      n = split($7, entries, "\036")
      for (i = 1; i <= n; i++) {
        split(entries[i], w, " ")
        f = key(w[1], w[2]); seen[f] = 1; failed[f]++
        add_tokens(f, w[3])
        if (w[3] ~ /^[0-9]+$/) wasted[f] += w[3]
        why = entries[i]; for (j = 1; j <= 3; j++) sub(/^[^ ]* */, "", why)
        reruns = reruns "- " $1 " accepted from " k " on attempt " attempt \
          "; earlier " f " (" w[3] " tokens): " why "\n"
      }
    }
  }
  $2 != "" {
    k = key($3, $4); seen[k] = 1; if ($8 != "") tool[k] = $8
    add_tokens(k, $6)
    nfix++; fixstage[nfix] = $2; fixby[nfix] = k; fixtok[nfix] = $6
    fixsubj[nfix] = $9; fixhash[nfix] = $10
  }
  END {
    print "## Work by model"
    print ""
    print "Range `" range "`: " nstages + 0 " accepted stages, " nfix + 0 " later fixes."
    print ""
    print "| Model | Effort | Tool | Stages | First try | Clean | Failed tries | Fixes needed | Tokens spent | Wasted | Per stage |"
    print "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    for (i = 1; i <= nfix; i++) {
      fixed[fixstage[i]] = 1
      if (fixstage[i] in builder) fixes[builder[fixstage[i]]]++
    }
    for (s in builder) if ((s in firsttry) && !(s in fixed)) cleanc[builder[s]]++
    for (k in seen) {
      split(k, me, " ")
      printf "| %s | %s | %s | %d | %d/%d | %d/%d | %d | %d | %s | %d | %s |\n",
        me[1], me[2], (k in tool ? tool[k] : "-"), stages[k],
        first[k], stages[k], cleanc[k], stages[k], failed[k], fixes[k],
        tok(spent[k] + 0, unknown[k]), wasted[k],
        counted[k] ? int(built[k] / counted[k]) : "n/a"
      tstages += stages[k]; tfirst += first[k]; tclean += cleanc[k]
      tfailed += failed[k]; tfixes += fixes[k]; tspent += spent[k]
      tunknown += unknown[k]; twasted += wasted[k]
    }
    printf "| **All** | | | %d | %d/%d | %d/%d | %d | %d | %s | %d | |\n",
      tstages, tfirst, tstages, tclean, tstages, tfailed, tfixes,
      tok(tspent + 0, tunknown), twasted + 0
    print ""
    print "### Reruns"
    print ""
    printf "%s", (reruns == "" ? "None.\n" : reruns)
    print ""
    print "### Fixes after acceptance"
    print ""
    if (!nfix) print "None."
    for (i = 1; i <= nfix; i++)
      printf "- %s (built by %s): %s; by %s, %s tokens [%s]\n", fixstage[i],
        (fixstage[i] in builder ? builder[fixstage[i]] : "outside this range"),
        fixsubj[i], fixby[i], (fixtok[i] == "" ? "unknown" : fixtok[i]), fixhash[i]
  }'
