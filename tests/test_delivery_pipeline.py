from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_main_is_the_single_automatic_iso_delivery_branch():
    workflow = (ROOT / ".github/workflows/build-quantic-final.yml").read_text()
    test_workflow = (ROOT / ".github/workflows/test-quantic-v2.yml").read_text()
    assert "branches: [main]" in workflow
    assert "contents: write" in workflow
    assert "timeout-minutes: 360" in workflow
    assert "pull_request:\n    branches:\n      - main" in test_workflow


def test_large_iso_is_split_and_published_as_persistent_release_assets():
    workflow = (ROOT / ".github/workflows/build-quantic-final.yml").read_text()
    publisher = (ROOT / "scripts/publish-release-assets.sh").read_text()
    assert "split -b 1500M" in workflow
    assert "scripts/publish-release-assets.sh build/live" in workflow
    assert "gh release create" in publisher
    assert "gh release upload" in publisher
    assert "for attempt in 1 2 3" in publisher
    assert "--clobber" in publisher
    assert "size < 2000000000" in publisher


def test_windows_data_bootstrap_accepts_drive_or_drive_root():
    script = (ROOT / "scripts/prepare-quantic-data.ps1").read_text()
    assert "ValidatePattern('^[A-Za-z]:(\\\\)?$')" in script
    assert '$normalizedDrive = "$driveLetter`:"' in script
    assert '$root = "$normalizedDrive\\quantic-state"' in script


def test_missing_model_error_does_not_reference_nonexistent_setup_script():
    agent = (ROOT / "services/qagent.py").read_text()
    assert "setup-local-ai.sh" not in agent
    assert "QUANTIC-DATA" in agent


def test_foundation_uses_module_test_runner_from_repository_root():
    verifier = (ROOT / "scripts/verify-foundation.sh").read_text()
    assert "python3 -m pytest -q" in verifier
    assert "\npytest -q\n" not in verifier


def test_early_persistence_service_has_no_local_fs_ordering_cycle():
    unit = (ROOT / "systemd/quantic-persistence.service").read_text()
    verifier = (ROOT / "scripts/verify-foundation.sh").read_text()
    assert "Before=local-fs.target quantic-core.target" in unit
    # PrivateTmp orders a service after systemd-tmpfiles-setup, which itself is
    # after local-fs.target. Combining it with Before=local-fs.target creates a
    # cycle and systemd drops the persistence job during boot.
    assert "PrivateTmp=yes" not in unit
    assert "systemd-analyze verify systemd/quantic-persistence.service systemd/quantic-core.target" in verifier


def test_final_image_contains_the_privileged_approval_boundary():
    remaster = (ROOT / "scripts" / "remaster-quantic-final.sh").read_text()
    rpm = (ROOT / "rpm" / "quantic-services.spec").read_text()
    assert 'services/qapproval_privileged.sh" "$ROOT_TREE/usr/libexec/quantic-approval' in remaster
    assert 'polkit/org.quantic.approval.policy" "$ROOT_TREE/usr/share/polkit-1/actions/org.quantic.approval.policy' in remaster
    assert 'test -x "$VERIFY_MNT/usr/libexec/quantic-approval"' in remaster
    assert "services/qapproval_privileged.sh %{buildroot}%{_libexecdir}/quantic-approval" in rpm
    assert "polkit/org.quantic.approval.policy" in rpm


def test_iso_checksum_records_only_the_portable_basename():
    for name in ("remaster-quantic-final.sh", "remaster-fedora-kde.sh"):
        remaster = (ROOT / "scripts" / name).read_text()
        assert 'sha256sum "$(basename "$OUT_ISO")"' in remaster
        assert 'sha256sum "$OUT_ISO" > "$OUT_ISO.sha256"' not in remaster
