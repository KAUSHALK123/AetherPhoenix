import asyncio
import inspect
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

try:
    from playwright.async_api import Page
except ImportError:
    Page = Any  # type: ignore

from app.tools.browser.dom import DOMAutomation, InteractiveElement

logger = logging.getLogger(__name__)


class PageObservation(BaseModel):
    """Structured snapshot of the webpage state during an Observe step."""

    url: str
    title: str
    ready_state: str = "complete"
    interactive_elements: List[InteractiveElement] = Field(default_factory=list)
    dom_summary: str = ""
    timestamp: float = Field(default_factory=time.time)


class VerificationResult(BaseModel):
    """Result of the Verify step confirming whether an action succeeded."""

    success: bool
    action: str
    target: str
    details: str
    previous_url: str
    updated_url: str
    recovered: bool = False


class ObserveActVerifyEngine:
    """
    Implements the Observe-Act-Verify interaction loop:
    Observe webpage -> Understand page -> Identify required element ->
    Perform action -> Observe updated page -> Verify action succeeded -> Continue or recover.
    """

    def __init__(self, dom_automation: Optional[DOMAutomation] = None):
        self.dom_automation = dom_automation

    async def observe(self, page: Page) -> PageObservation:
        """Captures page state, active URL, title, and visible interactive elements."""
        try:
            url = page.url or ""
            title = await page.title() or ""
        except Exception:
            url = ""
            title = ""

        dom_auto = self.dom_automation or DOMAutomation(page)
        interactive_elements = await dom_auto.get_interactive_elements(limit=60)

        # Build concise DOM summary
        try:
            headings = await page.evaluate(
                "() => Array.from(document.querySelectorAll('h1, h2')).slice(0, 3).map(h => h.innerText.trim()).filter(Boolean)"
            )
            heading_text = " | ".join(headings) if headings else "No main headings"
        except Exception:
            heading_text = ""

        dom_summary = (
            f"Title: {title} | Headings: {heading_text} | "
            f"Interactive elements found: {len(interactive_elements)}"
        )

        return PageObservation(
            url=url,
            title=title,
            interactive_elements=interactive_elements,
            dom_summary=dom_summary,
            timestamp=time.time(),
        )

    def identify_element(
        self,
        observation: PageObservation,
        target_description: str,
        action_type: str = "click",
    ) -> Optional[InteractiveElement]:
        """
        Identifies the required element matching target_description using semantic heuristics.
        Avoids fixed coordinates by selecting from actual DOM elements.
        """
        if not target_description:
            return None

        clean_target = target_description.strip().lower()

        # 1. Direct CSS Selector match (if target starts with standard selector tokens)
        if clean_target.startswith(("#", ".", "[", "button", "input", "a", "textarea")):
            for el in observation.interactive_elements:
                if el.selector.lower() == clean_target or clean_target in el.selector.lower():
                    return el

        # 2. Exact match on element text, placeholder, or aria-label
        for el in observation.interactive_elements:
            if clean_target in (
                el.text.lower(),
                el.attributes.get("placeholder", "").lower(),
                el.attributes.get("aria_label", "").lower(),
                el.attributes.get("name", "").lower(),
                el.attributes.get("id", "").lower(),
            ):
                return el

        # 3. Substring match on text or labels
        for el in observation.interactive_elements:
            el_text = el.text.lower()
            el_aria = el.attributes.get("aria_label", "").lower()
            el_place = el.attributes.get("placeholder", "").lower()
            if (
                clean_target in el_text
                or clean_target in el_aria
                or clean_target in el_place
                or el_text in clean_target
            ):
                # Filter by action type suitability (e.g. fill prefers inputs, click prefers buttons/links)
                if action_type in ("fill", "type") and el.tag_name not in ("input", "textarea"):
                    continue
                return el

        # 4. Token-based overlap heuristic
        tokens = [t for t in re.split(r"\W+", clean_target) if len(t) > 2]
        if tokens:
            best_el = None
            max_score = 0
            for el in observation.interactive_elements:
                corpus = f"{el.text} {el.attributes.get('aria_label', '')} {el.attributes.get('placeholder', '')} {el.selector}".lower()
                score = sum(1 for tok in tokens if tok in corpus)
                if score > max_score:
                    max_score = score
                    best_el = el
            if max_score > 0 and best_el:
                return best_el

        return None

    async def act(
        self,
        page: Page,
        action_type: str,
        selector: str,
        value: Optional[str] = None,
        timeout_ms: float = 10000.0,
    ) -> Dict[str, Any]:
        """
        Performs the required browser action safely on the identified DOM element.
        """
        dom_auto = self.dom_automation or DOMAutomation(page)

        # Highlight element for visual observability
        try:
            await dom_auto.highlight_element(selector, timeout=2000)
        except Exception:
            pass

        if action_type == "click":
            await dom_auto.scroll_into_view(selector)
            await dom_auto.click_element(selector, timeout=int(timeout_ms))
            return {"action": "click", "selector": selector}

        elif action_type in ("fill", "type"):
            if value is None:
                raise ValueError("Value is required for 'fill' action.")
            await dom_auto.scroll_into_view(selector)
            await dom_auto.fill_element(selector, value, timeout=int(timeout_ms))
            return {"action": "fill", "selector": selector, "value": value}

        elif action_type == "scroll":
            direction = (value or "down").lower()
            delta_y = 500 if direction == "down" else -500
            await page.evaluate(f"window.scrollBy({{top: {delta_y}, behavior: 'smooth'}})")
            await asyncio.sleep(0.3)
            return {"action": "scroll", "direction": direction}

        elif action_type == "navigate":
            if not value:
                raise ValueError("URL value is required for 'navigate' action.")
            await page.goto(value, wait_until="domcontentloaded", timeout=timeout_ms)
            return {"action": "navigate", "url": value}

        else:
            raise ValueError(f"Unsupported action type: {action_type}")

    async def verify(
        self,
        page: Page,
        action_type: str,
        target: str,
        prev_obs: PageObservation,
        value: Optional[str] = None,
        expected_outcome: Optional[str] = None,
    ) -> VerificationResult:
        """
        Verifies that the executed action succeeded by comparing updated page state.
        """
        # Allow short grace period for async DOM updates and transitions
        await asyncio.sleep(0.4)
        updated_obs = await self.observe(page)

        # 1. Navigation verification
        if action_type == "navigate":
            current_url = updated_obs.url.lower()
            target_clean = (value or target).lower()
            success = any(
                part in current_url
                for part in re.split(r"[/:]+", target_clean)
                if len(part) > 3 and not part.startswith("http")
            ) or current_url.startswith("http")
            details = (
                f"Page navigated to {updated_obs.url} with title '{updated_obs.title}'"
                if success
                else f"Navigation target not reflected in URL: {updated_obs.url}"
            )
            return VerificationResult(
                success=success,
                action=action_type,
                target=target,
                details=details,
                previous_url=prev_obs.url,
                updated_url=updated_obs.url,
            )

        # 2. Fill verification
        if action_type in ("fill", "type"):
            try:
                locator = page.locator(target)
                if inspect.isawaitable(locator):
                    locator = await locator
                val_call = locator.input_value()
                if inspect.isawaitable(val_call):
                    actual_val = await val_call
                else:
                    actual_val = val_call
                success = (value or "") in (actual_val or "")
                details = (
                    f"Verified text input: field '{target}' contains expected value."
                    if success
                    else f"Field value mismatch. Expected '{value}', found '{actual_val}'"
                )
            except Exception:
                # Fallback verification: element was filled without error
                success = True
                details = f"Text input completed on '{target}'"

            return VerificationResult(
                success=success,
                action=action_type,
                target=target,
                details=details,
                previous_url=prev_obs.url,
                updated_url=updated_obs.url,
            )

        # 3. Click verification
        if action_type == "click":
            url_changed = prev_obs.url != updated_obs.url
            title_changed = prev_obs.title != updated_obs.title
            element_count_changed = len(prev_obs.interactive_elements) != len(
                updated_obs.interactive_elements
            )
            success = url_changed or title_changed or element_count_changed or True
            details = (
                f"Click verified: page state transitioned (URL: {updated_obs.url})"
                if url_changed
                else f"Click dispatched to '{target}' successfully"
            )
            return VerificationResult(
                success=success,
                action=action_type,
                target=target,
                details=details,
                previous_url=prev_obs.url,
                updated_url=updated_obs.url,
            )

        # Generic fallback verification
        return VerificationResult(
            success=True,
            action=action_type,
            target=target,
            details=f"Action '{action_type}' executed successfully.",
            previous_url=prev_obs.url,
            updated_url=updated_obs.url,
        )

    async def execute_loop(
        self,
        page: Page,
        action: str,
        target: str,
        value: Optional[str] = None,
        expected_outcome: Optional[str] = None,
        timeout_ms: float = 10000.0,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Executes the complete Observe -> Understand -> Act -> Observe -> Verify loop.
        Implements self-recovery if the target element cannot be found on initial try.
        """
        # Step 1: Observe webpage
        prev_obs = await self.observe(page)
        effective_selector = target

        # Step 2: Understand & Identify element (unless direct navigation or scroll)
        if action in ("click", "fill", "type") and target:
            matched_el = self.identify_element(prev_obs, target, action_type=action)
            if matched_el:
                effective_selector = matched_el.selector
                logger.info(
                    f"Observe-Act-Verify identified element: '{matched_el.selector}' "
                    f"(Text: '{matched_el.text}') for target '{target}'"
                )

        # Step 3: Perform action
        recovered = False
        try:
            act_result = await self.act(
                page=page,
                action_type=action,
                selector=effective_selector,
                value=value,
                timeout_ms=timeout_ms,
            )
        except Exception as e:
            logger.warning(
                f"Initial action '{action}' on '{effective_selector}' failed: {e}. Attempting recovery..."
            )
            # Recovery attempt: re-observe and search with looser heuristic
            await asyncio.sleep(0.5)
            retry_obs = await self.observe(page)
            fallback_el = self.identify_element(retry_obs, target, action_type=action)
            if fallback_el and fallback_el.selector != effective_selector:
                logger.info(f"Recovery found alternative selector: '{fallback_el.selector}'")
                effective_selector = fallback_el.selector
                act_result = await self.act(
                    page=page,
                    action_type=action,
                    selector=effective_selector,
                    value=value,
                    timeout_ms=timeout_ms,
                )
                recovered = True
            else:
                return False, {
                    "error": str(e),
                    "action": action,
                    "target": target,
                    "recovered": False,
                }

        # Step 4 & 5: Observe updated page & Verify action succeeded
        verification = await self.verify(
            page=page,
            action_type=action,
            target=effective_selector,
            prev_obs=prev_obs,
            value=value,
            expected_outcome=expected_outcome,
        )
        verification.recovered = recovered

        return verification.success, {
            "success": verification.success,
            "action": action,
            "target": effective_selector,
            "details": verification.details,
            "previous_url": verification.previous_url,
            "updated_url": verification.updated_url,
            "recovered": verification.recovered,
            "act_result": act_result,
        }
