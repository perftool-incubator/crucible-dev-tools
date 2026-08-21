---
description: Structured multi-dimension code review for a PR in the perftool-incubator org
---

Perform a structured, comprehensive code review of a pull request.

## Instructions

1. **Prompt for configuration** using `AskUserQuestion` with two questions:

   **Question 1: PR selection**
   - Header: "PR"
   - Question: "Which PR should be reviewed?"
   - Options:
     - **Number**: "PR number in current repo" (will prompt for number in Other field; detects repo from git remote)
     - **URL**: "Full GitHub PR URL" (will prompt for URL in Other field, e.g., https://github.com/perftool-incubator/bench-trafficgen/pull/126)
     - **Repo+Number**: "Repo name and PR number" (will prompt for format: repo|number in Other field, e.g., rickshaw|863)
   - Default: Number

   **Question 2: Prior findings**
   - Header: "Prior review"
   - Question: "Should any prior review findings be excluded?"
   - Options:
     - **None**: "No prior findings to exclude"
     - **Exclude**: "Exclude specific findings" (will prompt for description of already-known issues in Other field)
   - Default: None

2. **Process the answers:**
   - For **PR selection**:
     - If "Number": parse PR number from Other field, detect repo from current directory's git remote via `git remote get-url origin`
     - If "URL": extract both repo and PR number from the URL (format: `https://github.com/perftool-incubator/<repo>/pull/<number>`)
     - If "Repo+Number": parse as `repo|number` from the Other field
   - For **Prior findings**:
     - If "Exclude": use the Other field text as the prior findings description
     - If "None": no filtering

3. **Gather PR context:**
   - Run `gh pr view <number> --repo perftool-incubator/<repo> --json title,body,files,commits,state` to get the PR metadata.
   - Run `gh pr diff <number> --repo perftool-incubator/<repo>` to get the full diff.
   - Read the PR description to understand the intent — what problem is being solved and what approach was taken.
   - List all changed files. This is your coverage checklist — every file must be examined.

4. **Read changed files in full.** Before writing any findings, read the COMPLETE current content of every changed file using the Read tool. Do not review from the diff alone — you need surrounding context to catch issues like mismatched function signatures, missing parameter propagation, and inconsistent naming.

   For each changed file, also identify its callers and callees. If file A adds a new parameter, check that file B (which calls into A) passes it. Use grep to find call sites.

   **Git history context.** For non-trivial changes, run `git log --oneline -5 <file>` and `git blame -L <changed-range> <file>` on the PR's base branch to understand why the code was written the way it was. Code that looks wrong may be an intentional workaround — history tells you. Also check recent PRs that touched the same files (`gh pr list --state merged --search "<filename>" --limit 3 --repo perftool-incubator/<repo>`) for reviewer comments that may apply to this PR too.

5. **Review by dimension.** Make six focused passes. Passes 1–5 examine every changed file through a single lens — do not skip files in any pass. Pass 6 checks whether the diff itself is complete by looking for files that should have been changed but weren't.

   **Pass 1 — Correctness:**
   Trace code paths with concrete values, not abstract reasoning. For each non-trivial code change, pick specific inputs and walk through the logic step by step. Check:
   - Boundary conditions and off-by-one errors
   - Sign errors in arithmetic (especially clock/time math)
   - Integer overflow, truncation, or type mismatch
   - Null/undefined/empty handling
   - Error return values — are failures propagated correctly?
   - Resource leaks (file descriptors, memory, semaphores)
   - Race conditions in concurrent code
   - Test coverage — if the repo has a test suite, does this change add or update tests for the new behavior? Flag untested code paths as an Issue, not a Bug.

   **Pass 2 — API & Contracts:**
   Check that callers and callees agree. For every function/parameter added or changed:
   - Is the parameter declared in all layers? (CLI argparse → config propagation → usage site)
   - Do format strings match their arguments? Count every `%d`/`%s` and verify the argument list.
   - Are getopt option strings consistent with the long_opts table? (`required_argument` = `:`, `optional_argument` = `::`, `no_argument` = nothing)
   - Are return values checked at every call site?
   - Do JSON schema entries match the actual field names and types used in code?

   **Pass 3 — Build & Deploy:**
   Check infrastructure wiring. Skip checks that reference artifacts not present in the target repo (e.g., `rickshaw.json` and `workshop.json` only apply to benchmark and tool repos). For every new file or dependency:
   - Is it listed in `rickshaw.json` files-from-controller (for runtime-transferred files)?
   - Is it in the correct workshop JSON (for image-baked dependencies)?
   - Are system package dependencies declared (`distro` requirements in workshop JSON)?
   - Are `multiplex.json` entries present for new parameters?
   - Do file paths in config files match actual file locations?
   - Source files (`.c`, `.py`) should not be copied to `/usr/bin/` — only compiled binaries or executable scripts belong there.

   **Pass 4 — Documentation:**
   Check that docs match the code. For every behavioral change:
   - Does the README parameter table reflect actual defaults and semantics?
   - Does CLAUDE.md list new/renamed files accurately?
   - Does help text (`--help` output) match the actual options?
   - Are renamed or removed files updated in ALL documentation references? (Grep for the old name across the repo.)
   - Do code comments accurately describe what the code does?

   **Pass 5 — Style & Convention:**
   Check consistency with the existing codebase. Read surrounding code to learn patterns before flagging deviations:
   - Indentation and formatting (check modelines if present)
   - Variable naming conventions (lowercase_with_underscores vs camelCase — match what the file already uses)
   - Error handling patterns (does the file use `exit_error`, `fprintf(stderr, ...)`, exceptions?)
   - Shell: `[[ ]]` vs `[ ]`, deprecated operators (`-a`, `-o`)
   - Do NOT report style preferences that differ from the codebase's existing conventions. Only flag deviations from what the codebase already does.

   **Pass 6 — Completeness:**
   Check for files that SHOULD be in the diff but aren't. Passes 1–5 review files that ARE changed — this pass catches missing co-changes in files outside the diff.

   a. **CLAUDE.md co-change rules.** Read the repo's CLAUDE.md (if present). Look for co-change requirements — rules that say "when you change X, also update Y." For each rule, check whether the triggering condition is met by the actual changes in this PR (not just whether a listed file was touched). If the trigger applies and a required companion file is missing from the diff, that is a finding. Common co-change patterns include: CLI flag changes requiring help text + completions + implementation updates; config file changes requiring schema updates; behavioral changes requiring documentation updates.

   b. **Documentation cross-references.** Extract the key terms introduced or changed in the diff: new config keys, flag names, version strings, enum values. Grep `docs/` for these terms in files NOT already in the diff. Read each candidate file and confirm that its content is actually inconsistent with the PR's changes before reporting — do not flag a file just because it mentions a related concept.

   c. **Deduplicate.** If a missing-file finding from this pass describes the same root cause as a finding from an earlier pass (e.g., Pass 4 flagged stale help text in a changed file, and this pass flags the same help file as absent from the diff), keep only the more actionable one.

6. **File coverage audit.** After all six passes, produce a checklist of EVERY file in the diff. For each file, state either the findings or "No issues found." If a file is missing from this list, the review is incomplete — go back and examine it. If Pass 6 identified missing files (files that should be in the diff but aren't), list them separately under a "Missing from diff" sub-heading.

7. **Classify findings by severity:**
   - **Bug**: Incorrect behavior that WILL manifest at runtime. You must describe the specific scenario: what input or condition triggers it, and what goes wrong. If you cannot construct a triggering scenario, downgrade to Issue.
   - **Issue**: Suboptimal but functional — missing validation, fragile assumption, potential future problem. State what would need to happen for this to become a real problem.
   - **Doc**: Documentation inaccuracy, stale reference, or gap.
   - **Style**: Convention deviation with no behavioral impact.

8. **Filter prior findings.** If a prior findings description was given (Question 2), remove any findings that describe the same issue. Do not re-report known problems.

9. **Output the report** in this format:

   ```
   ## PR Review: <repo>#<number> — <title>

   **Summary:** <one sentence describing what the PR does>
   **Changed files:** <count>
   **Review dimensions:** Correctness, API & Contracts, Build & Deploy, Documentation, Style, Completeness

   ### Bugs
   - **[file:line] <description>** — <triggering scenario>

   ### Issues
   - **[file:line] <description>** — <what would need to happen>
   - **[file] <description>** — (for Pass 6 findings about files absent from the diff, omit line number)

   ### Documentation
   - **[file:line] <description>**

   ### Style
   - **[file:line] <description>**

   ### File Coverage
   - [x] file1.c — 2 bugs, 1 issue
   - [x] file2.py — No issues
   - [x] file3.json — 1 doc issue
   ...

   Missing from diff:
   - [ ] schema/services.json — description string needs v10dev added
   ...

   ### Limitations
   <what this review could NOT verify — e.g., runtime behavior, performance, hardware-specific paths>

   ### Verdict
   **<Approve | Approve with comments | Request changes>** — <one-line rationale>
   ```

   Omit any severity section that has zero findings (e.g., if there are no Style findings, omit that section entirely).

10. **Verdict.** End the report with a clear verdict:

   ```
   ### Verdict

   **<verdict>** — <one-line rationale>
   ```

   Use one of these three verdicts:
   - **Approve** — no findings, or only style/cosmetic items that don't need changes before merge.
   - **Approve with comments** — findings exist but none are blocking. The PR is functional and safe to merge; the findings are suggestions or minor doc fixes the author can address at their discretion.
   - **Request changes** — at least one Bug or a blocking Issue that should be fixed before merge. State which specific finding(s) block approval.

## Methodology Rules

These rules govern how findings are evaluated. They are not suggestions — they are requirements.

- **Read before judging.** Read every changed file completely before writing any findings. First impressions from diffs are often wrong because they lack context.
- **Concrete over abstract.** "If `probe_rate=100` and `max_latency_ms=5`, the loop takes `2*5+1=11ms` per iteration, giving 90 probes/sec not 100" catches bugs. "The probe rate might not be accurate" does not.
- **Callers and callees.** A parameter added in file A must be received in file B. A function signature change must be reflected at every call site. Grep for the function name across the repo.
- **No false authority.** If you are unsure whether something is a bug, say so. "This MIGHT be wrong if X, but I cannot verify without Y" is more useful than a confident wrong answer.
- **Codebase conventions win.** The existing code defines the style rules, not external style guides. If the file uses `[ ]` everywhere and one new line uses `[[ ]]`, that is a style finding. If the file uses `[[ ]]` everywhere, a new `[ ]` is the finding.
- **Severity discipline.** Bugs must have triggering scenarios. Issues must have escalation conditions. Do not inflate severity to appear thorough.

## False Positive Exclusions

Do NOT report any of the following — they produce noise, not value:

- **Pre-existing issues.** Problems that exist in the codebase before this PR. The review scope is what this PR changes, not what was already broken.
- **Issues on unmodified lines.** If the PR didn't touch it, don't flag it — even if the surrounding code has problems.
- **Linter/compiler territory.** Missing imports, type mismatches, formatting, unused variables — tools catch these. Don't duplicate their work.
- **Pedantic nitpicks.** Minor style preferences a senior engineer would not bother flagging in a real review.
- **Intentional behavior changes.** If the PR's stated purpose is to change behavior X, don't flag "behavior X changed" as a bug.

## Confidence Check

After assembling all findings but before writing the final report, re-examine each one:

- Can you construct a specific scenario that triggers it? (Bugs and Issues)
- Does git history or the PR description explain why the code is written this way?
- Is this something a senior engineer familiar with the codebase would flag?

Drop any finding where your confidence is low. A shorter report with high-confidence findings is more useful than a longer one padded with uncertain ones.
