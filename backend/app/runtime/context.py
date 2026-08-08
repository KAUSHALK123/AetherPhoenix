import uuid
from typing import Optional

from shared.contracts.workflow import SharedWorkflowState


class RuntimeContext:
    """
    Represents an active execution context for a session or workflow.
    Provides the environment needed for agents and orchestration.
    """

    def __init__(
        self, session_id: str, shared_state: Optional[SharedWorkflowState] = None
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

        self.is_active = True

    def mark_complete(self):
        """Marks this execution context as completed."""
        self.is_active = False
