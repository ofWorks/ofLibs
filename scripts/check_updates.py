#!/usr/bin/env python3
"""
Check if repositories in chalet.yaml files are up-to-date with their remotes.
Compares current commit/tag against the remote default branch.
Can also update the YAML files with the latest commits.
"""

import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml


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
    if match:
        return match.group(1)
    return None


def get_remote_commit(remote_url: str, ref: str) -> str | None:
    """Get the commit hash for a specific ref from a remote."""
    code, stdout, _ = run_git_command(["ls-remote", remote_url, ref])
    if code != 0:
        return None
    lines = stdout.strip().split("\n")
    for line in lines:
        parts = line.split()
        if parts:
            return parts[0]
    return None


def get_latest_tag(remote_url: str) -> tuple[str | None, str | None]:
    """Get the latest tag from a remote repository."""
    code, stdout, _ = run_git_command(
        ["ls-remote", "--tags", "--sort=-v:refname", remote_url]
    )
    if code != 0 or not stdout.strip():
        return None, None

    lines = stdout.strip().split("\n")
    for line in lines:
        if "^{}" in line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            commit = parts[0]
            ref = parts[1]
            match = re.match(r"refs/tags/(.+)", ref)
            if match:
                return match.group(1), commit
    return None, None


def check_dependency(folder: str, name: str, info: dict) -> dict:
    """Check a single dependency for updates."""
    # Ensure commits are strings (YAML might parse numeric-looking commits as ints)
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
        "repository": info.get("repository", "unknown"),
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

    default_branch = get_default_branch(repo_url)
    result["default_branch"] = default_branch or "unknown"

    latest = get_remote_commit(repo_url, default_branch or "HEAD")
    if not latest:
        result["error"] = "Failed to fetch remote"
        return result

    result["latest_commit"] = latest

    latest_tag, latest_tag_commit = get_latest_tag(repo_url)
    result["latest_tag"] = latest_tag
    result["latest_tag_commit"] = latest_tag_commit

    # Pinned dependencies are always considered up-to-date
    if is_pinned:
        result["is_up_to_date"] = True
        return result

    if current_commit:
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
    """Parse a chalet.yaml file and extract dependency information."""
    try:
        with open(filepath, "r") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        print(f"Warning: Failed to parse {filepath}: {e}", file=sys.stderr)
        return []

    if not data or "externalDependencies" not in data:
        return []

    # Read raw content to detect comments (like # pinned)
    try:
        with open(filepath, "r") as f:
            raw_content = f.read()
    except Exception as e:
        print(f"Warning: Failed to read {filepath}: {e}", file=sys.stderr)
        raw_content = ""

    folder = filepath.parent.name
    deps = []

    for dep_name, dep_info in data["externalDependencies"].items():
        if isinstance(dep_info, dict) and dep_info.get("kind") == "git":
            # Check if commit line has # pinned comment
            is_pinned = False
            if dep_info.get("commit") and raw_content:
                # Look for the commit line in the raw content
                commit_value = str(dep_info.get("commit"))

                # Pattern 1: Inline comment - commit: <value> # pinned
                # Matches: # pinned, #pinned, # pinned some comment, etc.
                inline_pattern = rf"^\s*commit:\s*{re.escape(commit_value)}.*#\s*pinned\b"
                if re.search(inline_pattern, raw_content, re.MULTILINE | re.IGNORECASE):
                    is_pinned = True
                else:
                    # Pattern 2: Comment on previous line - # pinned...\n  commit: <value>
                    # Matches: # pinned, # pinned some comment, # Pinned to version X, etc.
                    prev_line_pattern = rf"#\s*pinned\b.*$\s*^\s*commit:\s*{re.escape(commit_value)}"
                    if re.search(prev_line_pattern, raw_content, re.MULTILINE | re.IGNORECASE):
                        is_pinned = True

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


