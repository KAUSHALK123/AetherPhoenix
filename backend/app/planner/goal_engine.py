import logging
from typing import Any, Dict, Optional, Union

from shared.contracts.planner import (
    Goal,
    GoalExtractionResult,
    PlannerRequest,
)

from app.planner.goal_hierarchy import GoalHierarchyBuilder
from app.planner.goal_metadata import GoalMetadataGenerator
from app.planner.goal_parser import GoalParser
from app.planner.goal_validator import GoalValidator

logger = logging.getLogger(__name__)


class GoalExtractionEngine:
    """
    Primary engine for identifying primary objectives, sub-goals, and expected
    outcomes from user requests into a structured goal hierarchy with metadata.
    Does NOT generate tasks.
    """

    def __init__(
        self,
        parser: Optional[GoalParser] = None,
        hierarchy_builder: Optional[GoalHierarchyBuilder] = None,
        validator: Optional[GoalValidator] = None,
        metadata_generator: Optional[GoalMetadataGenerator] = None,
    ):
        self.parser = parser or GoalParser()
        self.hierarchy_builder = hierarchy_builder or GoalHierarchyBuilder()
        self.validator = validator or GoalValidator()
        self.metadata_generator = metadata_generator or GoalMetadataGenerator()

    def extract_goals(
        self,
        request: Union[str, PlannerRequest],
        context: Optional[Dict[str, Any]] = None,
    ) -> GoalExtractionResult:
        """
        Extracts structured goals from a user request string or PlannerRequest.
        """
        if isinstance(request, PlannerRequest):
            message = request.message
            req_context = request.context or {}
        else:
            message = request
            req_context = context or {}

        logger.info(f"Extracting goals for request: '{message[:50]}...'")

        # Step 1: Validate raw input text
        is_raw_valid, raw_errors = self.validator.validate_raw_request(message)
        if not is_raw_valid:
            logger.warning(f"Raw request validation failed: {raw_errors}")
            return GoalExtractionResult(
                primary_goal=None,
                goal_count=0,
                confidence_score=0.0,
                is_valid=False,
                validation_messages=raw_errors,
                extraction_metadata={"raw_message": message},
            )

        # Step 2: Parse raw text into goal attributes
        title, description, subgoals_raw, outcomes = self.parser.parse_raw_goal(message)
        intent = self.parser.parse_intent(message)
        priority = self.parser.parse_priority(message)

        # Step 3: Instantiate primary root Goal
        primary_goal = Goal(
            title=title,
            description=description,
            category=intent,
            priority=priority,
            expected_outcomes=outcomes,
            metadata={"context": req_context},
        )

        # Step 4: Instantiate sub-goals
        sub_goals = []
        for sub_title, sub_desc in subgoals_raw:
            sub_intent = self.parser.parse_intent(sub_title)
            sub_outcomes = self.parser.extract_outcomes(sub_title)
            child = Goal(
                title=sub_title,
                description=sub_desc,
                category=sub_intent,
                priority=priority,
                expected_outcomes=sub_outcomes,
            )
            sub_goals.append(child)

        # Step 5: Construct hierarchy tree
        root_goal = self.hierarchy_builder.build_hierarchy(primary_goal, sub_goals)

        # Step 6: Validate full hierarchy structure
        is_tree_valid, tree_errors = self.validator.validate_hierarchy(root_goal)
        if not is_tree_valid:
            logger.warning(f"Goal hierarchy validation failed: {tree_errors}")

        # Step 7: Enrich hierarchy with metadata (confidence, tags, risk)
        enriched_root = self.metadata_generator.enrich_goal(root_goal)

        # Step 8: Calculate overall metrics
        total_goals = self.hierarchy_builder.count_total_goals(enriched_root)
        confidence = self.metadata_generator.compute_confidence_score(enriched_root)

        return GoalExtractionResult(
            primary_goal=enriched_root,
            goal_count=total_goals,
            confidence_score=confidence,
            is_valid=is_tree_valid,
            validation_messages=tree_errors,
            extraction_metadata={
                "tree_depth": self.hierarchy_builder.get_tree_depth(enriched_root),
                "raw_message": message,
                "context_provided": bool(req_context),
            },
        )
