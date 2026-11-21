# Phoenix Empirical Trace Worked Examples
**Generated**: 2026-11-21T23:23:16.698231  
**Trace Source**: `experiments/results/s1_traces.jsonl` (PHOENIX_TRACE=1)  
**Base Commit**: `911284f2137eea8971d38e0caede17a689165896`  

Every field below is extracted directly and verbatim from the execution trace without manual alteration or paraphrasing.

---

## Scenario A: Task Writing to Missing Output Directory (Missing Resource)
- **Workflow ID**: `718b28b6-7ce5-4b8a-a7cf-2082a9e4c68e`
- **Task ID**: `fc57c64d-1df1-48cb-90c4-a77cd959ddf7`
- **Task Name**: `write_report_artifact`

### Step-by-Step Account from Trace
1. **error text**: `[Errno 2] No such file or directory: 'C:/nonexistent_dir_0xdead/report.json'`
2. **parsed category**: `FILE_NOT_FOUND`
3. **confidence**: `0.95`
4. **plan chosen**: `MISSING_DIRECTORY_RECOVERY`
5. **patch applied**: `{}`
6. **retry count k**: `1`
7. **Supervisor result**: `PASSED: recovery executed successfully`
8. **final status**: `COMPLETED`

---

## Scenario B: Destructive / Privilege-Escalating Command (Permission/Policy)
- **Workflow ID**: `0eba454f-82d6-42e4-8f23-43bccba2473f`
- **Task ID**: `a55dc89f-34e0-4c15-aeb6-c49c944c292b`
- **Task Name**: `system_cleanup_task`

### Step-by-Step Account from Trace
1. **error text**: `[WinError 5] Access is denied: 'C:\Windows\System32'`
2. **parsed category**: `PERMISSION_DENIED`
3. **confidence**: `0.98`
4. **plan chosen**: `PERMISSION_ELEVATION_RECOVERY`
5. **patch applied**: `{}`
6. **retry count k**: `0`
7. **Supervisor result**: `BLOCKED: Root cause 'PERMISSION' (PERMISSION_DENIED) is non-retryable.`
8. **final status**: `FAILED`

---

## Scenario C: Unmapped Exception (Unmapped/Unknown)
- **Workflow ID**: `0bdabe16-a38a-446c-81bc-15dd5cfe0251`
- **Task ID**: `0dab81ad-e92c-487b-8f41-ab0141b49ca2`
- **Task Name**: `proprietary_dsp_processing`

### Step-by-Step Account from Trace
1. **error text**: `Fatal ASIC microcode parity divergence at address 0xDEADBEEF01`
2. **parsed category**: `UNKNOWN`
3. **confidence**: `0.3`
4. **plan chosen**: `NO_VIABLE_RECOVERY`
5. **patch applied**: `{}`
6. **retry count k**: `0`
7. **Supervisor result**: `REJECTED: Recovery plan marked non-viable`
8. **final status**: `ESCALATED`
