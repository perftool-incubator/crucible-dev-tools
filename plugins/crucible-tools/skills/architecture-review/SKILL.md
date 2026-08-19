---
description: Top-down architecture and design review across crucible subsystems
---

Evaluate crucible's architecture across defined dimensions — abstraction integrity, coupling, plugin contracts, error handling, configuration, data flow, and sustainability. Produces subsystem-level analysis with trade-off discussion and recommendations, not line-level bug reports.

## Instructions

1. **Prompt for configuration** using `AskUserQuestion` with three questions:

   **Question 1: Review scope**
   - Header: "Scope"
   - Question: "Which architectural dimensions should be reviewed?"
   - Options:
     - **All**: "All dimensions (abstraction, coupling, contracts, errors, config, dataflow, evolution)"
     - **Abstraction**: "Abstraction integrity only"
     - **Coupling**: "Coupling analysis only"
     - **Contracts**: "Plugin contracts only"
     - **Errors**: "Error handling only"
     - **Config**: "Configuration only"
     - **Dataflow**: "Data flow only"
     - **Evolution**: "Sustainability/evolution only"
   - Default: All

   **Question 2: Review depth**
   - Header: "Depth"
   - Question: "How thorough should the review be?"
   - Options:
     - **Survey**: "High-level assessment examining key files and patterns"
     - **Deep**: "Thorough analysis tracing specific code paths end-to-end"
   - Default: Survey

   **Question 3: Repository focus**
   - Header: "Repo focus"
   - Question: "Focus on a specific repository's integration?"
   - Options:
     - **System-wide**: "Review the entire system architecture"
     - **Specific repo**: "Focus on how a specific repo integrates" (will prompt for repo name in Other field)
   - Default: System-wide

2. **Process the answers:**
   - For **Review scope**: map the selection to dimension(s)
   - For **Review depth**: use "survey" or "deep" mode
   - For **Repository focus**: if "Specific repo", parse repo name from Other field

3. **Read architecture documentation.** Before spawning agents, read these docs to establish the intended architecture. Agents need this context to distinguish intentional design from accidental drift.
   - `$CRUCIBLE_HOME/docs/crucible-architecture-overview.md` — the intended layering
   - `$CRUCIBLE_HOME/docs/implementing-a-new-benchmark.md` — the plugin contract
   - `$CRUCIBLE_HOME/docs/implementing-a-new-tool.md` — the tool plugin contract
   - `$CRUCIBLE_HOME/docs/how-engines-work.md` — engine isolation model
   - `$CRUCIBLE_HOME/docs/how-endpoints-work.md` — endpoint abstraction
   - `$CRUCIBLE_HOME/docs/developer-guide.md` — coding conventions and language strategy

   Summarize the key architectural invariants from these docs (e.g., "engines don't know their endpoint type", "benchmarks interact only through rickshaw.json contract"). Include these invariants in each agent's prompt so they can verify whether the code upholds them.

