---
description: Generate a weekly activity summary for the perftool-incubator GitHub organization
---

Generate a weekly activity summary for the perftool-incubator GitHub organization.

## Instructions

1. Get the authenticated GitHub user with `gh api user --jq '.login'`

2. Set the time range to the past 7 days: `since=$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ)`

3. Collect the following data using `gh api`:

   **PRs authored** (created in the past week):
   ```
   gh api "search/issues?q=org:perftool-incubator+author:<user>+type:pr+created:>=${since}&per_page=100" --jq '.items[] | "[\(.repository_url | split("/") | .[-1])] \(.title) (#\(.number)) [\(.state)] \(.created_at[0:10]) \(.html_url)"'
   ```

   **PRs merged** (merged in the past week):
   ```
   gh api "search/issues?q=org:perftool-incubator+author:<user>+type:pr+merged:>=${since}&per_page=100" --jq '.total_count'
   ```

   **Open PRs**:
   ```
   gh api "search/issues?q=org:perftool-incubator+author:<user>+type:pr+state:open&per_page=100" --jq '.items[] | "[\(.repository_url | split("/") | .[-1])] \(.title) (#\(.number)) \(.html_url)"'
   ```

   **PRs reviewed** (by user, not authored by user):
   ```
   gh api "search/issues?q=org:perftool-incubator+reviewed-by:<user>+type:pr+-author:<user>+updated:>=${since}&per_page=100" --jq '.items[] | "[\(.repository_url | split("/") | .[-1])] \(.title) (#\(.number)) \(.html_url)"'
   ```

   **Issues created**:
   ```
   gh api "search/issues?q=org:perftool-incubator+author:<user>+type:issue+created:>=${since}&per_page=100" --jq '.items[] | "[\(.repository_url | split("/") | .[-1])] \(.title) (#\(.number)) \(.html_url)"'
   ```

   **Commits per repo** (iterate all repos in the org):
   ```
   repos=$(gh api search/repositories --method GET -f q="org:perftool-incubator" -f per_page=100 --jq '[.items[].name] | .[]')
   for repo in ${repos}; do
       count=$(gh api "repos/perftool-incubator/${repo}/commits?author=<user>&since=${since}&per_page=100" --jq 'length')
       # only report repos with count > 0
   done
   ```

4. Write the summary to `/tmp/weekly-summary.html` as an HTML file formatted for easy copy-paste into Google Docs:
   - Use plain text styling only — bold (`<b>`) for labels, `<p>` for paragraphs, `<ul>`/`<li>` for lists, `<br>` for line breaks. No headings (`<h1>`-`<h6>`), no `<code>` tags.
   - Use `<a href="...">` for all PR/issue references so they paste as clickable links in Google Docs.
   - Sections:
     - **Headline**: "Weekly Activity Summary — perftool-incubator (date range)"
     - **Stats line**: PRs authored, merged, open, reviewed
     - **Key themes**: Group related PRs by theme/category (e.g., "CI modernization", "bug fixes", "documentation", "new features"). Describe what was accomplished in each theme in 1-2 sentences. Include PR links.
     - **Commits by repo**: One line showing repo (count) sorted by count descending, with total
     - **Still open**: List any open PRs with links
     - **Reviews**: List any PRs reviewed for others with links
   - Also display the summary as markdown in the conversation output.
