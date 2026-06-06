#!/usr/bin/env python3
"""
Update chalet.yaml dependencies to the latest commit of their remote default branch.

By default this updates the YAML files in place. Use --check to only report what is
outdated, or --dry-run to preview changes without writing them. Dependencies marked
with a `# pinned` comment are never updated.
"""

import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent


def run_git_command(args: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)


def get_default_branch(remote_url: str) -> str | None:
    """Get the default branch (HEAD) of a remote repository."""
    code, stdout, _ = run_git_command(["ls-remote", "--symref", remote_url, "HEAD"])
    if code != 0:
        return None
    match = re.search(r"ref: refs/heads/([^\s]+)\tHEAD", stdout)
    return match.group(1) if match else None


def get_remote_commit(remote_url: str, ref: str) -> str | None:
    """Get the commit hash for a specific ref from a remote."""
    code, stdout, _ = run_git_command(["ls-remote", remote_url, ref])
    if code != 0:
        return None
    for line in stdout.strip().split("\n"):
        parts = line.split()
        if parts:
            return parts[0]
    return None


def get_latest_tag(remote_url: str) -> tuple[str | None, str | None]:
    """Get the latest tag (by version sort) and its commit from a remote."""
    code, stdout, _ = run_git_command(
        ["ls-remote", "--tags", "--sort=-v:refname", remote_url]
    )
    if code != 0 or not stdout.strip():
        return None, None

    for line in stdout.strip().split("\n"):
        if "^{}" in line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            match = re.match(r"refs/tags/(.+)", parts[1])
            if match:
                return match.group(1), parts[0]
    return None, None


def check_dependency(folder: str, name: str, info: dict) -> dict:
    """Check a single dependency for updates."""
    current_commit = info.get("commit")
    if current_commit is not None:
        current_commit = str(current_commit)
    current_tag = info.get("tag")
    if current_tag is not None:
        current_tag = str(current_tag)
    is_pinned = info.get("is_pinned", False)

    result = {
        "folder": folder,
        "name": name,
        "repository": info.get("repository"),
        "current_commit": current_commit,
        "current_tag": current_tag,
        "default_branch": None,
        "latest_commit": None,
        "latest_tag": None,
        "latest_tag_commit": None,
        "is_up_to_date": False,
        "has_commit": current_commit is not None,
        "is_pinned": is_pinned,
        "error": None,
    }

    repo_url = info.get("repository")
    if not repo_url:
        result["error"] = "Missing repository URL"
        return result

    result["default_branch"] = get_default_branch(repo_url) or "unknown"

    latest = get_remote_commit(repo_url, result["default_branch"])
    if not latest:
        result["error"] = "Failed to fetch remote"
        return result
    result["latest_commit"] = latest

    latest_tag, latest_tag_commit = get_latest_tag(repo_url)
    result["latest_tag"] = latest_tag
    result["latest_tag_commit"] = latest_tag_commit

    if is_pinned:
        result["is_up_to_date"] = True
    elif current_commit:
        result["is_up_to_date"] = (
            current_commit.lower() == latest.lower()
            or latest.lower().startswith(current_commit.lower())
        )
    elif current_tag:
        result["is_up_to_date"] = (
            latest_tag == current_tag
            or (latest_tag_commit and latest.lower().startswith(latest_tag_commit.lower()))
        )
    else:
        result["error"] = "Missing both commit and tag"

    return result


def parse_chalet_yaml(filepath: Path) -> list[dict]:
    """Parse a chalet.yaml file and extract git dependency information."""
    try:
        raw_content = filepath.read_text()
        data = yaml.safe_load(raw_content)
    except Exception as e:
        print(f"Warning: failed to parse {filepath}: {e}", file=sys.stderr)
        return []

    if not data or "externalDependencies" not in data:
        return []

    folder = filepath.parent.name
    deps = []

    for dep_name, dep_info in data["externalDependencies"].items():
        if not (isinstance(dep_info, dict) and dep_info.get("kind") == "git"):
            continue

        is_pinned = False
        if dep_info.get("commit"):
            commit_value = re.escape(str(dep_info["commit"]))
            # Inline:  commit: <value> # pinned   OR   previous line: # pinned\n commit: <value>
            inline = rf"^\s*commit:\s*{commit_value}.*#\s*pinned\b"
            prev = rf"#\s*pinned\b.*$\s*^\s*commit:\s*{commit_value}"
            flags = re.MULTILINE | re.IGNORECASE
            is_pinned = bool(
                re.search(inline, raw_content, flags) or re.search(prev, raw_content, flags)
            )

        deps.append(
            {
                "folder": folder,
                "name": dep_name,
                "repository": dep_info.get("repository"),
                "commit": dep_info.get("commit"),
                "tag": dep_info.get("tag"),
                "is_pinned": is_pinned,
            }
        )

    return deps


