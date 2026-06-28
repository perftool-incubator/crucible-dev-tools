# crucible-dev-tools — Claude Code Plugin for Crucible Development

## Purpose

Provides development workflow skills and agents for the crucible performance testing framework as a Claude Code plugin.

## Structure

```
.claude-plugin/marketplace.json     Plugin marketplace registration
plugins/crucible-tools/
  .claude-plugin/plugin.json        Plugin metadata
  skills/                           8 skill directories, each with SKILL.md
  agents/                           Agent definitions (ci-analyzer.md)
  bin/                              Python scripts backing the skills
```

## Skills

Each skill is a directory under `plugins/crucible-tools/skills/` containing a `SKILL.md` with YAML frontmatter (`description:`) and markdown instructions.

| Skill | Script | Description |
|-------|--------|-------------|
| activity-summary | — | Activity summary (delegates to gh CLI) |
| debug-log | — | Analyze crucible logs |
| dev-activity | `bin/dev-activity.py` | Development activity charts |
| image-cleanup | — | Clean up podman images |
| new-repo | — | Create new org repo with standard config |
| open-prs | `bin/open-prs.py` | Open PRs in the org |
| repo-status | `bin/repo-status.py` | Git status across crucible repos |
| workflow-status | `bin/workflow-status.py` | Active CI workflow runs |

Skills without a backing script are instruction-only (Claude executes `gh` commands directly).

## Agents

| Agent | File | Description |
|-------|------|-------------|
| ci-analyzer | `agents/ci-analyzer.md` | Diagnose GitHub Actions CI failures |

## Key Conventions

- Python scripts output pipe-delimited rows with a type prefix (e.g., `RUN|`, `RUNNER|`, `REPO_SUMMARY|`)
- SKILL.md instructions tell Claude how to parse and display the script output
- Scripts write progress to stderr, data to stdout
- All scripts require `gh` CLI authenticated with the perftool-incubator organization
- Python scripts use no external dependencies beyond the standard library

## Testing

- Syntax check: `python3 -c "import ast; ast.parse(open('file').read())"`
- Run scripts directly: `python3 plugins/crucible-tools/bin/<script>.py --help`
- Scripts can be tested with `--format pretty` (where supported) for terminal output
