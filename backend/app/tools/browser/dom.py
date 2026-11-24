import logging
from typing import Dict

from playwright.async_api import Locator, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


JS_INSPECT_ELEMENT_SCRIPT = (
    "(el) => {\n"
    "    const attrs = {};\n"
    "    for (const attr of el.attributes) {\n"
    "        attrs[attr.name] = attr.value;\n"
    "    }\n"
    "    return {\n"
    "        tagName: el.tagName.toLowerCase(),\n"
    "        text: el.innerText || el.textContent || '',\n"
    "        attributes: attrs\n"
    "    };\n"
    "}"
)

JS_DISCOVER_INTERACTIVE_ELEMENTS_SCRIPT = (
    "() => {\n"
    "    const candidates = document.querySelectorAll(\n"
    '        \'button, a[href], input, textarea, select, [role="button"], [role="link"], [onclick], [tabindex="0"]\'\n'
    "    );\n"
    "    const results = [];\n"
    "    const isVisible = (el) => {\n"
    "        const style = window.getComputedStyle(el);\n"
    "        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return false;\n"
    "        const rect = el.getBoundingClientRect();\n"
    "        return rect.width > 0 && rect.height > 0;\n"
    "    };\n"
    "    for (const el of candidates) {\n"
    "        if (!isVisible(el)) continue;\n"
    "        const rect = el.getBoundingClientRect();\n"
    "        const tag = el.tagName.toLowerCase();\n"
    "        let selector = '';\n"
    "        if (el.id) {\n"
    "            selector = `#${CSS.escape(el.id)}`;\n"
    "        } else if (el.getAttribute('data-testid')) {\n"
    "            selector = `[data-testid=\"${CSS.escape(el.getAttribute('data-testid'))}\"]`;\n"
    "        } else if (el.name) {\n"
    '            selector = `${tag}[name="${CSS.escape(el.name)}"]`;\n'
    "        } else if (el.getAttribute('aria-label')) {\n"
    "            selector = `${tag}[aria-label=\"${CSS.escape(el.getAttribute('aria-label'))}\"]`;\n"
    "        } else if (el.placeholder) {\n"
    '            selector = `${tag}[placeholder="${CSS.escape(el.placeholder)}"]`;\n'
    "        } else if (tag === 'a' && el.getAttribute('href') && !el.getAttribute('href').startsWith('javascript:')) {\n"
    "            const href = el.getAttribute('href');\n"
    "            selector = href.length < 50 ? `a[href=\"${CSS.escape(href)}\"]` : 'a';\n"
    "        } else {\n"
    "            selector = tag;\n"
    "        }\n"
    "        const text = (el.innerText || el.textContent || el.value || el.placeholder || el.getAttribute('aria-label') || '').trim();\n"
    "        results.push({\n"
    "            selector: selector,\n"
    "            tag_name: tag,\n"
    "            text: text.slice(0, 100),\n"
    "            role: el.getAttribute('role') || tag,\n"
    "            is_visible: true,\n"
    "            is_enabled: !el.disabled,\n"
    "            attributes: {\n"
    "                id: el.id || '',\n"
    "                name: el.name || '',\n"
    "                type: el.type || '',\n"
    "                placeholder: el.placeholder || '',\n"
    "                aria_label: el.getAttribute('aria-label') || '',\n"
    "                href: el.getAttribute('href') || ''\n"
    "            },\n"
    "            rect: {\n"
    "                x: Math.round(rect.x),\n"
    "                y: Math.round(rect.y),\n"
    "                width: Math.round(rect.width),\n"
    "                height: Math.round(rect.height)\n"
    "            }\n"
    "        });\n"
    "        if (results.length >= 100) break;\n"
    "    }\n"
    "    return results;\n"
    "}"
)


class DOMAutomationError(Exception):
    """Base exception for DOM automation errors."""

    pass


class ElementNotFoundError(DOMAutomationError):
    """Raised when an element cannot be found."""

    pass


class StaleElementError(DOMAutomationError):
    """Raised when an element is no longer attached to the DOM."""

    pass


class DOMElement(BaseModel):
    """Abstraction representing a DOM element's state."""

    selector: str
    tag_name: str
    text: str = ""
    is_visible: bool
    is_enabled: bool
    attributes: Dict[str, str] = Field(default_factory=dict)


class InteractiveElement(BaseModel):
    """Structured representation of an interactive element on the page."""

    selector: str
    tag_name: str
    text: str = ""
    role: str = ""
    is_visible: bool = True
    is_enabled: bool = True
    attributes: Dict[str, str] = Field(default_factory=dict)
    rect: Dict[str, int] = Field(default_factory=dict)