def update_yaml_file(filepath: Path, dep_name: str, latest_commit: str, current_tag: str | None, has_commit: bool, is_pinned: bool = False) -> bool:
    """
    Update a chalet.yaml file with the latest commit.
    - If tag exists and is uncommented, comment it out and add/update commit
    - If no commit exists, add it after the repository line
    - If commit exists, update it
    - If commit is pinned, skip updating it
    """
    # Skip update if this dependency is pinned
    if is_pinned:
        return True

    try:
        with open(filepath, "r") as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {filepath}: {e}", file=sys.stderr)
        return False

    # Use a regex-based approach for more reliable editing
    # Find the dependency block and process it
    lines = content.split("\n")

    # Find the dependency section
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

    # Find the end of this dependency block
    dep_end = len(lines)
    for i in range(dep_start + 1, len(lines)):
        line = lines[i]
        stripped = line.lstrip()
        if stripped and not stripped.startswith("#"):
            current_indent = len(line) - len(stripped)
            if current_indent <= dep_indent:
                # This is a new top-level key, we've left the dependency
                dep_end = i
                break

    # Process the dependency block
    dep_lines = lines[dep_start:dep_end]
    new_dep_lines = []
    commit_updated = False
    found_repository = False

    for line in dep_lines:
        stripped = line.lstrip()
        current_indent = len(line) - len(stripped)

        # Check for repository line
        if stripped.startswith("repository:"):
            found_repository = True
            new_dep_lines.append(line)
            continue

        # Check for commit line - update it (but preserve any inline comments except # pinned)
        if stripped.startswith("commit:"):
            indent_str = " " * current_indent
            # Check if there's an inline comment (other than # pinned)
            comment_match = re.search(r"\s+#(?!\s*pinned\s*$)(.+)$", line, re.IGNORECASE)
            if comment_match:
                # Preserve the inline comment
                comment = comment_match.group(1).strip()
                new_dep_lines.append(f"{indent_str}commit: {latest_commit[:12]} # {comment}")
            else:
                new_dep_lines.append(f"{indent_str}commit: {latest_commit[:12]}")
            commit_updated = True
            continue

        # Check for uncommented tag line - comment it out
        if stripped.startswith("tag:") and not stripped.startswith("#"):
            indent_str = " " * current_indent
            tag_value = stripped[4:].strip()
            new_dep_lines.append(f"{indent_str}# tag: {tag_value}")
            continue

        new_dep_lines.append(line)

    # If we didn't update a commit and we found a repository, we need to add one
    # Insert it after the repository line
    if not commit_updated and found_repository:
        # Find where to insert (after repository line)
        insert_idx = -1
        for i, line in enumerate(new_dep_lines):
            if line.lstrip().startswith("repository:"):
                insert_idx = i + 1
                break

        if insert_idx > 0:
            indent_str = " " * (dep_indent + 2)
            new_dep_lines.insert(insert_idx, f"{indent_str}commit: {latest_commit[:12]}")

    # Reconstruct the file
    new_lines = lines[:dep_start] + new_dep_lines + lines[dep_end:]

    # Write back
    try:
        with open(filepath, "w") as f:
            f.write("\n".join(new_lines))
        return True
    except Exception as e:
        print(f"Error writing {filepath}: {e}", file=sys.stderr)
        return False


def format_commit(commit: str | None) -> str:
    """Format a commit hash for display."""
    if not commit:
        return "?"
    return commit[:12]


