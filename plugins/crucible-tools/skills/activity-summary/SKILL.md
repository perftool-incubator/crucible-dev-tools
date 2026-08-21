---
description: Generate an activity summary for the perftool-incubator GitHub organization
---

Generate an activity summary for the perftool-incubator GitHub organization.

## Instructions

1. **Prompt for configuration** using `AskUserQuestion` with three questions:

   **Question 1: Audience**
   - Header: "Audience"
   - Question: "What audience is this summary for?"
   - Options:
     - **User**: "User-facing changes only (new features, bug fixes, user-visible enhancements)" 
     - **Developer**: "All changes including internal refactoring, CI, testing, and infrastructure"
   - Default: Developer

   **Question 2: Author scope**
   - Header: "Author"
   - Question: "Show activity for which author(s)?"
   - Options:
     - **Me**: "Just my activity" (get authenticated user via `gh api user --jq '.login'`)
     - **Specific**: "Specific GitHub user" (will prompt for username in Other field)
     - **All**: "All organization members"
   - Default: Me

   **Question 3: Date range**
   - Header: "Date range"
   - Question: "What date range should the summary cover?"
   - Options:
     - **1w**: "Past week"
     - **2w**: "Past 2 weeks"
     - **1m**: "Past month"
     - **Custom**: "Custom date range" (will prompt for dates in Other field, format: YYYY-MM-DD..YYYY-MM-DD or YYYY-MM-DD)
   - Default: Past week (1w)

2. **Process the answers:**
   - For **Audience**: set `audience_mode` to either `"user"` or `"developer"`
   - For **Author scope**:
     - If "Me": get authenticated user with `gh api user --jq '.login'`, set `author_mode` to `"user"` and `author_filter` to that username
     - If "Specific": parse username from the Other field, set `author_mode` to `"user"` and `author_filter` to that username
     - If "All": set `author_mode` to `"all"` and `author_filter` to empty
   - For **Date range**: 
     - If "1w": set since date to 7 days ago
     - If "2w": set since date to 14 days ago
     - If "1m": set since date to 30 days ago
     - If "Custom": parse the date range from the Other field (format: `YYYY-MM-DD..YYYY-MM-DD` for a range, or `YYYY-MM-DD` for start date with today as end)

3. **Set the time range:**
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

   **PRs reviewed** (when `author_mode` is `"all"`, skip the `-author:` exclusion):
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

6. **Filter PRs and issues for user mode** (skip this step if `audience_mode` is `"developer"`):
   
   When `audience_mode` is `"user"`, filter the collected PRs, issues, and commits to include only user-visible changes:
   
   **Include PRs/issues with titles matching:**
   - `feat:` - new features
   - `fix:` - bug fixes
   - New tools or benchmarks (e.g., `bench-*`, `tool-*` in repo name or title)
   - Metric or data enhancements (keywords: `metric`, `topology`, `NUMA`, `aggregation`, `class`)
   - User-visible CLI changes (keywords: `CLI`, `command`, `--flag`)
   - API changes (keywords: `API`, `schema`, `endpoint`)
   - Documentation that affects users (keywords: `docs:` with `user`, `guide`, `how-to`, but NOT `CLAUDE.md`, `README` for developers)
   
   **Exclude PRs/issues with titles matching:**
   - `refactor:` - internal code restructuring
   - `ci:` - CI/CD infrastructure
   - `test:` - test infrastructure and coverage
   - `chore:` - maintenance, repo compliance, rulesets, fork-check workflows
   - `docs:` for developer documentation (CLAUDE.md, developer guides, ruleset backups)
   - Developer tooling (plugin manifests, dev-activity scripts, unless user-facing)
   - Internal migrations (keywords: `migrate`, `refactor`, unless user impact is clear)
   
   After filtering:
   - Recalculate stats (PR counts, commit counts) to include only the filtered items
   - Update the commits-by-repo section to only include repos with user-visible commits
   - Update the open PRs and reviews sections to only show filtered items

7. Write the summary to `/tmp/activity-summary.html` as an HTML file formatted for easy copy-paste into Google Docs:
   - Start the file with `<meta charset="UTF-8">` to prevent encoding issues with special characters (em dashes, etc.)
   - Use HTML entities for special characters: `&mdash;` for em dashes, `&ndash;` for en dashes. Do not use raw UTF-8 punctuation in the HTML output.
   - Use plain text styling only — bold (`<b>`) for labels, `<p>` for paragraphs, `<ul>`/`<li>` for lists, `<br>` for line breaks. No headings (`<h1>`-`<h6>`), no `<code>` tags.
   - Use `<a href="...">` for all references — PRs, issues, AND Jira tickets — so they paste as clickable links in Google Docs. Every mention of a Jira ticket key (e.g., PERFNFV-409) must be an `<a>` link, including in the Key themes section.
   - Sections:
     - **Headline**: Format varies by mode:
       - User audience, all authors: "Activity Summary — perftool-incubator (date range) [User-facing changes]"
       - User audience, specific user: "Activity Summary — perftool-incubator / username (date range) [User-facing changes]"
       - Developer audience, all authors: "Activity Summary — perftool-incubator (date range)"
       - Developer audience, specific user: "Activity Summary — perftool-incubator / username (date range)"
     - **Stats line**: PRs authored, merged, open, reviewed (counts reflect filtered data in user mode)
     - **Key themes**: Group related PRs by theme/category (e.g., "CI modernization", "bug fixes", "documentation", "new features"). Describe what was accomplished in each theme in **2-3 sentences**:
       - **First sentence**: What changed (the technical change)
       - **Second sentence**: Why it matters or what impact it has (user/developer benefit)
       - **Optional third sentence**: Additional context for larger initiatives or cross-cutting changes
       - Include PR links and Jira ticket references where applicable. **All Jira ticket keys must be `<a>` links** to `https://issues.redhat.com/browse/<KEY>` (e.g., `<a href="https://issues.redhat.com/browse/PERFNFV-464">PERFNFV-464</a>`)
       - When `author_mode` is `"all"`, include the author username for each PR
       - In user mode, focus language on user impact rather than technical implementation details
       - **Use nested `<ul>`/`<li>` sub-bullets** when a theme covers multiple distinct subtopics. For example, if a theme mentions infrastructure work, tool coverage, and bug fixes, break those into sub-bullets with bolded labels (e.g., `<li><b>Infrastructure:</b> description</li>`)
     - **Jira tickets** (if available): List tickets with key, summary, status, and links
     - **Commits by repo**: One line showing repo (count) sorted by count descending, with total
     - **Still open**: List any open PRs with links
     - **Reviews**: List any PRs reviewed for others with links
   - Also display the summary as markdown in the conversation output.
