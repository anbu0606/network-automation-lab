"""Small IP address tools for network engineering, built on Python's ipaddress module."""
import argparse
import ipaddress


def describe(text):
    """Print everything about the subnet an address belongs to, e.g. '10.1.5.200/22'."""
    iface = ipaddress.ip_interface(text)          # an address WITH its prefix length
    net = iface.network                           # the subnet it belongs to
    print(f"Address:    {iface.ip}")
    print(f"Network:    {net}")
    print(f"Mask:       {net.netmask}")
    print(f"Broadcast:  {net.broadcast_address}")
    if net.prefixlen <= 30:
        print(f"Usable:     {net.network_address + 1} - {net.broadcast_address - 1}")
        print(f"Hosts:      {net.num_addresses - 2}")
    else:
        print(f"Hosts:      {net.num_addresses} (/31 and /32 have no network or broadcast address)")


def find_overlaps(prefixes):
    """Return every pair of prefixes that overlap (a classic VPC-peering or IP-plan mistake)."""
    nets = [ipaddress.ip_network(p, strict=False) for p in prefixes]
    clashes = []
    for i, a in enumerate(nets):
        for b in nets[i + 1:]:
            if a.overlaps(b):
                clashes.append((a, b))
    return clashes


def allocate_links(pool, links):
    """Give each router-to-router link its own /31 from a pool, in order."""
    subnets = ipaddress.ip_network(pool).subnets(new_prefix=31)
    plan = []
    for (a, b), sub in zip(links, subnets):
        plan.append((a, f"{sub[0]}/31", b, f"{sub[1]}/31"))
    return plan


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IP address tools")
    sub = parser.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("describe", help="describe the subnet of one or more addresses")
    d.add_argument("addresses", nargs="+")
    o = sub.add_parser("overlaps", help="find overlapping prefixes")
    o.add_argument("prefixes", nargs="+")
    sub.add_parser("links", help="allocate /31s to the Lab 1 core links")
    args = parser.parse_args()

    if args.cmd == "describe":
        for addr in args.addresses:
            describe(addr)
            print()
    elif args.cmd == "overlaps":
        clashes = find_overlaps(args.prefixes)
        for a, b in clashes:
            print(f"OVERLAP: {a} and {b}")
        if not clashes:
            print("No overlaps.")
    elif args.cmd == "links":
        core = [("r1", "r3"), ("r1", "r4"), ("r1", "r2"), ("r2", "r3"), ("r2", "r4")]
        for a, ip_a, b, ip_b in allocate_links("10.255.0.0/24", core):
            print(f"{a} {ip_a:<16} <-> {b} {ip_b}")
