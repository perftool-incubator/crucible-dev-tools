# crucible-dev-tools

Claude Code plugin providing development tools for the [crucible](https://github.com/perftool-incubator/crucible) performance testing framework.

## Installation

New crucible installations include this repo as a subproject. For existing
installs, run `crucible update` first. Then register the plugin marketplace:

```
claude plugin marketplace add ${CRUCIBLE_HOME}/subprojects/core/crucible-dev-tools
```

Claude Code will prompt you to install the crucible-tools plugin — accept it.

## Skills

| Skill | Description |
|-------|-------------|
| `/crucible-tools:activity-summary` | Generate an activity summary for the perftool-incubator GitHub organization |
| `/crucible-tools:debug-log` | Analyze crucible logs to debug failed runs or commands |
| `/crucible-tools:dev-activity` | Generate development activity charts for the perftool-incubator GitHub organization |
| `/crucible-tools:image-cleanup` | Clean up local podman images (engine images, dangling images, local builds) |
| `/crucible-tools:new-repo` | Create a new repository in the perftool-incubator GitHub organization |
| `/crucible-tools:open-prs` | Show all open PRs in the perftool-incubator GitHub organization |
| `/crucible-tools:repo-status` | Show the local git status for all crucible repos |
| `/crucible-tools:workflow-status` | Show active CI workflow runs across crucible repos |

## Agents

| Agent | Description |
|-------|-------------|
| `ci-analyzer` | Analyze GitHub Actions CI workflow runs to diagnose failures |

## Requirements

- `gh` CLI authenticated with the perftool-incubator organization
- `python3` available in PATH
- `jq` available in PATH
