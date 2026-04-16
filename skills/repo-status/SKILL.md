---
description: Show the local git status for all crucible repos
---

Show the local git status for all crucible repos.

## Instructions

1. Run `repo-status.py` to collect repo status.

2. The script reads `config/repos.json` and outputs pipe-delimited rows for repos that have something noteworthy (not clean, not on default branch, or has extra local branches). Repos that are clean on their default branch with no extra branches are omitted.

3. Display the output as a markdown table with columns: Repo, Type, Branch, Status, Other Branches.
   - Only show the "Other Branches" column if any repo has extra branches.
