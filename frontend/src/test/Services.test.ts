import { describe, it, expect } from 'vitest';
import { plannerService } from '../services/plannerService';

describe('plannerService parsePlanSafely', () => {
  it('parses direct JSON string properly', () => {
    const jsonStr = JSON.stringify({
      workflow_spec: 'Test Workflow',
      tasks: [{ task_id: '1', task_name: 'Test Task' }],
    });

    const parsed = plannerService.parsePlanSafely(jsonStr);
    expect(parsed).not.toBeNull();
    expect(parsed?.workflow_spec).toBe('Test Workflow');
    expect(parsed?.tasks?.[0].task_name).toBe('Test Task');
  });

  it('gracefully extracts JSON embedded inside markdown code fences', () => {
    const markdownStr = `Here is the generated plan:
\`\`\`json
{
  "workflow_spec": "Embedded Plan",
  "estimated_time_seconds": 30
}
\`\`\`
Let me know if you want to proceed.`;

    const parsed = plannerService.parsePlanSafely(markdownStr);
    expect(parsed).not.toBeNull();
    expect(parsed?.workflow_spec).toBe('Embedded Plan');
    expect(parsed?.estimated_time_seconds).toBe(30);
  });

  it('returns null safely on malformed JSON without throwing', () => {
    const malformed = 'Not a json object at all { incomplete...';
    const parsed = plannerService.parsePlanSafely(malformed);
    expect(parsed).toBeNull();
  });
});
