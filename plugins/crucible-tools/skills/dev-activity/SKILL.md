---
description: Generate development activity charts for the perftool-incubator GitHub organization
---

Generate development activity charts for the perftool-incubator GitHub organization.

## Instructions

1. **Prompt for configuration** using `AskUserQuestion`:

   **Question: Time range**
   - Header: "Time range"
   - Question: "How many weeks of activity should the charts cover?"
   - Options:
     - **26**: "26 weeks (6 months)"
     - **52**: "52 weeks (1 year)"
     - **13**: "13 weeks (3 months)"
     - **Custom**: "Custom number of weeks" (will prompt for number in Other field)
   - Default: 52 weeks

2. **Process the answer:**
   - If "Custom": parse the number from the Other field
   - Otherwise: use the selected weeks value

3. Run `../../bin/dev-activity.py --weeks <N> --output /tmp/dev-activity.html` (relative to this skill directory)

4. Tell the user the report was written to `/tmp/dev-activity.html` and they can open it in a browser.
   The report contains charts for:
   - Commits per week (stacked by repo)
   - Lines changed per week (additions + deletions, stacked by repo)
   - Additions vs deletions per week (all repos combined)
   - PRs merged per week (by repo)
   - PRs merged vs closed per week
   - Workflow runs per week (by status)
   - Average workflow duration per week
   - Total workflow duration per week
   - Active contributors per week
   - Commits per week (by contributor)
   - PRs merged per week (by contributor)
   - Contributor summary table (commits, additions, deletions, net, PRs merged/closed)
