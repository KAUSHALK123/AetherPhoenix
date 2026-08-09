import pytest
from app.planner.goal_hierarchy import GoalHierarchyBuilder

from shared.contracts.planner import Goal


@pytest.fixture
def hierarchy_builder():
    return GoalHierarchyBuilder()


def test_build_hierarchy(hierarchy_builder):
    root = Goal(title="Main Goal", description="Main Goal Desc")
    child1 = Goal(title="Sub Goal 1", description="Sub Goal 1 Desc")
    child2 = Goal(title="Sub Goal 2", description="Sub Goal 2 Desc")

    result = hierarchy_builder.build_hierarchy(root, [child1, child2])

    assert len(result.sub_goals) == 2
    assert child1.parent_id == root.goal_id
    assert child2.parent_id == root.goal_id


def test_add_subgoal(hierarchy_builder):
    root = Goal(title="Main Goal", description="Main Goal Desc")
    child = Goal(title="Sub Goal 1", description="Sub Goal 1 Desc")

    hierarchy_builder.add_subgoal(root, child)

    assert len(root.sub_goals) == 1
    assert root.sub_goals[0].goal_id == child.goal_id
    assert child.parent_id == root.goal_id


def test_flatten_hierarchy(hierarchy_builder):
    root = Goal(title="Root", description="Root Desc")
    child1 = Goal(title="Child 1", description="Child 1 Desc")
    grandchild1 = Goal(title="Grandchild 1", description="Grandchild 1 Desc")

    hierarchy_builder.add_subgoal(root, child1)
    hierarchy_builder.add_subgoal(child1, grandchild1)

    flat_list = hierarchy_builder.flatten_hierarchy(root)
    assert len(flat_list) == 3
    assert flat_list[0].title == "Root"
    assert flat_list[1].title == "Child 1"
    assert flat_list[2].title == "Grandchild 1"


def test_find_goal_by_id(hierarchy_builder):
    root = Goal(title="Root", description="Root Desc")
    child1 = Goal(title="Child 1", description="Child 1 Desc")
    hierarchy_builder.add_subgoal(root, child1)

    found = hierarchy_builder.find_goal_by_id(root, child1.goal_id)
    assert found is not None
    assert found.title == "Child 1"

    not_found = hierarchy_builder.find_goal_by_id(root, "non-existent-id")
    assert not_found is None


def test_get_tree_depth(hierarchy_builder):
    root = Goal(title="Root", description="Root Desc")
    child1 = Goal(title="Child 1", description="Child 1 Desc")
    grandchild1 = Goal(title="Grandchild 1", description="Grandchild 1 Desc")

    hierarchy_builder.add_subgoal(root, child1)
    hierarchy_builder.add_subgoal(child1, grandchild1)

    depth = hierarchy_builder.get_tree_depth(root)
    assert depth == 3


def test_count_total_goals(hierarchy_builder):
    root = Goal(title="Root", description="Root Desc")
    child1 = Goal(title="Child 1", description="Child 1 Desc")
    child2 = Goal(title="Child 2", description="Child 2 Desc")

    hierarchy_builder.add_subgoal(root, child1)
    hierarchy_builder.add_subgoal(root, child2)

    total = hierarchy_builder.count_total_goals(root)
    assert total == 3
