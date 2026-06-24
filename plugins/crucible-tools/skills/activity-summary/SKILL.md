---
description: Generate an activity summary for the perftool-incubator GitHub organization
---

Generate an activity summary for the perftool-incubator GitHub organization.

Arguments: $ARGUMENTS

## Instructions

1. Parse the arguments:
   - A date range like `2026-04-01..2026-04-15` or `2026-04-01 to 2026-04-15`: use the start date as `since` and the end date as `until`
   - A single date like `2026-04-01`: use it as the start date, with today as the end date
   - A relative duration like `2w`, `14d`, `30d`: use that many days/weeks ago as the start date
   - No arguments: default to the past 7 days

2. Get the authenticated GitHub user with `gh api user --jq '.login'`

3. Set the time range:
   - `since` as an ISO 8601 timestamp (e.g., `2026-04-01T00:00:00Z`)
   - `until` as an ISO 8601 timestamp (default: now)
   - For GitHub search queries, format dates as `YYYY-MM-DD` and use `created:START..END` or `merged:START..END` range syntax
   - For the commits API, use `since=` and `until=` query parameters

4. Collect the following data using `gh api`. Use `${since_date}` and `${until_date}` as YYYY-MM-DD formatted dates for search queries, and ISO 8601 timestamps for the commits API.

   **PRs authored** (created in the date range):
   ```
   gh api "search/issues?q=org:perftool-incubator+author:<user>+type:pr+created:${since_date}..${until_date}&per_page=100" --jq '.items[] | "[\(.repository_url | split("/") | .[-1])] \(.title) (#\(.number)) [\(.state)] \(.created_at[0:10]) \(.html_url)"'
   ```

   **PRs merged** (merged in the date range):
   ```
   gh api "search/issues?q=org:perftool-incubator+author:<user>+type:pr+merged:${since_date}..${until_date}&per_page=100" --jq '.total_count'
   ```

   **Open PRs**:
   ```
   gh api "search/issues?q=org:perftool-incubator+author:<user>+type:pr+state:open&per_page=100" --jq '.items[] | "[\(.repository_url | split("/") | .[-1])] \(.title) (#\(.number)) \(.html_url)"'
   ```

   **PRs reviewed** (by user, not authored by user):
   ```
   gh api "search/issues?q=org:perftool-incubator+reviewed-by:<user>+type:pr+-author:<user>+updated:${since_date}..${until_date}&per_page=100" --jq '.items[] | "[\(.repository_url | split("/") | .[-1])] \(.title) (#\(.number)) \(.html_url)"'
   ```

   **Issues created**:
   ```
   gh api "search/issues?q=org:perftool-incubator+author:<user>+type:issue+created:${since_date}..${until_date}&per_page=100" --jq '.items[] | "[\(.repository_url | split("/") | .[-1])] \(.title) (#\(.number)) \(.html_url)"'
   ```

   **Commits per repo** (iterate all repos in the org):
   ```
   repos=$(gh api search/repositories --method GET -f q="org:perftool-incubator" -f per_page=100 --jq '[.items[].name] | .[]')
   for repo in ${repos}; do
       count=$(gh api "repos/perftool-incubator/${repo}/commits?author=<user>&since=${since}&until=${until}&per_page=100" --jq 'length')
       # only report repos with count > 0
   done
   ```

5. **Jira tickets (optional):** If a Jira MCP server is available (check for tools with names starting with `mcp__jira__`), collect tickets updated or created during the date range:

   - Search for tickets assigned to the current user that were created or updated in the date range:
     ```
     mcp__jira__search-issues with jql: "project = PERFNFV AND assignee = currentUser() AND (created >= \"${since_date}\" OR updated >= \"${since_date}\") ORDER BY updated DESC"
     ```
   - For each ticket, note: key, summary, status, and type
   - Include these in the summary output under a **Jira tickets** section, with links to each ticket
   - When writing the **Key themes** section, associate Jira tickets with their related PRs where the connection is apparent (e.g., PR title or description references the ticket)

   If no Jira MCP server is available, skip this step entirely — do not error or warn.

6. Write the summary to `/tmp/activity-summary.html` as an HTML file formatted for easy copy-paste into Google Docs:
   - Use plain text styling only — bold (`<b>`) for labels, `<p>` for paragraphs, `<ul>`/`<li>` for lists, `<br>` for line breaks. No headings (`<h1>`-`<h6>`), no `<code>` tags.
   - Use `<a href="...">` for all PR/issue references so they paste as clickable links in Google Docs.
   - Sections:
     - **Headline**: "Activity Summary — perftool-incubator (date range)"
     - **Stats line**: PRs authored, merged, open, reviewed
     - **Key themes**: Group related PRs by theme/category (e.g., "CI modernization", "bug fixes", "documentation", "new features"). Describe what was accomplished in each theme in 1-2 sentences. Include PR links and Jira ticket references where applicable.
     - **Jira tickets** (if available): List tickets with key, summary, status, and links
     - **Commits by repo**: One line showing repo (count) sorted by count descending, with total
     - **Still open**: List any open PRs with links
     - **Reviews**: List any PRs reviewed for others with links
   - Also display the summary as markdown in the conversation output.
