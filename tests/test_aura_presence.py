from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_quantic_os_aura_presence_is_packaged_and_enabled():
    daemon = (ROOT / "services" / "qaura_presence.py").read_text(encoding="utf-8")
    unit = (ROOT / "systemd" / "quantic-aura-presence.service").read_text(encoding="utf-8")
    spec = (ROOT / "rpm" / "quantic-services.spec").read_text(encoding="utf-8")
    kickstart = (ROOT / "scripts" / "generate-kickstart.py").read_text(encoding="utf-8")

    assert "from aura_bridge import observe, register" in daemon
    assert "content_forwarded" in daemon
    assert "INTERVAL_SECONDS = 300" in daemon
    assert "EnvironmentFile=-/etc/quantic/aura.env" in unit
    assert "NoNewPrivileges=yes" in unit
    assert "quantic-aura-presence.service" in spec
    assert "systemctl enable quantic-aura-presence.service" in kickstart