4. **Dispatch parallel agents.** Spawn one agent per review dimension. Each agent focuses on a single dimension but reads across repos as needed. Use the Agent tool with `run_in_background: true`.

   When `--scope` limits to a single dimension, use one agent. When `--repo` is specified, agents should focus their analysis on that repo's integration points.

   | Agent | Dimension | Key files to examine |
   |-------|-----------|---------------------|
   | 1 | Abstraction Integrity | rickshaw-run.py, endpoints/*.py, engine.py, bootstrap.py, benchmark scripts |
   | 2 | Coupling Analysis | toolbox imports across consumers, rickshaw imports, benchmark/tool imports |
   | 3 | Plugin Contract | rickshaw.json files, schemas, implementation guides, multiplex.json files |
   | 4 | Error Model | exit_error, sys.exit calls, roadblock error paths, engine abort handling |
   | 5 | Configuration | config/, schema/, sysconfig, run-file flow, jsonsettings.py |
   | 6 | Data Flow | post-process scripts, CDM indexing, file transfer code, logger |
   | 7 | Evolution | language stats, schema versioning, test infrastructure, docs vs code |

5. **Agent prompt template.** Each agent receives a prompt structured as follows (adapt per dimension):

   ```
   You are reviewing crucible's architecture for the "<dimension name>" dimension.

   CRUCIBLE CONTEXT:
   Crucible is a multi-repo performance testing framework (~40 repos). Key architectural invariants:
   <paste the invariants extracted from the docs in step 2>

   Key repo locations (all under $CRUCIBLE_HOME = /opt/crucible):
   - bin/ — CLI entry point (Bash)
   - subprojects/core/rickshaw/ — orchestrator (Python)
   - subprojects/core/toolbox/ — shared library (Python + Bash)
   - subprojects/core/roadblock/ — distributed synchronization (Python)
   - subprojects/core/multiplex/ — parameter expansion (Python)
   - subprojects/core/workshop/ — container image builds (Python)
   - subprojects/core/CommonDataModel/ — data model and query engine (JavaScript)
   - subprojects/core/packrat/ — archive/restore (Bash)
   - subprojects/benchmarks/<name>/ — benchmark plugins (Bash + Python)
   - subprojects/tools/<name>/ — tool plugins (Bash + Python)
   - docs/ — architecture and implementation guides

   DEPTH: <survey|deep>
   [If --repo specified: FOCUS: Evaluate all aspects through the lens of <repo>'s integration]

   YOUR DIMENSION: <dimension name>
   Evaluate the following aspects. For each, assess the current state, identify concerns, and provide recommendations.

   <dimension-specific instructions below>
   ```

   **Dimension 1 — Abstraction Integrity:**
   ```
   Evaluate whether crucible's defined abstraction boundaries hold in practice.

   a) ENDPOINT ABSTRACTION
   The three endpoint types (remotehosts, kube, osp) should expose identical semantics to rickshaw. Check:
   - Read rickshaw-run.py and grep for endpoint-type-specific branches (if.*remotehost, if.*kube, etc.). Each such branch is a potential abstraction leak.
   - Read endpoints/endpoints.py to understand the base class contract. Then spot-check one or two endpoint implementations (e.g., kube/kube.py, remotehosts/remotehosts.py) — do they diverge in what they report back?
   - Check benchmark scripts for endpoint-type awareness. Grep across subprojects/benchmarks/ for "remotehost", "kube", "osp", "endpoint.*type".

   b) ENGINE ISOLATION
   Engines should not know what endpoint type deployed them. Check:
   - Read engine/engine.py and engine/bootstrap.py for any references to endpoint types, kube-specific paths, or SSH assumptions.
   - Check if engine scripts in benchmarks/tools make assumptions about their deployment environment.

   c) CONTROLLER ENCAPSULATION
   The controller container should be a clean boundary. Check:
   - Do bin/ scripts (host-side) reference paths inside the controller container?
   - Does anything outside the controller assume what's installed inside it?

   d) PLUGIN BOUNDARY
   Benchmarks/tools should interact only through their rickshaw.json contract. Check:
   - Do any benchmarks import from rickshaw, toolbox, or other core repos directly (beyond what's delivered via files-from-controller)?
   - Do benchmarks reference rickshaw internal variables, paths, or conventions not documented in the integration contract?

   OUTPUT FORMAT:
   For each sub-aspect (a-d), provide:
   - Assessment: Good / Adequate / Needs Attention / Significant Debt
   - Strengths (what works well)
   - Concerns (numbered, with severity, evidence from specific files, impact, and recommendation)
   ```

   **Dimension 2 — Coupling Analysis:**
   ```
   Map dependency directions and identify problematic coupling patterns.

   a) TOOLBOX DEPENDENCY SURFACE
   Toolbox is the shared library used by rickshaw, engine code, and some benchmarks. Check:
   - What modules/functions are imported from toolbox? Run: grep -r "from toolbox" across subprojects/core/rickshaw/ and subprojects/benchmarks/ and subprojects/tools/. Categorize by module.
   - Is the API surface minimal and focused, or has it grown to include too many unrelated things?
   - Are there toolbox functions that only one consumer uses (suggesting the function belongs in that consumer, not toolbox)?

   b) ROADBLOCK COUPLING
   Rickshaw uses both toolbox.roadblock (wrapper) and roadblock.roadblock (direct import). Check:
   - Why both? Does the wrapper add value (error handling, logging, retry)?
   - Could one be eliminated?

   c) CROSS-REPO DEPENDENCY GRAPH
   Map which repos depend on which other repos at import/source time:
   - grep for "from toolbox", "from roadblock", "import roadblock", "source.*toolbox", "source.*bench-base", "source.*tool-base" across all subprojects/
   - Draw the dependency direction. Flag any unexpected edges or near-circular dependencies.

   d) IMPLICIT COUPLING VIA CONVENTIONS
   Repos couple through naming conventions (<name>-client, <name>-post-process, metric types, CDM field names). Check:
   - Are these conventions enforced by schemas/validation, or just by tradition and copy-paste?
   - What happens when a convention is violated? Silent failure or caught error?

   OUTPUT FORMAT:
   Same as Dimension 1 — assessment, strengths, and numbered concerns per sub-aspect.
   ```

   **Dimension 3 — Plugin Contract Completeness:**
   ```
   Evaluate whether the three-file integration contract (rickshaw.json + multiplex.json + workshop.json) fully specifies a benchmark's/tool's requirements.

   a) UNDOCUMENTED ASSUMPTIONS
   Read docs/implementing-a-new-benchmark.md and docs/implementing-a-new-tool.md. Then read 2-3 actual benchmark implementations (e.g., fio, trafficgen, cyclictest). Identify things the benchmarks rely on that aren't documented in the contract:
   - Environment variables set by the engine/bootstrap
   - Utilities assumed to be available in the container
   - Filesystem layout conventions
   - CDM output format expectations

   b) CONTRACT VARIATIONS
   Some benchmarks use non-standard file naming:
   - client-workshop-*.json / server-workshop.json instead of workshop.json
   - <name>-runtime instead of <name>-get-runtime
   - Multiple workshop files (trafficgen has client-workshop-01, client-workshop-02)
   Are these documented exceptions with a reason, or organic drift? Is rickshaw's code flexible enough to handle them, or does it special-case each variant?

   c) SCHEMA VS. REALITY
   Compare rickshaw/schema/benchmark.json and rickshaw/schema/tool.json against what rickshaw-run.py actually parses from rickshaw.json files. Are there fields the code reads that aren't in the schema? Fields in the schema the code ignores?

   d) POST-PROCESSING CONTRACT
   How well defined is the output format post-processors must produce?
   - Read toolbox/python/toolbox/metrics.py (CDMMetrics class) to understand the expected API
   - Compare against what docs/implementing-a-new-benchmark.md says about post-processing
   - Check 2-3 post-processors (e.g., cyclictest, fio, trafficgen) — do they use the same patterns, or has each evolved its own approach?

   OUTPUT FORMAT:
   Same as Dimension 1 — assessment, strengths, and numbered concerns per sub-aspect.
   ```

   **Dimension 4 — Error Model:**
   ```
   Evaluate error handling as a system property across all layers.

   a) ERROR PROPAGATION ACROSS BOUNDARIES
   Trace the error path from a benchmark failure to the user:
   - A benchmark script calls exit 1 or exit_error → engine.py detects this how? → roadblock is notified how? → rickshaw-run.py learns of it how? → the controller produces what output? → the CLI shows what to the user?
   - Read the relevant code at each boundary. Identify where error context (the original error message, the failing component, the failing host) is preserved, translated, or lost.

   b) DISTRIBUTED FAILURE COORDINATION
   When one engine in a multi-engine run fails:
   - How does roadblock propagate this to other engines? Read the abort handling in roadblock and engine.py.
   - Can zombie engines persist after a failure? Check cleanup paths.
   - What happens to partial results from engines that completed before the failure?

   c) ERROR CLASSIFICATION
   Does the system distinguish between:
   - User errors (bad run file, unreachable endpoint)
   - Infrastructure failures (container pull failed, SSH timeout)
   - Benchmark bugs (crash in benchmark script)
   - Framework bugs (crash in rickshaw)
   Check if error messages help users identify which category they're in.

   d) RECOVERY MODEL
   - Can post-processing be re-run on existing results? (crucible index <dir>)
   - Can a partial run be resumed?
   - Can individual failed samples be retried without re-running the entire iteration?

   OUTPUT FORMAT:
   Same as Dimension 1 — assessment, strengths, and numbered concerns per sub-aspect.
   ```

   **Dimension 5 — Configuration Architecture:**
   ```
   Evaluate the configuration system's consistency and ergonomics.

   a) CONFIG FORMAT INVENTORY
   Catalog all configuration mechanisms in crucible:
   - JSON config files (config/*.json)
   - JSON run files (user-provided)
   - Shell environment variables (CRUCIBLE_HOME, CRUCIBLE_NAME, etc.)
   - Sysconfig files (/etc/sysconfig/crucible)
   - CLI flags (bin/_main argument parsing)
   - Identity files (~/.crucible/identity)
   How many distinct config mechanisms exist? Do they interact cleanly?

   b) DEFAULTS AND OVERRIDE CHAINS
   Pick a specific config value (e.g., the OpenSearch host, or the number of samples) and trace how its default is set, where it can be overridden, and what the precedence order is. Is this precedence consistent across different config values, or does each have its own rules?

   c) VALIDATION COVERAGE
   - Which config paths go through JSON schema validation? (Check schema/ directory and validation calls)
   - Which config paths are unvalidated? (sysconfig, environment variables, CLI flags)
   - What happens when invalid config is provided to an unvalidated path?

   d) CONFIG DOCUMENTATION
   - Are all config files documented? Check if docs/how-services-work.md covers all services.json fields.
   - Are environment variables documented? Check if docs/how-the-installer-works.md covers all CRUCIBLE_* variables.
   - Are there undocumented config knobs (grep for os.environ.get or ${VAR:-default} patterns)?

   OUTPUT FORMAT:
   Same as Dimension 1 — assessment, strengths, and numbered concerns per sub-aspect.
   ```

   **Dimension 6 — Data Flow Architecture:**
   ```
   Evaluate how data moves through the system from benchmark execution to query results.

   a) METRIC DATA PIPELINE
   Trace the path of a metric value from benchmark output to query result:
   - Benchmark produces raw output files (JSON, CSV, text)
   - Post-processor reads raw output, produces CDM metric-data documents
   - rickshaw-post-process.py collects and indexes documents into OpenSearch
   - CDM server queries and aggregates on request
   At each stage: are there data fidelity risks? Type coercion? Silent drops? Truncation?
   Check toolbox/python/toolbox/metrics.py for the CDMMetrics API.

   b) FILE TRANSFER MODEL
   Engine files are delivered via SSH/SFTP at runtime rather than baked into images.
   - What happens when file transfer fails? Read bootstrap.py and engine.py for retry/error handling.
   - Is the set of files transferred validated against what rickshaw.json declares?
   - Are transferred files integrity-checked (checksums)?

   c) RESULT STORAGE
   Run data at /var/lib/crucible/run/:
   - Is the storage format documented and stable?
   - Can old results be re-indexed with newer CDM versions? (crucible index <dir>)
   - Is there a migration path when the storage format changes?

   d) LOG CONVERGENCE
   Logs come from: CLI (crucible logger), controller (rickshaw), engines (benchmark/tool scripts), endpoints (deployment). Check:
   - Can a user trace a failure from the CLI error message back to the root cause in an engine log?
   - Are timestamps synchronized across layers?
   - Read docs/how-the-logger-works.md — does it describe the full picture or only the CLI layer?

   OUTPUT FORMAT:
   Same as Dimension 1 — assessment, strengths, and numbered concerns per sub-aspect.
   ```

   **Dimension 7 — Evolution and Sustainability:**
   ```
   Evaluate how well the architecture supports ongoing development and change.

   a) LANGUAGE STRATEGY COHERENCE
   The stated strategy is: "new code in Python, Bash for host-side CLI, JavaScript for CDM."
   - Count files by language across the project to see the current mix.
   - Are there recent additions in the wrong language? (e.g., new Bash where Python was called for)
   - Are there friction points where language boundaries create problems? (e.g., Bash calling Python calling Bash)

   b) SCHEMA EVOLUTION
   How does the system handle version skew?
   - CDM versions (v9dev, v10dev): how are new versions added? Read CommonDataModel code for version handling.
   - rickshaw.json schema versions: what happens when a benchmark uses an old schema version?
   - Run file versions: is there a version field? What's the migration story?
   - Is forward/backward compatibility considered in the design?

   c) TEST COVERAGE MODEL
   - What tests exist? find subprojects/ -name "test*" -o -name "*test*" -type f | group by repo
   - What's testable in isolation vs. requires a full crucible run?
   - Are abstraction boundaries tested at their interfaces (e.g., can you test a benchmark's integration without deploying to an endpoint)?
   - Is there a mock/stub infrastructure for testing components in isolation?

   d) DOCUMENTATION CURRENCY
   - Compare docs/ guides against the current code. Pick 2-3 guides and spot-check whether their descriptions of specific mechanisms match what the code actually does.
   - Check CLAUDE.md files across repos — do they reflect the current file structure?
   - Are there areas of the architecture with no documentation at all?

   OUTPUT FORMAT:
   Same as Dimension 1 — assessment, strengths, and numbered concerns per sub-aspect.
   ```

5. **Collect and synthesize results.** As agents complete, read each dimension's output. Look for cross-cutting themes that appear in multiple dimensions (e.g., if both the error model and data flow dimensions flag the same subsystem, that's a convergent signal).

6. **Present the consolidated report:**

   ```
   ## Crucible Architecture Review

   **Scope:** <what was reviewed>
   **Date:** <today's date>
   **Depth:** <survey|deep>

   ### Executive Summary
   <3-5 sentence overview of architectural health — what's strong, what needs attention, and the single most impactful recommendation>

   ### Dimension Scorecard

   | Dimension | Assessment | Concerns |
   |-----------|-----------|----------|
   | 1. Abstraction Integrity | Good / Adequate / Needs Attention / Significant Debt | N |
   | 2. Coupling Analysis | ... | N |
   | 3. Plugin Contract | ... | N |
   | 4. Error Model | ... | N |
   | 5. Configuration | ... | N |
   | 6. Data Flow | ... | N |
   | 7. Evolution | ... | N |

   ### Detailed Findings

   <For each dimension, present:>

   ## <N>. <Dimension Name>

   ### Overall Assessment: <rating>

   ### Strengths
   - <what the architecture does well>

   ### Concerns

   1. **<short title>** — severity: <low|medium|high>

      <description of the concern>

      **Evidence:** <specific files, patterns, or code paths>
      **Impact:** <what problems this causes or could cause>
      **Recommendation:** <what to do, with trade-offs>

   ### Recommendations Summary
   | # | Concern | Severity | Effort | Recommendation |
   |---|---------|----------|--------|----------------|

   <end of per-dimension section>

   ### Top Recommendations
   <Prioritized list of the 5-10 most impactful recommendations across all dimensions, ordered by impact × feasibility. For each, note which dimension(s) it addresses.>

   ### Cross-Cutting Themes
   <Patterns that appeared in multiple dimensions — these are often the most important architectural issues because they reflect systemic properties, not isolated problems.>

   ### Scope Limitations
   <What this review could NOT evaluate:>
   - Runtime performance characteristics
   - Production failure mode analysis (requires operational data)
   - User experience and ergonomics (requires user research)
   - Security posture (requires dedicated security review)
   ```

   Omit any dimension section that was excluded by `--scope`.

7. **Offer issue creation.** After presenting the report, ask: "Would you like me to create Jira tickets from the recommendations?"

   If yes:
   - Architecture findings are typically larger work items. Create stories or epics, not bugs.
   - Group related concerns into single tickets where they share a common fix.
   - Set story points based on effort estimates from the recommendations.
   - Link to the review report in the ticket description for context.

## Methodology Rules

- **Architecture, not code quality.** This skill evaluates design decisions and structural properties. Individual code bugs belong in codebase-audit. If you find a bug while tracing architecture, note it briefly but don't make it a primary finding.
- **Intended vs. actual.** The docs describe the intended architecture. The code shows the actual architecture. Discrepancies are findings, not errors — the question is whether the drift is intentional evolution or accidental degradation.
- **Trade-offs, not judgments.** Every architectural decision has trade-offs. When you identify a concern, acknowledge what the current design gains (not just what it costs). "The file-transfer model creates runtime fragility but enables cacheable images" is useful. "The file-transfer model is bad" is not.
- **Evidence over opinion.** Every concern must cite specific files, functions, or patterns. "The endpoint abstraction leaks" requires showing where specifically the leak is.
- **Proportional depth.** In `survey` mode, read key files and grep for patterns. In `deep` mode, trace code paths end-to-end. Don't deep-dive when surveying.
- **Respect intentional simplicity.** Not every subsystem needs a sophisticated abstraction. A bash script that calls `exit 1` may be perfectly appropriate for its context. Evaluate whether complexity is warranted before recommending it.
