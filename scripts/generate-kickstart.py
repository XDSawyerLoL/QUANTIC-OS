#!/usr/bin/env python3
from pathlib import Path
import argparse
p=argparse.ArgumentParser();p.add_argument('--base',required=True);p.add_argument('--repo',required=True);p.add_argument('--out',required=True);a=p.parse_args()
base=Path(a.base).read_text();extra=[x.strip() for x in Path(__file__).resolve().parents[1].joinpath('live/quantic-packages.txt').read_text().splitlines() if x.strip() and not x.lstrip().startswith('#')]
lines=base.splitlines();out=[];in_packages=False;inserted=False
for line in lines:
    if line.strip().startswith('%packages'): in_packages=True
    if in_packages and line.strip()=='%end' and not inserted: out.extend(extra);inserted=True
    out.append(line)
    if in_packages and line.strip()=='%end': in_packages=False
if not inserted: raise SystemExit('No %packages section found in base KDE kickstart')
out.insert(0,f'repo --name=quantic-local --baseurl=file://{Path(a.repo).resolve()} --cost=1')
out += ['%post --erroronfail','set -eux','systemctl enable quantic-resource.service || true','systemctl enable quantic-usb-safe.service || true','cat >/etc/profile.d/quantic-live.sh <<\'EOF\'','export QUANTIC_LIVE=1','EOF','chmod 0644 /etc/profile.d/quantic-live.sh','%end']
Path(a.out).write_text('\n'.join(out)+'\n')
