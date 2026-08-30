#!/usr/bin/env python3
"""Q-Explain — append/read auditable local decision records."""
from __future__ import annotations
import argparse,json,time
from pathlib import Path

def append(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True,exist_ok=True); record={"ts":int(time.time()),**record}
    with path.open("a",encoding="utf-8") as f:f.write(json.dumps(record,ensure_ascii=False)+"\n")

def tail(path: Path,n:int=20):
    if not path.exists():return []
    return [json.loads(x) for x in path.read_text().splitlines()[-n:] if x.strip()]

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--log",default=str(Path.home()/".local/share/quantic/explain.jsonl"));p.add_argument("--tail",type=int,default=20);p.add_argument("--append");a=p.parse_args();path=Path(a.log)
    if a.append:append(path,json.loads(a.append))
    print(json.dumps(tail(path,a.tail),ensure_ascii=False,indent=2))
