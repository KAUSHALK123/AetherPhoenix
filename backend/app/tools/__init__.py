try:
    from app.tools.desktop import (
        DesktopController,
        DesktopTool,
        DesktopToolAdapter,
        KeyboardController,
        MouseController,
        register_desktop_tool,
    )
except ImportError:
    DesktopController = None
    DesktopTool = None
    DesktopToolAdapter = None
    KeyboardController = None
    MouseController = None
    register_desktop_tool = None

try:
    from app.tools.document import (
        DocumentGenerator,
        DocumentToolAdapter,
        register_document_tool,
    )
except ImportError:
    DocumentGenerator = None
    DocumentToolAdapter = None
    register_document_tool = None

try:
    from app.tools.pdf import PDFGenerator, PDFToolAdapter, register_pdf_tool
except ImportError:
    PDFGenerator = None
    PDFToolAdapter = None
    register_pdf_tool = None

try:
    from app.tools.screenshot import (
        ScreenshotCaptureError,
        ScreenshotEngine,
        ScreenshotToolAdapter,
        register_screenshot_tool,
    )
except ImportError:
    ScreenshotCaptureError = None
    ScreenshotEngine = None
    ScreenshotToolAdapter = None
    register_screenshot_tool = None

try:
    from app.tools.git import GitToolAdapter, register_git_tool
except ImportError:
    GitToolAdapter = None
    register_git_tool = None

try:
    from app.tools.terminal import TerminalToolAdapter, register_terminal_tool
except ImportError:
    TerminalToolAdapter = None
    register_terminal_tool = None

from app.tools.ppt import PPTGenerator, ppt_tool_metadata
from app.tools.registry import ToolRegistry

try:
    from app.tools.web_research import (
        BaseResearchTool,
        ContentExtractor,
        DuckDuckGoSearchEngine,
        ExtractedPageContent,
        MockSearchEngine,
        SearchEngineInterface,
        SourceMetadata,
        SourceStatus,
        StructuredResearchResult,
        WebResearchRequest,
        WebResearchTool,
    )
except ImportError:
    BaseResearchTool = None
    ContentExtractor = None
    DuckDuckGoSearchEngine = None
    ExtractedPageContent = None
    MockSearchEngine = None
    SearchEngineInterface = None
    SourceMetadata = None
    SourceStatus = None
    StructuredResearchResult = None
    WebResearchRequest = None
    WebResearchTool = None

try:
    from app.tools.file_explorer import (
        FileExplorerExecutor,
        FileExplorerToolAdapter,
        register_file_explorer_tool,
    )
except ImportError:
    FileExplorerExecutor = None
    FileExplorerToolAdapter = None
    register_file_explorer_tool = None

try:
    from app.tools.export import (
        ExportEngine,
        ExportError,
        ExportToolAdapter,
        register_export_tool,
    )
except ImportError:
    ExportEngine = None
    ExportError = None
    ExportToolAdapter = None
    register_export_tool = None

try:
    from app.tools.ocr import (
        OCREngine,
        OCRError,
        OCRToolAdapter,
        register_ocr_tool,
    )
except ImportError:
    OCREngine = None
    OCRError = None
    OCRToolAdapter = None
    register_ocr_tool = None


__all__ = [
    "ToolRegistry",
    "DesktopController",
    "DesktopTool",
    "DesktopToolAdapter",
    "KeyboardController",
    "MouseController",
    "register_desktop_tool",
    "DocumentGenerator",
    "DocumentToolAdapter",
    "register_document_tool",
    "PDFGenerator",
    "PDFToolAdapter",
    "register_pdf_tool",
    "ScreenshotEngine",
    "ScreenshotToolAdapter",
    "register_screenshot_tool",
    "ScreenshotCaptureError",
    "register_git_tool",
    "GitToolAdapter",
    "WebResearchTool",
    "BaseResearchTool",
    "SearchEngineInterface",
    "DuckDuckGoSearchEngine",
    "MockSearchEngine",
    "ContentExtractor",
    "SourceStatus",
    "SourceMetadata",
    "ExtractedPageContent",
    "WebResearchRequest",
    "StructuredResearchResult",
    "PPTGenerator",
    "ppt_tool_metadata",
    "FileExplorerExecutor",
    "FileExplorerToolAdapter",
    "register_file_explorer_tool",
    "ExportEngine",
    "ExportToolAdapter",
    "register_export_tool",
    "ExportError",
    "OCREngine",
    "OCRToolAdapter",
    "register_ocr_tool",
    "OCRError",
    "register_terminal_tool",
    "TerminalToolAdapter",
]
