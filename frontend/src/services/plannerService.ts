import { request } from './apiClient';
import type { GeneratePlanRequest, PlannerPlan, PlannerResponse } from '../types/planner';

export const plannerService = {
  /**
   * Sends goal to the Planner Agent endpoint: POST /api/v1/planner/generate
   */
  async generatePlan(goal: string, sessionId?: string): Promise<PlannerResponse> {
    const payload: GeneratePlanRequest = { goal };
    if (sessionId) {
      payload.session_id = sessionId;
    }

    return request<PlannerResponse>('/api/v1/planner/generate', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Parses the planner reply JSON safely without crashing on malformed strings.
   */
  parsePlanSafely(replyText: string): PlannerPlan | null {
    if (!replyText || typeof replyText !== 'string') return null;
    try {
      // First try standard JSON.parse
      const parsed = JSON.parse(replyText);
      if (typeof parsed === 'object' && parsed !== null) {
        return parsed as PlannerPlan;
      }
      return null;
    } catch {
      // Try to extract JSON substring if embedded in markdown backticks
      try {
        const jsonMatch = replyText.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
        if (jsonMatch && jsonMatch[1]) {
          const parsed = JSON.parse(jsonMatch[1]);
          if (typeof parsed === 'object' && parsed !== null) {
            return parsed as PlannerPlan;
          }
        }
      } catch {
        // Fallback gracefully
      }
      return null;
    }
  },

  /**
   * Modifies a specific task inside the active plan session without regenerating unrelated tasks.
   */
  async modifyTask(
    taskId: string,
    instruction: string,
    sessionId?: string
  ): Promise<PlannerResponse> {
    const goal = `Modify task [${taskId}]: ${instruction}`;
    return this.generatePlan(goal, sessionId);
  },
};
