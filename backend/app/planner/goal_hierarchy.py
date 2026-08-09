import logging
from typing import List, Optional

from shared.contracts.planner import Goal

logger = logging.getLogger(__name__)


class GoalHierarchyBuilder:
    """
    Manages the creation, navigation, query, and manipulation of goal hierarchies.
    Enforces parent-child relationships and structure traversal.
    """

    def build_hierarchy(self, primary_goal: Goal, sub_goals: List[Goal]) -> Goal:
        """
        Attaches a list of sub-goals to the primary goal, setting parent_id links.
        """
        primary_goal.sub_goals = []
        for child in sub_goals:
            child.parent_id = primary_goal.goal_id
            primary_goal.sub_goals.append(child)
        return primary_goal

    def add_subgoal(self, parent_goal: Goal, child_goal: Goal) -> Goal:
        """
        Adds a single sub-goal under a specified parent goal node.
        """
        child_goal.parent_id = parent_goal.goal_id
        parent_goal.sub_goals.append(child_goal)
        return parent_goal

    def flatten_hierarchy(self, root_goal: Optional[Goal]) -> List[Goal]:
        """
        Flattens a goal tree into a single list of goals via pre-order traversal.
        """
        if not root_goal:
            return []

        result = [root_goal]
        for child in root_goal.sub_goals:
            result.extend(self.flatten_hierarchy(child))
        return result

    def find_goal_by_id(
        self, root_goal: Optional[Goal], goal_id: str
    ) -> Optional[Goal]:
        """
        Searches the goal hierarchy recursively for a node with matching goal_id.
        """
        if not root_goal:
            return None

        if root_goal.goal_id == goal_id:
            return root_goal

        for child in root_goal.sub_goals:
            found = self.find_goal_by_id(child, goal_id)
            if found:
                return found

        return None

    def get_tree_depth(self, root_goal: Optional[Goal]) -> int:
        """
        Computes the maximum depth of the goal tree.
        Root node alone has depth 1. An empty root has depth 0.
        """
        if not root_goal:
            return 0

        if not root_goal.sub_goals:
            return 1

        max_child_depth = max(
            self.get_tree_depth(child) for child in root_goal.sub_goals
        )
        return 1 + max_child_depth

    def count_total_goals(self, root_goal: Optional[Goal]) -> int:
        """
        Counts the total number of goals in the hierarchy.
        """
        return len(self.flatten_hierarchy(root_goal))
