---
name: pr-review
description: High-confidence pull-request review for perftool-incubator repositories, with optional Crucible integration and documentation auditing
---

Review a pull request for defects introduced by the proposed change. Prioritize concrete, actionable correctness and security findings over exhaustive commentary. Do not modify files, create commits, or post GitHub comments unless the user explicitly asks.

## Review target

Accept any of these targets:

- A GitHub PR URL, repository/name plus PR number, or the current branch's PR.
- A local commit or a base branch.
- Current local changes, including staged, unstaged, and untracked files.

If the target is unambiguous, do not stop for a configuration questionnaire. If it is ambiguous, ask one concise question. If prior findings are supplied, use them only to avoid restating the same root cause; never suppress a new symptom, regression, or independent security exposure.

For a GitHub PR, resolve and record the repository, PR number, base SHA, head SHA, title, description, changed-file statuses, CI/check results, existing reviews, and review comments. Use the actual PR head revision for source inspection. Do not combine a PR diff with whatever happens to be checked out in the current workspace. If the head is not locally available, use an isolated temporary worktree or an equivalent read-only source view.

For a local target, record the exact diff range before inspecting files. Include rename, deletion, binary, generated, and untracked-file status in the coverage map.

## Repository context

Before judging code, load the applicable project instructions. Starting at the repository root and walking toward each changed file, apply the normal precedence: the most-specific `AGENTS.override.md`, `AGENTS.md`, `CLAUDE.md`, or configured fallback file wins; user instructions take precedence over repository instructions. For changes in an independently versioned Crucible subproject, read that subproject's instructions and history as well as the parent repository's.

Read the PR description and linked issue context when available. Inspect relevant CI workflows, build files, schemas, and implementation guides only when they bear on the changed behavior. History is useful when intent is ambiguous, but do not run blanket `log` or `blame` passes over every file.

For a GitHub PR, inspect the PR body and commit messages for explicit issue-closing references: `close`, `closes`, `closed`, `fix`, `fixes`, `fixed`, `resolve`, `resolves`, or `resolved` followed by an issue reference, such as `Fixes #123` or `Closes owner/repo#123`. These keywords are case-insensitive and may be followed by a colon. Resolve an unqualified reference against the PR repository and a fully qualified reference against the named repository. A plain issue URL or mention, such as `Related to #123`, is not a closing reference and does not trigger issue coverage.

When closing references exist, inspect each referenced issue's available description and explicit acceptance criteria. Compare every clear stated requirement with behavior delivered by the PR, using its changes and relevant validation as evidence. Do not infer requirements from vague goals or ordinary issue links. If an issue is inaccessible, its reference cannot be resolved unambiguously, or a requirement cannot be assessed from available context, mark the affected issue or requirement inconclusive rather than assuming it is satisfied or unmet.

## Evidence and coverage

1. Build a changed-file and changed-line map from the target's exact base-to-head diff.
2. Read each changed hunk with enough surrounding context to understand the enclosing function, state machine, data structure, or configuration flow. Read an entire file when it is small or when cross-file context requires it; do not consume context reading large unrelated files wholesale.
3. For changed functions, parameters, schemas, commands, and configuration keys, find callers, callees, consumers, and validation sites with repository-aware search. Follow symlinks or subproject boundaries when the architecture requires it.
4. For every code finding, prove that the changed code introduces it. Check the base version, history, or an equivalent before/after execution path when necessary. For issue coverage, verify the PR's explicit closing claim and compare it with the issue's stated requirements.
5. Every primary code finding must point to the shortest possible changed-line range that explains the defect. Do not report a problem only on an unchanged line or attach a finding to a file absent from the diff. If a missing companion file is the cause, attach the finding to the changed line that creates the broken contract and name the missing file in the explanation. For issue coverage, the PR's explicit claim to close an issue is the behavior under review; a concrete unmet requirement does not need a changed code line.

## Finding gate

Report a finding only when all of the following are true:

- It is introduced by this change.
- It is discrete and actionable.
- It materially affects correctness, security, performance, compatibility, or maintainability.
- A concrete input, state, environment, or deployment condition triggers it.
- The author would likely fix it if they knew about it.
- The conclusion does not depend on an unstated assumption about intent or environment.
- It is not merely a linter/compiler/style result, typo, or optional refactoring.

Do not report pre-existing defects, intentional behavior changes, vague future risks, or missing tests by themselves. Report missing regression coverage only when the new behavior is high-risk or the repository's applicable instructions explicitly require the test.

For GitHub issue coverage, report a finding only for a concrete, clearly stated issue requirement that the PR explicitly claims to close but leaves unmet. This mismatch is considered introduced by the PR's closing claim. Apply the normal priority and verdict policy according to the impact of the unmet requirement; do not elevate a finding solely because the issue was linked or closed.

## Primary review passes

Use these passes in priority order. Keep an internal coverage matrix so every changed file and hunk is considered, but do not manufacture a finding for a file with no defect.

### 1. Dataflow, correctness, and contracts

Trace non-trivial changes with concrete values and states. Check boundary and empty cases, arithmetic and time calculations, type and encoding conversions, error propagation, default values, state transitions, retries, cancellation, resource ownership, and concurrent access. For every changed API or parameter, verify declaration, propagation, validation, serialization, and use across all layers. Check callers and callees, format arguments, CLI option definitions, JSON schemas, and backward compatibility.

### 2. Security and trust boundaries

