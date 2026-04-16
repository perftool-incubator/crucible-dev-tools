---
description: Generate development activity charts for the perftool-incubator GitHub organization
---

Generate development activity charts for the perftool-incubator GitHub organization.

Arguments: $ARGUMENTS

## Instructions

1. Parse the arguments:
   - A number sets the weeks (e.g., `/crucible-tools:dev-activity 26` for 26 weeks)
   - No arguments defaults to 52 weeks

2. Run `dev-activity.py --weeks <N> --output /tmp/dev-activity.html`

3. Tell the user the report was written to `/tmp/dev-activity.html` and they can open it in a browser.
   The report contains charts for:
   - Commits per week (stacked by repo)
   - Lines changed per week (additions + deletions, stacked by repo)
   - Additions vs deletions per week (all repos combined)
   - PRs merged per week (by repo)
   - PRs merged vs closed per week
   - Workflow runs per week (by status)
   - Average workflow duration per week
   - Total workflow duration per week
