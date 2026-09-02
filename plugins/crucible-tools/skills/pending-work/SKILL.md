---
description: Generate a comprehensive pending work report from Jira tickets and GitHub issues/PRs
---

Generate a comprehensive, synthesized inventory of pending and actionable work across Jira (PERFNFV) and GitHub (perftool-incubator), organized by actionability, assignment, and priority.

## Instructions

1. **Prompt for configuration** using `AskUserQuestion` with three questions:

   **Question 1: Assignee / Scope**
   - Header: "Assignee"
   - Question: "Show pending work for which user(s)?"
   - Options:
     - **Me**: "My direct assignments and open PRs/issues" (get authenticated user via `gh api user --jq '.login'`, name via Jira/Git config)
     - **All**: "All organization members (all assignees and unassigned work)"
     - **Specific**: "Specific user" (will prompt for username in Other field)
   - Default: Me

   **Question 2: Focus area**
   - Header: "Focus"
   - Question: "What types of pending work should be prioritized?"
   - Options:
     - **All**: "All pending work (PRs, direct assignments, audit fixes, backlog, campaigns)"
     - **PRs**: "Open PRs requiring review or merge actions only"
     - **Direct Assignments**: "Direct Jira assignments and assigned GitHub issues"
     - **High Priority**: "High-priority items, blockers, and in-progress tasks only"
   - Default: All

   **Question 3: Backlog depth**
   - Header: "Backlog depth"
   - Question: "How deep should the backlog review be?"
   - Options:
     - **Comprehensive**: "Full categorized inventory (PRs, direct tasks, audit fixes, backlog, campaigns)"
     - **Active & Immediate**: "Immediate PR actions and in-progress work only"
   - Default: Comprehensive

2. **Process the answers:**
   - For **Assignee / Scope**:
     - If "Me": get authenticated user with `gh api user --jq '.login'`, set `user_scope` to `"user"` and `target_user` to that username
     - If "Specific": parse username from the Other field, set `user_scope` to `"user"` and `target_user` to that username
     - If "All": set `user_scope` to `"all"` and `target_user` to empty
   - For **Focus area**: set `focus_mode` to `"all"`, `"prs"`, `"assignments"`, or `"high-priority"`
   - For **Backlog depth**: set `backlog_depth` to `"comprehensive"` or `"active"`

3. **Collect GitHub Data using `gh api`:**

   In the queries below, `<author_q>` is:
   - `author:<target_user>` when `user_scope` is `"user"`
   - omitted entirely when `user_scope` is `"all"`

   **A. Open PRs across the organization:**
   ```bash
   gh api "search/issues?q=org:perftool-incubator+type:pr+state:open&per_page=100"
   ```
   For each open PR, extract: repository, PR number, title, author (`user.login`), HTML URL, draft status, and updated timestamp.

   Inspect each PR for mergeability, merge conflict status, CI status, and reviews:
   ```bash
   gh api "repos/perftool-incubator/${repo}/pulls/${number}" --jq '{mergeable: .mergeable, mergeable_state: .mergeable_state, draft: .draft, head_sha: .head.sha}'
   gh api "repos/perftool-incubator/${repo}/pulls/${number}/reviews" --jq '[.[] | {user: .user.login, state: .state}]'
   ```

   **B. Open Issues across the organization:**
   ```bash
   gh api "search/issues?q=org:perftool-incubator+type:issue+state:open&per_page=100"
   ```
   Query total open issue count across all repositories in `perftool-incubator`.

4. **Collect Jira Tickets (optional):**
   If a Jira MCP server is available (check for tools starting with `jira` or `mcp__jira__`), query the `PERFNFV` project:

   **A. Unresolved Tickets Assigned to User:**
   ```
   jql: "project = PERFNFV AND assignee in (\"${target_user}\", \"${target_user}@redhat.com\", \"Karl Rister\", \"krister\") AND resolution is EMPTY ORDER BY key ASC"
   ```

   **B. In-Progress and Active Tickets in Project:**
   ```
   jql: "project = PERFNFV AND status in (\"In Progress\", \"Selected for Development\", \"To Do\") ORDER BY updated DESC"
   ```

   **C. Codebase Audit Epics and Sub-Tasks:**
   ```
   jql: "project = PERFNFV AND (key = PERFNFV-426 OR \"Epic Link\" = PERFNFV-426 OR parent = PERFNFV-426 OR summary ~ \"Codebase audit\" OR summary ~ \"Audit:\") AND resolution is EMPTY ORDER BY key ASC"
   ```

   **D. Performance Studies & Campaign Tickets:**
   ```
   jql: "project = PERFNFV AND (summary ~ \"Campaign\" OR summary ~ \"Latency\" OR summary ~ \"PREEMPT_RT\" OR summary ~ \"tail latency\" OR summary ~ \"vDU\") AND resolution is EMPTY ORDER BY updated DESC"
   ```

