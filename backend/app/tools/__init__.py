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

__all__ = [
    "ToolRegistry",
    "DocumentGenerator",
    "DocumentToolAdapter",
    "register_document_tool",
    "PDFGenerator",
    "PDFToolAdapter",
    "register_pdf_tool",
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
]
