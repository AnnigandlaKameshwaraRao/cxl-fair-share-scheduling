#!/bin/bash
# Run one experiment of the study from its joblist, restoring each host from the checkpoint library.
#
#   run_experiment.sh <joblist.json> <workload>:<slot>                      alone run (1 host)
#   run_experiment.sh <joblist.json> <w0> <w1> <w2> <w3>                    4-host mix, host i = slot i
#
# <workload> is the checkpoint tag used by make_ckpt.sh (for example v4tea, v2stream24m, v6mchase).
# Checkpoints are read from $SIM/ckpt_lib/wl-<workload>/btp_<slot>/checkpoint (see make_ckpt.sh).
# The run directory is $SIM/<joblist name without exp_>_a1; each host writes btp_<i>/stats.txt
# (one block per statistics period) and config.ini. Checkpoint copies are removed afterwards.
#
# This is the same command every run of the study used: unified_run.py with --checkpoints False
# restores the checkpoint found in each host's directory.
set -u
SIM=${SIM:-$HOME/BTP/cxl-clustersim}
SST=${SST:-$HOME/sst-core/bin/sst}
JOB=$(readlink -f "$1"); shift
NAME=$(basename "$JOB" .json); NAME=${NAME#exp_}; E=${NAME}_a1
cd "$SIM" || exit 1
[ -e "$E" ] && { echo "$E exists; remove it or rename the joblist"; exit 1; }
# Open MPI would otherwise bind every run to the same few CPUs
export OMPI_MCA_hwloc_base_binding_policy=none
if [ $# -eq 1 ]; then
    W=${1%:*}; K=${1#*:}; H=1
    mkdir -p "$E/btp_0" && cp -r "ckpt_lib/wl-$W/btp_$K/checkpoint" "$E/btp_0/" || exit 1
elif [ $# -eq 4 ]; then
    H=4; ws=("$@")
    for i in 0 1 2 3; do
        mkdir -p "$E/btp_$i" && cp -r "ckpt_lib/wl-${ws[$i]}/btp_$i/checkpoint" "$E/btp_$i/" || exit 1
    done
else
    sed -n '2,10p' "$0"; exit 1
fi
cp "$JOB" disaggregated_memory/ 2>/dev/null
python3 disaggregated_memory/unified_run.py --count $H --isa x86 --joblist "disaggregated_memory/$(basename "$JOB")" \
    --exp-name "$E" --clock 3GHz --systemd True --checkpoints False --sst "$SST" > "${E}_full_log.txt" 2>&1 < /dev/null
rm -rf -- "$E"/btp_*/checkpoint
echo "$E done, statistics blocks per host:$(for i in $(seq 0 $((H-1))); do echo -n " $(grep -c 'End Simulation Statistics' "$E/btp_$i/stats.txt" 2>/dev/null)"; done)"
