---
description: Create a new repository in the perftool-incubator GitHub organization
---

Create a new repository in the perftool-incubator GitHub organization with standard files, workflows, team permissions, and branch protection rulesets.

Arguments: $ARGUMENTS

## Instructions

1. Gather the following from the user (or from the arguments):
   - **Repo name** (e.g., `tool-mlxreg`, `bench-newbench`)
   - **Description** (one-line summary)
   - **License** (default: `apache-2.0`)

   The primary branch is always `main`.

2. Create the repo:
   ```
   gh repo create perftool-incubator/<repo> --public --description "<description>" --license <license>
   ```

3. Clone it to a temporary directory and create the standard files:

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
       types: [opened, reopened]

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
   - Add `.github/rulesets/README.md` with content: `The files stored here are for documentation / tracking purposes only.  They must be loaded into the GitHub web GUI to be "active" -- there presence here does not result in any behavioral changes by GitHub.`

8. Commit the ruleset backups on a feature branch, create a PR requesting review from the Developers team, and self-assign.
