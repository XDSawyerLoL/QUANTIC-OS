#!/usr/bin/env python3
"""Patch an official Fedora KDE Live KIWI description into Quantic OS.

This intentionally keeps Fedora's boot/driver/Plasma definitions and adds only
Quantic packages, product identity, Live safety and removal of the installer.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import xml.etree.ElementTree as ET


def write_xml(path: Path, root: ET.Element) -> None:
    ET.indent(root, space="\t")
    path.write_text(ET.tostring(root, encoding="unicode") + "\n", encoding="utf-8")


def patch_fedora_kiwi(desc: Path) -> None:
    path = desc / "Fedora.kiwi"
    tree = ET.parse(path)
    root = tree.getroot()
    root.set("name", "Quantic-OS")
    spec = root.find("./description/specification")
    if spec is not None:
        spec.text = "Quantic OS — Fedora KDE Live based"

    includes = [e.get("from", "") for e in root.findall("include")]
    repo_ref = "this://./repositories/quantic.xml"
    comp_ref = "this://./components/quantic.xml"
    if repo_ref not in includes:
        first_component = next((i for i, e in enumerate(root) if e.tag == "include" and "components/" in e.get("from", "")), len(root))
        root.insert(first_component, ET.Element("include", {"from": repo_ref}))
    if comp_ref not in includes:
        live_idx = next((i for i, e in enumerate(root) if e.tag == "include" and e.get("from", "").endswith("components/liveinstall.xml")), len(root))
        root.insert(live_idx, ET.Element("include", {"from": comp_ref}))
    write_xml(path, root)


def patch_liveinstall(desc: Path) -> None:
    path = desc / "components/liveinstall.xml"
    tree = ET.parse(path)
    root = tree.getroot()
    # Keep Fedora's proven Live boot profile, but remove the installer payload.
    banned_packages = {"anaconda-install-env-deps", "anaconda-live"}
    for packages in root.findall("packages"):
        if packages.get("profiles") != "LiveInstall":
            continue
        for child in list(packages):
            if child.tag == "namedCollection" and child.get("name") == "anaconda-tools":
                packages.remove(child)
            elif child.tag == "package" and child.get("name") in banned_packages:
                packages.remove(child)
    for typ in root.findall(".//type"):
        cmd = typ.get("kernelcmdline", "").strip()
        if "quantic.live=1" not in cmd:
            typ.set("kernelcmdline", (cmd + " quantic.live=1").strip())
        typ.set("publisher", "Quantic OS")
        typ.set("volid", "QUANTIC_OS")
        typ.set("application_id", "Quantic_OS_Live")
    write_xml(path, root)


def write_quantic_repo(desc: Path, repo: Path) -> None:
    (desc / "repositories").mkdir(exist_ok=True)
    xml = f'''<image>\n\t<repository type="rpm-md" alias="quantic-local" priority="1" imageinclude="false" package_gpgcheck="false">\n\t\t<source path="dir://{repo.resolve()}"/>\n\t</repository>\n</image>\n'''
    (desc / "repositories/quantic.xml").write_text(xml, encoding="utf-8")


def write_quantic_component(desc: Path) -> None:
    packages = [
        "quantic-shell", "quantic-services", "quantic-theme",
        "ollama", "python3-ollama", "wine", "winetricks", "gamemode",
        "mangohud", "bubblewrap", "smartmontools", "lm_sensors",
        "pciutils", "usbutils", "vulkan-tools",
    ]
    body = "\n".join(f'\t\t<package name="{p}"/>' for p in packages)
    xml = f'''<image>\n\t<packages type="image" patternType="plusRecommended" profiles="KDE-Desktop-Live">\n{body}\n\t</packages>\n</image>\n'''
    (desc / "components/quantic.xml").write_text(xml, encoding="utf-8")


def patch_config(desc: Path) -> None:
    path = desc / "config.sh"
    original = path.read_text(encoding="utf-8") if path.exists() else "#!/usr/bin/bash\nset -e\n"
    marker = "# --- Quantic OS product overlay ---"
    if marker in original:
        original = original.split(marker, 1)[0].rstrip() + "\n"
    overlay = r'''
# --- Quantic OS product overlay ---
systemctl enable quantic-resource.service quantic-usb-safe.service || true
systemctl --global enable quantic-companion.service || true
# The Live branch is intentionally not an installer.
rm -f /usr/share/applications/*anaconda*.desktop /usr/share/applications/*liveinst*.desktop || true
mkdir -p /etc/quantic
cat >/etc/quantic/product-release <<'EOF'
QUANTIC_VERSION=1.1
QUANTIC_EDITION=Live
QUANTIC_BASE=Fedora-KDE-44
QUANTIC_USB_ONLY=1
EOF
'''
    path.write_text(original + overlay, encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--description", required=True)
    p.add_argument("--repo", required=True)
    args = p.parse_args()
    desc = Path(args.description).resolve()
    repo = Path(args.repo).resolve()
    if not (desc / "Fedora.kiwi").exists():
        raise SystemExit(f"Fedora.kiwi missing in {desc}")
    if not (repo / "repodata").exists():
        raise SystemExit(f"RPM metadata missing in {repo}")
    patch_fedora_kiwi(desc)
    patch_liveinstall(desc)
    write_quantic_repo(desc, repo)
    write_quantic_component(desc)
    patch_config(desc)
    print(f"Prepared Quantic KIWI description: {desc}")


if __name__ == "__main__":
    main()
