---
description: Create a new repository in the perftool-incubator GitHub organization
---

Create a new repository in the perftool-incubator GitHub organization with standard files, workflows, team permissions, and branch protection rulesets.

## Instructions

1. **Prompt for configuration** using `AskUserQuestion` with four questions:

   **Question 1: License**
   - Header: "License"
   - Question: "Which license should the repository use?"
   - Options:
     - **apache-2.0**: "Apache License 2.0"
     - **mit**: "MIT License"
     - **gpl-3.0**: "GNU General Public License v3.0"
   - Default: apache-2.0

   **Question 2: Repository type**
   - Header: "Type"
   - Question: "What kind of repository is this?"
   - Options:
     - **Tool**: "New tool repository — name should follow the tool-<name> convention"
     - **Benchmark**: "New benchmark repository — name should follow the bench-<name> convention"
     - **Custom**: "Other kind of repository — no naming convention required"
   - Default: Tool

   **Question 3: Repository name**
   - Header: "Name"
   - Question: "What should the full repository name be? Type it into the Other field (e.g. tool-mlxreg, bench-perftest)."
   - Options:
     - **Tool example**: "e.g. tool-mlxreg — type your actual name in Other"
     - **Benchmark example**: "e.g. bench-perftest — type your actual name in Other"
   - Default: none (the name is mandatory — if the user selects a labeled option instead of typing into Other, ask a direct follow-up question for the literal name before proceeding)

   **Question 4: Repository description**
   - Header: "Description"
   - Question: "What should the repository description be?"
   - Options:
     - **Custom**: "Type a one-line description in the Other field"
     - **Auto**: "Generate a default description from the repo name and type"
   - Default: Custom

2. **Process the answers:**
   - For **License**: use the selected license value
   - For **Repository type**: use to validate/suggest the naming convention for Question 3
   - For **Repository name**: use the literal text from the Other field. This value is mandatory — if it's missing, ask a follow-up question rather than guessing
   - For **Repository description**: if "Custom", use the Other field text; if "Auto", generate "<Type> plugin for the crucible performance testing framework" using the type from Question 2
   - The primary branch is always `main`

3. Create the repo:
   ```
   gh repo create perftool-incubator/<repo> --public --description "<description>" --license <license>
   ```

4. Clone it to a temporary directory and create the standard files:

   **README.md:**
   ```markdown
   # <repo>

   <description> for the [crucible](https://github.com/perftool-incubator/crucible) performance testing framework.
   ```

   **`.github/workflows/fork-check.yaml`:**
   ```yaml
   name: fork-check

   on:
     pull_request_target:
       types: [opened, reopened, synchronize, edited]

   permissions:
     issues: write
     pull-requests: write

   jobs:
     block-fork-pr:
       if: github.event.pull_request.head.repo.fork == true
       runs-on: ubuntu-latest
       steps:
         - name: Comment and close fork PR
           uses: actions/github-script@v7
           with:
             script: |
               await github.rest.issues.createComment({
                 owner: context.repo.owner,
                 repo: context.repo.repo,
                 issue_number: context.issue.number,
                 body: 'This PR was opened from a fork. PRs must be opened from branches on the upstream repository so that CI workflows have access to required secrets and variables.\n\nPlease push your branch to this repository and open a new PR.\n\nClosing this PR automatically.'
               });
               await github.rest.pulls.update({
                 owner: context.repo.owner,
                 repo: context.repo.repo,
                 pull_number: context.issue.number,
                 state: 'closed'
               });
   ```

   **`.github/workflows/run-crucible-tracking.yaml`:**
   ```yaml
   name: run-crucible-tracking

   on:
     pull_request:
       types: [ opened ]
     issues:
       types: [ opened ]

   jobs:
     call-crucible-tracking:
       if: github.repository_owner == 'perftool-incubator'
       uses: perftool-incubator/crucible-ci/.github/workflows/crucible-tracking.yaml@main
       with:
         app_id: ${{ vars.APP_ID__PROJECT_CRUCIBLE_TRACKING }}
       secrets:
         private_key: ${{ secrets.PRIVATE_KEY__PROJECT_CRUCIBLE_TRACKING }}
   ```

4. Commit and push the initial files to `main`.

5. Add organization teams to the repo:
   ```
   gh api orgs/perftool-incubator/teams/administrators/repos/perftool-incubator/<repo> --method PUT -f permission=admin
   gh api orgs/perftool-incubator/teams/developers/repos/perftool-incubator/<repo> --method PUT -f permission=push
   gh api orgs/perftool-incubator/teams/maintainers/repos/perftool-incubator/<repo> --method PUT -f permission=maintain
   ```

6. Create branch protection rulesets:

   **default-branch ruleset** (`gh api repos/perftool-incubator/<repo>/rulesets --method POST`):
   ```json
   {
     "name": "default-branch",
     "target": "branch",
     "enforcement": "active",
     "conditions": {
       "ref_name": {
         "include": ["~DEFAULT_BRANCH"],
         "exclude": []
       }
     },
     "rules": [
       {"type": "deletion"},
       {"type": "non_fast_forward"},
       {
         "type": "pull_request",
         "parameters": {
           "required_approving_review_count": 1,
           "dismiss_stale_reviews_on_push": true,
           "required_reviewers": [],
           "require_code_owner_review": false,
           "require_last_push_approval": false,
           "required_review_thread_resolution": true,
           "allowed_merge_methods": ["merge"]
         }
       }
     ],
     "bypass_actors": []
   }
   ```

   **releases ruleset** (`gh api repos/perftool-incubator/<repo>/rulesets --method POST`):
   ```json
   {
     "name": "releases",
     "target": "branch",
     "enforcement": "active",
     "conditions": {
       "ref_name": {
         "include": ["refs/heads/20[2-9][0-9]\\.[1234]", "refs/heads/ci-version-test"],
         "exclude": []
       }
     },
     "rules": [
       {"type": "deletion"},
       {"type": "non_fast_forward"},
       {
         "type": "pull_request",
         "parameters": {
           "required_approving_review_count": 1,
           "dismiss_stale_reviews_on_push": true,
           "required_reviewers": [],
           "require_code_owner_review": false,
           "require_last_push_approval": false,
           "required_review_thread_resolution": true,
           "allowed_merge_methods": ["merge"]
         }
       }
     ],
     "bypass_actors": [
       {
         "actor_id": 962037,
         "actor_type": "Integration",
         "bypass_mode": "always"
       }
     ]
   }
   ```

7. Back up the rulesets into the repo:
   - Fetch each ruleset via `gh api repos/perftool-incubator/<repo>/rulesets/<id>`
   - Strip metadata fields (`node_id`, `created_at`, `updated_at`, `current_user_can_bypass`, `_links`)
   - Save to `.github/rulesets/branches/default-branch.json` and `.github/rulesets/branches/releases.json`
   - Add `.github/rulesets/README.md` with content: `The files stored here are for documentation / tracking purposes only.  They must be loaded into the GitHub web GUI to be "active" -- their presence here does not result in any behavioral changes by GitHub.`

8. Commit the ruleset backups on a feature branch, create a PR requesting review from the Developers team, and self-assign.
