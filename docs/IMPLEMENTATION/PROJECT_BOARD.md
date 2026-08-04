# Project Board Workflow

This document explains the Kanban workflow used in the project board.

## Columns

### Backlog
- **Purpose**: A holding area for all verified issues and planned tasks that are not yet prioritized for the current sprint.
- **When an issue moves here**: Newly triaged issues, feature requests, or bugs that have been acknowledged but not yet scheduled.

### Todo
- **Purpose**: Issues that are scheduled for the current sprint or work cycle and are ready to be picked up by a developer.
- **When an issue moves here**: During sprint planning, when a developer is ready to take on new work.

### In Progress
- **Purpose**: Issues that are actively being worked on by a developer.
- **When an issue moves here**: When a developer assigns the issue to themselves and begins writing code or creating a PR.

### Code Review
- **Purpose**: Work that is complete from a development standpoint and has an open Pull Request awaiting review from other team members.
- **When an issue moves here**: When a developer opens a Pull Request linked to the issue.

### Testing
- **Purpose**: Work that has been approved in Code Review and merged (or is in a testing environment) and requires QA or final manual testing.
- **When an issue moves here**: When a PR is merged, and the feature/fix needs to be validated in a staging or test environment before final sign-off.

### Done
- **Purpose**: Work that is fully complete, tested, and released or merged into the main development branch.
- **When an issue moves here**: When the issue is successfully tested and verified as complete.
