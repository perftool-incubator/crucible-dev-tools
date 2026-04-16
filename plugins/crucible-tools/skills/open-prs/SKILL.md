---
description: Show all open PRs in the perftool-incubator GitHub organization
---

Show all open PRs in the perftool-incubator GitHub organization.

Arguments: $ARGUMENTS

## Instructions

1. Parse the arguments:
   - If a username is provided (e.g., `/crucible-tools:open-prs k-rister`), pass `--author <username>` to the script
   - If no arguments or `--all`, run the script with no author filter

2. Run `open-prs.py [--author <username>]` to collect open PRs.

3. The script outputs pipe-delimited rows: `repo|#number|title|url|created_date|author|merge_status|review_status`. If no open PRs, it prints "No open PRs".

4. Display as a markdown table with columns: Repo, PR, Title, Created, Author, Merge, Reviews.
   - PR column should be the #number as a markdown link to the URL.
