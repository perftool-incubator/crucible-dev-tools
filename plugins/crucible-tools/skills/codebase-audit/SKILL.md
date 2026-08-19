---
description: Comprehensive multi-pass codebase audit across all crucible repos
---

Run a structured, repeatable codebase audit across crucible repositories. Checks for code bugs, convention compliance, structural completeness, schema validity, documentation accuracy, and cross-repo consistency.

## Instructions

1. **Prompt for configuration** using `AskUserQuestion` with five questions:

   **Question 1: Audit scope**
   - Header: "Scope"
   - Question: "Which repositories should be audited?"
   - Options:
     - **All**: "All repositories in repos.json"
     - **Core**: "Core subprojects only (rickshaw, toolbox, roadblock, etc.)"
     - **Benchmarks**: "All benchmarks"
     - **Tools**: "All tools"
     - **Specific**: "Specific repository" (will prompt for repo name in Other field)
   - Default: All

   **Question 2: Focus areas**
   - Header: "Focus"
   - Question: "Which audit passes should run?"
   - Options:
     - **All**: "All passes (bugs, conventions, structure, schemas, docs, consistency)"
     - **Bugs**: "Code bugs only (Pass 1)"
     - **Conventions**: "Convention compliance only (Pass 2)"
     - **Structure**: "Structural completeness only (Pass 3)"
     - **Schemas**: "Schema validity only (Pass 4)"
     - **Docs**: "Documentation accuracy only (Pass 5)"
     - **Consistency**: "Cross-repo consistency only (Pass 6)"
   - Default: All

   **Question 3: Severity filter**
   - Header: "Severity"
   - Question: "Filter findings by severity level?"
   - Options:
     - **All**: "Show all findings"
     - **High**: "High severity only"
     - **Medium**: "Medium and high severity"
     - **Low**: "Low, medium, and high severity"
   - Default: All

   **Question 4: Changed files filter**
   - Header: "Changed files"
   - Question: "Audit all files or only recently changed files?"
   - Options:
     - **All files**: "Audit all files in scope"
     - **Since date**: "Only files changed since a specific date" (will prompt for date in Other field, format: YYYY-MM-DD or relative like 1w, 1m)
   - Default: All files

   **Question 5: Jira epic**
   - Header: "Jira epic"
   - Question: "Jira epic for issue tracking (optional)?"
   - Options:
     - **None**: "Don't create Jira tickets"
     - **Specify**: "Use a specific epic" (will prompt for epic key like PERFNFV-334 in Other field)
   - Default: None

2. **Process the answers:**
   - For **Audit scope**: map to repo list (all, core category, benchmark category, tool category, or specific repo name)
   - For **Focus areas**: map to pass list (all or specific pass numbers)
   - For **Severity filter**: use "all", "high", "medium", or "low"
   - For **Changed files filter**: if "Since date", parse date from Other field; otherwise audit all files
   - For **Jira epic**: if "Specify", parse epic key from Other field; otherwise no epic

3. **Discover repos.** Read `$CRUCIBLE_HOME/config/repos.json`. Parse the `official` and `unofficial` arrays. For each repo entry, extract `name`, `type`, `repository` (git URL), and `primary-branch`. Map types to filesystem paths:
   - `primary` → `$CRUCIBLE_HOME`
   - `core` → `$CRUCIBLE_HOME/subprojects/core/<name>`
   - `benchmark` → `$CRUCIBLE_HOME/subprojects/benchmarks/<name>`
   - `tool` → `$CRUCIBLE_HOME/subprojects/tools/<name>`
   - `doc` → `$CRUCIBLE_HOME/subprojects/docs/<name>`
   - `userenvs` → `$CRUCIBLE_HOME/subprojects/userenvs/<name>`

   Filter the repo list according to the selected scope. Verify each repo directory exists before including it.

4. **Dispatch parallel agents.** Spawn agents organized by logical grouping. Each agent receives the full audit methodology (all applicable passes) and the structured output format. Use the Agent tool with `run_in_background: true`.

   When `--scope all`, use this grouping:

   | Agent | Repos | Rationale |
   |-------|-------|-----------|
   | 1 | crucible (main repo) | Largest, unique structure (bin/, config/, schema/) |
   | 2 | rickshaw | Second largest, Python + bash + JSON + schemas |
   | 3 | Core subprojects: toolbox, roadblock, multiplex, workshop, packrat, CommonDataModel | Shared libraries, smaller repos |
   | 4 | RT benchmarks: cyclictest, hwlatdetect, hwnoise, oslat, osnoise, timerlat | Similar structure, same patterns |
   | 5 | Network benchmarks: trafficgen, uperf, iperf | Complex multi-role benchmarks |
   | 6 | Other benchmarks: fio, sleep, tracer, flexran, pytorch, ilab, rant | Varied complexity |
   | 7 | All tools: sysstat, procstat, ftrace, kernel, ovs, nvidia, power, forkstat, rt-trace-bpf, mlxreg, ethtool, dpdk | Similar structure |
   | 8 | Infrastructure: crucible-ci, crucible-dev-tools, crucible-examples, testing-repo, external-userenvs | CI/docs/meta repos |

   When `--scope` limits to a single repo, use one agent. When limited to a category, use 1-2 agents.

   If `--since` is specified, include the date in each agent's prompt so they limit their file scope accordingly.

