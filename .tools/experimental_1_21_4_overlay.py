#!/usr/bin/env python3
"""Generate exact-format-46 compatibility overlays from the ``split`` branch.

This is intentionally separate from ``migrate_26_2.py``.  The 26.2 assets stay
at each pack root; files whose 1.21.4 form differs are restored under the
``1_21_4`` overlay.  Run with ``--check`` for a read-only consistency audit.
"""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any


PACKS = (
    "city", "dev", "dvz", "entities", "hats", "items", "leveling", "lom",
    "memes", "music", "paladins", "quests", "seasonal_xmas", "spells",
    "systems", "tutorial",
)
OVERLAY_DIRECTORY = "1_21_4"
SOURCE_FORMAT = 46
CURRENT_FORMAT = 88
LAST_LEGACY_FORMAT = 64


def git(root: Path, *args: str, binary: bool = False) -> bytes | str:
    result = subprocess.run(
        ("git", *args),
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {message}")
    return result.stdout if binary else result.stdout.decode("utf-8")


def wanted_metadata(current: dict[str, Any], enable_overlay: bool) -> dict[str, Any]:
    result = dict(current)
    pack = dict(result.get("pack", {}))
    pack["pack_format"] = SOURCE_FORMAT
    pack["supported_formats"] = [SOURCE_FORMAT, LAST_LEGACY_FORMAT]
    pack["min_format"] = SOURCE_FORMAT
    pack["max_format"] = [CURRENT_FORMAT, 0]
    result["pack"] = pack

    overlays = dict(result.get("overlays", {}))
    entries = [
        entry
        for entry in overlays.get("entries", [])
        if entry.get("directory") != OVERLAY_DIRECTORY
    ]
    if enable_overlay:
        entries.append({"formats": SOURCE_FORMAT, "directory": OVERLAY_DIRECTORY})
    if entries:
        overlays["entries"] = entries
        result["overlays"] = overlays
    else:
        result.pop("overlays", None)
    return result


class Generator:
    def __init__(self, root: Path, source_ref: str, check: bool):
        self.root = root
        self.source_ref = source_ref
        self.check = check
        self.changes: list[str] = []
        self.problems: list[str] = []

    def expected_overlay(self, pack: str) -> dict[Path, bytes]:
        expected: dict[Path, bytes] = {}
        prefix = f"{pack}/"
        changed_output = git(
            self.root,
            "diff", "--name-only", "--no-renames",
            f"{self.source_ref}..HEAD", "--", f"{pack}/assets",
        )
        assert isinstance(changed_output, str)
        changed = set(changed_output.splitlines())
        archive = git(
            self.root,
            "archive", "--format=tar", self.source_ref, f"{pack}/assets",
            binary=True,
        )
        assert isinstance(archive, bytes)
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue
                if member.name not in changed:
                    continue
                relative = Path(member.name.removeprefix(prefix))
                extracted = tar.extractfile(member)
                assert extracted is not None
                source = extracted.read()
                expected[Path(OVERLAY_DIRECTORY) / relative] = source
        return expected

    def sync_overlay(self, pack: str) -> bool:
        pack_root = self.root / pack
        overlay_root = pack_root / OVERLAY_DIRECTORY
        expected = self.expected_overlay(pack)
        actual = {
            path.relative_to(pack_root)
            for path in overlay_root.rglob("*")
            if path.is_file()
        } if overlay_root.is_dir() else set()

        for relative, content in expected.items():
            target = pack_root / relative
            if target.is_file() and target.read_bytes() == content:
                continue
            if self.check:
                self.problems.append(f"missing/stale overlay file: {pack}/{relative.as_posix()}")
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                self.changes.append(f"{pack}/{relative.as_posix()}")

        stale = sorted(actual - set(expected))
        for relative in stale:
            target = pack_root / relative
            if self.check:
                self.problems.append(f"stale overlay file: {pack}/{relative.as_posix()}")
            else:
                target.unlink()
                self.changes.append(f"removed {pack}/{relative.as_posix()}")

        if not self.check and overlay_root.is_dir():
            for directory in sorted(overlay_root.rglob("*"), reverse=True):
                if directory.is_dir() and not any(directory.iterdir()):
                    directory.rmdir()
        return bool(expected)

    def sync_metadata(self, pack: str, enable_overlay: bool) -> None:
        path = self.root / pack / "pack.mcmeta"
        current = json.loads(path.read_text(encoding="utf-8"))
        wanted = json.dumps(
            wanted_metadata(current, enable_overlay), indent=2, ensure_ascii=False
        ) + "\n"
        if path.read_text(encoding="utf-8") == wanted:
            return
        if self.check:
            self.problems.append(f"stale metadata: {pack}/pack.mcmeta")
        else:
            path.write_text(wanted, encoding="utf-8")
            self.changes.append(f"{pack}/pack.mcmeta")

    def run(self) -> int:
        git(self.root, "rev-parse", "--verify", f"{self.source_ref}^{{commit}}")
        for pack in PACKS:
            enable_overlay = self.sync_overlay(pack)
            self.sync_metadata(pack, enable_overlay)

        if self.problems:
            for problem in self.problems:
                print(f"ERROR: {problem}", file=sys.stderr)
            return 1
        action = "Check passed" if self.check else "Overlay generation complete"
        print(f"{action} ({len(self.changes)} changed paths).")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-ref", default="split")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    root_text = git(Path.cwd(), "rev-parse", "--show-toplevel")
    assert isinstance(root_text, str)
    root = Path(root_text.strip()).resolve()
    return Generator(root, args.source_ref, args.check).run()


if __name__ == "__main__":
    sys.exit(main())
