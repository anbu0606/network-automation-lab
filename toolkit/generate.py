"""Generate every router's FRR config from one YAML source of truth and one Jinja2 template."""
import ipaddress                 # to check that each IP is valid
import sys                       # to stop with an error code
from pathlib import Path         # easy file reading/writing

import yaml                      # reads routers.yml into Python dicts and lists
from jinja2 import Environment, FileSystemLoader, StrictUndefined   # the template engine


def validate(data):
    """Catch mistakes BEFORE generating anything: bad IPs, duplicate IPs or router IDs."""
    errors, seen_ips, seen_ids = [], {}, {}      # problems found; IPs and router IDs already used (and by whom)
    for name, r in data["routers"].items():      # each router in the YAML, e.g. name="r1"
        if r["router_id"] in seen_ids:           # has another router already taken this ID?
            errors.append(f"{name}: router-id {r['router_id']} already used by {seen_ids[r['router_id']]}")
        seen_ids[r["router_id"]] = name
        for intf in r["interfaces"]:             # each interface of this router
            try:
                ip = ipaddress.ip_interface(intf["ip"]).ip     # "20.238.142.1/24" -> 20.238.142.1
            except ValueError:                   # not a valid address at all
                errors.append(f"{name} {intf['name']}: '{intf['ip']}' is not a valid address")
                continue
            if ip in seen_ips:                   # the same IP on two interfaces = duplicate
                errors.append(f"{name} {intf['name']}: {ip} already used on {seen_ips[ip]}")
            seen_ips[ip] = f"{name} {intf['name']}"
    return errors                                # empty list = everything is fine


def main(source="routers.yml", out_dir="generated"):
    data = yaml.safe_load(Path(source).read_text())   # the YAML file becomes a Python dict
    errors = validate(data)
    if errors:                                   # refuse to generate anything if the data is wrong
        print("Not generating, fix these first:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    env = Environment(
        loader=FileSystemLoader("templates"),
        trim_blocks=True,          # drop the newline after a {% ... %} line
        lstrip_blocks=True,        # drop spaces before a {% ... %} tag
        undefined=StrictUndefined, # a missing variable is an error, not a silent blank
        keep_trailing_newline=True,
    )
    template = env.get_template("frr.conf.j2")   # templates/frr.conf.j2
    Path(out_dir).mkdir(exist_ok=True)           # make the "generated" folder if it doesn't exist
    for name, router in data["routers"].items():
        text = template.render(hostname=name, ospf=data["ospf"], **router)   # fill the blanks with this router's data
        Path(out_dir, f"{name}.conf").write_text(text)                        # save generated/r1.conf, etc.
        print(f"wrote {out_dir}/{name}.conf")


if __name__ == "__main__":
    main()