class DOMAutomation:
    """
    Provides safe, structured DOM-level interactions using Playwright.
    Encapsulates Playwright specifics to prevent exposing internals.
    """

    def __init__(self, page: Page):
        self._page = page

    def _validate_selector(self, selector: str) -> None:
        """Validates that a selector is not empty."""
        if not selector or not selector.strip():
            raise ValueError("Selector cannot be empty.")

    async def _get_locator(self, selector: str, timeout: int = 5000) -> Locator:
        """
        Safely gets a locator for a selector.
        Raises ElementNotFoundError if the element doesn't appear within the timeout.
        """
        self._validate_selector(selector)
        try:
            locator = self._page.locator(selector).first
            await locator.wait_for(state="attached", timeout=timeout)
            return locator
        except PlaywrightTimeoutError:
            raise ElementNotFoundError(
                f"Element not found within {timeout}ms: {selector}"
            )
        except Exception as e:
            if "Target closed" in str(e) or "Node is detached" in str(e):
                raise StaleElementError(f"Element became stale: {selector}")
            raise DOMAutomationError(f"Error locating element '{selector}': {str(e)}")

    async def inspect_element(self, selector: str, timeout: int = 5000) -> DOMElement:
        """Inspects an element and returns its structured state."""
        locator = await self._get_locator(selector, timeout)

        try:
            # We use evaluate to safely pull all attributes and basic properties
            element_data = await locator.evaluate(JS_INSPECT_ELEMENT_SCRIPT)

            is_visible = await locator.is_visible()
            is_enabled = await locator.is_enabled()

            return DOMElement(
                selector=selector,
                tag_name=element_data["tagName"],
                text=element_data["text"].strip(),
                is_visible=is_visible,
                is_enabled=is_enabled,
                attributes=element_data["attributes"],
            )
        except Exception as e:
            if "Target closed" in str(e) or "Node is detached" in str(e):
                raise StaleElementError(
                    f"Element became stale during inspection: {selector}"
                )
            raise DOMAutomationError(
                f"Failed to inspect element '{selector}': {str(e)}"
            )

    async def click_element(self, selector: str, timeout: int = 5000) -> None:
        """Clicks an element safely."""
        locator = await self._get_locator(selector, timeout)
        try:
            await locator.wait_for(state="visible", timeout=timeout)
            await locator.click(timeout=timeout)
        except PlaywrightTimeoutError:
            raise ElementNotFoundError(
                f"Element not visible or clickable within {timeout}ms: {selector}"
            )
        except Exception as e:
            if "Target closed" in str(e) or "Node is detached" in str(e):
                raise StaleElementError(
                    f"Element became stale during click: {selector}"
                )
            raise DOMAutomationError(f"Failed to click element '{selector}': {str(e)}")

    async def fill_element(self, selector: str, text: str, timeout: int = 5000) -> None:
        """Fills an input element safely."""
        locator = await self._get_locator(selector, timeout)
        try:
            await locator.wait_for(state="visible", timeout=timeout)
            await locator.fill(text, timeout=timeout)
        except PlaywrightTimeoutError:
            raise ElementNotFoundError(
                f"Element not visible or fillable within {timeout}ms: {selector}"
            )
        except Exception as e:
            if "Target closed" in str(e) or "Node is detached" in str(e):
                raise StaleElementError(f"Element became stale during fill: {selector}")
            raise DOMAutomationError(f"Failed to fill element '{selector}': {str(e)}")

    async def extract_text(self, selector: str, timeout: int = 5000) -> str:
        """Extracts text content from an element safely."""
        locator = await self._get_locator(selector, timeout)
        try:
            return (await locator.inner_text()).strip()
        except Exception as e:
            if "Target closed" in str(e) or "Node is detached" in str(e):
                raise StaleElementError(
                    f"Element became stale during text extraction: {selector}"
                )
            raise DOMAutomationError(
                f"Failed to extract text from '{selector}': {str(e)}"
            )

    async def get_interactive_elements(
        self, limit: int = 50
    ) -> list[InteractiveElement]:
        """Discovers visible interactive elements on the page."""
        try:
            raw_elements = await self._page.evaluate(
                JS_DISCOVER_INTERACTIVE_ELEMENTS_SCRIPT
            )
            elements = []
            for item in raw_elements[:limit]:
                elements.append(InteractiveElement(**item))
            return elements
        except Exception as e:
            logger.warning(f"Failed to discover interactive elements: {e}")
            return []

    async def highlight_element(self, selector: str, timeout: int = 3000) -> None:
        """Highlights an element temporarily for visual feedback."""
        try:
            locator = await self._get_locator(selector, timeout)
            await locator.evaluate(
                "(el) => {"
                "    const prevOutline = el.style.outline;"
                "    const prevTransition = el.style.transition;"
                "    el.style.transition = 'outline 0.15s ease';"
                "    el.style.outline = '3px solid #6366f1';"
                "    setTimeout(() => {"
                "        el.style.outline = prevOutline;"
                "        el.style.transition = prevTransition;"
                "    }, 1500);"
                "}"
            )
        except Exception:
            pass

    async def scroll_into_view(self, selector: str, timeout: int = 5000) -> None:
        """Scrolls an element into view if needed."""
        locator = await self._get_locator(selector, timeout)
        try:
            await locator.scroll_into_view_if_needed(timeout=timeout)
        except Exception as e:
            logger.debug(f"scroll_into_view_if_needed failed on '{selector}': {e}")
