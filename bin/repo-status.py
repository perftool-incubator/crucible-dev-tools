#!/usr/bin/env python3
"""Show local git status for all crucible repos defined in repos.json."""

import json
import os
import subprocess

CRUCIBLE_HOME = "/opt/crucible"
REPOS_JSON = os.path.join(CRUCIBLE_HOME, "config", "repos.json")

TYPE_MAP = {
    "primary": ".",
    "core": "subprojects/core",
    "benchmark": "subprojects/benchmarks",
    "tool": "subprojects/tools",
    "doc": "subprojects/docs",
    "userenvs": "subprojects/userenvs",
}


def git(path, *args):
    result = subprocess.run(
        ["git", "-C", path] + list(args),
        capture_output=True, text=True
    )
    return result.stdout.strip()


def main():
    with open(REPOS_JSON) as f:
        config = json.load(f)

    repos = []
    for entry in config.get("official", []) + config.get("unofficial", []):
        name = entry["name"]
        rtype = entry["type"]
        default_branch = entry.get("primary-branch", "master")
        if rtype == "primary":
            path = CRUCIBLE_HOME
        else:
            base = TYPE_MAP.get(rtype, "")
            path = os.path.join(CRUCIBLE_HOME, base, name)
        repos.append((name, rtype, path, default_branch))

    results = []
    has_other_branches = False

    for name, rtype, path, default_branch in repos:
        if not os.path.isdir(path):
            results.append((name, rtype, "—", "not found", "", True))
            continue

        branch = git(path, "branch", "--show-current")
        all_branches = git(path, "branch").splitlines()
        others = [b.strip().lstrip("* ") for b in all_branches if not b.startswith("*")]
        other_str = ", ".join(others) if others else ""
        if other_str:
            has_other_branches = True

        status_lines = git(path, "status", "--short", "-u").splitlines()
        status_lines = [l for l in status_lines if "__pycache__" not in l and not l.endswith(".pyc")]

        if not status_lines:
            status = "(clean)"
        else:
            m = sum(1 for l in status_lines if l[:2].strip() and l[:2].strip() != "??" and "D" not in l[:2])
            d = sum(1 for l in status_lines if "D" in l[:2])
            u = sum(1 for l in status_lines if l.startswith("??"))
            parts = []
            if m:
                parts.append(f"{m}M")
            if d:
                parts.append(f"{d}D")
            if u:
                parts.append(f"{u}??")
            status = ", ".join(parts) if parts else "(clean)"

        noteworthy = status != "(clean)" or branch != default_branch or other_str != ""
        results.append((name, rtype, branch, status, other_str, noteworthy))

    # Output as pipe-delimited for easy parsing
    for r in results:
        if r[5]:
            print(f"{r[0]}|{r[1]}|{r[2]}|{r[3]}|{r[4]}")


if __name__ == "__main__":
    main()
