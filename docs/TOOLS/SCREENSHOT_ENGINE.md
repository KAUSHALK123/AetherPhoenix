# Screenshot Engine Capability

**Version:** 1.0  
**Category:** AUTOMATION / DESKTOP / BROWSER  
**Owner:** Worker Agent / Automation Team  

---

## Overview

The **Screenshot Engine** provides the Worker Agent and automation runtime with controlled, secure, and observable visual feedback capabilities.

Autonomous computer-use workflows rely on screenshots to observe current application state, detect modal dialogs, locate UI elements, verify execution results, and identify unexpected visual errors.

```
Worker performs action
        ↓
Screenshot captured
        ↓
System observes current state
        ↓
Next action determined
```

---

## Key Features

1. **Desktop Screenshot Capture (`capture_desktop`)**: Captures full-screen display output via PyAutoGUI and Pillow abstractions.
2. **Coordinate Region Capture (`capture_region`)**: Captures bounded coordinate windows (`x`, `y`, `width`, `height`) with strict validation against non-negative coordinates and positive dimensions.
3. **Browser Page Capture (`capture_browser`)**: Captures screenshots from active Playwright browser sessions (`BrowserTool`), supporting viewport and full-page captures with CSS/viewport clipping.
4. **Unified Capture Pipeline (`capture`)**: Processes structured `ScreenshotRequest` objects and returns comprehensive `ScreenshotResult` metadata contracts.
5. **Format & Encoding Support**: Encodes images to PNG, JPEG, and WEBP with customizable compression quality settings.
6. **Managed Temporary Storage**: Stores screenshot artifacts in an isolated managed directory, generating unique UUID-based safe filenames (`screenshot_<uuid>.<ext>`).
7. **Automated Lifecycle Cleanup**: Supports selective file cleanup (`cleanup`), bulk/TTL-based deletion (`cleanup_all`), and context managers (`__enter__`/`__exit__`, `__aenter__`/`__aexit__`) to prevent disk bloat.
8. **Permission & Privacy Protection**: Enforces permission verification (`SCREEN_CAPTURE`, `DESKTOP_AUTOMATION`, `BROWSER_ACCESS`) via `PermissionManager` prior to capturing visual contents.
9. **Centralized Logging & Observability**: Integrated with `app.core.logging` structured logging framework.
10. **Tool Registry & Worker Integration**: Registered as `screenshot_engine` tool and `screen_inspector` capability.

---

## Security, Privacy & Constraints

The Screenshot Engine strictly enforces privacy and security constraints:
- **Authorization Required**: Rejects capture operations if the required permissions (`SCREEN_CAPTURE`, `DESKTOP_AUTOMATION`, or `BROWSER_ACCESS`) are not granted.
- **No Indefinite Retention**: Temporary screenshots are tracked and subject to automatic cleanup.
- **No External Uploads**: Screen captures remain on the local filesystem within managed directories unless explicitly routed by an authorized workflow.
- **Content Integrity**: Every captured file generates a SHA-256 checksum and verified dimensions.

---

## Data Schemas

### `CaptureRegion`

| Parameter | Type | Constraint | Description |
|---|---|---|---|
| `x` | `int` | `>= 0` | X coordinate of top-left corner |
| `y` | `int` | `>= 0` | Y coordinate of top-left corner |
| `width` | `int` | `> 0` | Width of region in pixels |
| `height` | `int` | `> 0` | Height of region in pixels |

### `ScreenshotRequest`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `source` | `CaptureSource` | `DESKTOP` | Target capture source (`DESKTOP`, `BROWSER`, `REGION`) |
| `region` | `Optional[CaptureRegion]` | `None` | Optional coordinate bounding box |
| `format` | `ImageFormat` | `PNG` | Output image format (`PNG`, `JPEG`, `WEBP`) |
| `quality` | `Optional[int]` | `None` | Compression quality (1–100) for JPEG/WEBP |
| `output_path` | `Optional[str]` | `None` | Destination path (managed temp directory if omitted) |
| `full_page` | `bool` | `False` | For browser capture: capture entire scrollable page |
| `workflow_id` | `Optional[UUID]` | `None` | Associated workflow ID |
| `task_id` | `Optional[UUID]` | `None` | Associated task ID |
| `metadata` | `dict[str, Any]` | `{}` | Contextual metadata |

### `ScreenshotResult`

| Attribute | Type | Description |
|---|---|---|
| `screenshot_id` | `UUID` | Unique identifier for captured screenshot |
| `filepath` | `str` | Absolute path to the saved image file |
| `file_name` | `str` | File name of the screenshot |
| `source` | `CaptureSource` | Environment captured (`DESKTOP`, `BROWSER`, `REGION`) |
| `format` | `ImageFormat` | Image encoding format |
| `width` | `int` | Width in pixels |
| `height` | `int` | Height in pixels |
| `size_bytes` | `int` | File size in bytes |
| `checksum` | `str` | SHA-256 hash of image file |
| `captured_at` | `datetime` | UTC timestamp of capture |
| `status` | `str` | `SUCCESS` or `FAILED` |
| `is_temporary` | `bool` | True if stored in managed temporary directory |
| `metadata` | `dict[str, Any]` | Execution timing and custom metadata |

---

## Code Examples

### 1. Full-Screen Desktop Capture

```python
from app.tools.screenshot import ScreenshotEngine
from shared.contracts.screenshot import ImageFormat

engine = ScreenshotEngine()

# Capture desktop as PNG in managed temporary storage
result = await engine.capture_desktop(format=ImageFormat.PNG)
print(f"Captured: {result.filepath} ({result.width}x{result.height})")
print(f"Checksum: {result.checksum}")

# Clean up when finished
engine.cleanup(result.filepath)
```

### 2. Region Capture with Context Manager Cleanup

```python
from app.tools.screenshot import ScreenshotEngine
from shared.contracts.screenshot import CaptureRegion, ImageFormat

# Context manager automatically cleans up temporary files on exit
async with ScreenshotEngine() as engine:
    region = CaptureRegion(x=100, y=100, width=800, height=600)
    result = await engine.capture_region(region=region, format=ImageFormat.PNG)
    print(f"Region captured: {result.file_name}, size: {result.size_bytes} bytes")
```

### 3. Browser Capture via BrowserTool

```python
from app.tools.browser import BrowserTool
from app.tools.screenshot import ScreenshotEngine
from shared.contracts.screenshot import CaptureSource, ScreenshotRequest

browser = BrowserTool()
await browser.start_session()
await browser.navigate("https://example.com")

engine = ScreenshotEngine(browser_controller=browser)
result = await engine.capture_browser(full_page=True)

print(f"Browser screenshot saved to: {result.filepath}")
await browser.close_session()
```

### 4. Worker Agent Task Execution

```python
from app.tools.screenshot import ScreenshotToolAdapter
from shared.contracts.task import Task, TaskCategory
from uuid import uuid4

adapter = ScreenshotToolAdapter()

task = Task(
    task_id=uuid4(),
    workflow_id=uuid4(),
    task_name="Capture error dialog",
    category=TaskCategory.DESKTOP,
    required_tool="screenshot_engine",
    metadata={
        "source": "REGION",
        "region": {"x": 200, "y": 200, "width": 400, "height": 300},
        "format": "PNG",
    }
)

execution_result = await adapter.execute(task)
assert execution_result.success is True
print(f"Output metadata: {execution_result.output}")
```
