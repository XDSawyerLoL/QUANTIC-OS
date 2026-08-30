#!/usr/bin/env python3
"""Q-Trust — detached signature verification for Quantic update manifests.

Uses the system OpenSSL binary so the verifier can stay small and independent
from the generative AI stack. Private signing keys are intentionally NOT stored
in the Quantic OS image.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


def canonical_bytes(manifest: dict) -> bytes:
    clean = {k: v for k, v in manifest.items() if k not in {"signature", "signature_verified"}}
    return json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def manifest_digest(manifest: dict) -> str:
    return hashlib.sha256(canonical_bytes(manifest)).hexdigest()


def verify_detached(manifest: dict, signature: Path, public_key: Path) -> tuple[bool, str]:
    if not signature.exists() or not public_key.exists():
        return False, "signature or public key missing"
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(canonical_bytes(manifest))
        payload = Path(tmp.name)
    try:
        proc = subprocess.run(
            ["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(public_key),
             "-sigfile", str(signature), "-rawin", "-in", str(payload)],
            text=True, capture_output=True, timeout=5,
        )
        return proc.returncode == 0, (proc.stdout or proc.stderr or "signature verified").strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"OpenSSL verification unavailable: {exc}"
    finally:
        payload.unlink(missing_ok=True)


def main() -> None:
    p = argparse.ArgumentParser(description="Quantic detached update signature verifier")
    p.add_argument("manifest")
    p.add_argument("signature")
    p.add_argument("public_key")
    args = p.parse_args()
    manifest = json.loads(Path(args.manifest).read_text())
    ok, detail = verify_detached(manifest, Path(args.signature), Path(args.public_key))
    print(json.dumps({"verified": ok, "sha256": manifest_digest(manifest), "detail": detail}, indent=2))
    raise SystemExit(0 if ok else 2)


if __name__ == "__main__": main()
