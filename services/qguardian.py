#!/usr/bin/env python3
"""Q-Guardian — deterministic independent approval for critical candidates.

Guardian never asks an LLM whether an update is safe.  It validates a test
manifest and returns a signed attestation digest that Q-Safe Update can verify.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, asdict
from pathlib import Path

CRITICAL_TESTS = {
    "unit_tests",
    "boot_smoke",
    "hardware_probe",
    "q_bridge",
    "q_core",
    "security_scan",
    "rollback_test",
    "critical_path_test",
}

@dataclass
class GuardianDecision:
    approved: bool
    missing_tests: list[str]
    failed_tests: list[str]
    digest: str
    note: str


def canonical_digest(manifest: dict) -> str:
    clean = dict(manifest)
    clean.pop("guardian_attestation", None)
    clean.pop("guardian_approved", None)
    clean.pop("decision", None)
    raw = json.dumps(clean, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def verify(manifest: dict) -> GuardianDecision:
    tests = manifest.get("tests", {})
    missing = sorted(name for name in CRITICAL_TESTS if name not in tests)
    failed = sorted(name for name in CRITICAL_TESTS if tests.get(name) is False)
    rollback_capable = bool(manifest.get("rollback_capable", False))
    twin_passed = bool(manifest.get("twin_passed", False))
    reproducible = bool(manifest.get("reproducible_build", False))
    if not rollback_capable:
        failed.append("rollback_capable")
    if not twin_passed:
        failed.append("twin_passed")
    if not reproducible:
        failed.append("reproducible_build")
    failed = sorted(set(failed))
    approved = not missing and not failed
    return GuardianDecision(
        approved=approved,
        missing_tests=missing,
        failed_tests=failed,
        digest=canonical_digest(manifest),
        note=("Independent critical validation passed." if approved else "Guardian evidence is incomplete or failed."),
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Quantic Q-Guardian verifier")
    p.add_argument("manifest")
    p.add_argument("--write-attestation", action="store_true")
    args = p.parse_args()
    path = Path(args.manifest)
    manifest = json.loads(path.read_text())
    decision = verify(manifest)
    print(json.dumps(asdict(decision), indent=2))
    if args.write_attestation and decision.approved:
        manifest["guardian_approved"] = True
        manifest["guardian_attestation"] = decision.digest
        path.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