def print_results(results: list[dict], quiet: bool = False):
    """Print results in human-readable format."""
    outdated = [r for r in results if not r["is_up_to_date"] and not r["error"]]
    errors = [r for r in results if r["error"] and "Missing both commit and tag" not in r["error"]]
    using_tags = [r for r in results if r["error"] and "Missing both commit and tag" in r["error"]]
    pinned = [r for r in results if r.get("is_pinned", False)]

    for result in results:
        folder = result["folder"]
        name = result["name"]
        current_commit = format_commit(result["current_commit"])
        latest_commit = format_commit(result["latest_commit"])
        branch = result["default_branch"] or "?"
        current_tag = result["current_tag"]
        latest_tag = result["latest_tag"]
        is_pinned = result.get("is_pinned", False)

        if quiet and result["is_up_to_date"] and not result["error"]:
            continue

        if result["error"]:
            if "Missing both commit and tag" in result["error"]:
                tag_str = current_tag or latest_tag or "unknown"
                status = f"⚠️  USING TAG: {tag_str}\n   Latest:  {latest_commit} ({branch})"
            else:
                status = f"❌ ERROR: {result['error']}"
        elif is_pinned:
            status = f"📌 PINNED ({branch})\n   Commit: {current_commit}"
            if latest_commit and latest_commit.lower() != current_commit.lower():
                status += f"\n   Latest: {latest_commit} (update available)"
        elif result["is_up_to_date"]:
            if current_tag and not result["has_commit"]:
                status = f"✅ Up-to-date via tag: {current_tag} ({branch})"
            else:
                status = f"✅ Up-to-date ({branch})"
        else:
            tag_info = f" (current tag: {current_tag})" if current_tag else ""
            status = f"⬆️  OUTDATED{tag_info}\n   Current: {current_commit}\n   Latest:  {latest_commit} ({branch})"
            if latest_tag:
                status += f"\n   Latest tag: {latest_tag} ({format_commit(result['latest_tag_commit'])}"

        print(f"\n{folder}/{name}:")
        print(f"   Repo: {result['repository']}")
        print(f"   Status: {status}")

    if not quiet:
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total:      {len(results)}")
        print(f"Up-to-date: {len(results) - len(outdated) - len(errors) - len(using_tags) - len(pinned)}")
        print(f"Pinned:     {len(pinned)}")
        print(f"Outdated:   {len(outdated)}")
        print(f"Tag-only:   {len(using_tags)}")
        print(f"Errors:     {len(errors)}")

    if outdated:
        print("\n" + "-" * 80)
        print("OUTDATED DEPENDENCIES:")
        print("-" * 80)
        for r in outdated:
            folder = r["folder"]
            name = r["name"]
            current = format_commit(r["current_commit"])
            latest = format_commit(r["latest_commit"])
            branch = r["default_branch"] or "?"
            tag_info = f" (tag: {r['current_tag']})" if r.get("current_tag") else ""
            print(f"  {folder}/{name}{tag_info}")
            print(f"    Current: {current}")
            print(f"    Latest:  {latest} ({branch})")
            if r.get("latest_tag"):
                print(f"    Latest tag: {r['latest_tag']}")

    if using_tags:
        print("\n" + "-" * 80)
        print("DEPENDENCIES USING TAGS (no commit pinned):")
        print("-" * 80)
        for r in using_tags:
            folder = r["folder"]
            name = r["name"]
            tag = r.get("current_tag") or r.get("latest_tag") or "unknown"
            latest = format_commit(r["latest_commit"])
            branch = r["default_branch"] or "?"
            print(f"  {folder}/{name}: tag={tag}")
            print(f"    Latest commit: {latest} ({branch})")

    if errors:
        print("\n" + "-" * 80)
        print("ERRORS:")
        print("-" * 80)
        for r in errors:
            print(f"  {r.get('folder', '?')}/{r.get('name', '?')}: {r.get('error', 'Unknown error')}")


