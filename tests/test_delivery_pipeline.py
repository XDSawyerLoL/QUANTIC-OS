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
