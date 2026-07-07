---
description: Generate an activity summary for the perftool-incubator GitHub organization
---

Generate an activity summary for the perftool-incubator GitHub organization.

Arguments: $ARGUMENTS

## Instructions

1. Parse the arguments:
   - **Author filter** (optional, can appear anywhere in the arguments):
     - `--all`: show activity for all org members (no author filter)
     - `--author <username>` or `@<username>`: show activity for a specific GitHub user
     - No author argument: default to the authenticated user
   - **Date range** (optional):
     - A date range like `2026-04-01..2026-04-15` or `2026-04-01 to 2026-04-15`: use the start date as `since` and the end date as `until`
     - A single date like `2026-04-01`: use it as the start date, with today as the end date
     - A relative duration like `2w`, `14d`, `30d`: use that many days/weeks ago as the start date
     - No date argument: default to the past 7 days

2. Determine the author scope:
   - If `--all` was specified, set `author_mode` to `"all"` and `author_filter` to empty (no `author:` filter in queries)
   - If `--author <username>` or `@<username>` was specified, set `author_mode` to `"user"` and `author_filter` to that username
   - Otherwise, get the authenticated GitHub user with `gh api user --jq '.login'` and set `author_mode` to `"user"` and `author_filter` to that user
   - Update the headline to reflect the scope: "Activity Summary — perftool-incubator (date range)" for `--all`, or "Activity Summary — perftool-incubator / <username> (date range)" for a specific user

3. Set the time range:
   - `since` as an ISO 8601 timestamp (e.g., `2026-04-01T00:00:00Z`)
   - `until` as an ISO 8601 timestamp (default: now)
   - For GitHub search queries, format dates as `YYYY-MM-DD` and use `created:START..END` or `merged:START..END` range syntax
   - For the commits API, use `since=` and `until=` query parameters

4. Collect the following data using `gh api`. Use `${since_date}` and `${until_date}` as YYYY-MM-DD formatted dates for search queries, and ISO 8601 timestamps for the commits API.

   In the queries below, `<author_q>` is:
   - `author:<user>` when `author_mode` is `"user"`
   - omitted entirely when `author_mode` is `"all"`

   Similarly, `<author_commits_q>` is:
   - `author=<user>&` when `author_mode` is `"user"`
   - omitted entirely when `author_mode` is `"all"`

   **PRs authored** (created in the date range):
   ```
   gh api "search/issues?q=org:perftool-incubator+<author_q>+type:pr+created:${since_date}..${until_date}&per_page=100" --jq '.items[] | "[\(.repository_url | split("/") | .[-1])] \(.title) (#\(.number)) [\(.state)] \(.created_at[0:10]) \(.user.login) \(.html_url)"'
   ```

   **PRs merged** (merged in the date range):
   ```
   gh api "search/issues?q=org:perftool-incubator+<author_q>+type:pr+merged:${since_date}..${until_date}&per_page=100" --jq '.total_count'
   ```

   **Open PRs**:
   ```
   gh api "search/issues?q=org:perftool-incubator+<author_q>+type:pr+state:open&per_page=100" --jq '.items[] | "[\(.repository_url | split("/") | .[-1])] \(.title) (#\(.number)) \(.user.login) \(.html_url)"'
   ```

   **PRs reviewed** (in `--all` mode, skip the `-author:` exclusion):
   - When `author_mode` is `"user"`:
     ```
     gh api "search/issues?q=org:perftool-incubator+reviewed-by:<user>+type:pr+-author:<user>+updated:${since_date}..${until_date}&per_page=100" --jq '.items[] | "[\(.repository_url | split("/") | .[-1])] \(.title) (#\(.number)) \(.html_url)"'
     ```
   - When `author_mode` is `"all"`: skip this section (reviews are only meaningful per-user)

   **Issues created**:
   ```
   gh api "search/issues?q=org:perftool-incubator+<author_q>+type:issue+created:${since_date}..${until_date}&per_page=100" --jq '.items[] | "[\(.repository_url | split("/") | .[-1])] \(.title) (#\(.number)) \(.user.login) \(.html_url)"'
   ```

   **Commits per repo** (iterate all repos in the org):
   ```
   repos=$(gh api search/repositories --method GET -f q="org:perftool-incubator" -f per_page=100 --jq '[.items[].name] | .[]')
   for repo in ${repos}; do
       count=$(gh api "repos/perftool-incubator/${repo}/commits?<author_commits_q>since=${since}&until=${until}&per_page=100" --jq 'length')
       # only report repos with count > 0
   done
   ```

5. **Jira tickets (optional):** If a Jira MCP server is available (check for tools with names starting with `mcp__jira__`), collect tickets updated or created during the date range:

   - Search for tickets created or updated in the date range:
     - When `author_mode` is `"user"`:
       ```
       mcp__jira__search-issues with jql: "project = PERFNFV AND assignee = currentUser() AND (created >= \"${since_date}\" OR updated >= \"${since_date}\") ORDER BY updated DESC"
       ```
     - When `author_mode` is `"all"`:
       ```
       mcp__jira__search-issues with jql: "project = PERFNFV AND (created >= \"${since_date}\" OR updated >= \"${since_date}\") ORDER BY updated DESC"
       ```
   - For each ticket, note: key, summary, status, and type
   - Include these in the summary output under a **Jira tickets** section, with links to each ticket
   - When writing the **Key themes** section, associate Jira tickets with their related PRs where the connection is apparent (e.g., PR title or description references the ticket)

   If no Jira MCP server is available, skip this step entirely — do not error or warn.

6. Write the summary to `/tmp/activity-summary.html` as an HTML file formatted for easy copy-paste into Google Docs:
   - Start the file with `<meta charset="UTF-8">` to prevent encoding issues with special characters (em dashes, etc.)
   - Use HTML entities for special characters: `&mdash;` for em dashes, `&ndash;` for en dashes. Do not use raw UTF-8 punctuation in the HTML output.
   - Use plain text styling only — bold (`<b>`) for labels, `<p>` for paragraphs, `<ul>`/`<li>` for lists, `<br>` for line breaks. No headings (`<h1>`-`<h6>`), no `<code>` tags.
   - Use `<a href="...">` for all PR/issue references so they paste as clickable links in Google Docs.
   - Sections:
     - **Headline**: "Activity Summary — perftool-incubator (date range)" for `--all`, or "Activity Summary — perftool-incubator / username (date range)" for a specific user
     - **Stats line**: PRs authored, merged, open, reviewed
     - **Key themes**: Group related PRs by theme/category (e.g., "CI modernization", "bug fixes", "documentation", "new features"). Describe what was accomplished in each theme in 1-2 sentences. Include PR links and Jira ticket references where applicable. In `--all` mode, include the author username for each PR.
     - **Jira tickets** (if available): List tickets with key, summary, status, and links
     - **Commits by repo**: One line showing repo (count) sorted by count descending, with total
     - **Still open**: List any open PRs with links
     - **Reviews**: List any PRs reviewed for others with links
   - Also display the summary as markdown in the conversation output.
