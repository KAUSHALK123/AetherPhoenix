# 12_TOOL_REGISTRY.md

Version: 1.0

---

# Purpose

The Tool Registry maps abstract capabilities to concrete implementations.

Capabilities answer

"What can be done?"

Tools answer

"How will it be done?"

---

# Runtime Flow

Capability

↓

Tool Registry

↓

Adapter

↓

Library

↓

Execution

---

# Example

Capability

Browser Automation

↓

Playwright Adapter

↓

Playwright

---

Future

Browser Automation

↓

Selenium Adapter

↓

Selenium

Worker never changes.

---

# Responsibilities

- Register tools
- Health monitoring
- Version management
- Tool discovery
- Dependency tracking
- Adapter loading
- Tool lifecycle

---

# Registry Structure

Tool

↓

Adapter

↓

Library

↓

Supported Platforms

↓

Permissions

↓

Capabilities

---

# Tool Categories

## Browser

Playwright

Future

Selenium

---

## Desktop

pywinauto

PyAutoGUI

---

## OCR

PaddleOCR

OpenCV

---

## Vision

YOLO

OpenCV

---

## Git

GitPython

---

## PowerShell

subprocess

PowerShell

---

## Python

Python Runtime

---

## Office

python-pptx

ReportLab

python-docx

---

# Tool Metadata

Stores

- Tool ID
- Name
- Version
- Status
- Health
- Adapter
- Dependencies
- Required Permissions
- Last Updated

---

# Tool States

Installed

↓

Ready

↓

Busy

↓

Unavailable

↓

Updating

↓

Disabled

---

# Tool Health

Healthy

Warning

Failed

Unknown

Planner never queries Tool Registry.

Only

Execution Engine

Worker

Tool Sandbox

---

# Adapter Pattern

Execution Engine

↓

Browser Adapter

↓

Playwright

Later

↓

Selenium

Execution Engine remains unchanged.

---

# Future

- Docker tools
- Remote tools
- Cloud tools
- Marketplace
- Auto updates