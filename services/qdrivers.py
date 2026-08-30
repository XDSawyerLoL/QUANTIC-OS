#!/usr/bin/env python3
"""Q-Drivers — report kernel driver binding for discovered PCI/USB devices."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess


def pci() -> list[dict]:
    if not shutil.which("lspci"): return []
    p=subprocess.run(["lspci","-nnk"],text=True,capture_output=True)
    out=[];current=None
    for line in p.stdout.splitlines():
        if line and not line[0].isspace():
            if current: out.append(current)
            current={"device":line.strip(),"driver":None,"modules":None}
        elif current:
            s=line.strip()
            if s.startswith("Kernel driver in use:"): current["driver"]=s.split(":",1)[1].strip()
            elif s.startswith("Kernel modules:"): current["modules"]=s.split(":",1)[1].strip()
    if current: out.append(current)
    return out


def usb() -> list[dict]:
    if not shutil.which("lsusb"): return []
    p=subprocess.run(["lsusb"],text=True,capture_output=True)
    return [{"device":line} for line in p.stdout.splitlines() if line.strip()]


def summary() -> dict:
    p=pci(); return {"pci":p,"usb":usb(),"pci_total":len(p),"pci_bound":sum(1 for x in p if x.get("driver")),"pci_unbound":[x["device"] for x in p if not x.get("driver")]}


def main():
    a=argparse.ArgumentParser();a.add_argument("--json",action="store_true");args=a.parse_args();s=summary()
    if args.json: print(json.dumps(s,ensure_ascii=False,indent=2)); return
    print(f"PCI drivers: {s['pci_bound']}/{s['pci_total']} bound")
    for item in s['pci_unbound'][:20]: print("UNBOUND",item)


if __name__=="__main__": main()
