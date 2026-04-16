# crucible-dev-tools

Claude Code plugin providing development tools for the [crucible](https://github.com/perftool-incubator/crucible) performance testing framework.

## Installation

This plugin is automatically available when working in the crucible project. Run `crucible update` to clone it, then accept the plugin prompt when opening crucible in Claude Code.

For manual installation:

```
/plugin marketplace add perftool-incubator/crucible-dev-tools
/plugin install crucible-tools@crucible-dev-tools
```

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