5. **Cross-Correlate and Synthesize Findings:**

   Cross-reference every GitHub issue/PR with Jira tickets:
   - Match by key in title/body (e.g., `PERFNFV-400` in PR title or commit message).
   - Match by referenced GitHub issue URL or `#number` in Jira summary/description (e.g., `Issue #55 ... for bench-iperf` -> `bench-iperf#55`).
   - Group findings into clear thematic categories:

   **1. Immediate Pull Request Actions:**
   - Table or structured breakdown of each open PR with:
     - Repository & PR number / link
     - Author
     - Detailed status: Approved & Mergeable (CI green), Changes Requested, Conflicting / Needs Rebase, Awaiting Review
     - Action Needed: Specific technical step required (e.g., "Ready to merge", "Rebase on main to resolve conflict", "Address review comments")

   **2. High-Priority Direct Assignments (for User):**
   - Subdivide into actionable areas:
     - **A. Active Infrastructure & Ongoing Work** (e.g. OpenSearch, shared storage, CDM metric ports)
     - **B. CI Unit Test Workflow Expansion Initiative** (e.g. unit test workflows across subprojects)
     - **C. Core Framework & Subproject Backlog Tasks** (e.g. schema fixes, endpoint refactoring, action migrations)

   **3. Recent Codebase Audit & Systemic Fixes (PERFNFV-426 Epic):**
   - Subdivide by area:
     - **Systemic Bash Bug** (PERFNFV-427 / crucible#647)
     - **Crucible CLI & Framework** (PERFNFV-428, PERFNFV-429, PERFNFV-430, PERFNFV-431)
     - **Benchmark Fixes** (bench-flexran#30, bench-ilab#28, bench-oslat#88, bench-rant#5, bench-timerlat#13, bench-tracer#12)
     - **Tool Post-Processing & Packaging** (tool-rt-trace-bpf#21, tool-ftrace#13, tool-kernel#63, tool-ethtool#7)
     - **Repository Hygiene** (PERFNFV-447 fork-checks, PERFNFV-448 .gitignore additions)

   **4. Active Framework & Tooling Backlog:**
   - Subdivide into:
     - **Tool Metadata & CLI Discovery** (crucible#653, crucible#654)
     - **CommonDataModel (CDM)** (PERFNFV-470, CommonDataModel#207, CommonDataModel#200, PERFNFV-460)
     - **Rickshaw Orchestrator** (PERFNFV-475, PERFNFV-474, rickshaw#866)
     - **Subproject Golden-File Test Batch** (toolbox#127)

   **5. Performance Studies & Benchmark Campaigns:**
   - Highlight active research, RT latency evaluations, and campaign benchmarks:
     - SNO 8x8h Low-Latency Benchmark Campaign with PREEMPT_RT (PERFNFV-476)
     - softirq_inline patch impact on RT kernel network tail latency (PERFNFV-472)
     - SNO vDU Emulation: Impact of OpenShift Housekeeping on Network Latency (PERFNFV-471)
     - Kernel networking tail latency investigation (PERFNFV-270)
     - perftest RDMA subproject addition (PERFNFV-473)

6. **Write the report to `/tmp/pending-work.html`:**
   Generate an HTML file formatted for clean copy-pasting into Google Docs:
   - Start the file with `<meta charset="UTF-8">` to ensure correct character encoding.
   - Use HTML entities for special characters: `&mdash;` for em dashes, `&ndash;` for en dashes, `&bull;` for bullet points. Do not use raw UTF-8 punctuation in the HTML output.
   - Use plain text styling only — bold (`<b>`) for labels, `<p>` for paragraphs, `<ul>`/`<li>` for lists, `<br>` for line breaks. No headings (`<h1>`-`<h6>`), no `<code>` tags.
   - Use `<a href="...">` for all references — PRs, issues, AND Jira tickets (e.g. `<a href="https://issues.redhat.com/browse/PERFNFV-473">PERFNFV-473</a>`), so they paste as clickable links in Google Docs. Every mention of a Jira ticket key or GitHub issue/PR must be an `<a>` link.
   - Dual-link entries wherever a Jira ticket and GitHub issue correspond to each other (e.g., `<a href="https://issues.redhat.com/browse/PERFNFV-400">PERFNFV-400</a> / <a href="https://github.com/perftool-incubator/bench-iperf/issues/55">bench-iperf#55</a>: Description`).
   - Structure sections cleanly with bold section dividers matching the synthesized inventory.

7. **Display the complete synthesized inventory in the conversation output:**
   Present the full categorized report in clean markdown with clickable links for all PRs, issues, and Jira tickets.