def update_yaml_file(filepath: Path, dep_name: str, latest_commit: str) -> bool:
    """
    Update a chalet.yaml dependency with the latest commit.
    - If a commit line exists, update it (preserving inline comments other than # pinned).
    - If a tag line exists and is uncommented, comment it out.
    - If no commit exists, add one after the repository line.
    """
    try:
        lines = filepath.read_text().split("\n")
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return False

    # Locate the dependency block.
    dep_start = -1
    dep_indent = 0
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(f"{dep_name}:"):
            dep_start = i
            dep_indent = len(line) - len(stripped)
            break

    if dep_start == -1:
        print(f"Dependency {dep_name} not found in {filepath}", file=sys.stderr)
        return False

    dep_end = len(lines)
    for i in range(dep_start + 1, len(lines)):
        stripped = lines[i].lstrip()
        if stripped and not stripped.startswith("#"):
            if (len(lines[i]) - len(stripped)) <= dep_indent:
                dep_end = i
                break

    new_dep_lines = []
    commit_updated = False
    found_repository = False
    short = latest_commit[:12]

    for line in lines[dep_start:dep_end]:
        stripped = line.lstrip()
        indent_str = " " * (len(line) - len(stripped))

        if stripped.startswith("repository:"):
            found_repository = True
            new_dep_lines.append(line)
        elif stripped.startswith("commit:"):
            comment_match = re.search(r"\s+#(?!\s*pinned\s*$)(.+)$", line, re.IGNORECASE)
            if comment_match:
                comment = comment_match.group(1).strip()
                new_dep_lines.append(f'{indent_str}commit: "{short}" # {comment}')
            else:
                new_dep_lines.append(f'{indent_str}commit: "{short}"')
            commit_updated = True
        elif stripped.startswith("tag:"):
            new_dep_lines.append(f"{indent_str}# tag: {stripped[4:].strip()}")
        else:
            new_dep_lines.append(line)

    if not commit_updated and found_repository:
        for i, line in enumerate(new_dep_lines):
            if line.lstrip().startswith("repository:"):
                indent_str = " " * (dep_indent + 2)
                new_dep_lines.insert(i + 1, f'{indent_str}commit: "{short}"')
                break

    new_lines = lines[:dep_start] + new_dep_lines + lines[dep_end:]
    try:
        filepath.write_text("\n".join(new_lines))
        return True
    except Exception as e:
        print(f"Error writing {filepath}: {e}", file=sys.stderr)
        return False


def gather_results(workers: int, progress: bool = True) -> list[dict]:
    """Check every git dependency across all chalet.yaml files."""
    chalet_files = sorted(ROOT.glob("*/chalet.yaml"))
    if not chalet_files:
        print("No chalet.yaml files found!", file=sys.stderr)
        sys.exit(1)

    all_deps = [d for f in chalet_files for d in parse_chalet_yaml(f)]
    if not all_deps:
        print("No git dependencies found!", file=sys.stderr)
        sys.exit(1)

    total = len(all_deps)
    if progress:
        print(f"ofLibs — checking {total} dependencies across {len(chalet_files)} files...", file=sys.stderr)

    results = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(check_dependency, d["folder"], d["name"], d): d
            for d in all_deps
        }
        for future in as_completed(futures):
            if progress:
                dep = futures[future]
                print(f"\r  [{len(results) + 1}/{total}] {dep['folder']}/{dep['name']}".ljust(60), end="", file=sys.stderr, flush=True)
            try:
                results.append(future.result())
            except Exception as e:
                dep = futures[future]
                results.append(
                    {
                        "folder": dep["folder"],
                        "name": dep["name"],
                        "repository": dep.get("repository"),
                        "is_up_to_date": False,
                        "is_pinned": False,
                        "has_commit": dep.get("commit") is not None,
                        "current_commit": dep.get("commit"),
                        "current_tag": dep.get("tag"),
                        "latest_commit": None,
                        "error": str(e),
                    }
                )

    if progress:
        print("\r".ljust(60) + "\r" + "done.", file=sys.stderr)

    results.sort(key=lambda r: (r["folder"], r["name"]))
    return results


