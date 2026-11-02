#!/usr/bin/env python3
"""Snapshot routing state before and after a change, then compare.

Usage:
  python3 prepost.py pre     # before the change
  python3 prepost.py post    # after the change
  python3 prepost.py diff    # what changed?
"""
import json                      # FRR's "... json" output -> Python dicts; also saving snapshots
import subprocess                # run vtysh inside the router containers
import sys                       # command-line word (pre/post/diff) and exit code
from pathlib import Path         # file paths

ROUTERS = ["r1", "r2", "r3", "r4"]
SNAPDIR = Path("snapshots")      # snapshots are saved in this folder


def vtysh_json(router, command):
    cmd = ["docker", "exec", f"clab-netsim-ospf-{router}",
           "vtysh", "-c", command]
    out = subprocess.run(cmd, capture_output=True, text=True,
                         check=True).stdout
    return json.loads(out)                       # JSON text -> Python dict, ready to use


def routes_from(raw):
    """Keep only the chosen route per prefix: protocol + sorted next hops."""
    table = {}                                   # prefix -> short description, e.g. "ospf via 20.238.10.2"
    for prefix, entries in raw.items():          # each prefix can have several candidate routes
        for e in entries:
            if not e.get("selected"):            # skip routes the router isn't actually using
                continue
            hops = sorted(                       # sorted, so the same next hops in a different order aren't a "change"
                nh.get("ip", nh.get("interfaceName", "direct"))   # next-hop IP, or the interface for connected routes
                for nh in e.get("nexthops", []) if nh.get("active")
            )
            table[prefix] = f'{e["protocol"]} via {",".join(hops)}'
    return table


def neighbours_from(raw):
    return sorted(raw.get("neighbors", {}).keys())   # just the neighbours' router IDs


def take_snapshot():
    snap = {}
    for r in ROUTERS:                            # for every router, record neighbours and routes
        snap[r] = {
            "neighbours": neighbours_from(
                vtysh_json(r, "show ip ospf neighbor json")),
            "routes": routes_from(vtysh_json(r, "show ip route json")),
        }
    return snap


def diff(pre, post):
    changes = 0
    for r in ROUTERS:
        a, b = pre[r], post[r]                   # a = before, b = after
        lost = set(a["neighbours"]) - set(b["neighbours"])   # there before, gone now
        new = set(b["neighbours"]) - set(a["neighbours"])    # not there before, there now
        for n in sorted(lost):
            print(f"{r}: NEIGHBOUR LOST   {n}"); changes += 1
        for n in sorted(new):
            print(f"{r}: NEIGHBOUR NEW    {n}"); changes += 1
        ra, rb = a["routes"], b["routes"]
        for p in sorted(ra.keys() - rb.keys()):              # prefixes that disappeared
            print(f"{r}: ROUTE REMOVED    {p}  (was {ra[p]})"); changes += 1
        for p in sorted(rb.keys() - ra.keys()):              # prefixes that appeared
            print(f"{r}: ROUTE ADDED      {p}  ({rb[p]})"); changes += 1
        for p in sorted(ra.keys() & rb.keys()):              # in both: did the path change?
            if ra[p] != rb[p]:
                print(f"{r}: ROUTE CHANGED    {p}  {ra[p]}  ->  {rb[p]}")
                changes += 1
    print(f"\n{changes} change(s)" if changes else "No changes. Safe.")
    return changes


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("pre", "post", "diff"):
        sys.exit(__doc__)                        # wrong usage: print the help text at the top and stop
    step = sys.argv[1]                           # "pre", "post" or "diff"
    SNAPDIR.mkdir(exist_ok=True)
    if step in ("pre", "post"):
        path = SNAPDIR / f"{step}.json"          # snapshots/pre.json or snapshots/post.json
        path.write_text(json.dumps(take_snapshot(), indent=2))   # save the snapshot as a readable file
        print(f"saved {path}")
    else:                                        # "diff": load both files and compare
        pre = json.loads((SNAPDIR / "pre.json").read_text())
        post = json.loads((SNAPDIR / "post.json").read_text())
        sys.exit(1 if diff(pre, post) else 0)    # exit 1 if anything changed


if __name__ == "__main__":
    main()
