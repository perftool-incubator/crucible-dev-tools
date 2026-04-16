#!/usr/bin/env python3
"""Generate development activity charts for all crucible repos."""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta


def gh_api(endpoint, retries=0):
    """Call GitHub API and return parsed JSON. Retries on 202 (stats computing)."""
    for attempt in range(retries + 1):
        result = subprocess.run(
            ["gh", "api", endpoint, "--include"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return None

        parts = result.stdout.split("\r\n\r\n", 1)
        if len(parts) < 2:
            parts = result.stdout.split("\n\n", 1)
        headers = parts[0] if len(parts) > 0 else ""
        body = parts[1] if len(parts) > 1 else ""

        if "HTTP/2 202" in headers or "202 Accepted" in headers:
            if attempt < retries:
                time.sleep(2)
                continue
            return None

        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return None
    return None


def gh_api_simple(endpoint):
    """Call GitHub API without --include (for simple queries)."""
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


CRUCIBLE_HOME = "/opt/crucible"
REPOS_JSON = os.path.join(CRUCIBLE_HOME, "config", "repos.json")


def get_repos():
    """Get repos from crucible config/repos.json."""
    with open(REPOS_JSON) as f:
        config = json.load(f)

    repos = []
    for entry in config.get("official", []) + config.get("unofficial", []):
        url = entry["repository"]
        repo_name = url.rstrip("/").split("/")[-1].removesuffix(".git")
        repos.append(repo_name)

    return sorted(set(repos))


def get_contributor_stats(repo):
    """Get weekly contributor stats for a repo."""
    data = gh_api(f"repos/perftool-incubator/{repo}/stats/contributors", retries=0)
    if not data or not isinstance(data, list):
        return {}

    weeks = {}
    for contributor in data:
        for week in contributor.get("weeks", []):
            ts = week["w"]
            if ts not in weeks:
                weeks[ts] = {"commits": 0, "additions": 0, "deletions": 0}
            weeks[ts]["commits"] += week["c"]
            weeks[ts]["additions"] += week["a"]
            weeks[ts]["deletions"] += week["d"]

    return weeks


def get_pr_data(repos, since_date):
    """Get merged and closed PR counts per week per repo."""
    pr_data = {}
    for repo in repos:
        pr_data[repo] = {}

    # Fetch merged PRs
    page = 1
    while True:
        data = gh_api_simple(
            f"search/issues?q=org:perftool-incubator+type:pr+is:merged+merged:>={since_date}&per_page=100&page={page}"
        )
        if not data or not data.get("items"):
            break

        for item in data["items"]:
            repo = item["repository_url"].split("/")[-1]
            if repo not in pr_data:
                continue
            # Get the Monday of the week this was merged
            merged_str = item.get("pull_request", {}).get("merged_at") or item["closed_at"]
            if not merged_str:
                continue
            dt = datetime.fromisoformat(merged_str.replace("Z", "+00:00"))
            week_start = dt - timedelta(days=dt.weekday())
            week_key = week_start.strftime("%Y-%m-%d")
            if week_key not in pr_data[repo]:
                pr_data[repo][week_key] = {"merged": 0, "closed": 0}
            pr_data[repo][week_key]["merged"] = pr_data[repo][week_key].get("merged", 0) + 1

        if len(data["items"]) < 100:
            break
        page += 1

    # Fetch closed (not merged) PRs
    page = 1
    while True:
        data = gh_api_simple(
            f"search/issues?q=org:perftool-incubator+type:pr+is:closed+is:unmerged+closed:>={since_date}&per_page=100&page={page}"
        )
        if not data or not data.get("items"):
            break

        for item in data["items"]:
            repo = item["repository_url"].split("/")[-1]
            if repo not in pr_data:
                continue
            closed_str = item["closed_at"]
            if not closed_str:
                continue
            dt = datetime.fromisoformat(closed_str.replace("Z", "+00:00"))
            week_start = dt - timedelta(days=dt.weekday())
            week_key = week_start.strftime("%Y-%m-%d")
            if week_key not in pr_data[repo]:
                pr_data[repo][week_key] = {"merged": 0, "closed": 0}
            pr_data[repo][week_key]["closed"] = pr_data[repo][week_key].get("closed", 0) + 1

        if len(data["items"]) < 100:
            break
        page += 1

    return pr_data


def get_workflow_data(repos, since_date):
    """Get workflow run data per week per repo."""
    workflow_data = {}

    for repo in repos:
        page = 1
        while True:
            data = gh_api_simple(
                f"repos/perftool-incubator/{repo}/actions/runs?created=>={since_date}&per_page=100&page={page}"
            )
            if not data or not data.get("workflow_runs"):
                break

            for run in data["workflow_runs"]:
                if run["status"] != "completed":
                    continue

                name = run["name"]
                conclusion = run["conclusion"] or "unknown"
                started = run.get("run_started_at") or run["created_at"]
                ended = run["updated_at"]

                dt_start = datetime.fromisoformat(started.replace("Z", "+00:00"))
                dt_end = datetime.fromisoformat(ended.replace("Z", "+00:00"))
                duration_min = (dt_end - dt_start).total_seconds() / 60

                week_start = dt_start - timedelta(days=dt_start.weekday())
                week_key = week_start.strftime("%Y-%m-%d")

                if week_key not in workflow_data:
                    workflow_data[week_key] = {
                        "total": 0, "success": 0, "failure": 0, "other": 0,
                        "total_duration_min": 0, "by_name": {}
                    }

                w = workflow_data[week_key]
                w["total"] += 1
                if conclusion == "success":
                    w["success"] += 1
                elif conclusion == "failure":
                    w["failure"] += 1
                else:
                    w["other"] += 1
                w["total_duration_min"] += duration_min

                if name not in w["by_name"]:
                    w["by_name"][name] = {"count": 0, "duration_min": 0}
                w["by_name"][name]["count"] += 1
                w["by_name"][name]["duration_min"] += duration_min

            if len(data["workflow_runs"]) < 100:
                break
            page += 1

    return workflow_data


def generate_html(all_data, pr_data, workflow_data, weeks_back, output_file):
    """Generate HTML with all charts."""
    # --- Contributor stats charts ---
    all_timestamps = set()
    for repo_data in all_data.values():
        all_timestamps.update(repo_data.keys())

    if not all_timestamps:
        print("No contributor data found", file=sys.stderr)
        all_timestamps = set()

    all_timestamps = sorted(all_timestamps)
    if all_timestamps:
        cutoff = all_timestamps[-1] - (weeks_back * 7 * 24 * 3600)
        all_timestamps = [t for t in all_timestamps if t >= cutoff]

    contrib_labels = [datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d")
                      for t in all_timestamps]

    active_repos = []
    for repo, weeks in sorted(all_data.items()):
        total = sum(
            weeks.get(t, {}).get("commits", 0) +
            weeks.get(t, {}).get("additions", 0) +
            weeks.get(t, {}).get("deletions", 0)
            for t in all_timestamps
        )
        if total > 0:
            active_repos.append(repo)

    colors = [
        "#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4",
        "#42d4f4", "#f032e6", "#bfef45", "#fabed4", "#469990",
        "#dcbeff", "#9A6324", "#fffac8", "#800000", "#aaffc3",
        "#808000", "#ffd8b1", "#000075", "#a9a9a9", "#000000",
        "#e6beff", "#1abc9c", "#e74c3c", "#3498db", "#2ecc71",
        "#9b59b6", "#f39c12", "#1abc9c", "#e67e22", "#2c3e50",
        "#16a085", "#c0392b", "#2980b9", "#8e44ad", "#27ae60",
        "#d35400", "#34495e", "#7f8c8d", "#95a5a6", "#bdc3c7",
    ]

    def build_datasets(metric):
        datasets = []
        for i, repo in enumerate(active_repos):
            color = colors[i % len(colors)]
            values = [all_data[repo].get(t, {}).get(metric, 0)
                      for t in all_timestamps]
            if sum(values) == 0:
                continue
            datasets.append({
                "label": repo,
                "data": values,
                "backgroundColor": color + "80",
                "borderColor": color,
                "borderWidth": 1,
                "fill": True,
                "pointRadius": 0,
            })
        return datasets

    def build_combined_datasets():
        datasets = []
        for i, repo in enumerate(active_repos):
            color = colors[i % len(colors)]
            values = [
                all_data[repo].get(t, {}).get("additions", 0) +
                all_data[repo].get(t, {}).get("deletions", 0)
                for t in all_timestamps
            ]
            if sum(values) == 0:
                continue
            datasets.append({
                "label": repo,
                "data": values,
                "backgroundColor": color + "80",
                "borderColor": color,
                "borderWidth": 1,
                "fill": True,
                "pointRadius": 0,
            })
        return datasets

    # --- PR chart data ---
    all_pr_weeks = set()
    for repo_weeks in pr_data.values():
        all_pr_weeks.update(repo_weeks.keys())
    pr_weeks_sorted = sorted(all_pr_weeks)

    pr_merged_by_repo = {}
    for repo, weeks in pr_data.items():
        values = [weeks.get(w, {}).get("merged", 0) for w in pr_weeks_sorted]
        if sum(values) > 0:
            pr_merged_by_repo[repo] = values

    pr_closed_total = [
        sum(pr_data[r].get(w, {}).get("closed", 0) for r in pr_data)
        for w in pr_weeks_sorted
    ]
    pr_merged_total = [
        sum(pr_data[r].get(w, {}).get("merged", 0) for r in pr_data)
        for w in pr_weeks_sorted
    ]

    # --- Workflow chart data ---
    wf_weeks_sorted = sorted(workflow_data.keys())

    wf_success = [workflow_data[w]["success"] for w in wf_weeks_sorted]
    wf_failure = [workflow_data[w]["failure"] for w in wf_weeks_sorted]
    wf_other = [workflow_data[w]["other"] for w in wf_weeks_sorted]
    wf_avg_duration = [
        round(workflow_data[w]["total_duration_min"] / workflow_data[w]["total"], 1)
        if workflow_data[w]["total"] > 0 else 0
        for w in wf_weeks_sorted
    ]
    wf_total_hours = [
        round(workflow_data[w]["total_duration_min"] / 60, 1)
        for w in wf_weeks_sorted
    ]

    # --- Build all charts ---
    charts_config = []

    if contrib_labels:
        charts_config.extend([
            {
                "id": "commitsChart",
                "title": "Commits per Week",
                "labels": contrib_labels,
                "datasets": json.dumps(build_datasets("commits")),
                "stacked": "true",
            },
            {
                "id": "linesChart",
                "title": "Lines Changed (Additions + Deletions) per Week",
                "labels": contrib_labels,
                "datasets": json.dumps(build_combined_datasets()),
                "stacked": "true",
            },
            {
                "id": "addDelChart",
                "title": "Additions vs Deletions per Week (All Repos Combined)",
                "labels": contrib_labels,
                "datasets": json.dumps([
                    {
                        "label": "Additions",
                        "data": [sum(all_data[r].get(t, {}).get("additions", 0)
                                     for r in active_repos)
                                 for t in all_timestamps],
                        "backgroundColor": "#3cb44b80",
                        "borderColor": "#3cb44b",
                        "borderWidth": 1, "fill": True, "pointRadius": 0,
                    },
                    {
                        "label": "Deletions",
                        "data": [sum(all_data[r].get(t, {}).get("deletions", 0)
                                     for r in active_repos)
                                 for t in all_timestamps],
                        "backgroundColor": "#e6194b80",
                        "borderColor": "#e6194b",
                        "borderWidth": 1, "fill": True, "pointRadius": 0,
                    },
                ]),
                "stacked": "true",
            },
        ])

    if pr_weeks_sorted:
        pr_stacked_datasets = []
        for i, (repo, values) in enumerate(sorted(pr_merged_by_repo.items())):
            color = colors[i % len(colors)]
            pr_stacked_datasets.append({
                "label": repo,
                "data": values,
                "backgroundColor": color + "80",
                "borderColor": color,
                "borderWidth": 1, "fill": True, "pointRadius": 0,
            })

        charts_config.append({
            "id": "prMergedChart",
            "title": "PRs Merged per Week (by Repo)",
            "labels": pr_weeks_sorted,
            "datasets": json.dumps(pr_stacked_datasets),
            "stacked": "true",
        })

        charts_config.append({
            "id": "prSummaryChart",
            "title": "PRs Merged vs Closed (Not Merged) per Week",
            "labels": pr_weeks_sorted,
            "datasets": json.dumps([
                {
                    "label": "Merged",
                    "data": pr_merged_total,
                    "backgroundColor": "#3cb44b80",
                    "borderColor": "#3cb44b",
                    "borderWidth": 1, "fill": True, "pointRadius": 0,
                },
                {
                    "label": "Closed (not merged)",
                    "data": pr_closed_total,
                    "backgroundColor": "#e6194b80",
                    "borderColor": "#e6194b",
                    "borderWidth": 1, "fill": True, "pointRadius": 0,
                },
            ]),
            "stacked": "true",
        })

    if wf_weeks_sorted:
        charts_config.append({
            "id": "wfStatusChart",
            "title": "Workflow Runs per Week (by Status)",
            "labels": wf_weeks_sorted,
            "datasets": json.dumps([
                {
                    "label": "Success",
                    "data": wf_success,
                    "backgroundColor": "#3cb44b80",
                    "borderColor": "#3cb44b",
                    "borderWidth": 1, "fill": True, "pointRadius": 0,
                },
                {
                    "label": "Failure",
                    "data": wf_failure,
                    "backgroundColor": "#e6194b80",
                    "borderColor": "#e6194b",
                    "borderWidth": 1, "fill": True, "pointRadius": 0,
                },
                {
                    "label": "Other",
                    "data": wf_other,
                    "backgroundColor": "#a9a9a980",
                    "borderColor": "#a9a9a9",
                    "borderWidth": 1, "fill": True, "pointRadius": 0,
                },
            ]),
            "stacked": "true",
        })

        charts_config.append({
            "id": "wfAvgDurationChart",
            "title": "Average Workflow Duration per Week (minutes)",
            "labels": wf_weeks_sorted,
            "datasets": json.dumps([
                {
                    "label": "Avg Duration (min)",
                    "data": wf_avg_duration,
                    "backgroundColor": "#4363d880",
                    "borderColor": "#4363d8",
                    "borderWidth": 2, "fill": True, "pointRadius": 2,
                },
            ]),
            "stacked": "false",
        })

        charts_config.append({
            "id": "wfTotalDurationChart",
            "title": "Total Workflow Duration per Week (hours)",
            "labels": wf_weeks_sorted,
            "datasets": json.dumps([
                {
                    "label": "Total Duration (hours)",
                    "data": wf_total_hours,
                    "backgroundColor": "#f5823180",
                    "borderColor": "#f58231",
                    "borderWidth": 2, "fill": True, "pointRadius": 2,
                },
            ]),
            "stacked": "false",
        })

    # --- Generate HTML ---
    html = f"""<html>
<head>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
    body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 20px auto; background: #fafafa; }}
    .chart-container {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 30px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
    canvas {{ width: 100% !important; }}
</style>
</head>
<body>
<h1>Crucible Development Activity — Last {weeks_back} Weeks</h1>
<p>Generated {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")} — {len(active_repos)} active repos</p>
"""

    for chart in charts_config:
        html += f"""
<div class="chart-container">
<canvas id="{chart['id']}"></canvas>
</div>
"""

    html += "<script>\n"

    for chart in charts_config:
        extra_scales = chart.get("extra_scales", "")
        y_title = chart.get("y_title", "")
        y_title_config = f"title: {{ display: true, text: '{y_title}' }}," if y_title else ""

        html += f"""
new Chart(document.getElementById('{chart["id"]}'), {{
    type: 'line',
    data: {{
        labels: {json.dumps(chart["labels"])},
        datasets: {chart["datasets"]}
    }},
    options: {{
        responsive: true,
        plugins: {{
            title: {{ display: true, text: '{chart["title"]}', font: {{ size: 16 }} }},
            legend: {{ position: 'bottom', labels: {{ boxWidth: 12, font: {{ size: 10 }} }} }}
        }},
        scales: {{
            x: {{ ticks: {{ maxTicksLimit: 12 }} }},
            y: {{ stacked: {chart["stacked"]}, beginAtZero: true, {y_title_config} }},
            {extra_scales}
        }},
        interaction: {{ mode: 'index', intersect: false }}
    }}
}});
"""

    html += "</script>\n</body>\n</html>"

    with open(output_file, "w") as f:
        f.write(html)

    print(f"Report written to {output_file}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Generate development activity charts for perftool-incubator"
    )
    parser.add_argument("--weeks", type=int, default=52,
                        help="Number of weeks to include (default: 52)")
    parser.add_argument("--output", type=str, default="/tmp/dev-activity.html",
                        help="Output HTML file path")
    args = parser.parse_args()

    repos = get_repos()
    since_date = (datetime.now(timezone.utc) - timedelta(weeks=args.weeks)).strftime("%Y-%m-%d")

    # --- Contributor stats ---
    print(f"Fetching contributor stats for {len(repos)} repos...", file=sys.stderr)
    pending = []
    all_data = {}
    for i, repo in enumerate(repos):
        print(f"  [{i+1}/{len(repos)}] {repo}...", file=sys.stderr, end="")
        stats = get_contributor_stats(repo)
        if stats:
            all_data[repo] = stats
            print(f" {len(stats)} weeks", file=sys.stderr)
        else:
            pending.append(repo)
            print(" pending", file=sys.stderr)

    attempt = 0
    while pending:
        attempt += 1
        print(f"Waiting for {len(pending)} repos (attempt {attempt})...",
              file=sys.stderr)
        time.sleep(5)
        still_pending = []
        for repo in pending:
            print(f"  {repo}...", file=sys.stderr, end="")
            stats = get_contributor_stats(repo)
            if stats:
                all_data[repo] = stats
                print(f" {len(stats)} weeks", file=sys.stderr)
            else:
                still_pending.append(repo)
                print(" pending", file=sys.stderr)
        pending = still_pending

    print(f"Got contributor data for {len(all_data)} repos", file=sys.stderr)

    # --- PR data ---
    print(f"Fetching PR data since {since_date}...", file=sys.stderr)
    pr_data = get_pr_data(repos, since_date)
    total_prs = sum(
        sum(w.get("merged", 0) + w.get("closed", 0) for w in repo_weeks.values())
        for repo_weeks in pr_data.values()
    )
    print(f"Got {total_prs} PRs", file=sys.stderr)

    # --- Workflow data ---
    print(f"Fetching workflow data for {len(repos)} repos...", file=sys.stderr)
    workflow_data = get_workflow_data(repos, since_date)
    total_runs = sum(w["total"] for w in workflow_data.values())
    print(f"Got {total_runs} workflow runs", file=sys.stderr)

    # --- Generate ---
    generate_html(all_data, pr_data, workflow_data, args.weeks, args.output)


if __name__ == "__main__":
    main()
