#!/usr/bin/env python3
"""Show active CI workflow runs across crucible repos."""

import argparse
import json
import os
import re
import subprocess
import sys

CRUCIBLE_HOME = "/opt/crucible"
REPOS_JSON = os.path.join(CRUCIBLE_HOME, "config", "repos.json")
RUNNER_TAGS = ["aws-cloud-1"]


def gh_api(endpoint):
    result = subprocess.run(
        ["gh", "api", endpoint],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def gh_api_paginated(endpoint, jq_filter):
    cmd = ["gh", "api", endpoint, "--paginate", "--jq", jq_filter]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def parse_repo_url(url):
    m = re.match(r"git@github\.com:([^/]+)/(.+?)(?:\.git)?$", url)
    if m:
        return m.group(1), m.group(2)
    m = re.match(r"https?://github\.com/([^/]+)/(.+?)(?:\.git)?$", url)
    if m:
        return m.group(1), m.group(2)
    return None, None


def get_crucible_repos():
    with open(REPOS_JSON) as f:
        config = json.load(f)
    repos = []
    for entry in config.get("official", []) + config.get("unofficial", []):
        org, github_name = parse_repo_url(entry["repository"])
        if org and github_name:
            repos.append((entry["name"], org, github_name))
    return repos


def get_runner_summary(org):
    raw = gh_api_paginated(
        f"orgs/{org}/actions/runners",
        '.runners[] | [.name, .status, (.busy | tostring), ([.labels[].name] | join(","))] | @tsv'
    )

    runners = []
    for tag in RUNNER_TAGS:
        total = online = busy = idle = offline = 0
        if raw:
            for line in raw.splitlines():
                if tag not in line:
                    continue
                parts = line.split("\t")
                if len(parts) < 4:
                    continue
                total += 1
                if parts[1] == "online":
                    online += 1
                    if parts[2] == "true":
                        busy += 1
                    else:
                        idle += 1
                else:
                    offline += 1
        runners.append({"tag": tag, "total": total, "online": online,
                        "busy": busy, "idle": idle, "offline": offline})
    return runners


def get_active_runs(org, repo):
    runs = []
    for status in ("in_progress", "queued"):
        data = gh_api(f"repos/{org}/{repo}/actions/runs?status={status}&per_page=10")
        if not data:
            continue
        for run in data.get("workflow_runs", []):
            pr_url = ""
            prs = run.get("pull_requests") or []
            if prs:
                pr_url = f"https://github.com/{org}/{repo}/pull/{prs[0]['number']}"
            elif run.get("event") in ("pull_request", "pull_request_target"):
                branch = run.get("head_branch", "")
                if branch:
                    pr_data = gh_api(
                        f"repos/{org}/{repo}/pulls?head={org}:{branch}&state=open&per_page=1"
                    )
                    if pr_data and len(pr_data) > 0:
                        pr_url = pr_data[0].get("html_url", "")
            runs.append({
                "id": run["id"],
                "name": run.get("name", ""),
                "branch": run.get("head_branch", ""),
                "attempt": run.get("run_attempt", 1),
                "created": run.get("created_at", ""),
                "status": run.get("status", ""),
                "url": run.get("html_url", ""),
                "pr_url": pr_url,
            })
    return runs


def get_job_counts(org, repo, run_id):
    counts = {"total": 0, "success": 0, "failure": 0, "in_progress": 0,
              "queued": 0, "skipped": 0, "cancelled": 0}

    first_page = gh_api(
        f"repos/{org}/{repo}/actions/runs/{run_id}/jobs?per_page=1&filter=latest"
    )
    if not first_page:
        return counts

    total = first_page.get("total_count", 0)
    if total == 0:
        return counts

    pages = (total + 99) // 100
    for page in range(1, pages + 1):
        data = gh_api(
            f"repos/{org}/{repo}/actions/runs/{run_id}/jobs?per_page=100&page={page}&filter=latest"
        )
        if not data:
            break
        for job in data.get("jobs", []):
            counts["total"] += 1
            status = job.get("status", "")
            conclusion = job.get("conclusion") or "pending"
            if status == "completed":
                if conclusion == "success":
                    counts["success"] += 1
                elif conclusion == "failure":
                    counts["failure"] += 1
                elif conclusion == "skipped":
                    counts["skipped"] += 1
                elif conclusion == "cancelled":
                    counts["cancelled"] += 1
            elif status == "in_progress":
                counts["in_progress"] += 1
            elif status == "queued":
                counts["queued"] += 1

    return counts


def collect_data(crucible_repos, include_runners):
    runners = []
    if include_runners:
        orgs = set(r[1] for r in crucible_repos)
        for org in sorted(orgs):
            runners.extend(get_runner_summary(org))

    all_runs = []
    for i, (name, org, github_repo) in enumerate(crucible_repos):
        print(f"Scanning [{i+1}/{len(crucible_repos)}] {name}...", file=sys.stderr)
        runs = get_active_runs(org, github_repo)
        for run in runs:
            job_counts = get_job_counts(org, github_repo, run["id"])
            run["repo"] = name
            run["counts"] = job_counts
            all_runs.append(run)

    repo_agg = {}
    org_totals = {"workflows": 0, "total": 0, "success": 0, "failure": 0,
                  "in_progress": 0, "queued": 0, "skipped": 0, "cancelled": 0}

    for run in all_runs:
        repo = run["repo"]
        c = run["counts"]
        if repo not in repo_agg:
            repo_agg[repo] = {"workflows": 0, "total": 0, "success": 0, "failure": 0,
                              "in_progress": 0, "queued": 0, "skipped": 0, "cancelled": 0}
        repo_agg[repo]["workflows"] += 1
        for key in ("total", "success", "failure", "in_progress", "queued", "skipped", "cancelled"):
            repo_agg[repo][key] += c[key]
            org_totals[key] += c[key]
        org_totals["workflows"] += 1

    return runners, all_runs, repo_agg, org_totals


def output_raw(runners, all_runs, repo_agg, org_totals):
    for r in runners:
        print(f"RUNNER|{r['tag']}|{r['total']}|{r['online']}|{r['busy']}|{r['idle']}|{r['offline']}")

    if not all_runs:
        print("NO_RUNS")
        return

    for repo in sorted(repo_agg):
        a = repo_agg[repo]
        print(f"REPO_SUMMARY|{repo}|{a['workflows']}|{a['total']}|{a['success']}|"
              f"{a['failure']}|{a['in_progress']}|{a['queued']}|{a['skipped']}|{a['cancelled']}")

    t = org_totals
    print(f"ORG_TOTAL|{t['workflows']}|{t['total']}|{t['success']}|{t['failure']}|"
          f"{t['in_progress']}|{t['queued']}|{t['skipped']}|{t['cancelled']}")

    for run in all_runs:
        c = run["counts"]
        print(f"RUN|{run['repo']}|{run['id']}|{run['name']}|{run['branch']}|"
              f"{run['attempt']}|{run['status']}|{run['created']}|{run['url']}|"
              f"{run['pr_url']}|{c['total']}|{c['success']}|{c['failure']}|"
              f"{c['in_progress']}|{c['queued']}|{c['skipped']}|{c['cancelled']}")


def output_pretty(runners, all_runs, repo_agg, org_totals):
    from datetime import datetime, timezone

    for r in runners:
        print(f"Self-hosted runners [{r['tag']}]: {r['total']} total, "
              f"{r['online']} online ({r['busy']} busy, {r['idle']} idle), "
              f"{r['offline']} offline")
    if runners:
        print("GitHub-hosted runners [ubuntu-latest]: on-demand")
        print()

    if not all_runs:
        print("No active workflow runs found.")
        return

    cols = ["Repository", "Wkflows", "Total", "Success", "Failure",
            "In Progress", "Queued", "Skipped", "Cancelled"]
    keys = ["workflows", "total", "success", "failure", "in_progress",
            "queued", "skipped", "cancelled"]

    max_repo = max(len("Repository"), max(len(r) for r in repo_agg), len("TOTAL"))
    widths = [max_repo] + [max(len(c), 9) for c in cols[1:]]

    fmt = "  ".join(f"%-{w}s" if i == 0 else f"%{w}s" for i, w in enumerate(widths))
    sep = "-" * (sum(widths) + 2 * (len(widths) - 1))

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"Summary @ {now}")
    print(sep)
    print(fmt % tuple(cols))
    print(sep)
    for repo in sorted(repo_agg):
        a = repo_agg[repo]
        print(fmt % tuple([repo] + [str(a[k]) for k in keys]))
    print(sep)
    print(fmt % tuple(["TOTAL"] + [str(org_totals[k]) for k in keys]))
    print(sep)
    print()

    for run in all_runs:
        c = run["counts"]
        print("=" * 79)
        print(f"Repo:     {run['repo']}")
        print(f"Workflow: {run['name']}")
        print(f"Branch:   {run['branch']} (attempt {run['attempt']})")
        print(f"Status:   {run['status']}")
        print(f"Created:  {run['created']}")
        print(f"Run ID:   {run['id']}")
        print(f"URL:      {run['url']}")
        if run["pr_url"]:
            print(f"PR:       {run['pr_url']}")
        print()
        if c["total"] == 0:
            print("  No job data available")
        else:
            print(f"  {'Total:':<14} {c['total']}")
            print(f"  {'Success:':<14} {c['success']}")
            print(f"  {'Failure:':<14} {c['failure']}")
            print(f"  {'In Progress:':<14} {c['in_progress']}")
            print(f"  {'Queued:':<14} {c['queued']}")
            if c["skipped"] > 0:
                print(f"  {'Skipped:':<14} {c['skipped']}")
            if c["cancelled"] > 0:
                print(f"  {'Cancelled:':<14} {c['cancelled']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Show active CI workflow runs across crucible repos"
    )
    parser.add_argument("--repo", default=None,
                        help="Comma-separated crucible repo names to check")
    parser.add_argument("--no-runners", action="store_true",
                        help="Skip runner summary")
    parser.add_argument("--format", choices=["raw", "pretty"], default="raw",
                        help="Output format: raw (pipe-delimited) or pretty (terminal)")
    args = parser.parse_args()

    crucible_repos = get_crucible_repos()

    if args.repo:
        filter_names = set(args.repo.split(","))
        crucible_repos = [r for r in crucible_repos if r[0] in filter_names]

    runners, all_runs, repo_agg, org_totals = collect_data(
        crucible_repos, not args.no_runners
    )

    if args.format == "pretty":
        output_pretty(runners, all_runs, repo_agg, org_totals)
    else:
        output_raw(runners, all_runs, repo_agg, org_totals)


if __name__ == "__main__":
    main()
