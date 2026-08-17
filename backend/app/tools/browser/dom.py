import logging
from typing import Dict

from playwright.async_api import Locator, Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


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
            element_data = await locator.evaluate("""(el) => {
                    const attrs = {};
                    for (const attr of el.attributes) {
                        attrs[attr.name] = attr.value;
                    }
                    return {
                        tagName: el.tagName.toLowerCase(),
                        text: el.innerText || el.textContent || "",
                        attributes: attrs
                    };
                }""")

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