Look specifically for credential or sensitive-data disclosure; shell, command, SQL, template, or path injection; unsafe deserialization; path traversal; authorization or authentication bypass; insecure temporary-file handling; privilege escalation; unsafe container/host or controller/engine boundaries; and sensitive data in logs, metadata, or error responses. Construct an actual triggering input before reporting a security finding.

### 3. Integration and deployment

Check the repository's actual build and runtime wiring. For Crucible benchmarks and tools, inspect applicable `rickshaw.json`, `workshop.json`, `multiplex.json`, schemas, controller-file transfer lists, and executable paths. For other repositories, use their own manifests, CI, packaging, and deployment conventions. Verify new files, dependencies, generated artifacts, configuration keys, migrations, and cross-repository interfaces are connected correctly. Do not apply Crucible-specific checks to repositories where they do not exist.

### 4. Failure, compatibility, and operational behavior

Check malformed input, partial failure, unavailable services, permissions, timeouts, retries, cleanup, restart/resume behavior, upgrades, rollback, mixed-version clients, concurrency, and resource exhaustion. Consider architecture-specific or container-specific paths when the diff affects them. A possible issue is not a finding until the affected path and trigger are demonstrated.

### 5. Tests and validation

Discover the repository's canonical commands from applicable instructions and CI. Run focused tests, schema validation, build checks, or targeted reproductions when practical; use bounded output capture for noisy commands. Run broader validation only when useful. Do not claim a test passed unless it was actually run. A test failure is evidence for a finding only after confirming it is caused by the change rather than the environment or a pre-existing failure.

### 6. Issue coverage (GitHub PRs)

- If the PR has no explicit issue-closing references, omit issue coverage; ordinary issue links and mentions do not trigger it.
- If closing references exist, include an `Issue coverage` section with an outcome for each referenced issue: **addressed**, **unmet**, or **inconclusive**. Mark an issue addressed only when all clear stated requirements are met. If any concrete requirement remains unmet, mark it unmet and report an issue-coverage finding. Mark inaccessible or ambiguous issue context inconclusive. If an issue has both a concrete unmet requirement and other requirements that cannot be assessed, report the unmet finding and note the remaining uncertainty.
- Anchor an issue-coverage finding to the closing reference or issue URL; a changed-file line is not required. State the specific unmet requirement and its impact, then recommend the missing behavior or scope. Do not report vague or unstated expectations as unmet requirements.

## Optional Crucible audit

After the primary review, perform a separate, non-blocking audit when the repository or user request calls for it:

- Documentation and help text reflect changed behavior, defaults, flags, schemas, and file names.
- Crucible CLI changes update the required help and completion locations.
- Required companion files, schemas, image dependencies, and runtime transfer lists are present.
- Relevant architecture and implementation guides remain accurate.
- Style and comments match local conventions and explain intent.

Do not let documentation, cosmetic style, or ordinary missing-test observations obscure primary findings or change the verdict unless the user explicitly asks for that audit to be blocking. Only report a missing-from-diff item when its absence causes a concrete broken contract; attach it to the changed line that demonstrates the break.

## History and prior review

Use `git log` or `git blame` selectively when code intent, compatibility, or a workaround is unclear. For GitHub PRs, inspect existing review comments and unresolved threads. Deduplicate findings by root cause and changed location. Do not treat a prior reviewer comment as proof that the current revision still has the problem; re-check the current head.

## Severity and output

Use priority labels for primary findings:

- **P0** — universal release, data-loss, security, or operational blocker.
- **P1** — serious realistic correctness or security defect that should block merge.
- **P2** — meaningful defect or regression risk that should normally be fixed.
- **P3** — minor but concrete issue; non-blocking unless project context makes it important.

Each finding must have a short imperative title beginning with its priority, a location, one concise paragraph explaining the trigger and impact, and a practical remedy. Code findings use a changed-file line location; issue-coverage findings use the closing reference or issue URL. Include confidence when useful. Keep one finding per distinct root cause. Do not include speculative alternatives or long code excerpts, and do not provide a patch unless requested.

Use this report format:

```text
## PR Review: <repo>#<number> — <title>

**Summary:** <one sentence>
**Scope:** <PR, commit, base branch, or local changes>
**Changed files:** <count>

### Findings
- **[P1] [path/to/file:line] Imperative finding title** — <concrete trigger, impact, and remedy>

### Issue coverage
- `<closing reference>` — **addressed | unmet | inconclusive** — <brief requirement coverage or reason it cannot be assessed>

### Validation
- <commands actually run and results>
- <important limitations>

### Supplemental audit
- <only actionable documentation, deployment, or completeness items; omit when empty>

### File coverage
- [x] <file> — <finding count or no primary findings>

### Verdict
**<Request changes | Approve with comments | Approve>** — <one-line rationale>
```

Omit empty sections. Keep the file-coverage checklist concise; it is an audit trail, not a reason to add findings.

Use this verdict policy:

- **Request changes** for any P0/P1 or another clearly merge-blocking defect.
- **Approve with comments** for P2/P3 or supplemental findings that are actionable but non-blocking.
- **Approve** when no primary findings remain after the confidence check.

Before finalizing, re-check every finding against the exact head revision, location requirement, finding gate, project instructions, and PR intent. For issue-coverage findings, verify the closing reference and unmet requirement; a changed-line location is not required. Remove anything that is pre-existing, speculative, duplicate, non-actionable, or merely cosmetic.
