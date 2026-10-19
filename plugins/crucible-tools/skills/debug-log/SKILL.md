---
description: Analyze crucible logs to debug failed runs or commands
---

Analyze crucible logs to debug a failed run or command.

## Instructions

1. **Prompt for configuration** using `AskUserQuestion`:

   **Question: Session selection**
   - Header: "Session"
   - Question: "Which session(s) should be analyzed?"
   - Options:
     - **Last**: "Most recent session"
     - **Last N**: "Last N sessions" (will prompt for number in Other field)
     - **Specific**: "Specific session ID" (will prompt for session ID in Other field)
     - **Since**: "Sessions from a time range" (will prompt for time like 1h, 2d, YYYY-MM-DD in Other field)
   - Default: Last

2. **Process the answer:**
   - If "Last": analyze the most recent session
   - If "Last N": parse number from the Other field, analyze last N sessions
   - If "Specific": parse session ID from the Other field, analyze that session
   - If "Since": parse time range from the Other field, analyze sessions from that time
   - Resolve the selection to one or more exact `session_id` values from the session listing before gathering diagnostics. For "Since", compare the session timestamps to the requested range.

3. Start by listing recent sessions to establish context:
   ```
   crucible log sessions --sort timestamp --order desc --format json
   ```
   Use each entry's `session_id`, `timestamp`, and `command` fields to resolve the selected session IDs. Show the user the recent sessions so they can identify which one to investigate.

4. For the target session(s), gather diagnostic information:

   **Check for errors:**
   ```
   crucible log view sessionid <session-id> --stream stderr --tail 50
   ```

   **Check the end of the session for exit status:**
   ```
   crucible log view sessionid <session-id> --tail 30
   ```

   **Search for common failure patterns:**
   ```
   crucible log view sessionid <session-id> --grep "ERROR|FAIL|error|abort|timeout"
   ```
   Run each query for every selected session ID.

5. If a run session is identified, also check:

   Find that session's run directory by matching the session ID suffix (run directories are named `<benchmark>--<timestamp>--<session-id>`):
   ```
   find /var/lib/crucible/run -mindepth 1 -maxdepth 1 -type d -name "*--<session-id>" -print
   ```
   Use the matching directory in the artifact paths below for each selected run session. If there is no match, skip the run artifacts for that session. Do not use the `latest` symlink for a selected historical session.

   **Run result summary:**
   ```
   cat <run-directory>/run/result-summary.txt
   ```

   **Endpoint logs (for kube/remotehost failures):**
   ```
   xzcat <run-directory>/run/endpoint/*/endpoint-stderrout.txt.xz | grep -i "error\|fail\|abort\|timeout" | tail -20
   ```

   **Roadblock timeouts:**
   ```
   xzcat <run-directory>/run/endpoint/*/endpoint-stderrout.txt.xz | grep -i "roadblock.*timeout\|CRITICAL"
   ```

6. Present findings as a summary:
   - What command was run and when
   - Session duration
   - Key errors found (with context lines)
   - Where in the pipeline the failure occurred (image sourcing, deployment, execution, post-processing, indexing)
   - Suggested next steps for investigation
