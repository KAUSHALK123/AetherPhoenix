import uuid
from typing import Optional

from shared.contracts.workflow import SharedWorkflowState

from app.memory.task_history import TaskHistoryService, get_task_history_service


class RuntimeContext:
    """
    Represents an active execution context for a session or workflow.
    Provides the environment needed for agents and orchestration.
    """

    def __init__(
        self,
        session_id: str,
        shared_state: Optional[SharedWorkflowState] = None,
        task_history_service: Optional[TaskHistoryService] = None,
    ):
        self.context_id = str(uuid.uuid4())
        self.session_id = session_id

        if shared_state is None:
            from shared.contracts.workflow import WorkflowMetadata

            self.shared_state = SharedWorkflowState(
                metadata=WorkflowMetadata(goal="Active Session")
            )
        else:
            self.shared_state = shared_state

        self.task_history_service = task_history_service or get_task_history_service()

        if self.shared_state and self.shared_state.metadata:
            self.task_history_service.record_workflow_status(
                workflow_id=self.shared_state.metadata.workflow_id,
                goal=self.shared_state.metadata.goal,
                status=(
                    self.shared_state.metadata.status.value
                    if hasattr(self.shared_state.metadata.status, "value")
                    else str(self.shared_state.metadata.status)
                ),
            )

        self.is_active = True

    def mark_complete(self):
        """Marks this execution context as completed."""
        self.is_active = False
        if self.shared_state and self.shared_state.metadata:
            self.task_history_service.record_workflow_status(
                workflow_id=self.shared_state.metadata.workflow_id,
                goal=self.shared_state.metadata.goal,
                status="COMPLETED",
            )
