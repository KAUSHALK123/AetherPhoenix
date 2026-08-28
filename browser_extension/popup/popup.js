document.addEventListener("DOMContentLoaded", async () => {
  const statusBadge = document.getElementById("statusBadge");
  const tabTitleEl = document.getElementById("tabTitle");
  const tabUrlEl = document.getElementById("tabUrl");

  // Check stored connection status
  chrome.storage.local.get(["extension_status"], (result) => {
    if (result.extension_status === "connected") {
      statusBadge.textContent = "Connected";
      statusBadge.className = "badge connected";
    } else {
      statusBadge.textContent = "Disconnected";
      statusBadge.className = "badge disconnected";
    }
  });

  // Query active tab info
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tabs.length > 0) {
      tabTitleEl.textContent = tabs[0].title || "Untitled";
      tabUrlEl.textContent = tabs[0].url || "";
    }
  } catch (err) {
    tabTitleEl.textContent = "Unable to read active tab";
  }
});
