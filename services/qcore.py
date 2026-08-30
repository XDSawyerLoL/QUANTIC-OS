#!/usr/bin/env python3
"""Quantic OS Q-Core V0.

Tiny educational state-vector simulator used to validate the Q-Core concept.
It intentionally avoids depending on a full quantum SDK.
"""

from __future__ import annotations

import argparse
import cmath
import math
import random
from dataclasses import dataclass
from typing import Iterable

try:
    import numpy as np
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Q-Core requires numpy. Run: pip install -r requirements.txt") from exc


H = np.array([[1, 1], [1, -1]], dtype=complex) / math.sqrt(2)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)
I = np.eye(2, dtype=complex)


@dataclass
class MeasurementResult:
    bitstring: str
    probability: float


class QuantumRegister:
    def __init__(self, qubits: int):
        if qubits < 1:
            raise ValueError("qubits must be >= 1")
        self.qubits = qubits
        self.state = np.zeros(2**qubits, dtype=complex)
        self.state[0] = 1.0

    def _single_qubit_operator(self, gate: np.ndarray, target: int) -> np.ndarray:
        if not 0 <= target < self.qubits:
            raise IndexError(target)
        op = np.array([[1]], dtype=complex)
        for q in range(self.qubits):
            op = np.kron(op, gate if q == target else I)
        return op

    def apply(self, gate: np.ndarray, target: int) -> None:
        self.state = self._single_qubit_operator(gate, target) @ self.state

    def h(self, target: int) -> None:
        self.apply(H, target)

    def x(self, target: int) -> None:
        self.apply(X, target)

    def cnot(self, control: int, target: int) -> None:
        if control == target:
            raise ValueError("control and target must differ")
        new_state = np.zeros_like(self.state)
        n = self.qubits
        for index, amp in enumerate(self.state):
            bits = list(format(index, f"0{n}b"))
            if bits[control] == "1":
                bits[target] = "0" if bits[target] == "1" else "1"
            new_index = int("".join(bits), 2)
            new_state[new_index] += amp
        self.state = new_state

    def probabilities(self) -> dict[str, float]:
        return {
            format(i, f"0{self.qubits}b"): float(abs(a) ** 2)
            for i, a in enumerate(self.state)
            if abs(a) > 1e-12
        }

    def measure(self, rng: random.Random | None = None) -> MeasurementResult:
        rng = rng or random
        probs = np.abs(self.state) ** 2
        r = rng.random()
        cumulative = 0.0
        chosen = len(probs) - 1
        for i, p in enumerate(probs):
            cumulative += float(p)
            if r <= cumulative:
                chosen = i
                break
        bitstring = format(chosen, f"0{self.qubits}b")
        probability = float(probs[chosen])
        self.state[:] = 0
        self.state[chosen] = 1
        return MeasurementResult(bitstring, probability)


def bell_state() -> QuantumRegister:
    q = QuantumRegister(2)
    q.h(0)
    q.cnot(0, 1)
    return q


def _measurement_axis(theta: float) -> np.ndarray:
    """Observable in the X-Z plane: cos(theta) Z + sin(theta) X."""
    return math.cos(theta) * Z + math.sin(theta) * X


def _expectation_pair(theta_a: float, theta_b: float) -> float:
    q = bell_state()
    observable = np.kron(_measurement_axis(theta_a), _measurement_axis(theta_b))
    value = np.vdot(q.state, observable @ q.state)
    return float(np.real_if_close(value))


def chsh_theoretical() -> tuple[float, dict[str, float]]:
    a0 = 0.0
    a1 = math.pi / 2
    b0 = math.pi / 4
    b1 = -math.pi / 4
    correlators = {
        "E(a0,b0)": _expectation_pair(a0, b0),
        "E(a0,b1)": _expectation_pair(a0, b1),
        "E(a1,b0)": _expectation_pair(a1, b0),
        "E(a1,b1)": _expectation_pair(a1, b1),
    }
    s = correlators["E(a0,b0)"] + correlators["E(a0,b1)"] + correlators["E(a1,b0)"] - correlators["E(a1,b1)"]
    return abs(s), correlators


def chsh_sampled(shots: int, seed: int | None = None) -> float:
    rng = random.Random(seed)
    settings = [
        (0.0, math.pi / 4, +1),
        (0.0, -math.pi / 4, +1),
        (math.pi / 2, math.pi / 4, +1),
        (math.pi / 2, -math.pi / 4, -1),
    ]
    total = 0.0
    for ta, tb, sign in settings:
        e = _expectation_pair(ta, tb)
        same_probability = (1 + e) / 2
        acc = 0
        for _ in range(shots):
            product = 1 if rng.random() < same_probability else -1
            acc += product
        total += sign * (acc / shots)
    return abs(total)


def cmd_bell(_: argparse.Namespace) -> None:
    q = bell_state()
    print("Bell state |Φ+> probabilities:")
    for k, v in q.probabilities().items():
        print(f"  |{k}> : {v:.6f}")


def cmd_chsh(args: argparse.Namespace) -> None:
    theoretical, corr = chsh_theoretical()
    sampled = chsh_sampled(args.shots, args.seed)
    print("CHSH experiment")
    for name, value in corr.items():
        print(f"  {name}: {value:+.6f}")
    print(f"  Classical local bound: 2.000000")
    print(f"  Quantum theoretical S: {theoretical:.6f}")
    print(f"  Sampled S ({args.shots} shots/setting): {sampled:.6f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Quantic OS Q-Core")
    sub = parser.add_subparsers(dest="command", required=True)
    p_bell = sub.add_parser("bell", help="Prepare a Bell state")
    p_bell.set_defaults(func=cmd_bell)
    p_chsh = sub.add_parser("chsh", help="Run a Bell/CHSH simulation")
    p_chsh.add_argument("--shots", type=int, default=5000)
    p_chsh.add_argument("--seed", type=int, default=42)
    p_chsh.set_defaults(func=cmd_chsh)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
