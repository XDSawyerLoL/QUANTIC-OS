#!/usr/bin/env python3
"""Q-Bridge V0: detect an app/file and choose an execution backend.

Default mode is a dry-run. Use --execute only when you explicitly want to launch.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class Route:
    platform: str
    backend: str
    confidence: str
    command: list[str] | None
    note: str


def which_any(*names: str) -> str | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def detect(path: str) -> Route:
    p = pathlib.Path(path).expanduser()
    name = p.name.lower()
    suffix = p.suffix.lower()

    if p.is_dir() and name.endswith(".app"):
        darling = which_any("darling")
        return Route(
            "macOS",
            "Darling" if darling else "Darling (not installed)",
            "experimental",
            [darling, "shell", "open", str(p)] if darling else None,
            "Most macOS GUI apps are not supported by Darling yet.",
        )

    if suffix in {".exe", ".com", ".bat"}:
        wine = which_any("wine", "wine64")
        return Route(
            "Windows",
            "Wine" if wine else "Wine (not installed)",
            "high for detection",
            [wine, str(p)] if wine else None,
            "Compatibility depends on the individual application.",
        )

    if suffix == ".msi":
        wine = which_any("wine")
        return Route(
            "Windows",
            "Wine msiexec" if wine else "Wine (not installed)",
            "high for detection",
            [wine, "msiexec", "/i", str(p)] if wine else None,
            "Installer will run inside the selected Wine prefix.",
        )

    if suffix in {".dmg", ".pkg"}:
        darling = which_any("darling")
        return Route(
            "macOS",
            "Darling" if darling else "Darling (not installed)",
            "experimental",
            [darling, "shell"] if darling else None,
            "Mount/install support exists, but GUI compatibility remains limited.",
        )

    if suffix == ".appimage":
        return Route("Linux", "AppImage native", "high", [str(p)], "The file may need chmod +x first.")

    if suffix == ".flatpakref":
        flatpak = which_any("flatpak")
        return Route(
            "Linux",
            "Flatpak" if flatpak else "Flatpak (not installed)",
            "high",
            [flatpak, "install", "--user", str(p)] if flatpak else None,
            "Flatpak sandboxing is preferred for supported apps.",
        )

    if suffix == ".deb":
        apt = which_any("apt")
        return Route(
            "Linux",
            "APT/dpkg",
            "high",
            ["sudo", apt, "install", str(p)] if apt else None,
            "System package installation requires administrator permission.",
        )

    if os.access(p, os.X_OK) and p.is_file():
        return Route("Linux", "native executable", "medium", [str(p)], "Launching directly.")

    return Route("Unknown", "Q-Bridge inspection", "low", None, "No V0 route is defined for this file type.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Quantic OS Q-Bridge V0")
    parser.add_argument("path")
    parser.add_argument("--execute", action="store_true", help="Actually run the resolved command")
    args = parser.parse_args()

    route = detect(args.path)
    print(f"Platform : {route.platform}")
    print(f"Backend  : {route.backend}")
    print(f"Confidence: {route.confidence}")
    print(f"Note     : {route.note}")
    if route.command:
        print("Command  :", " ".join(str(x) for x in route.command))
    else:
        print("Command  : unavailable")

    if args.execute:
        if not route.command or route.command[0] is None:
            raise SystemExit("No executable route is available.")
        subprocess.run(route.command, check=False)


if __name__ == "__main__":
    main()
