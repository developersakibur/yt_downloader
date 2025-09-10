document.addEventListener("DOMContentLoaded", () => {
  // ===============================
  // Element references (DOM nodes)
  // ===============================
  const serverDown = document.getElementById("server-down");
  const startServerBtn = document.getElementById("start-server-btn");

  const notYoutube = document.getElementById("not-youtube");
  const goYoutube = document.getElementById("go-youtube");

  const unsupportedLink = document.getElementById("unsupported-link");

  const ytForm = document.getElementById("youtube-form");
  const quantityRow = document.getElementById("quantity-row");
  const playlistRow = document.getElementById("playlist-row");
  const downloadBtn = document.getElementById("download-btn");

  const logo = document.getElementById("logo");
  const statusMsg = document.getElementById("status");

  // ===============================
  // Utility Functions
  // ===============================

  /**
   * Hide all UI sections, then show only the given ones.
   */
  function showView(...viewsToShow) {
    [ytForm, notYoutube, serverDown, quantityRow, playlistRow, unsupportedLink].forEach((v) =>
      v.classList.add("hidden")
    );
    viewsToShow.forEach((v) => v.classList.remove("hidden"));
  }

  /**
   * Open the server tab if it's not already open.
   * Called only once when the server starts.
   */
  function openServerTabOnce() {
    chrome.tabs.query({ url: "*://yt_downloader.local/*" }, (tabs) => {
      if (tabs.length === 0) {
        chrome.tabs.create({ url: "http://yt_downloader.local/" });
      }
    });
  }

  /**
   * Focus on the server tab if it exists,
   * otherwise create it and make it active.
   * Triggered when user clicks on the logo.
   */
  function focusOrCreateServerTab() {
    chrome.tabs.query({ url: "*://yt_downloader.local/*" }, (tabs) => {
      if (tabs.length > 0) {
        chrome.tabs.update(tabs[0].id, { active: true });
        chrome.windows.update(tabs[0].windowId, { focused: true });
      } else {
        chrome.tabs.create({ url: "http://yt_downloader.local/" });
      }
    });
  }

  /**
   * Check if the backend server is running.
   * If yes → show correct view for current YouTube tab.
   * If no → show the "server down" message.
   */
  async function checkAndShowServer() {
    try {
      const res = await fetch("http://yt_downloader.local/api/status");
      if (!res.ok) {
        showView(serverDown);
        return false; // server responded but not OK
      }
      openServerTabOnce();
      checkCurrentTabAndShowView(); // show correct UI
      return true;
    } catch (e) {
      showView(serverDown); // network error or unreachable
      return false;
    }
  }

  /**
   * Detect current active tab and update UI accordingly.
   * - If not YouTube → show "Not YouTube" view
   * - If YouTube search → show form + quantity options
   * - If YouTube playlist → show form + playlist options
   * - Otherwise → show basic form
   */
function checkCurrentTabAndShowView() {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const currentUrl = tabs[0]?.url || "";

    // Not a YouTube domain
    if (!currentUrl.includes("youtube.com")) {
      showView(notYoutube);
      return;
    }

    statusMsg.textContent = "Ready";

    // Supported URL types
    if (currentUrl.includes("youtube.com/results?search_query=")) {
      showView(ytForm, quantityRow); // search
    } else if (currentUrl.includes("watch?v=") && currentUrl.includes("list=")) {
      showView(ytForm, playlistRow); // playlist
    } else if (currentUrl.includes("playlist") && currentUrl.includes("list=")) {
      showView(ytForm); // Orginal playlist
    } else if (currentUrl.includes("watch?v=")) {
      showView(ytForm); // single video
    } else if (currentUrl.includes("/shorts/")) {
      showView(ytForm); // shorts
    } else if (currentUrl.match(/youtube\.com\/@[^/]+$/)) {
      showView(ytForm); // channel
    } else if (currentUrl.match(/youtube\.com\/@[^/]+\/videos$/)) {
      showView(ytForm); // channel videos
    } else if (currentUrl.match(/youtube\.com\/@[^/]+\/shorts$/)) {
      showView(ytForm); // channel shorts
    } else {
      // Anything else → unsupported
      showView(unsupportedLink);
    }
  });
}


  // ===============================
  // Event Listeners
  // ===============================

  // Start server button → tell native app to launch backend
  startServerBtn.addEventListener("click", () => {
    chrome.runtime.sendNativeMessage(
      "com.sakib.ytdownloader",
      { action: "start_server" },
      (response) => {
        if (chrome.runtime.lastError) {
          console.error(chrome.runtime.lastError);
          statusMsg.textContent = "❌ Native host error.";
          return;
        }
        if (response && response.server_url) {
          openServerTabOnce(); // open server page once
        }
        statusMsg.textContent = "✅ Server start signal sent.";
      }
    );
  });

  // Download button → send request to backend with selected options
  downloadBtn.addEventListener("click", async () => {
    statusMsg.textContent = "Sending download request...";
    const [tab] = await chrome.tabs.query({
      active: true,
      currentWindow: true,
    });

    const body = JSON.stringify({
      url: tab.url,
      format: document.querySelector("input[name='format']:checked")?.value,
      quantity: document.querySelector("input[name='quantity']:checked")?.value,
      playlist: document.querySelector("input[name='playlist']:checked")?.value,
    });

    await fetch("http://yt_downloader.local/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    
  });

  // "Go to YouTube" button → focus existing YouTube tab, or open new one
  goYoutube.addEventListener("click", () => {
    chrome.tabs.query({ url: "*://*.youtube.com/*" }, (tabs) => {
      if (tabs.length > 0) {
        chrome.tabs.update(tabs[0].id, { active: true });
      } else {
        chrome.tabs.create({ url: "https://www.youtube.com/" });
      }
    });
  });

  // Logo → focus or open the yt_downloader.local tab
  logo.addEventListener("click", focusOrCreateServerTab);

  // ===============================
  // Initial Execution
  // ===============================
  checkAndShowServer(); // Run on extension load
});
