---
description: Show all open PRs in the perftool-incubator GitHub organization
---

Show all open PRs in the perftool-incubator GitHub organization.

## Instructions

1. **Prompt for configuration** using `AskUserQuestion`:

   **Question: Author filter**
   - Header: "Author"
   - Question: "Show open PRs for which author(s)?"
   - Options:
     - **All**: "All organization members"
     - **Me**: "Just my open PRs" (get authenticated user via `gh api user --jq '.login'`)
     - **Specific**: "Specific GitHub user" (will prompt for username in Other field)
   - Default: All

2. **Process the answer:**
   - If "Me": get authenticated user with `gh api user --jq '.login'`, pass `--author <username>` to the script
   - If "Specific": parse username from the Other field, pass `--author <username>` to the script
   - If "All": run the script with no author filter

3. Run `../../bin/open-prs.py [--author <username>]` (relative to this skill directory) to collect open PRs.

4. The script outputs pipe-delimited rows: `repo|#number|title|url|created_date|author|merge_status|review_status`. If no open PRs, it prints "No open PRs".

5. Display as a markdown table with columns: Repo, PR, Title, Created, Author, Merge, Reviews.
   - PR column should be the #number as a markdown link to the URL.
