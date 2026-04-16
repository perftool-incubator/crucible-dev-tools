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
| `/crucible-tools:repo-status` | Show git status across all crucible repos |
| `/crucible-tools:open-prs` | Show open PRs in the org (optionally filter by author) |
| `/crucible-tools:dev-activity` | Generate development activity charts (commits, PRs, workflow runs) |
| `/crucible-tools:weekly-summary` | Generate a weekly activity summary with PR links |

## Agents

| Agent | Description |
|-------|-------------|
| `ci-analyzer` | Analyze GitHub Actions CI workflow runs to diagnose failures |

## Requirements

- `gh` CLI authenticated with the perftool-incubator organization
- `python3` available in PATH
- `jq` available in PATH
