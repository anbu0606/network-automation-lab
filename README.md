# Network Automation Lab: OSPF, BGP and Python tooling

Hands-on labs and tools I built to practise network engineering. The network is rebuilt from a six-router design I first made in a university networking assignment (static routing in the CORE emulator). It now runs FRRouting (FRR 10.0) routers in Containerlab on WSL, with dynamic routing and Python tools that check and change it.

## What's in this repo

| Folder | What it is |
|---|---|
| `lab1-ospf/` | Four-router OSPF core (area 0) with four host LANs: topology, router configs, host setup script, evidence |
| `lab2-bgp/` | Lab 1 connected by eBGP to two other autonomous systems: topology, configs, evidence |
| `toolkit/` | Python scripts for IP planning, health checks, config generation, compliance and pre/post change checks |

## Lab 1: OSPF

- Replaced every static route with OSPF. Set real link bandwidths and a reference bandwidth of 10,000 Mbps, so a 1 Gbps link costs 10 and a 100 Mbps link costs 100, and traffic prefers the fast path.
- Failed links on purpose: with the interface down, OSPF rerouted immediately; with a silent failure (100% packet loss, interface still up), traffic stopped for about 40 seconds until the dead timer expired.
- Converted a link to point-to-point and confirmed there's no DR/BDR election on it.
- Evidence: `lab1-ospf/evidence/` (OSPF neighbours and routing table from R3).

## Lab 2: BGP across three autonomous systems

- Talos (AS 65100, the Lab 1 routers, R3 at the border), an Internet transit AS (65000) and Delos (AS 65200).
- Advertised one aggregate, 20.238.0.0/16, backed by a blackhole route, and gave the internal routers a default route through OSPF.
- Reproduced the routing loop from the original assignment (packets to unused addresses bouncing between two routers) and fixed it with the blackhole route.
- Hit FRR's RFC 8212 behaviour (eBGP sessions Established but no routes exchanged) and wrote prefix-list/route-map policies to advertise only our block and accept only the expected prefix.
- Added a second path, then controlled path selection: shortest AS_PATH, LOCAL_PREF for outbound traffic, and AS-path prepending to influence inbound traffic.
- Evidence: `lab2-bgp/evidence/` (BGP summary, BGP table, both paths to Delos after prepending, R1's routing table).

## Toolkit (`toolkit/`)

| Script | What it does |
|---|---|
| `iptools.py` | Describes a subnet, finds overlapping prefixes in an IP plan, allocates /31s to point-to-point links |
| `ospf_health.py` | Runs `show ip ospf neighbor` on every router in parallel and compares the Full neighbours with an expected set; exits non-zero on failure |
| `generate.py` | Validates `routers.yml` (no duplicate IPs or router IDs) and renders each router's config from one Jinja2 template |
| `compliance.py` | Checks running configs against house rules: reference bandwidth, router ID, interface descriptions, no shut interfaces |
| `prepost.py` | Snapshots OSPF neighbours and selected routes before and after a change, then prints exactly what changed |

## Problems I hit, and how I found them

1. **OSPF costs stuck at 1.** `show ip ospf interface` showed "BW 100000 Mbit": FRR's `bandwidth` command is in Mbps, while my configs used Cisco-style kbps values. Fixed the units on every router.
2. **Traffic took the wrong path after a link failure.** Neighbours were all Full, but the route metric was higher than calculated. Checking each link's cost along the path showed one router was missing the reference-bandwidth setting.
3. **Internal hosts couldn't reach other ASes in Lab 2.** Containerlab gives each container a management default route; as a kernel route (administrative distance 0) it beat the OSPF default route (110). Removed it on the routers.
4. **Changes disappeared after a redeploy.** A redeploy reloads each router from its config file, so changes made only on the live router are lost. Changes now go into the files.

## How to run it

Needs Docker and Containerlab (I used the WSL-Containerlab distribution on Windows), plus Python 3.

```bash
# Lab 1
cd lab1-ospf
sudo containerlab deploy -t netsim-ospf.clab.yml
./setup-hosts.sh                    # after about a minute

# Toolkit (with Lab 1 running)
cd ../toolkit
python3 -m venv .venv && source .venv/bin/activate
pip install -r ../requirements.txt
python3 ospf_health.py

# Lab 2 (destroy Lab 1 first)
cd ../lab2-bgp
sudo containerlab deploy -t netsim-bgp.clab.yml
```

All addresses are lab-only, taken from the original assignment.
