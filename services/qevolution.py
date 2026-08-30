#!/usr/bin/env python3
"""Q-Evolution — rank measured candidate strategies without magical claims."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Candidate:
    name: str
    score: float
    reversible: bool = True
    safe: bool = True


def choose(candidates: list[Candidate]) -> Candidate | None:
    eligible=[c for c in candidates if c.safe and c.reversible]
    return max(eligible,key=lambda c:c.score) if eligible else None

if __name__=="__main__":
    demo=[Candidate("baseline",1.0),Candidate("candidate-a",1.04),Candidate("unsafe",2.0,safe=False)]
    print(choose(demo))
