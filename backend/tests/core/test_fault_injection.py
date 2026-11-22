import asyncio
import subprocess
import sys
from pathlib import Path

import pytest

# Add Major root to sys.path
root_dir = Path(__file__).resolve().parents[2]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from experiments.fault_injection import FaultInjector, UnmappedCustomException
from shared.contracts.execution import ExecutionResult


@pytest.mark.asyncio
async def test_fault_injector_synthetic_mode():
    injector = FaultInjector(mode="synthetic", seed=123)
    assert injector.mode == "synthetic"
    assert injector.seed == 123

    for fc in ["TIMEOUT", "MISSING_RESOURCE", "TOOL_ADAPTER_FAILURE", "PERMISSION_DENIED", "STATE_INCONSISTENCY"]:
        res = await injector.generate_fault(fc)
        assert isinstance(res, ExecutionResult)
        assert res.success is False
        assert res.output["mode"] == "synthetic"
        assert res.output["fault_class"] == fc


@pytest.mark.asyncio
async def test_fault_injector_real_exception_mode():
    injector = FaultInjector(mode="real_exception", seed=456)
    assert injector.mode == "real_exception"

    # 1. Timeout
    exc_timeout = await injector.generate_fault("TIMEOUT")
    assert isinstance(exc_timeout, (asyncio.TimeoutError, TimeoutError))

    # 2. FileNotFoundError
    exc_fnf = await injector.generate_fault("MISSING_RESOURCE")
    assert isinstance(exc_fnf, FileNotFoundError)

    # 3. Subprocess CalledProcessError
    exc_subproc = await injector.generate_fault("TOOL_ADAPTER_FAILURE")
    assert isinstance(exc_subproc, subprocess.CalledProcessError)
    assert exc_subproc.returncode == 42

    # 4. PermissionError
    exc_perm = await injector.generate_fault("PERMISSION_DENIED")
    assert isinstance(exc_perm, PermissionError)

    # 5. Unmapped custom exception
    exc_unmapped = await injector.generate_fault("STATE_INCONSISTENCY")
    assert isinstance(exc_unmapped, UnmappedCustomException)


def test_fault_injector_invalid_mode():
    with pytest.raises(ValueError, match="Invalid mode"):
        FaultInjector(mode="invalid_mode")
