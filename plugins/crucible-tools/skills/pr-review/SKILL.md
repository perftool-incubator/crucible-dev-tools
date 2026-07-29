---
description: Structured multi-dimension code review for a PR in the perftool-incubator org
---

Perform a structured, comprehensive code review of a pull request.

Arguments: $ARGUMENTS

## Instructions

1. **Parse arguments:**
   - First positional argument: PR number (required) or full GitHub PR URL
   - `--repo <name>`: repository name within perftool-incubator (optional — if omitted, detect from the current working directory's git remote)
   - `--prior "<text>"`: prior review findings to exclude from this review, as a quoted string describing already-known issues. Findings that match prior items should be silently excluded from the report.
   - If a full URL like `https://github.com/perftool-incubator/bench-trafficgen/pull/126` is given, extract both the repo and PR number from it.

2. **Gather PR context:**
   - Run `gh pr view <number> --repo perftool-incubator/<repo> --json title,body,files,commits,state` to get the PR metadata.
   - Run `gh pr diff <number> --repo perftool-incubator/<repo>` to get the full diff.
   - Read the PR description to understand the intent — what problem is being solved and what approach was taken.
   - List all changed files. This is your coverage checklist — every file must be examined.

3. **Read changed files in full.** Before writing any findings, read the COMPLETE current content of every changed file using the Read tool. Do not review from the diff alone — you need surrounding context to catch issues like mismatched function signatures, missing parameter propagation, and inconsistent naming.

   For each changed file, also identify its callers and callees. If file A adds a new parameter, check that file B (which calls into A) passes it. Use grep to find call sites.

4. **Review by dimension.** Make five focused passes through ALL changed files. Each pass examines every file through a single lens. Do not skip files in any pass.

   **Pass 1 — Correctness:**
   Trace code paths with concrete values, not abstract reasoning. For each non-trivial code change, pick specific inputs and walk through the logic step by step. Check:
   - Boundary conditions and off-by-one errors
   - Sign errors in arithmetic (especially clock/time math)
   - Integer overflow, truncation, or type mismatch
   - Null/undefined/empty handling
   - Error return values — are failures propagated correctly?
   - Resource leaks (file descriptors, memory, semaphores)
   - Race conditions in concurrent code

   **Pass 2 — API & Contracts:**
   Check that callers and callees agree. For every function/parameter added or changed:
   - Is the parameter declared in all layers? (CLI argparse → config propagation → usage site)
   - Do format strings match their arguments? Count every `%d`/`%s` and verify the argument list.
   - Are getopt option strings consistent with the long_opts table? (`required_argument` = `:`, `optional_argument` = `::`, `no_argument` = nothing)
   - Are return values checked at every call site?
   - Do JSON schema entries match the actual field names and types used in code?

   **Pass 3 — Build & Deploy:**
   Check infrastructure wiring. For every new file or dependency:
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

5. **File coverage audit.** After all five passes, produce a checklist of EVERY file in the diff. For each file, state either the findings or "No issues found." If a file is missing from this list, the review is incomplete — go back and examine it.

6. **Classify findings by severity:**
   - **Bug**: Incorrect behavior that WILL manifest at runtime. You must describe the specific scenario: what input or condition triggers it, and what goes wrong. If you cannot construct a triggering scenario, downgrade to Issue.
   - **Issue**: Suboptimal but functional — missing validation, fragile assumption, potential future problem. State what would need to happen for this to become a real problem.
   - **Doc**: Documentation inaccuracy, stale reference, or gap.
   - **Style**: Convention deviation with no behavioral impact.

7. **Filter prior findings.** If `--prior` was provided, remove any findings that describe the same issue. Do not re-report known problems.

8. **Output the report** in this format:

   ```
   ## PR Review: <repo>#<number> — <title>

   **Summary:** <one sentence describing what the PR does>
   **Changed files:** <count>
   **Review dimensions:** Correctness, API & Contracts, Build & Deploy, Documentation, Style

   ### Bugs
   - **[file:line] <description>** — <triggering scenario>

   ### Issues
   - **[file:line] <description>** — <what would need to happen>

   ### Documentation
   - **[file:line] <description>**

   ### Style
   - **[file:line] <description>**

   ### File Coverage
   - [x] file1.c — 2 bugs, 1 issue
   - [x] file2.py — No issues
   - [x] file3.json — 1 doc issue
   ...

   ### Limitations
   <what this review could NOT verify — e.g., runtime behavior, performance, hardware-specific paths>

   ### Verdict
   **<Approve | Approve with comments | Request changes>** — <one-line rationale>
   ```

   Omit any severity section that has zero findings (e.g., if there are no Style findings, omit that section entirely).

9. **Verdict.** End the report with a clear verdict:

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