5. **Agent prompt template.** Each agent receives a prompt structured as follows (adapt the repo list and paths per agent):

   ```
   Audit the following crucible repos for bugs, convention violations, and structural issues.

   Repos to audit:
   - <name> at <path> (type: <type>, primary-branch: <branch>)
   - ...

   [If --since specified: Only audit files changed since <date>. Run `git log --since=<date> --name-only --pretty=format:` in each repo to get the file list.]
   [If --focus specified: Only run the specified passes.]

   Run these audit passes on each repo:

   PASS 1 — CODE BUGS
   Read every source file. Look for:
   - Typos in variable/function names that will cause NameError, undefined variable, or wrong-variable bugs
   - Logic errors: inverted conditions, wrong comparisons, off-by-one, unreachable code
   - Copy-paste bugs: wrong variable in repeated patterns, wrong repo/tool name in a script copied from another
   - String/format errors: wrong format specifiers, missing f-prefix on f-strings, broken interpolation, mismatched quotes
   - Error handling: wrong exception type caught, silently swallowed errors, wrong return value on error path
   - Resource leaks: unclosed files, unreleased locks or semaphores
   - Shell bugs: unquoted variable expansions in word-splitting contexts, wrong test operators (-z vs -n, = vs ==), array handling errors, missing `local` declarations
   - JSON structural issues: typos in keys that cause silent mismatches, duplicate keys

   For each finding, construct a specific triggering scenario — what input or state causes the bug to manifest. If you cannot construct one, downgrade to MEDIUM severity.

   PASS 2 — CONVENTION COMPLIANCE
   Check all Bash scripts (files with #!/bin/bash, #!/usr/bin/env bash, or sourced by such files) for:
   a) Both modelines present (first two lines after shebang):
      # -*- mode: sh; indent-tabs-mode: nil; sh-basic-offset: 4 -*-
      # vim: autoindent tabstop=4 shiftwidth=4 expandtab softtabstop=4 filetype=bash
   b) No tab indentation — all indentation must be 4 spaces
   c) Use of `exit_error "message"` from the base library instead of raw `exit 1` or `exit N`
   d) Scripts source the appropriate base file (benchmark scripts source bench-base which sources toolbox; tool scripts source tool-base; crucible scripts source $CRUCIBLE_HOME/bin/base)
   e) Variable naming: lowercase_with_underscores for local variables, UPPERCASE for exported/environment variables

   Check Python files for:
   f) PEP 8 compliance (focus on naming conventions and obvious violations, not whitespace nitpicks)

   Check JSON files for:
   g) kebab-case keys (not camelCase or snake_case)

   Report convention findings aggregated per repo — one summary line per check type, with a count and the list of affected files. Do NOT report one finding per file per check.

   PASS 3 — STRUCTURAL COMPLETENESS
   For benchmark repos, check required files per docs/implementing-a-new-benchmark.md:
   - rickshaw.json (required)
   - workshop.json (required — some repos use client-workshop-*.json/server-workshop.json instead; note the variant but don't flag as missing)
   - <name>-client (required)
   - <name>-post-process or <name>-post-process.py (required)
   - <name>-get-runtime (required — some repos use <name>-runtime; note the variant)
   - rickshaw.json `benchmark` field matches the directory name
   - rickshaw.json schema-version is current

   For tool repos, check required files per docs/implementing-a-new-tool.md:
   - rickshaw.json (required)
   - workshop.json (required)
   - <name>-start (required)
   - <name>-stop (required)
   - <name>-post-process or <name>-post-process.py (required)
   - rickshaw.json `tool` field matches the directory name
   - rickshaw.json schema-version is current

   For ALL repos, check per docs/developer-guide.md:
   - LICENSE file exists
   - README.md exists
   - CLAUDE.md exists
   - .gitignore exists
   - .github/workflows/fork-check.yaml exists
   - .github/workflows/run-crucible-tracking.yaml exists

   Report structural findings aggregated per repo.

   PASS 4 — SCHEMA VALIDATION
   First, validate the schema files themselves. The original codebase audit found typos in JSON Schema keywords (minLemgth, additionalProperies, uniqueuItems) that silently disabled validation constraints. Any misspelled keyword means the constraint it was meant to express is not enforced.

   Schema file locations to check:
   - rickshaw/schema/*.json (18 files: benchmark.json, tool.json, run-file.json, bench-params.json, tool-params.json, bench-metric.json, kube.json, remotehosts.json, osp.json, kvm.json, etc.)
   - crucible/schema/*.json (3 files: repos.json, services.json, registries.json)
   - multiplex/JSON/schema.json and multiplex/JSON/req-schema.json
   - workshop/schema.json
   - roadblock/roadblock.py — embedded schemas defined as Python dicts in define_msg_schema() and define_usr_msg_schema() methods
   - Any other files named *schema* discovered during the audit

   For each schema file, recursively walk every key. Check every key against the set of valid JSON Schema keywords for the declared draft. Valid draft-07 keywords are: $schema, $ref, $id, $comment, definitions, type, enum, const, properties, required, additionalProperties, patternProperties, items, additionalItems, contains, minItems, maxItems, uniqueItems, minimum, maximum, exclusiveMinimum, exclusiveMaximum, multipleOf, minLength, maxLength, pattern, format, allOf, anyOf, oneOf, not, if, then, else, title, description, default, examples, readOnly, writeOnly, contentMediaType, contentEncoding, propertyNames, minProperties, maxProperties, dependencies. Keys inside `properties` objects are user-defined field names and should not be checked. Pay special attention to keywords within edit distance 1-2 of a valid keyword — these are likely typos.

   Then validate data files against their schemas:
   - Each benchmark's rickshaw.json against rickshaw/schema/benchmark.json
   - Each tool's rickshaw.json against rickshaw/schema/tool.json
   - Each multiplex.json against multiplex/JSON/schema.json (check: no empty strings in vals arrays, every preset param has a matching validation rule)
   - Each workshop.json against workshop/schema.json
   - Crucible config files against their schemas (config/repos.json against schema/repos.json, etc.)

   Use `python3 -c "import jsonschema; ..."` for validation if the jsonschema library is available. If not, perform structural checks manually by reading both files and comparing.

   PASS 5 — DOCUMENTATION ACCURACY
   - CLAUDE.md: if it has a "Key files" or similar table, verify every listed file exists in the repo. Flag files listed but missing, and important files present but not listed.
   - README.md: if it documents parameters, verify they match multiplex.json defaults and valid values. If it describes scripts, verify the descriptions match what the scripts actually do.
   - No stale references to removed files: grep for filenames that were deleted in past commits but still referenced in docs or other files (check git log for deleted files, then grep for their names)
   - No stale language references: grep for "perl", ".pl", ".pm", "Perl" in docs/README — the Perl-to-Python port is complete and these references should be gone

   PASS 6 — CROSS-REPO CONSISTENCY
   - files-from-controller: for every entry in rickshaw.json `files-from-controller`, verify the `src` path references a file that actually exists relative to the benchmark/tool directory
   - workshop.json packages: check that distro package names in workshop.json are plausible (no obvious typos like `pyhton3` or `libpcap-devl`)
   - Tool collector types: verify whitelist/blacklist values in tool rickshaw.json are valid (must be from: all, worker, client, server, profiler)
   - Metric classes: post-process scripts should use valid CDM metric classes (throughput, count, latency)
   - default-aggregation values: where present in post-process scripts, values must be one of sum, avg, max, min

   OUTPUT FORMAT
   Return findings in these exact formats:

   Code bug findings (Passes 1, 4, 5, 6):
   FINDING|<repo>|<file>|<line>|<pass>|<severity>|<category>|<description>|<fix>

   Convention/structural findings (Passes 2, 3):
   CONVENTION|<repo>|<check>|<count>|<severity>|<file-list>

   Where:
   - repo: repository name (e.g., bench-trafficgen, rickshaw)
   - file: path relative to the repo root
   - line: line number (0 if N/A)
   - pass: 1-6
   - severity: high, medium, low
   - category: typo, logic-error, copy-paste, format-error, error-handling, resource-leak, shell-bug, json-structural, schema-keyword, schema-validation, stale-doc, stale-ref, missing-file, cross-ref
   - check: missing-modelines, tab-indentation, raw-exit, missing-base-source, var-naming, missing-license, missing-readme, missing-claude-md, missing-gitignore, missing-fork-check, missing-tracking-workflow, missing-required-file
   - description: one-line description of the finding
   - fix: suggested fix (or N/A for structural issues)
   - file-list: comma-separated list of affected files

   SEVERITY RULES:
   - HIGH: Will crash, produce wrong results, or silently skip functionality at runtime. Must have a concrete triggering scenario.
   - MEDIUM: Functional issue that may not always manifest, or convention/structural violation that impacts maintainability.
   - LOW: Cosmetic issue, documentation inaccuracy, or minor inconsistency with no runtime impact.

   FALSE POSITIVE EXCLUSIONS — do NOT report:
   - Intentional design choices documented in CLAUDE.md or code comments
   - Patterns consistent within a repo even if they differ from org-wide convention
   - Files under repos/ that are git clones — only audit via subprojects/ symlinks
   - Test files, example files, or generated files that intentionally violate conventions
   ```

