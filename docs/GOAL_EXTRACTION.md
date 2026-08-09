# Goal Extraction Engine Documentation

**Version:** 1.0  
**Module:** `app.planner.goal_engine`  
**Status:** Active  
**Last Updated:** August 2026  

---

## Overview

The **Goal Extraction Engine** is a core component of the Planner Agent in AetherPhoenix. It is responsible for analyzing natural language user requests and transforming them into structured goal hierarchies containing primary objectives, sub-goals, expected outcomes, and metadata.

> **Constraint:** The Goal Extraction Engine operates strictly at the goal abstraction level. It identifies *what* the user wants to achieve and does **NOT** generate tasks or step-by-step execution actions (task generation is performed separately by the Workflow Compiler in Sprint 3).

---

## Architecture & Data Flow

```
User Request / PlannerRequest
          │
          ▼
┌──────────────────────────┐
│     GoalValidator        │ ── (Check raw text safety & validity)
└─────────┬────────────────┘
          │ (Valid)
          ▼
┌──────────────────────────┐
│       GoalParser         │ ── (Extract primary title, sub-goals, outcomes)
└─────────┬────────────────┘
          │
          ▼
┌──────────────────────────┐
│  GoalHierarchyBuilder    │ ── (Construct tree & parent_id links)
└─────────┬────────────────┘
          │
          ▼
┌──────────────────────────┐
│     GoalValidator        │ ── (Validate tree hierarchy structure)
└─────────┬────────────────┘
          │
          ▼
┌──────────────────────────┐
│ GoalMetadataGenerator    │ ── (Compute confidence, timestamps, tags, risk)
└─────────┬────────────────┘
          │
          ▼
  GoalExtractionResult
```

---

## Key Components

### 1. Goal Contracts (`shared.contracts.planner`)

- `Goal`: Structured node in a goal hierarchy.
  - `goal_id` (str): Unique UUID identifier.
  - `title` (str): Concise goal title.
  - `description` (str): Full text or detailed objective description.
  - `category` (`IntentCategory`): `DATA_RETRIEVAL`, `SYSTEM_MODIFICATION`, `CONTENT_GENERATION`, or `UNKNOWN`.
  - `priority` (`GoalPriority`): `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`.
  - `expected_outcomes` (List[str]): List of expected artifacts or outcomes.
  - `sub_goals` (List[Goal]): List of child sub-goals.
  - `parent_id` (Optional[str]): UUID of parent goal node.
  - `metadata` (Dict[str, Any]): Analytical metadata.

- `GoalExtractionResult`: Output of the Goal Extraction Engine.
  - `primary_goal` (Optional[Goal]): Root goal object.
  - `goal_count` (int): Total goals (root + sub-goals).
  - `confidence_score` (float): Confidence level from `0.0` to `1.0`.
  - `is_valid` (bool): True if extraction succeeded without policy violations.
  - `validation_messages` (List[str]): Error or warning feedback.
  - `extraction_metadata` (Dict[str, Any]): Summary metrics.

---

### 2. Goal Parser (`app.planner.goal_parser.GoalParser`)

Parses natural language requests using sentence structure analysis, conjunctions (`then`, `after that`, `first`, `also`), delimiters, and intent keywords.

---

### 3. Goal Hierarchy Builder (`app.planner.goal_hierarchy.GoalHierarchyBuilder`)

Constructs and manages goal trees, sets `parent_id` references, flattens goal trees, searches nodes by ID, and computes tree depth.

---

### 4. Goal Validator (`app.planner.goal_validator.GoalValidator`)

Validates raw inputs and full goal hierarchies. Enforces safety policies (blocking dangerous commands such as hacking or disk wiping) and flags empty or overly ambiguous requests.

---

### 5. Goal Metadata Generator (`app.planner.goal_metadata.GoalMetadataGenerator`)

Enriches goal nodes with ISO timestamps, confidence scoring (0.0 to 1.0), domain tagging (`browser`, `desktop`, `content`, `coding`, `system`, `research`), and risk levels (`safe`, `low`, `medium`, `high`, `critical`).

---

### 6. Goal Extraction Engine (`app.planner.goal_engine.GoalExtractionEngine`)

Orchestrates the parser, hierarchy builder, validator, and metadata generator into a single unified entry point:

```python
from app.planner.goal_engine import GoalExtractionEngine

engine = GoalExtractionEngine()
result = engine.extract_goals("Research AI trends then create a PPT report and save to PDF")

print(result.is_valid)                  # True
print(result.primary_goal.title)        # "Research AI trends..."
print(result.goal_count)                # 4 (Primary + 3 Sub-goals)
print(result.primary_goal.expected_outcomes) # ['Generated PPT file/artifact', 'Generated PDF file/artifact', ...]
```

---

## Testing

Unit tests for the Goal Extraction Engine are located under `backend/tests/planner/`:

- `test_goal_parser.py`
- `test_goal_hierarchy.py`
- `test_goal_validator.py`
- `test_goal_metadata.py`
- `test_goal_engine.py`

Run tests via pytest:

```bash
pytest backend/tests/planner/
```
