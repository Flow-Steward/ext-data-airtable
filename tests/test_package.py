"""Offline package source-selection checks."""

import importlib.util
import subprocess
import zipfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/package_extension.py"


@pytest.fixture
def packager():
    spec = importlib.util.spec_from_file_location("package_extension", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    for name in ("extension.yaml", "extension-descriptor.yaml", "LICENSE", "NOTICE", "main.py"):
        (root / name).write_text("reviewed release content\n")
    (root / ".gitignore").write_text("local-settings.txt\n")
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.test",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "--quiet",
            "-m",
            "Package fixture",
        ],
        check=True,
    )
    return root


@pytest.mark.parametrize("name", [".unlisted", "local-settings.txt", "extra/notes.txt"])
def test_release_rejects_unreviewed_workspace_files(packager, source, tmp_path, name):
    entry = source / name
    entry.parent.mkdir(parents=True, exist_ok=True)
    entry.write_text("local-only fixture")

    with pytest.raises(ValueError, match="Unexpected package input"):
        packager.package_extension(source, "linux-amd64", tmp_path / "out")

    assert not list((tmp_path / "out").glob("*.zip"))


def test_release_uses_committed_source_bytes(packager, source, tmp_path):
    (source / "main.py").write_text("edited local content\n")

    path = packager.package_extension(source, "linux-arm64", tmp_path / "out")

    with zipfile.ZipFile(path) as archive:
        assert archive.read("flowsteward_airtable/main.py") == b"reviewed release content\n"
