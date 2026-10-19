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

3. Start by listing recent sessions to establish context:
   ```
   crucible log sessions --sort timestamp --order desc
   ```
   Show the user the recent sessions so they can identify which one to investigate.

4. For the target session(s), gather diagnostic information:

   **Check for errors:**
   ```
   crucible log view last --stream stderr --tail 50
   ```

   **Check the end of the session for exit status:**
   ```
   crucible log view last --tail 30
   ```

   **Search for common failure patterns:**
   ```
   crucible log view last --grep "ERROR\|FAIL\|error\|abort\|timeout"
   ```

5. If a run session is identified, also check:

   **Run result summary:**
   ```
   cat /var/lib/crucible/run/latest/run/result-summary.txt
   ```

   **Endpoint logs (for kube/remotehost failures):**
   ```
   xzcat /var/lib/crucible/run/latest/run/endpoint/*/endpoint-stderrout.txt.xz | grep -i "error\|fail\|abort\|timeout" | tail -20
   ```

   **Roadblock timeouts:**
   ```
   xzcat /var/lib/crucible/run/latest/run/endpoint/*/endpoint-stderrout.txt.xz | grep -i "roadblock.*timeout\|CRITICAL"
   ```

6. Present findings as a summary:
   - What command was run and when
   - Session duration
   - Key errors found (with context lines)
   - Where in the pipeline the failure occurred (image sourcing, deployment, execution, post-processing, indexing)
   - Suggested next steps for investigation
