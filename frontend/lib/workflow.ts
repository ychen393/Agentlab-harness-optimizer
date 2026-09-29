import type { WorkflowState } from "../types/contracts";

// Keep this table exhaustive: adding a WorkflowState requires updating the
// stage contract before the UI can compile.
const WORKFLOW_STAGE: Record<WorkflowState, 1 | 2 | 3 | 4 | 5> = {
  ready: 1,
  execution: 2,
  execution_failed: 2,
  diagnosed: 3,
  patch_ready: 4,
  validated: 5,
};

export function workflowStage(state: WorkflowState): 1 | 2 | 3 | 4 | 5 {
  return WORKFLOW_STAGE[state];
}
