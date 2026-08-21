---
description: Show active CI workflow runs across crucible repos
---

Show active CI workflow runs and self-hosted runner status for crucible repos.

## Instructions

1. **Prompt for configuration** using `AskUserQuestion` with two questions:

   **Question 1: Repository filter**
   - Header: "Repositories"
   - Question: "Show workflow runs for which repository(ies)?"
   - Options:
     - **All**: "All crucible repositories"
     - **Specific**: "Specific repository or repositories" (will prompt for repo names in Other field, comma-separated for multiple)
   - Default: All

   **Question 2: Runner summary**
   - Header: "Runners"
   - Question: "Include self-hosted runner summary?"
   - Options:
     - **Yes**: "Show runner pool status"
     - **No**: "Skip runner summary"
   - Default: Yes

2. **Process the answers:**
   - For **Repository filter**:
     - If "Specific": parse repo name(s) from the Other field, pass `--repo <name>` to the script (comma-separated names go through as-is)
     - If "All": run the script with no repo filter
   - For **Runner summary**:
     - If "No": pass `--no-runners` to the script
     - If "Yes": omit the flag

3. Run `../../bin/workflow-status.py [--repo <name>] [--no-runners]` (relative to this skill directory) to collect workflow status. Always use the default raw format (do not pass `--format`). The script also supports `--format pretty` for direct terminal use but that is not used by this skill.

4. The script outputs prefixed pipe-delimited rows to stdout. Parse by row type:

   - `RUNNER|tag|total|online|busy|idle|offline` — Self-hosted runner pool summary
   - `REPO_SUMMARY|repo|workflows|total|success|failure|in_progress|queued|skipped|cancelled` — Per-repo job aggregate
   - `ORG_TOTAL|workflows|total|success|failure|in_progress|queued|skipped|cancelled` — Overall totals
   - `RUN|repo|run_id|workflow|branch|attempt|status|created|url|pr_url|total|success|failure|in_progress|queued|skipped|cancelled` — Individual run detail
   - `NO_RUNS` — No active workflow runs found

5. Display the output in this order:

   **Runner Summary** (from RUNNER rows):
   Show each runner pool as a line: `Self-hosted runners [tag]: N total, N online (N busy, N idle), N offline`
   Add: `GitHub-hosted runners [ubuntu-latest]: on-demand`

   **Summary Table** (from REPO_SUMMARY and ORG_TOTAL rows):
   Markdown table with columns: Repository, Workflows, Total Jobs, Success, Failure, In Progress, Queued, Skipped, Cancelled.
   Include ORG_TOTAL as a bold **TOTAL** row. Omit Skipped/Cancelled columns if all values are 0.

   **Run Details** (from RUN rows):
   For each RUN row, display:
   - **Repo** / **Workflow** / **Branch** (attempt N) / **Status** / **Created** / **URL** (as link)
   - **PR** (as link, only if non-empty)
   - Job counts: total, success, failure, in progress, queued. Only show skipped/cancelled if > 0.

   If `NO_RUNS`: display "No active workflow runs found."
