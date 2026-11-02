#!/usr/bin/env python3
"""Check every router's running config against a few house rules."""
import subprocess                # to run vtysh inside each router container
import sys                       # for the exit code

ROUTERS = ["r1", "r2", "r3", "r4"]


def get_config(router):
    cmd = ["docker", "exec", f"clab-netsim-ospf-{router}",
           "vtysh", "-c", "show running-config"]      # the router's live config
    return subprocess.run(cmd, capture_output=True, text=True,
                          check=True).stdout          # check=True: crash loudly if the command fails


def interface_blocks(config):
    """Return {interface_name: [lines inside that block]}."""
    blocks, current = {}, None                   # current = which interface block we're inside (None = none)
    for line in config.splitlines():
        if line.startswith("interface "):        # a new block starts, e.g. "interface eth1"
            current = line.split()[1]            # remember its name: "eth1"
            blocks[current] = []
        elif line.strip() == "exit" or not line.startswith(" "):
            current = None                       # "exit" or a non-indented line ends the block
        elif current:
            blocks[current].append(line.strip()) # an indented line inside the block: keep it
    return blocks


def check(router, config):
    problems = []
    if "auto-cost reference-bandwidth 10000" not in config:   # rule 1: same reference bandwidth everywhere
        problems.append("reference bandwidth is not 10000")
    if "ospf router-id" not in config:                        # rule 2: router ID set by hand
        problems.append("router-id not set")
    for name, lines in interface_blocks(config).items():
        if name == "lo":                         # skip the loopback: it isn't a cable to anything
            continue
        if not any(l.startswith("description") for l in lines):   # rule 3: every interface described
            problems.append(f"{name}: no description")
        if "shutdown" in lines:                  # rule 4: nothing shut down by accident
            problems.append(f"{name}: interface is shut down")
    return problems                              # empty list = PASS


def main():
    failed = False
    for r in ROUTERS:
        problems = check(r, get_config(r))       # fetch the config, then check it
        if problems:
            failed = True
            for p in problems:
                print(f"FAIL {r}: {p}")
        else:
            print(f"PASS {r}")
    sys.exit(1 if failed else 0)                 # 1 = something failed (a pipeline can stop on this)


if __name__ == "__main__":
    main()
