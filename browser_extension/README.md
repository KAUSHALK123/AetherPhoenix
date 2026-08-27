# AetherPhoenix Browser Agent Extension

Chrome Manifest V3 extension enabling **AetherPhoenix AI Desktop Assistant** to perform visible, controlled browser operations in the user's browser.

## Features

- **Visible Desktop Operations**: Performs browser interactions directly in the user's active browser window.
- **Active Tab Detection**: Detects active tab URL, title, and state.
- **Controlled Page Interaction**: Navigates URLs, opens new tabs, clicks elements, inputs text, and extracts content.
- **Permission & Security**: Respects AetherPhoenix `PermissionManager` and Safe Execution Mode. Passwords and credentials are never stored or captured.

## Installation Instructions

1. Open Google Chrome (or Chromium-based browsers like Edge or Brave).
2. Navigate to `chrome://extensions`.
3. Enable **Developer mode** in the top right corner.
4. Click **Load unpacked**.
5. Select the `browser_extension` folder located inside the AetherPhoenix repository root.
6. The extension will automatically connect to AetherPhoenix backend WebSocket at `ws://localhost:8000/api/v1/browser-extension/ws`.
