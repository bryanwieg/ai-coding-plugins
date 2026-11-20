# Sourced by the eval scripts after KIT is set. Defines where runs live and
# the frozen starting repository every run copies.
#
# PIN is the commit the task briefs, references and expected values were
# written against (their line numbers and outputs depend on it). The builder
# directions are NOT frozen: each run gets the current stage-builder.md
# (or EVAL_DIRECTIONS), because the directions are what the evals measure.
PIN=ff8ce98
EVAL_HOME=${EVAL_HOME:-${TMPDIR:-/tmp}/phased-delivery-evals}
RUNS=$EVAL_HOME/runs
BASE=$EVAL_HOME/base-$PIN
DIRECTIONS=${EVAL_DIRECTIONS:-$KIT/../plugins/phased-delivery/skills/implement-in-phases/stage-builder.md}

if [ ! -d "$BASE" ]; then
  mkdir -p "$EVAL_HOME"
  building=$(mktemp -d "$EVAL_HOME/base.XXXXXX")
  git -C "$KIT/.." archive "$PIN" | tar -x -C "$building"
  rm -rf "$building/evals"
  mv "$building" "$BASE"
fi
