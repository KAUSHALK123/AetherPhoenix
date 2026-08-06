# DEVELOPMENT_GUIDE.md

# AetherPhoenix Development Guide

Version: 1.0

This document defines the official development workflow for every contributor.

---

# Repository Workflow

All development follows this branching strategy.

```
main
│
└── develop
      │
      ├── feature/*
      ├── bugfix/*
      ├── docs/*
      └── hotfix/*
```

Never commit directly to:

- main
- develop

Always create a feature branch.

---

# Initial Repository Setup

Clone the repository

```bash
git clone https://github.com/KAUSHALK123/AetherPhoenix.git

cd AetherPhoenix
```

Verify branches

```bash
git branch -a
```

Switch to develop

```bash
git checkout develop
```

Download the latest changes

```bash
git pull origin develop
```

Project is now ready.

---

# Starting a New Issue

Every issue starts from develop.

```bash
git checkout develop

git pull origin develop
```

Create a feature branch.

Example

```bash
git checkout -b feature/frontend-foundation
```

Verify branch

```bash
git branch
```

Expected

```
* feature/frontend-foundation
develop
main
```

Now begin development.

---

# Daily Workflow

Every morning before coding

```bash
git checkout develop

git pull origin develop
```

If continuing an existing feature

```bash
git checkout feature/frontend-foundation

git rebase develop
```

Resolve conflicts if prompted.

Continue development.

Never code on an outdated branch.

---

# During Development

Check current status

```bash
git status
```

View changes

```bash
git diff
```

View branch

```bash
git branch
```

---

# Saving Progress

Stage files

```bash
git add .
```

Commit

```bash
git commit -m "feat: setup frontend foundation"
```

Push

```bash
git push -u origin feature/frontend-foundation
```

---

# Updating an Existing Feature Branch

If develop has changed

```bash
git checkout develop

git pull origin develop

git checkout feature/frontend-foundation

git rebase develop
```

If rebase succeeds

```bash
git push --force-with-lease
```

Never use

```bash
git push --force
```

Always use

```bash
git push --force-with-lease
```

---

# Pull Request Workflow

Create Pull Request

```
feature/frontend-foundation

↓

develop
```

Never create a PR directly into main.

---

# Pull Request Checklist

Before opening a PR

- Project builds successfully
- No lint errors
- No debug code
- No TODO placeholders
- Documentation updated (if required)

---

# Pull Request Description

Include

- Objective
- Summary
- Files Changed
- Testing
- Architecture Compliance
- Reviewer Checklist

Always end with

```
Closes #<Issue Number>
```

Example

```
Closes #5
```

---

# Team Lead Review Process

The Team Lead will verify

- Architecture compliance
- Documentation compliance
- Folder structure
- Build success
- Code quality
- Naming conventions
- Acceptance criteria

Only after approval will the PR be merged.

---

# After PR is Approved

The Team Lead merges

```
feature/*

↓

develop
```

The developer should then update their local repository.

```bash
git checkout develop

git pull origin develop
```

Delete local feature branch

```bash
git branch -d feature/frontend-foundation
```

Delete remote branch (optional)

```bash
git push origin --delete feature/frontend-foundation
```

---

# Starting the Next Issue

Repeat

```bash
git checkout develop

git pull origin develop

git checkout -b feature/new-issue
```

---

# Sprint Completion

When every Sprint issue has been merged into develop

↓

Integration Testing

↓

Team Lead creates

```
develop

↓

main
```

Pull Request

↓

Merge

↓

Tag Release

Example

```
v0.1.0 - Sprint 0 Complete
```

---

# Branch Naming Convention

Feature

```
feature/<feature-name>
```

Example

```
feature/planner-agent
```

Bug

```
bugfix/<bug-name>
```

Documentation

```
docs/<document-name>
```

Hotfix

```
hotfix/<issue>
```

---

# Commit Message Convention

Feature

```
feat: add planner workflow
```

Fix

```
fix: resolve runtime validation bug
```

Documentation

```
docs: update planner architecture
```

Refactor

```
refactor: simplify worker execution flow
```

Style

```
style: improve formatting
```

Test

```
test: add planner unit tests
```

Chore

```
chore: update dependencies
```

---

# Things You Must Never Do

❌ Commit directly to main

❌ Commit directly to develop

❌ Push without testing

❌ Rename project folders

❌ Modify another teammate's feature branch

❌ Push secrets or .env files

❌ Use git push --force

❌ Skip reading the assigned GitHub Issue

---

# Standard Development Flow

```
GitHub Issue

↓

Read Documentation

↓

git checkout develop

↓

git pull origin develop

↓

git checkout -b feature/issue-name

↓

Implement

↓

git add .

↓

git commit

↓

git push

↓

Create Pull Request

↓

Team Lead Review

↓

Merge → develop

↓

Issue Closed

↓

Next Issue
```

---

# Team Responsibility

Developer

- Complete assigned issue
- Follow documentation
- Create Pull Request
- Respond to review comments

Team Lead

- Create Issues
- Review Pull Requests
- Maintain Architecture
- Merge Pull Requests
- Manage Sprint
- Merge develop → main
- Tag Releases