5. **Collect and deduplicate results.** As agents complete, parse their output lines. Deduplicate findings that describe the same issue from different angles (e.g., a missing file flagged by both Pass 3 and Pass 6). Keep the more specific finding.

6. **Apply severity filter.** If `--severity` was specified, filter findings to the requested minimum level.

7. **Present the consolidated report:**

   ```
   ## Crucible Codebase Audit Report

   **Scope:** <what was audited>
   **Date:** <today's date>
   **Focus:** <which passes were run>
   **Repos scanned:** <count>

   ### Summary

   | Severity | Count |
   |----------|-------|
   | HIGH     | N     |
   | MEDIUM   | N     |
   | LOW      | N     |
   | **Total**| N     |

   ### Findings by Pass

   | Pass | Focus | Findings |
   |------|-------|----------|
   | 1. Code Bugs | Typos, logic errors, shell bugs | N |
   | 2. Conventions | Modelines, indentation, error handling | N |
   | 3. Structure | Required files, repo hygiene | N |
   | 4. Schema | Schema self-validation, data validation | N |
   | 5. Documentation | CLAUDE.md accuracy, stale references | N |
   | 6. Cross-Repo | File references, workshop packages | N |

   ### HIGH Severity Findings

   #### <repo>

   | # | File | Line | Pass | Category | Description | Fix |
   |---|------|------|------|----------|-------------|-----|
   | 1 | path | N | 1 | category | desc | fix |

   ### MEDIUM Severity Findings

   #### <repo>

   Convention violations:
   - **missing-modelines**: N files — file1, file2, ...
   - **tab-indentation**: N files — file1, file2, ...

   Individual findings:
   | # | File | Line | Pass | Category | Description | Fix |
   |---|------|------|------|----------|-------------|-----|

   ### LOW Severity Findings
   ...

   ### Per-Repo Summary

   | Repo | Type | HIGH | MED | LOW | Total |
   |------|------|------|-----|-----|-------|
   | ... | | | | | |
   | **Total** | | | | | |
   ```

   Omit any severity section that has zero findings.

