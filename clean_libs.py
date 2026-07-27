#!/usr/bin/env python3
"""
Remove bundled/built library artifacts to free up disk space, keeping only the
recipes (chalet.yaml, patches, scripts) that live in this repo.

By default only `build/` directories are considered. Add --chalet-external and
--dist to also remove those, or --all for every known artifact directory.

Nothing is deleted unless --yes is passed; the default run only reports sizes.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# name -> enabled by default
ARTIFACT_DIRS = ["build", "chalet_external", "dist", "install", "Release"]
SKIP_DIRS = {".git"}


def find_artifact_dirs(root: Path, names: set[str]) -> list[Path]:
    """Find artifact directories anywhere under root, without descending into them."""
    found = []
    for dirpath, dirnames, _ in os.walk(root):
        keep = []
        for d in sorted(dirnames):
            if d in SKIP_DIRS:
                continue
            if d in names:
                found.append(Path(dirpath) / d)
            else:
                keep.append(d)
        dirnames[:] = keep
    return found


def dir_size(path: Path) -> int:
    """Total size in bytes of everything under path (symlinks not followed)."""
    total = 0
    for dirpath, dirnames, filenames in os.walk(path, onerror=lambda e: None):
        for name in filenames:
            f = Path(dirpath) / name
            try:
                if not f.is_symlink():
                    total += f.stat().st_size
            except OSError:
                pass
    return total


def human(size: int) -> str:
    value = float(size)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} TB"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove bundled library build artifacts.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--root", type=Path, default=ROOT, help="Directory to scan")
    parser.add_argument("--chalet-external", action="store_true", help="Also remove chalet_external/")
    parser.add_argument("--dist", action="store_true", help="Also remove dist/")
    parser.add_argument("--install", action="store_true", help="Also remove install/")
    parser.add_argument("--release", action="store_true", help="Also remove Release/")
    parser.add_argument("--all", action="store_true", help=f"Remove all of: {', '.join(ARTIFACT_DIRS)}")
    parser.add_argument("--no-build", action="store_true", help="Do not remove build/")
    parser.add_argument("-y", "--yes", action="store_true", help="Actually delete (default is a dry run)")
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 1

    names: set[str] = set(ARTIFACT_DIRS) if args.all else set()
    if not args.all:
        if not args.no_build:
            names.add("build")
        if args.chalet_external:
            names.add("chalet_external")
        if args.dist:
            names.add("dist")
        if args.install:
            names.add("install")
        if args.release:
            names.add("Release")
    elif args.no_build:
        names.discard("build")

    if not names:
        print("nothing selected to remove")
        return 0

    targets = find_artifact_dirs(root, names)
    if not targets:
        print(f"no {', '.join(sorted(names))} directories found under {root}")
        return 0

    total = 0
    failures = 0
    for path in targets:
        size = dir_size(path)
        total += size
        rel = path.relative_to(root)
        if args.yes:
            try:
                shutil.rmtree(path)
            except OSError as e:
                print(f"failed  {rel}  ({e})", file=sys.stderr)
                failures += 1
                total -= size
                continue
            print(f"removed {rel}  {human(size)}")
        else:
            print(f"would remove {rel}  {human(size)}")

    verb = "freed" if args.yes else "would free"
    print(f"\n{len(targets)} directories, {verb} {human(total)}")
    if not args.yes:
        print("re-run with --yes to delete")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