def output_json(results: list[dict]):
    """Output results as JSON."""
    output = []
    for r in results:
        output.append({
            "folder": r["folder"],
            "name": r["name"],
            "repository": r["repository"],
            "current_commit": r["current_commit"],
            "current_tag": r["current_tag"],
            "latest_commit": r["latest_commit"],
            "latest_tag": r["latest_tag"],
            "default_branch": r["default_branch"],
            "is_up_to_date": r["is_up_to_date"],
            "has_commit": r["has_commit"],
            "error": r["error"],
        })
    print(json.dumps(output, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Check if chalet.yaml dependencies are up-to-date with their remotes."
    )
    parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Only show outdated dependencies"
    )
    parser.add_argument(
        "--workers", "-w", type=int, default=10, help="Number of parallel workers (default: 10)"
    )
    parser.add_argument(
        "--update", "-u", action="store_true", help="Update YAML files with latest commits"
    )
    parser.add_argument(
        "--dry-run", "-n", action="store_true", help="Show what would be updated without making changes"
    )
    args = parser.parse_args()

    chalet_files = list(Path(".").glob("*/chalet.yaml"))

    if not chalet_files:
        print("No chalet.yaml files found!", file=sys.stderr)
        sys.exit(1)

    if not args.json and not args.quiet:
        print(f"Found {len(chalet_files)} chalet.yaml files")
        print("-" * 80)

    all_deps = []
    for filepath in chalet_files:
        deps = parse_chalet_yaml(filepath)
        all_deps.extend(deps)

    if not all_deps:
        print("No git dependencies found!", file=sys.stderr)
        sys.exit(1)

    if not args.json and not args.quiet:
        print(f"Checking {len(all_deps)} dependencies for updates...")
        print("-" * 80)

    results = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_dep = {
            executor.submit(check_dependency, d["folder"], d["name"], d): d
            for d in all_deps
        }

        for future in as_completed(future_to_dep):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                dep = future_to_dep[future]
                if not args.json:
                    print(f"\n❌ {dep['folder']}/{dep['name']}: Exception: {e}")
                results.append({
                    "folder": dep["folder"],
                    "name": dep["name"],
                    "repository": dep.get("repository", "unknown"),
                    "error": str(e),
                    "is_up_to_date": False,
                })

    results.sort(key=lambda x: (x["folder"], x["name"]))

    # Update YAML files if requested
    # Skip pinned dependencies from updates
    if args.update or args.dry_run:
        to_update = [r for r in results if (not r["is_up_to_date"] or not r["has_commit"]) and not r["error"] and not r.get("is_pinned", False)]

        pinned = [r for r in results if r.get("is_pinned", False)]

        if args.dry_run:
            print("\n" + "=" * 80)
            print("DRY RUN - Would update the following:")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print("UPDATING YAML FILES:")
            print("=" * 80)

        for r in to_update:
            folder = r["folder"]
            name = r["name"]
            filepath = Path(folder) / "chalet.yaml"
            latest = r["latest_commit"]
            current_tag = r["current_tag"]
            has_commit = r["has_commit"]
            is_pinned = r.get("is_pinned", False)

            action = "Would update" if args.dry_run else "Updating"
            print(f"\n{action} {filepath} - {name}:")

            if current_tag and not has_commit:
                print(f"  - Comment out tag: {current_tag}")
                print(f"  - Add commit: {latest[:12]}")
            elif has_commit:
                print(f"  - Update commit: {r['current_commit'][:12]} -> {latest[:12]}")
            else:
                print(f"  - Add commit: {latest[:12]}")

            if args.update and not args.dry_run:
                if update_yaml_file(filepath, name, latest, current_tag, has_commit, is_pinned):
                    print(f"  ✓ Updated successfully")
                else:
                    print(f"  ✗ Update failed")

        # Show pinned dependencies
        if pinned:
            print("\n" + "-" * 80)
            print("PINNED DEPENDENCIES (skipped):")
            print("-" * 80)
            for r in pinned:
                print(f"  {r['folder']}/{r['name']}: {r['current_commit'][:12]} # pinned")

    # Output results
    if args.json:
        output_json(results)
    elif not args.update or args.dry_run:
        print_results(results, quiet=args.quiet)

    outdated = [r for r in results if not r["is_up_to_date"] and not r["error"]]
    errors = [r for r in results if r["error"] and "Missing both commit and tag" not in r["error"]]
    return 1 if (outdated or errors) and not args.update else 0


if __name__ == "__main__":
    sys.exit(main())