8. **Offer issue creation.** After presenting the report, ask: "Would you like me to create Jira tickets and GitHub issues from these findings?"

   If the user says yes:
   - Group findings by repo. Create one Jira ticket per repo (or split large repos into logical groups if findings span very different areas).
   - Create a new Jira epic for this audit run, or use `--epic` if provided. Set epic summary to "Codebase audit: <date>".
   - Map severity to Jira priority: HIGH → Critical, MEDIUM → Major, LOW → Minor.
   - Set story points based on fix complexity: 1-2 for convention fixes, 3-5 for code bug fixes, 5-8 for cross-repo issues.
   - For each Jira ticket, create a corresponding GitHub issue in the affected repo. Include the Jira ticket key in the GitHub issue body. Include a checklist of individual findings.
   - Present a summary of created tickets when done.

## Methodology Rules

- **Read before judging.** Each agent must read every file in its scope before reporting findings. Grep-only analysis misses context.
- **Concrete over abstract.** "If `max_latency_ms=0`, the division on line 47 raises ZeroDivisionError" catches bugs. "The latency calculation might have edge cases" does not.
- **Verify against source.** When checking structural requirements, read the implementation guides (`docs/implementing-a-new-benchmark.md`, `docs/implementing-a-new-tool.md`, `docs/developer-guide.md`) to confirm the requirement is current. Requirements evolve — some repos may legitimately use variant file naming.
- **Schema keywords are case-sensitive.** `minlength` is not `minLength`. `additionalproperties` is not `additionalProperties`. These are HIGH severity because they silently disable validation.
- **Aggregate convention findings.** Convention violations (modelines, tabs, exit_error) are reported per-repo with file counts and lists, not as individual findings. This keeps the report scannable when dozens of files have the same issue.
- **Severity discipline.** HIGH findings must have triggering scenarios. MEDIUM findings must explain what would need to happen for the issue to manifest. Do not inflate severity.
