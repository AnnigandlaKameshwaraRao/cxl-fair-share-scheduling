#!/usr/bin/env python3
"""Assemble a multi-host experiment from the per-workload checkpoint library.

Host i always uses pool slot i (its address range is baked into its checkpoint),
so `compose.py mix_sp stream pchase` gives host0 = STREAM on slot 0 and
host1 = pchase on slot 1.

Creates (paths relative to ~/cxl-clustersim):
  disaggregated_memory/exp_<name>.json   joblist, one entry per host
  ckpt_lib/<name>/btp_<i>/checkpoint/    copied from ckpt_lib/wl-<workload>/btp_<i>/
Then upload ckpt_lib/<name> to the cluster's ~/btp_checkpoints/<name> and add a
batch line:  <name>  <name>  <hosts>  disaggregated_memory/exp_<name>.json
"""
import json
import os
import shutil
import sys

ROOT = os.path.expanduser("~/cxl-clustersim")
args = sys.argv[1:]
channels = None
if args and args[0].startswith("--channels="):
    channels = args.pop(0).split("=", 1)[1]
name, workloads = args[0], args[1:]
if not workloads or len(workloads) > 8:
    sys.exit("usage: compose.py [--channels=N] <name> <workload[:ckptset] for host0> [host1 ...]  (1-8 hosts)")

job = {}
for i, spec in enumerate(workloads):
    # "stream2t:r2" = same workload, checkpoint set ckpt_lib/wl-stream2t-r2
    w, _, ckset = spec.partition(":")
    wl = f"{ROOT}/disaggregated_memory/wl_{w}_8slot.json"
    if not os.path.isfile(wl):
        wl = f"{ROOT}/disaggregated_memory/wl_{w}_4slot.json"
    src = json.load(open(wl))[str(i)]
    job[str(i)] = src
    ck = f"{ROOT}/ckpt_lib/wl-{w}{'-' + ckset if ckset else ''}/btp_{i}/checkpoint"
    if not os.path.isfile(os.path.join(ck, "m5.cpt")):
        sys.exit(f"missing checkpoint {ck}")
    dst = f"{ROOT}/ckpt_lib/{name}/btp_{i}/checkpoint"
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(ck, dst)
if channels:
    job["0"]["metadata"]["pool-channels"] = channels
job["0"]["metadata"]["comment"] = f"{name}: " + ", ".join(
    f"host{i}={w}" for i, w in enumerate(workloads))
out = f"{ROOT}/disaggregated_memory/exp_{name}.json"
json.dump(job, open(out, "w"), indent=2)
print(f"pool channels: {job['0']['metadata'].get('pool-channels')}")
print(f"{name}: {len(workloads)} hosts ({', '.join(workloads)}) -> {out}")
print(f"batch line: {name}  {name}  {len(workloads)}  disaggregated_memory/exp_{name}.json")
