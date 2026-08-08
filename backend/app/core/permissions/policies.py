from typing import Set
from .models import PermissionType

# Define which permissions are inherently risky and always require explicit approval,
# even in ASSISTED mode. AUTONOMOUS mode might still execute them if explicitly configured,
# but usually, these are the dangerous operations.
RISKY_PERMISSIONS: Set[PermissionType] = {
    PermissionType.FILE_DELETE,
    PermissionType.TERMINAL_EXECUTE,
    PermissionType.POWERSHELL_EXECUTE,
    PermissionType.REGISTRY_EDIT,
    PermissionType.ADMIN_PRIVILEGE,
}

class PermissionPolicy:
    @staticmethod
    def requires_approval(permission_type: PermissionType, mode: str) -> bool:
        """
        Determines if a given permission requires explicit user approval based on the execution mode.
        """
        # In Safe Mode, EVERYTHING requires approval.
        if mode == "SAFE":
            return True
        
        # In Assisted Mode, only risky operations require approval.
        if mode == "ASSISTED":
            return permission_type in RISKY_PERMISSIONS
        
        # In Autonomous Mode, nothing requires explicit approval in real-time,
        # assuming it's within the bounds of what the user originally allowed.
        if mode == "AUTONOMOUS":
            return False
        
        # Default to safe if unknown mode
        return True
