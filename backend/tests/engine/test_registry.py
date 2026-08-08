import pytest
from backend.app.engine.registry import CapabilityRegistry
from shared.contracts.capability import Capability
from shared.contracts.task import TaskCategory


@pytest.fixture
def registry():
    return CapabilityRegistry()


def test_register_and_get(registry):
    cap = Capability(
        name="web_search",
        description="Search the web",
        category=TaskCategory.WEB_RESEARCH,
    )
    registry.register(cap)

    fetched = registry.get("web_search")
    assert fetched is not None
    assert fetched.name == "web_search"
    assert fetched.category == TaskCategory.WEB_RESEARCH


def test_register_duplicate(registry):
    cap1 = Capability(
        name="browser",
        description="Browser automation",
        category=TaskCategory.BROWSER,
    )
    registry.register(cap1)

    cap2 = Capability(
        name="browser",
        description="Duplicate",
        category=TaskCategory.BROWSER,
    )

    with pytest.raises(ValueError, match="already registered"):
        registry.register(cap2)


def test_unregister(registry):
    cap = Capability(
        name="temp_cap",
        description="Temporary capability",
        category=TaskCategory.OTHER,
    )
    registry.register(cap)

    registry.unregister("temp_cap")
    assert registry.get("temp_cap") is None


def test_list_all_and_by_category(registry):
    cap1 = Capability(name="cap1", description="1", category=TaskCategory.BROWSER)
    cap2 = Capability(name="cap2", description="2", category=TaskCategory.DESKTOP)
    cap3 = Capability(name="cap3", description="3", category=TaskCategory.BROWSER)

    registry.register(cap1)
    registry.register(cap2)
    registry.register(cap3)

    all_caps = registry.list_all()
    assert len(all_caps) == 3

    browser_caps = registry.list_by_category(TaskCategory.BROWSER)
    assert len(browser_caps) == 2
    names = [c.name for c in browser_caps]
    assert "cap1" in names
    assert "cap3" in names


def test_validate_capabilities(registry):
    cap1 = Capability(
        name="active_cap", description="Active", category=TaskCategory.OTHER
    )
    cap2 = Capability(
        name="disabled_cap",
        description="Disabled",
        category=TaskCategory.OTHER,
        enabled=False,
    )

    registry.register(cap1)
    registry.register(cap2)

    # Valid because 'active_cap' exists and is enabled
    assert registry.validate_capabilities(["active_cap"]) is True

    # Invalid because 'disabled_cap' exists but is disabled
    assert registry.validate_capabilities(["disabled_cap"]) is False

    # Invalid because 'missing_cap' is not registered
    assert registry.validate_capabilities(["missing_cap"]) is False

    # Invalid because one of the requested capabilities is disabled
    assert registry.validate_capabilities(["active_cap", "disabled_cap"]) is False