def short(commit: str | None) -> str:
    return commit[:12] if commit else "?"


def do_update(results: list[dict], dry_run: bool):
    """Update (or preview updates to) the YAML files. Concise output."""
    to_update = [
        r
        for r in results
        if not r["error"] and not r["is_pinned"] and (not r["is_up_to_date"] or not r["has_commit"])
    ]
    errors = [r for r in results if r["error"] and r["error"] != "Missing both commit and tag"]

    if not to_update:
        print("All dependencies are up-to-date.")
    else:
        verb = "Would update" if dry_run else "Updated"
        for r in to_update:
            target = f"{r['folder']}/{r['name']}"
            if r["has_commit"]:
                change = f"{short(r['current_commit'])} -> {short(r['latest_commit'])}"
            elif r["current_tag"]:
                change = f"tag {r['current_tag']} -> commit {short(r['latest_commit'])}"
            else:
                change = f"+ {short(r['latest_commit'])}"

            ok = True
            if not dry_run:
                ok = update_yaml_file(
                    ROOT / r["folder"] / "chalet.yaml", r["name"], r["latest_commit"]
                )
            mark = " ✗ FAILED" if not ok else ""
            print(f"  {target}: {change}{mark}")
        print(f"\n{verb} {len(to_update)} dependenc{'y' if len(to_update) == 1 else 'ies'}.")

    for r in errors:
        print(f"  ⚠️  {r['folder']}/{r['name']}: {r['error']}", file=sys.stderr)


def do_check(results: list[dict], verbose: bool):
    """Report status without modifying files. Concise output."""
    outdated = [r for r in results if not r["is_up_to_date"] and not r["error"]]
    errors = [r for r in results if r["error"] and r["error"] != "Missing both commit and tag"]
    tag_only = [r for r in results if r["error"] == "Missing both commit and tag"]
    pinned = [r for r in results if r["is_pinned"]]
    up_to_date = len(results) - len(outdated) - len(errors) - len(tag_only) - len(pinned)

    for r in outdated:
        tag = f" (tag: {r['current_tag']})" if r["current_tag"] else ""
        print(f"  ⬆️  {r['folder']}/{r['name']}{tag}: {short(r['current_commit'])} -> {short(r['latest_commit'])} ({r['default_branch']})")
    for r in tag_only:
        print(f"  🏷️  {r['folder']}/{r['name']}: using tag {r['current_tag'] or r['latest_tag']}, latest {short(r['latest_commit'])}")
    for r in errors:
        print(f"  ❌ {r['folder']}/{r['name']}: {r['error']}")
    if verbose:
        for r in pinned:
            print(f"  📌 {r['folder']}/{r['name']}: {short(r['current_commit'])} (pinned)")
        for r in results:
            if r["is_up_to_date"] and not r["is_pinned"]:
                print(f"  ✅ {r['folder']}/{r['name']}: {short(r['current_commit'])}")

    print(
        f"\n{len(results)} deps | {up_to_date} up-to-date | {len(outdated)} outdated | "
        f"{len(pinned)} pinned | {len(tag_only)} tag-only | {len(errors)} errors"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Update chalet.yaml dependencies to the latest remote commit (default action)."
    )
    parser.add_argument("--check", "-c", action="store_true", help="Only report status; do not modify files")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Show what would be updated without writing")
    parser.add_argument("--json", action="store_true", help="Output raw results as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="With --check, also list up-to-date/pinned deps")
    parser.add_argument("--workers", "-w", type=int, default=10, help="Parallel workers (default: 10)")
    args = parser.parse_args()

    results = gather_results(args.workers)

    if args.json:
        print(json.dumps(results, indent=2))
    elif args.check:
        do_check(results, verbose=args.verbose)
    else:
        do_update(results, dry_run=args.dry_run)

    # Non-zero exit only in check mode when something needs attention.
    if args.check:
        problems = [r for r in results if (not r["is_up_to_date"] and not r["error"]) or
                    (r["error"] and r["error"] != "Missing both commit and tag")]
        return 1 if problems else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
