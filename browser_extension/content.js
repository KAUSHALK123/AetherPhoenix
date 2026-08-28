/**
 * Content script for AetherPhoenix Browser Extension.
 * Handles DOM operations directly within page context.
 */

console.log("[AetherPhoenix Extension] Content script loaded.");

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "inspect_element") {
    const el = document.querySelector(request.selector);
    if (!el) {
      sendResponse({ success: false, error: `Element not found: ${request.selector}` });
      return true;
    }
    sendResponse({
      success: true,
      data: {
        tagName: el.tagName,
        text: el.innerText,
        value: el.type === "password" ? "******" : el.value,
        attributes: Array.from(el.attributes).reduce((acc, attr) => {
          if (attr.name !== "value" || el.type !== "password") {
            acc[attr.name] = attr.value;
          }
          return acc;
        }, {}),
      },
    });
    return true;
  }
});
