#!/usr/bin/env python3
"""How long does it take to move N terabytes over a given link? (Online vs offline decision.)

  python3 scripts/transfer_calc.py [--tb 40] [--links 100,1000] [--util 0.8] [--measured-mbps N]

--util is the share of the link you can actually give the migration (the rest is for the business).
--measured-mbps adds a row for a rate you measured (for example the DataSync agent's).
Decimal units, as links and disks are sold: 1 TB = 10^12 bytes, 1 Mbps = 10^6 bits/s.
"""
import argparse


def human(sec):
    d = sec / 86400
    return f"{d:6.1f} days" if d >= 1 else f"{sec / 3600:6.1f} hours"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tb", type=float, default=40)
    p.add_argument("--links", default="100,1000")
    p.add_argument("--util", type=float, default=0.8)
    p.add_argument("--measured-mbps", type=float)
    a = p.parse_args()
    bits = a.tb * 1e12 * 8
    print(f"Moving {a.tb:g} TB ({bits / 1e12:,.0f} Tbit)\n")
    print(f"{'link':>22} {'usable':>12} {'time at 100%':>14} {'time at ' + str(int(a.util * 100)) + '%':>14}")
    rows = [(f"{int(m)} Mbps line", m) for m in (float(x) for x in a.links.split(","))]
    if a.measured_mbps:
        rows.append((f"measured {a.measured_mbps:g} Mbps", a.measured_mbps))
    for name, mbps in rows:
        full = bits / (mbps * 1e6)
        part = bits / (mbps * 1e6 * a.util)
        print(f"{name:>22} {mbps * a.util:9.0f} Mbps {human(full):>14} {human(part):>14}")
    print("\nRule of thumb: if the online transfer takes longer than about a week at the share of the link the")
    print("business can spare, price an offline option too. Snowball Edge is no longer available to new")
    print("customers; AWS now points to AWS Data Transfer Terminals and partner services for offline transfer.")


if __name__ == "__main__":
    main()
