/**
 * Background Service Worker for AetherPhoenix Browser Extension (Manifest V3)
 * Manages WebSocket connection to AetherPhoenix backend and handles browser automation APIs.
 */

const BACKEND_WS_URL = "ws://localhost:8000/api/v1/browser-extension/ws";
let ws = null;
let isConnected = false;
let reconnectTimer = null;

// Connect to AetherPhoenix Backend
function connectWebSocket() {
  if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) {
    return;
  }

  console.log("[AetherPhoenix Extension] Connecting to backend WebSocket:", BACKEND_WS_URL);

  try {
    ws = new WebSocket(BACKEND_WS_URL);

    ws.onopen = () => {
      console.log("[AetherPhoenix Extension] Connected to AetherPhoenix Backend.");
      isConnected = true;
      chrome.storage.local.set({ extension_status: "connected" });
      sendHeartbeat();
    };

    ws.onmessage = async (event) => {
      try {
        const command = JSON.parse(event.data);
        console.log("[AetherPhoenix Extension] Received command:", command);
        await handleCommand(command);
      } catch (err) {
        console.error("[AetherPhoenix Extension] Failed to parse/handle message:", err);
      }
    };

    ws.onclose = () => {
      console.warn("[AetherPhoenix Extension] WebSocket closed. Scheduling reconnect...");
      isConnected = false;
      chrome.storage.local.set({ extension_status: "disconnected" });
      scheduleReconnect();
    };

    ws.onerror = (err) => {
      console.error("[AetherPhoenix Extension] WebSocket error:", err);
      ws.close();
    };
  } catch (err) {
    console.error("[AetherPhoenix Extension] Failed to initialize WebSocket:", err);
    scheduleReconnect();
  }
}

function scheduleReconnect() {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(connectWebSocket, 5000);
}

// Periodic heartbeat & status update
async function sendHeartbeat() {
  if (!isConnected || !ws || ws.readyState !== WebSocket.OPEN) return;

  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    const activeTab = tabs.length > 0 ? tabs[0] : null;

    const payload = {
      type: "heartbeat",
      active_tab_url: activeTab ? activeTab.url : null,
      active_tab_title: activeTab ? activeTab.title : null,
      timestamp: Date.now() / 1000.0,
    };

    ws.send(JSON.stringify(payload));
  } catch (err) {
    console.error("[AetherPhoenix Extension] Error sending heartbeat:", err);
  }
}

// Send command response back to backend
function sendResponse(commandId, success, data = null, error = null) {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;

  const responsePayload = {
    command_id: commandId,
    success: success,
    data: data,
    error: error,
    timestamp: Date.now() / 1000.0,
  };

  ws.send(JSON.stringify(responsePayload));
}

// Command Handler
async function handleCommand(command) {
  const { command_id, action, parameters = {} } = command;

  try {
    switch (action) {
      case "detect_active_tab": {
        const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tabs.length === 0) {
          sendResponse(command_id, false, null, "No active tab detected");
          return;
        }
        const activeTab = tabs[0];
        sendResponse(command_id, true, {
          tab_id: activeTab.id,
          window_id: activeTab.windowId,
          url: activeTab.url,
          title: activeTab.title,
          favIconUrl: activeTab.favIconUrl,
        });
        break;
      }

      case "read_page_info": {
        const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tabs.length === 0) {
          sendResponse(command_id, false, null, "No active tab to read");
          return;
        }
        const tab = tabs[0];
        sendResponse(command_id, true, {
          tab_id: tab.id,
          url: tab.url,
          title: tab.title,
          status: tab.status,
        });
        break;
      }

      case "navigate": {
        const { url } = parameters;
        if (!url) {
          sendResponse(command_id, false, null, "URL parameter is required for navigate");
          return;
        }
        const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
        let updatedTab;
        if (tabs.length > 0) {
          updatedTab = await chrome.tabs.update(tabs[0].id, { url: url });
        } else {
          updatedTab = await chrome.tabs.create({ url: url, active: true });
        }
        sendResponse(command_id, true, {
          tab_id: updatedTab.id,
          url: url,
          status: "navigating",
        });
        break;
      }

      case "open_new_tab": {
        const { url = "about:blank", active = true } = parameters;
        const newTab = await chrome.tabs.create({ url: url, active: active });
        sendResponse(command_id, true, {
          tab_id: newTab.id,
          url: newTab.url,
          status: "opened",
        });
        break;
      }

      case "extract_content": {
        const { include_html = false, selector } = parameters;
        const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tabs.length === 0) {
          sendResponse(command_id, false, null, "No active tab to extract content from");
          return;
        }
        const activeTab = tabs[0];

        const results = await chrome.scripting.executeScript({
          target: { tabId: activeTab.id },
          func: (incHtml, sel) => {
            if (sel) {
              const el = document.querySelector(sel);
              if (!el) return { error: `Element not found: ${sel}` };
              return { content: incHtml ? el.outerHTML : el.innerText };
            }
            return { content: incHtml ? document.documentElement.outerHTML : document.body.innerText };
          },
          args: [include_html, selector || null],
        });

        if (results && results[0] && results[0].result) {
          const resObj = results[0].result;
          if (resObj.error) {
            sendResponse(command_id, false, null, resObj.error);
          } else {
            sendResponse(command_id, true, { content: resObj.content });
          }
        } else {
          sendResponse(command_id, false, null, "Extraction returned empty response");
        }
        break;
      }

      case "interact": {
        const { selector, interaction_action = "click", value = null } = parameters;
        const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tabs.length === 0) {
          sendResponse(command_id, false, null, "No active tab for element interaction");
          return;
        }
        const activeTab = tabs[0];

        const results = await chrome.scripting.executeScript({
          target: { tabId: activeTab.id },
          func: (sel, act, val) => {
            const el = document.querySelector(sel);
            if (!el) return { success: false, error: `Element '${sel}' not found` };

            if (act === "click") {
              el.click();
              return { success: true, action: "click", selector: sel };
            } else if (act === "fill") {
              el.value = val;
              el.dispatchEvent(new Event("input", { bubbles: true }));
              el.dispatchEvent(new Event("change", { bubbles: true }));
              return { success: true, action: "fill", selector: sel };
            } else if (act === "submit") {
              if (el.form) {
                el.form.submit();
              } else {
                el.click();
              }
              return { success: true, action: "submit", selector: sel };
            }
            return { success: false, error: `Unsupported interaction action: ${act}` };
          },
          args: [selector, interaction_action, value],
        });

        if (results && results[0] && results[0].result) {
          const resObj = results[0].result;
          if (resObj.success) {
            sendResponse(command_id, true, resObj);
          } else {
            sendResponse(command_id, false, null, resObj.error);
          }
        } else {
          sendResponse(command_id, false, null, "Interaction script returned no result");
        }
        break;
      }

      default:
        sendResponse(command_id, false, null, `Unknown browser action: ${action}`);
        break;
    }
  } catch (err) {
    console.error(`[AetherPhoenix Extension] Exception executing action '${action}':`, err);
    sendResponse(command_id, false, null, err.toString());
  }
}

// Initial connection
connectWebSocket();
setInterval(sendHeartbeat, 15000);
