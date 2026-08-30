#!/usr/bin/env python3
"""Q-Hardware Intelligence — safe hardware discovery and first profile.

The module is deliberately read-only. It inventories hardware and derives a
small capability profile which Q-Model Hub and Q-Autopilot can consume.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def _read(path: str, default: str = "") -> str:
    try:
        return Path(path).read_text(errors="ignore").strip()
    except OSError:
        return default


def _run(args: list[str], timeout: int = 3) -> str:
    try:
        p = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
        return p.stdout.strip() if p.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def cpu_model() -> str:
    if platform.system() == "Linux":
        for line in _read("/proc/cpuinfo").splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or "Unknown CPU"


def total_ram_gib() -> float:
    if platform.system() == "Linux":
        for line in _read("/proc/meminfo").splitlines():
            if line.startswith("MemTotal:"):
                kb = int(line.split()[1])
                return round(kb / 1024 / 1024, 2)
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        size = os.sysconf("SC_PAGE_SIZE")
        return round(pages * size / 1024**3, 2)
    except (ValueError, OSError, AttributeError):
        return 0.0


def linux_gpus() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if shutil.which("nvidia-smi"):
        raw = _run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"])
        for line in raw.splitlines():
            parts = [x.strip() for x in line.split(",")]
            if len(parts) >= 3:
                out.append({"name": parts[0], "vram_mib": int(float(parts[1])), "driver": parts[2], "vendor": "NVIDIA"})
    if out:
        return out
    raw = _run(["lspci", "-mm"])
    for line in raw.splitlines():
        lower = line.lower()
        if "vga compatible controller" in lower or "3d controller" in lower:
            out.append({"name": line, "vram_mib": 0, "driver": "kernel/mesa discovery pending", "vendor": "unknown"})
    return out


def block_devices() -> list[dict[str, Any]]:
    if not shutil.which("lsblk"):
        return []
    raw = _run(["lsblk", "-J", "-b", "-o", "NAME,TYPE,SIZE,MODEL,TRAN,RO,RM,MOUNTPOINTS"])
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return data.get("blockdevices", [])


def pci_devices() -> list[str]:
    raw = _run(["lspci"])
    return [line for line in raw.splitlines() if line]


def usb_devices() -> list[str]:
    raw = _run(["lsusb"])
    return [line for line in raw.splitlines() if line]


@dataclass
class HardwareProfile:
    schema: int = 1
    hostname: str = ""
    os: str = ""
    kernel: str = ""
    arch: str = ""
    cpu: str = ""
    logical_cpus: int = 0
    ram_gib: float = 0.0
    gpus: list[dict[str, Any]] = field(default_factory=list)
    block_devices: list[dict[str, Any]] = field(default_factory=list)
    pci: list[str] = field(default_factory=list)
    usb: list[str] = field(default_factory=list)

    @property
    def best_vram_gib(self) -> float:
        return max((g.get("vram_mib", 0) for g in self.gpus), default=0) / 1024


def discover() -> HardwareProfile:
    return HardwareProfile(
        hostname=platform.node(),
        os=platform.platform(),
        kernel=platform.release(),
        arch=platform.machine(),
        cpu=cpu_model(),
        logical_cpus=os.cpu_count() or 0,
        ram_gib=total_ram_gib(),
        gpus=linux_gpus() if platform.system() == "Linux" else [],
        block_devices=block_devices() if platform.system() == "Linux" else [],
        pci=pci_devices() if platform.system() == "Linux" else [],
        usb=usb_devices() if platform.system() == "Linux" else [],
    )


def ai_tier(profile: HardwareProfile) -> str:
    vram = profile.best_vram_gib
    ram = profile.ram_gib
    if vram >= 16 and ram >= 32:
        return "max"
    if vram >= 8 or ram >= 24:
        return "balanced"
    return "light"


def save(profile: HardwareProfile, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(profile)
    payload["ai_tier"] = ai_tier(profile)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def main() -> None:
    p = argparse.ArgumentParser(description="Quantic hardware discovery")
    p.add_argument("--output", default="state/hardware-profile.json")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    profile = discover()
    if args.json:
        payload = asdict(profile)
        payload["ai_tier"] = ai_tier(profile)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        save(profile, Path(args.output))
        print(f"Hardware profile: {args.output}")
        print(f"CPU: {profile.cpu}")
        print(f"RAM: {profile.ram_gib} GiB")
        print(f"GPU(s): {len(profile.gpus)}")
        print(f"AI tier: {ai_tier(profile)}")


if __name__ == "__main__":
    main()
