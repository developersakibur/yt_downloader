document.addEventListener("DOMContentLoaded", () => {
  const serverDown = document.getElementById("server-down");
  const startServerBtn = document.getElementById("start-server-btn");

  const notYoutube = document.getElementById("not-youtube");
  const goYoutube = document.getElementById("go-youtube");

  const ytForm = document.getElementById("youtube-form");
  const quantityRow = document.getElementById("quantity-row");
  const playlistRow = document.getElementById("playlist-row");
  const downloadBtn = document.getElementById("download-btn");

  const statusMsg = document.getElementById("status");

  function showView(...viewsToShow) {
    [ytForm, notYoutube, serverDown, quantityRow, playlistRow].forEach((v) =>
      v.classList.add("hidden")
    );
    viewsToShow.forEach((v) => v.classList.remove("hidden"));
  }

  async function checkAndShowServer() {
    try {
      const res = await fetch("http://yt_downloader.local/api/status");
      if (!res.ok) {
        showView(serverDown);
        return false; // server responded but not OK
      }
      checkCurrentTabAndShowView();
      return true; // server is running
    } catch (e) {
      showView(serverDown); // network error or unreachable
      return false;
    }
  }

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
          chrome.tabs.create({ url: response.server_url });
        }
        statusMsg.textContent = "✅ Server start signal sent.";
      }
    );
  });

  function checkCurrentTabAndShowView() {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const currentUrl = tabs[0]?.url || "";

      if (!currentUrl.includes("youtube.com")) {
        showView(notYoutube);
        return;
      }

      statusMsg.textContent = "Ready";

      if (currentUrl.includes("youtube.com/results?search_query=")) {
        showView(ytForm, quantityRow);
      } else if (
        currentUrl.includes("watch?v=") &&
        currentUrl.includes("list=")
      ) {
        showView(ytForm, playlistRow);
      } else {
        showView(ytForm);
      }
    });
  }

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

  goYoutube.addEventListener("click", () => {
    // Query all tabs with YouTube URLs
    chrome.tabs.query({ url: "*://*.youtube.com/*" }, (tabs) => {
      if (tabs.length > 0) {
        // Focus the first YouTube tab
        chrome.tabs.update(tabs[0].id, { active: true });
      } else {
        // No YouTube tab found, open a new one
        chrome.tabs.create({ url: "https://www.youtube.com/" });
      }
    });
  });

  checkAndShowServer();

  // all your code here
});
