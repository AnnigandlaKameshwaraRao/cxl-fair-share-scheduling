#!/bin/bash
# Take ONE host's boot checkpoint on the desktop with KVM (one host at a time keeps
# memory low). Builds the exact gem5 command unified_run.py would, from a joblist entry.
# Usage: make_ckpt.sh <joblist.json> <host-index> <tag> [timeout-min]
# Output: ckpt_lib/<tag>/<experiment>_<host>/checkpoint/  (layout RESTORE_FROM expects)
set -u
JOBLIST=$1; HOST=$2; TAG=$3; TMO=${4:-60}
cd "${SIM:-$HOME/cxl-clustersim}" || exit 1
ARGS=$(python3 - "$JOBLIST" "$HOST" <<'PY'
import json, sys, shlex
j = json.load(open(sys.argv[1]))[sys.argv[2]]
a = ["--instance=" + sys.argv[2], "--ff-core-type=kvm",
     "--roi-core-type=" + j["cpu"]["roi-core"], "--core-count=" + j["cpu"]["count"],
     "--core-frequency=3GHz", "--cache-type=" + j["cache"]["type"],
     "--l1i-size=" + j["cache"]["l1i-size"], "--l1d-size=" + j["cache"]["l1d-size"],
     "--l2-size=" + j["cache"]["l2-size"], "--l3-size=" + j["cache"]["l3-size"],
     "--l3-assoc=" + j["cache"]["l3-assoc"],
     "--local-memory-type=" + j["local-memory"]["type"],
     "--local-memory-size=" + j["local-memory"]["size"],
     "--remote-memory-shared=" + j["remote-memory"]["shared"],
     "--remote-memory-start=" + j["remote-memory"]["start"],
     "--remote-memory-end=" + j["remote-memory"]["end"],
     "--is-composable=false", "--cmd=" + "__fmt__".join(j["workitem"]["cmd"]),
     "--disk-path=" + j["workitem"]["disk"], "--kernel-path=" + j["workitem"]["kernel"],
     "--bootloader-path=" + j["workitem"]["bootloader"], "--systemd=true"]
print(j["metadata"]["experiment"]); print(" ".join(shlex.quote(x) for x in a))
PY
) || exit 1
EXPN=$(echo "$ARGS" | head -1); GARGS=$(echo "$ARGS" | tail -1)
OUTD=$PWD/ckpt_lib/$TAG/${EXPN}_$HOST
rm -rf "$OUTD"; mkdir -p "$OUTD"
echo "[$(date +%T)] host $HOST -> $OUTD (timeout ${TMO}m)"
eval timeout ${TMO}m build/ALL/gem5.opt -re --outdir="$OUTD" \
    disaggregated_memory/configs/x86_unified.py $GARGS
RC=$?
if [ -f "$OUTD/checkpoint/m5.cpt" ]; then
    echo "[$(date +%T)] CHECKPOINT OK host $HOST ($(du -sh "$OUTD/checkpoint" | cut -f1))"
else
    echo "[$(date +%T)] NO CHECKPOINT host $HOST (gem5 rc=$RC) -- see $OUTD/simerr.txt"; exit 1
fi
