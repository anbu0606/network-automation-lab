"""OSPF health check for the Lab 1 network: are all the expected neighbours Full?"""
import re                                    # regular expressions: find patterns in text
import subprocess                            # run another program (docker) from Python
import sys                                   # used at the end to set the exit code
from concurrent.futures import ThreadPoolExecutor   # run several checks at the same time

LAB = "netsim-ospf"                      # the Containerlab lab name
EXPECTED = {                             # the "source of truth": who should be neighbours
    "r1": {"2.2.2.2", "3.3.3.3", "4.4.4.4"},     # R1 should see R2, R3 and R4
    "r2": {"1.1.1.1", "3.3.3.3", "4.4.4.4"},
    "r3": {"1.1.1.1", "2.2.2.2"},
    "r4": {"1.1.1.1", "2.2.2.2"},
}

IPV4 = r"\d+\.\d+\.\d+\.\d+"                              # pattern for an IP: digits.digits.digits.digits
ROW = re.compile(rf"^({IPV4})\s+(\d+)\s+(\S+)")          # neighbour ID, priority, state
ADDR_IFACE = re.compile(rf"\s({IPV4})\s+([\w.-]+):")    # neighbour address, our interface


def vtysh(router, command):
    """Run one FRR command inside a lab router and return its text output."""
    result = subprocess.run(
        ["docker", "exec", f"clab-{LAB}-{router}", "vtysh", "-c", command],   # same as typing it in the Shell
        capture_output=True, text=True, timeout=20,   # keep the output as text; give up after 20 s
    )
    if result.returncode != 0:                        # non-zero = the command failed
        raise RuntimeError(result.stderr.strip() or f"vtysh failed on {router}")
    return result.stdout                              # the table you'd normally see on screen


def parse_neighbors(text):
    """Turn 'show ip ospf neighbor' output into {router_id: {state, address, interface}}."""
    neighbors = {}                                   # router ID -> details
    for line in text.splitlines():                   # look at the output one line at a time
        row = ROW.match(line)                        # does the line START with a router ID?
        if not row:
            continue                                     # skip headers and blank lines
        rid, _priority, state = row.groups()         # the three captured pieces, e.g. "2.2.2.2", "1", "Full/DR"
        extra = ADDR_IFACE.search(line)              # also find the neighbour's IP and our interface name
        neighbors[rid] = {
            "state": state,
            "address": extra.group(1) if extra else "?",     # "?" if that part wasn't found
            "interface": extra.group(2) if extra else "?",
        }
    return neighbors


def check(router):
    """Compare one router's real neighbours with the expected set."""
    try:
        neighbors = parse_neighbors(vtysh(router, "show ip ospf neighbor"))
    except Exception as err:                             # router down, container missing...
        return router, [f"could not run command: {err}"]
    problems = []
    full = {rid for rid, n in neighbors.items() if n["state"].startswith("Full")}   # only the healthy ones
    for rid in sorted(EXPECTED[router] - full):          # expected but not Full = a problem
        state = neighbors.get(rid, {}).get("state", "missing")   # its real state, or "missing" if not listed at all
        problems.append(f"neighbour {rid} is {state}, expected Full")
    for rid in sorted(set(neighbors) - EXPECTED[router]):        # present but not expected = also worth reporting
        problems.append(f"unexpected neighbour {rid}")
    return router, problems                              # an empty list means PASS


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=8) as pool:          # check all routers at once
        results = list(pool.map(check, EXPECTED))            # run check() for r1, r2, r3, r4 in parallel
    failed = False
    for router, problems in results:                         # print one result per router
        if problems:
            failed = True
            print(f"FAIL {router}")
            for p in problems:
                print(f"     - {p}")
        else:
            print(f"PASS {router}: {len(EXPECTED[router])} neighbours Full")
    sys.exit(1 if failed else 0)                             # non-zero exit can stop a pipeline
