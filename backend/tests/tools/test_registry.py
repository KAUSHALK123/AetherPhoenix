import pytest
from app.tools.registry import ToolRegistry
from shared.contracts.tool import Tool, ToolHealth, ToolState


@pytest.fixture
def registry():
    return ToolRegistry()


def test_register_and_get(registry):
    tool = Tool(
        name="playwright",
        adapter="browser_adapter",
    )
    registry.register(tool)

    fetched = registry.get("playwright")
    assert fetched is not None
    assert fetched.name == "playwright"
    assert fetched.adapter == "browser_adapter"
    assert fetched.status == ToolState.INSTALLED
    assert fetched.health == ToolHealth.UNKNOWN


def test_register_duplicate(registry):
    tool1 = Tool(
        name="playwright",
        adapter="browser_adapter",
    )
    registry.register(tool1)

    tool2 = Tool(
        name="playwright",
        adapter="different_adapter",
    )

    with pytest.raises(ValueError, match="already registered"):
        registry.register(tool2)


def test_unregister(registry):
    tool = Tool(
        name="temp_tool",
        adapter="temp_adapter",
    )
    registry.register(tool)

    registry.unregister("temp_tool")
    assert registry.get("temp_tool") is None


def test_list_all_and_by_state(registry):
    tool1 = Tool(name="tool1", adapter="adpt1", status=ToolState.READY)
    tool2 = Tool(name="tool2", adapter="adpt2", status=ToolState.INSTALLED)
    tool3 = Tool(name="tool3", adapter="adpt3", status=ToolState.READY)

    registry.register(tool1)
    registry.register(tool2)
    registry.register(tool3)

    all_tools = registry.list_all()
    assert len(all_tools) == 3

    ready_tools = registry.list_by_state(ToolState.READY)
    assert len(ready_tools) == 2
    names = [t.name for t in ready_tools]
    assert "tool1" in names
    assert "tool3" in names


def test_update_state_and_health(registry):
    tool = Tool(name="my_tool", adapter="my_adapter")
    registry.register(tool)

    assert tool.status == ToolState.INSTALLED
    assert tool.health == ToolHealth.UNKNOWN

    registry.update_state("my_tool", ToolState.READY)
    registry.update_health("my_tool", ToolHealth.HEALTHY)

    updated = registry.get("my_tool")
    assert updated.status == ToolState.READY
    assert updated.health == ToolHealth.HEALTHY

    # Should safely ignore missing tools
    registry.update_state("non_existent", ToolState.BUSY)
    registry.update_health("non_existent", ToolHealth.FAILED)
