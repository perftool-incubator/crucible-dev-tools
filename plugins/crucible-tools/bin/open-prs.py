#!/usr/bin/env python3
"""Show all open PRs authored by the current user in the perftool-incubator org."""

import json
import subprocess
import sys


def gh_api(endpoint):
    result = subprocess.run(
        ["gh", "api", endpoint],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"ERROR: gh api failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def get_ci_status(repo, sha):
    """Determine CI status from check runs matching *-complete pattern."""
    data = gh_api(
        f"repos/perftool-incubator/{repo}/commits/{sha}/check-runs?per_page=100"
    )
    checks = data.get("check_runs", [])

    # Filter to top-level completion gate jobs
    gates = [c for c in checks if c["name"].endswith("-complete")]

    if not gates:
        return "no checks"

    conclusions = [c.get("conclusion") for c in gates]
    statuses = [c.get("status") for c in gates]

    if any(s != "completed" for s in statuses):
        return "CI running"
    elif all(c == "success" for c in conclusions):
        return "CI passed"
    elif any(c == "failure" for c in conclusions):
        failed = [g["name"] for g in gates if g.get("conclusion") == "failure"]
        return f"CI failed ({len(failed)})"
    else:
        return "CI unclear"


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--author", default=None,
                        help="Filter to a specific author (default: all)")
    args = parser.parse_args()

    # Build query
    author_filter = f"+author:{args.author}" if args.author else ""
    query = f"search/issues?q=org:perftool-incubator+type:pr+state:open{author_filter}&per_page=100"
    data = gh_api(query)

    if data["total_count"] == 0:
        print("No open PRs")
        return

    for item in data["items"]:
        repo = item["repository_url"].split("/")[-1]
        number = item["number"]
        title = item["title"]
        url = item["html_url"]
        created = item["created_at"][:10]
        author = item["user"]["login"]

        # Get merge status from the PR endpoint
        pr_data = gh_api(f"repos/perftool-incubator/{repo}/pulls/{number}")
        state = pr_data.get("mergeable_state", "unknown")
        sha = pr_data.get("head", {}).get("sha", "")

        # Get CI and review status
        ci_status = get_ci_status(repo, sha) if sha else "unknown"

        reviews = gh_api(f"repos/perftool-incubator/{repo}/pulls/{number}/reviews")
        approved = sum(1 for r in reviews if r["state"] == "APPROVED")
        changes_requested = sum(1 for r in reviews if r["state"] == "CHANGES_REQUESTED")
        if changes_requested > 0:
            review_status = "changes requested"
        elif approved > 0:
            review_status = f"{approved} approved"
        else:
            review_status = "no reviews"

        # Determine merge status
        if state == "clean":
            merge_status = "ready"
        elif state == "dirty":
            merge_status = "conflicts"
        elif state == "behind":
            merge_status = "behind"
        elif state == "blocked":
            if "failed" in ci_status:
                merge_status = "blocked (CI failed)"
            elif "running" in ci_status:
                merge_status = "blocked (CI running)"
            elif ci_status == "CI passed" and approved == 0:
                merge_status = "blocked (needs review)"
            elif ci_status == "CI passed" and approved > 0:
                merge_status = "blocked"
            else:
                merge_status = "blocked"
        elif state == "unstable":
            merge_status = "unstable"
        else:
            merge_status = state

        print(f"{repo}|#{number}|{title}|{url}|{created}|{author}|{merge_status}|{review_status}")


if __name__ == "__main__":
    main()
